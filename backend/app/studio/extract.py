"""
Reading text out of an uploaded file, safely. Supported: PDF, DOCX, PPTX, TXT, MD.

Safeguards: size limit (checked while reading), file type checked by extension AND by the first bytes, zip containers are refused when
they would unpack to something huge ("zip bomb"), PDFs are limited in pages and refused when encrypted, the whole job has a time limit,
and macros/scripts inside Office files are never executed (the libraries only read text).
Scanned pages without selectable text give no text; the student is told so instead of being given an empty pack.
"""
import asyncio
import io
import zipfile

from app.config import settings

ALLOWED = (".pdf", ".docx", ".pptx", ".txt", ".md")
MAX_UNPACKED_BYTES = 60 * 1024 * 1024


class ExtractError(Exception):
    def __init__(self, message: str, code: str = "bad_file"):
        super().__init__(message)
        self.message, self.code = message, code


def _ext(name: str) -> str:
    name = (name or "").lower().strip()
    for e in ALLOWED:
        if name.endswith(e):
            return e
    raise ExtractError("This file type is not supported. Please use PDF, DOCX, PPTX, TXT or MD, or paste the text.", "type")


def _check_zip(data: bytes) -> zipfile.ZipFile:
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ExtractError("This file looks damaged or is not a real Office file.")
    total = sum(i.file_size for i in z.infolist())
    if total > MAX_UNPACKED_BYTES or len(z.infolist()) > 3000:
        raise ExtractError("This file is far too large once opened, so it was refused.", "too_big")
    return z


def _pdf(data: bytes) -> str:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError
    try:
        r = PdfReader(io.BytesIO(data))
        if r.is_encrypted:
            raise ExtractError("This PDF is password protected. Remove the password and upload it again.")
        if len(r.pages) > settings.studio_max_pdf_pages:
            raise ExtractError(f"This PDF has {len(r.pages)} pages. The limit is {settings.studio_max_pdf_pages}. Please split it.", "too_big")
        out, n = [], 0
        for page in r.pages:
            t = page.extract_text() or ""
            out.append(t)
            n += len(t)
            if n > settings.studio_max_chars * 3:
                break
        return "\n\n".join(out)
    except ExtractError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, OSError, AssertionError, RecursionError):
        raise ExtractError("This PDF could not be read. It may be damaged.")


def _docx(data: bytes) -> str:
    _check_zip(data)
    import docx
    try:
        d = docx.Document(io.BytesIO(data))
    except Exception:
        raise ExtractError("This Word file could not be read.")
    parts = [p.text for p in d.paragraphs if p.text.strip()]
    for t in d.tables:
        for row in t.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells if c.text.strip()))
    return "\n".join(parts)


def _pptx(data: bytes) -> str:
    _check_zip(data)
    from pptx import Presentation
    try:
        prs = Presentation(io.BytesIO(data))
    except Exception:
        raise ExtractError("This PowerPoint file could not be read.")
    out = []
    for i, slide in enumerate(prs.slides, 1):
        lines = []
        for sh in slide.shapes:
            if getattr(sh, "has_text_frame", False) and sh.has_text_frame:
                lines += [p.text for p in sh.text_frame.paragraphs if p.text.strip()]
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
            n = slide.notes_slide.notes_text_frame.text.strip()
            if n:
                lines.append(n)
        if lines:
            out.append(f"Slide {i}\n" + "\n".join(lines))
    return "\n\n".join(out)


def _text(data: bytes) -> str:
    if b"\x00" in data[:4096]:
        raise ExtractError("This file is not plain text.")
    for enc in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeError:
            continue
    raise ExtractError("This text file could not be read.")


def _sniff(ext: str, data: bytes) -> None:
    if ext == ".pdf" and not data[:1024].lstrip().startswith(b"%PDF"):
        raise ExtractError("This file is not a real PDF.")
    if ext in (".docx", ".pptx") and not data.startswith(b"PK"):
        raise ExtractError("This file is not a real Office file.")


def extract_sync(filename: str, data: bytes) -> str:
    ext = _ext(filename)
    if len(data) > settings.studio_max_upload_mb * 1024 * 1024:
        raise ExtractError(f"The file is larger than {settings.studio_max_upload_mb} MB.", "too_big")
    if not data:
        raise ExtractError("The file is empty.")
    _sniff(ext, data)
    return {".pdf": _pdf, ".docx": _docx, ".pptx": _pptx, ".txt": _text, ".md": _text}[ext](data)


async def extract(filename: str, data: bytes) -> str:
    try:
        return await asyncio.wait_for(asyncio.to_thread(extract_sync, filename, data), timeout=settings.studio_extract_seconds)
    except asyncio.TimeoutError:
        raise ExtractError("Reading this file took too long, so it was stopped. Try a smaller file.", "timeout")
