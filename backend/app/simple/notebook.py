"""
My Notebook API: notes (write, edit, search, download as PDF or Word) and documents (store, view, download, rename, delete).

    /notebook/notes            GET (?q= search), POST
    /notebook/notes/{id}       GET, PATCH, DELETE;   /notebook/notes/{id}/download?format=pdf|docx
    /notebook/documents        GET, POST (multipart upload)
    /notebook/documents/{id}   PATCH (rename), DELETE;   /download, /view (the file itself), /text (readable text for the preview and the quiz)

Notes and documents are saved in the database under the student's account, so they are still there after logging out and in.
Every query is filtered by the student's id; another student's id returns 404, never the content.
"""
import asyncio
import io
import uuid
from datetime import datetime, timezone
from typing import Optional
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.sanitize import clean_text
from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import User
from app.ratelimit import LoginRateLimiter
from app.studio import extract as EX

from .models import SDocument, SNote

router = APIRouter(prefix="/notebook", tags=["notebook"])
_write_limit = LoginRateLimiter(max_failures=200, window_seconds=600)
_upload_limit = LoginRateLimiter(max_failures=30, window_seconds=600)
_export_limit = LoginRateLimiter(max_failures=40, window_seconds=600)
DOC_TYPES = (".pdf", ".docx", ".pptx", ".txt")
MIME = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation", ".txt": "text/plain; charset=utf-8"}
MAX_NOTES = 500
MAX_DOCS = 40
MAX_NOTE_CHARS = 60_000


def _rate(limiter: LoginRateLimiter, user: User) -> None:
    wait = limiter.retry_after(str(user.id))
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Please wait a moment.", headers={"Retry-After": str(wait)})
    limiter.record_failure(str(user.id))


# ---------------------------------------------------------------- notes
class NoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(default="", max_length=MAX_NOTE_CHARS)

    @field_validator("title")
    @classmethod
    def _title(cls, v: str) -> str:
        v = " ".join(clean_text(v, 200).split())
        if not v:
            raise ValueError("Give your note a title")
        return v[:120]

    @field_validator("body")
    @classmethod
    def _body(cls, v: str) -> str:
        # A note is the student's own text: keep line breaks and spacing, remove only control and hidden characters.
        v = v.replace("\r\n", "\n").replace("\r", "\n")
        return "".join(ch for ch in v if ch in "\n\t" or (ord(ch) >= 32 and ch not in "​‌‍⁠﻿‪‫‬‭‮" and ord(ch) != 127))


class NotePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    body: Optional[str] = Field(default=None, max_length=MAX_NOTE_CHARS)

    @field_validator("title")
    @classmethod
    def _title(cls, v):
        return None if v is None else NoteIn._title(v)

    @field_validator("body")
    @classmethod
    def _body(cls, v):
        return None if v is None else NoteIn._body(v)


def note_out(n: SNote, full: bool = True) -> dict:
    out = {"id": str(n.id), "title": n.title, "created_at": n.created_at.isoformat(), "updated_at": n.updated_at.isoformat(),
           "preview": " ".join(n.body.split())[:120]}
    if full:
        out["body"] = n.body
    return out


async def _own_note(db: AsyncSession, user: User, note_id: uuid.UUID) -> SNote:
    n = await db.get(SNote, note_id)
    if n is None or n.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")
    return n


def _like(q: str) -> str:
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


@router.get("/notes")
async def list_notes(q: str = Query(default="", max_length=100), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    stmt = select(SNote).where(SNote.user_id == user.id)
    q = " ".join(q.split())
    if q:
        pat = _like(q.lower())
        stmt = stmt.where(or_(func.lower(SNote.title).like(pat, escape="\\"), func.lower(SNote.body).like(pat, escape="\\")))
    rows = (await db.execute(stmt.order_by(SNote.updated_at.desc()).limit(300))).scalars()
    return {"notes": [note_out(n, full=False) for n in rows], "query": q}


@router.post("/notes", status_code=status.HTTP_201_CREATED)
async def create_note(body: NoteIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    _rate(_write_limit, user)
    if int(await db.scalar(select(func.count()).select_from(SNote).where(SNote.user_id == user.id)) or 0) >= MAX_NOTES:
        raise HTTPException(status.HTTP_409_CONFLICT, "You have many notes already. Please delete some you no longer need.")
    n = SNote(user_id=user.id, title=body.title, body=body.body)
    db.add(n)
    await db.commit()
    return note_out(n)


@router.get("/notes/{note_id}")
async def get_note(note_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    return note_out(await _own_note(db, user, note_id))


@router.patch("/notes/{note_id}")
async def edit_note(note_id: uuid.UUID, body: NotePatch, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    _rate(_write_limit, user)
    n = await _own_note(db, user, note_id)
    if body.title is None and body.body is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Nothing to change")
    if body.title is not None:
        n.title = body.title
    if body.body is not None:
        n.body = body.body
    n.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return note_out(n)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    n = await _own_note(db, user, note_id)
    await db.delete(n)
    await db.commit()


def _file_stem(title: str) -> str:
    keep = "".join(c if (c.isalnum() or c in " -_") else "_" for c in title).strip().replace(" ", "_")
    return (keep or "note")[:60]


def content_disposition(kind: str, filename: str) -> str:
    """attachment/inline with a plain ASCII fallback name plus the real (UTF-8) name, so any language works and no header can be broken."""
    from urllib.parse import quote
    ascii_name = "".join(c if (c.isascii() and (c.isalnum() or c in " .-_()")) else "_" for c in filename)[:150] or "file"
    return f"{kind}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename[:150], safe='')}"


def note_to_pdf(title: str, body: str) -> bytes:
    """A plain, readable A4 page. Standard PDF fonts only: letters outside Western European languages become '?'."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    def pdf_text(s: str) -> str:
        return escape(s.encode("cp1252", "replace").decode("cp1252"))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm, title=pdf_text(title)[:120], author="MindSync")
    h = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=10)
    b = ParagraphStyle("b", fontName="Helvetica", fontSize=11, leading=16, spaceAfter=6)
    parts = [Paragraph(pdf_text(title), h), Spacer(1, 4)]
    for para in body.split("\n"):
        parts.append(Paragraph(pdf_text(para).replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;") or "&nbsp;", b))
    doc.build(parts)
    return buf.getvalue()


def note_to_docx(title: str, body: str) -> bytes:
    import docx
    d = docx.Document()
    d.core_properties.author = "MindSync"
    d.core_properties.title = title[:120]
    d.add_heading(title, level=1)

    def clean(s: str) -> str:                                                           # XML cannot hold control characters
        return "".join(ch for ch in s if ch == "\t" or ord(ch) >= 32)
    for para in body.split("\n"):
        d.add_paragraph(clean(para))
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


@router.get("/notes/{note_id}/download")
async def download_note(note_id: uuid.UUID, format: str = Query(pattern="^(pdf|docx)$"), user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)) -> Response:
    _rate(_export_limit, user)
    n = await _own_note(db, user, note_id)
    build = note_to_pdf if format == "pdf" else note_to_docx
    data = await asyncio.to_thread(build, n.title, n.body)
    mime = MIME[".pdf"] if format == "pdf" else MIME[".docx"]
    return Response(content=data, media_type=mime, headers={"Content-Disposition": content_disposition("attachment", f"{_file_stem(n.title)}.{format}")})


# ---------------------------------------------------------------- documents
class RenameIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def _n(cls, v: str) -> str:
        v = clean_text(v.replace("\\", "/").split("/")[-1], 200)
        if not v or v in (".", ".."):
            raise ValueError("Give the document a name")
        return v


def doc_out(d: SDocument) -> dict:
    return {"id": str(d.id), "name": d.name, "ext": d.ext, "size": d.size, "created_at": d.created_at.isoformat(), "can_view_text": True}


async def _own_doc(db: AsyncSession, user: User, doc_id: uuid.UUID) -> SDocument:
    d = await db.get(SDocument, doc_id)
    if d is None or d.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return d


def _ext(name: str) -> str:
    low = name.lower()
    for e in DOC_TYPES:
        if low.endswith(e):
            return e
    return ""


@router.get("/documents")
async def list_documents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    rows = (await db.execute(select(SDocument.id, SDocument.name, SDocument.ext, SDocument.size, SDocument.created_at)
                             .where(SDocument.user_id == user.id).order_by(SDocument.created_at.desc()))).all()
    return {"documents": [{"id": str(r.id), "name": r.name, "ext": r.ext, "size": r.size, "created_at": r.created_at.isoformat()} for r in rows],
            "max_mb": settings.simple_doc_max_mb, "types": list(DOC_TYPES)}


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    _rate(_upload_limit, user)
    name = clean_text((file.filename or "").replace("\\", "/").split("/")[-1], 200)
    ext = _ext(name)
    if not name or not ext:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Please upload a PDF, Word (.docx), PowerPoint (.pptx) or text (.txt) file.")
    limit = settings.simple_doc_max_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"This file is larger than {settings.simple_doc_max_mb} MB.")
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "The file is empty.")
    try:
        EX._sniff(ext, data)                                   # the content must really be that kind of file, not only end with its name
    except EX.ExtractError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, e.message)
    if int(await db.scalar(select(func.count()).select_from(SDocument).where(SDocument.user_id == user.id)) or 0) >= MAX_DOCS:
        raise HTTPException(status.HTTP_409_CONFLICT, f"You can keep {MAX_DOCS} documents. Please delete one you no longer need.")
    d = SDocument(user_id=user.id, name=name, ext=ext, size=len(data), data=data)
    db.add(d)
    await db.commit()
    return doc_out(d)


@router.patch("/documents/{doc_id}")
async def rename_document(doc_id: uuid.UUID, body: RenameIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    d = await _own_doc(db, user, doc_id)
    new = body.name
    if _ext(new) != d.ext:                                     # the file type never changes by renaming
        new = new + d.ext
    d.name = new[:200]
    await db.commit()
    return doc_out(d)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    d = await _own_doc(db, user, doc_id)
    await db.delete(d)
    await db.commit()


def _file_response(d: SDocument, inline: bool) -> Response:
    # nosniff + attachment (or a PDF shown by the browser's own viewer) so an uploaded file can never run as a web page
    return Response(content=d.data, media_type=MIME[d.ext],
                    headers={"Content-Disposition": content_disposition("inline" if inline and d.ext == ".pdf" else "attachment", d.name)})


@router.get("/documents/{doc_id}/download")
async def download_document(doc_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Response:
    return _file_response(await _own_doc(db, user, doc_id), inline=False)


@router.get("/documents/{doc_id}/view")
async def view_document(doc_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Response:
    return _file_response(await _own_doc(db, user, doc_id), inline=True)


@router.get("/documents/{doc_id}/text")
async def document_text(doc_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    """The readable text of a document: shown when viewing Word or PowerPoint files and used to make a quiz."""
    d = await _own_doc(db, user, doc_id)
    try:
        text = await EX.extract(d.name, d.data)
    except EX.ExtractError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": e.code, "message": e.message})
    text = "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())
    text = clean_text(text, 400_000)
    if len(text) < 20:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "no_text", "message": "No readable text was found in this document. Scanned pages and pictures cannot be read."})
    return {"id": str(d.id), "name": d.name, "text": text, "chars": len(text)}
