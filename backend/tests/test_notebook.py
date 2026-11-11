"""My Notebook: notes (CRUD, search, PDF and Word download) and documents (store, view, download, rename, delete, text, quiz source)."""
import io
import zipfile

import pytest

from app.ai import service as ai_service
from app.ai.provider import MockProvider
from app.config import settings
from tests.test_studio import SOURCE, fake_pack, make_docx, make_pdf, make_pptx


def H(u):
    return u["headers"]


def note(api, u, title="Biology", body="Cells have a nucleus.\nSecond line."):
    r = api.client.post("/notebook/notes", json={"title": title, "body": body}, headers=H(u))
    assert r.status_code == 201, r.text
    return r.json()


def upload(api, u, name, data, ctype="application/octet-stream"):
    return api.client.post("/notebook/documents", files={"file": (name, data, ctype)}, headers=H(u))


# ------------------------------------------------------------------ notes
def test_create_read_edit_delete_a_note(api):
    u = api.register()
    n = note(api, u, "  My   first note ", "Line one\r\nLine two\x00\x07 with control characters")
    assert n["title"] == "My first note" and n["body"] == "Line one\nLine two with control characters"
    got = api.client.get(f"/notebook/notes/{n['id']}", headers=H(u)).json()
    assert got["body"] == n["body"]
    e = api.client.patch(f"/notebook/notes/{n['id']}", json={"title": "Renamed", "body": "New text\n\n  indented"}, headers=H(u))
    assert e.status_code == 200 and e.json()["title"] == "Renamed" and e.json()["body"] == "New text\n\n  indented"
    assert api.client.patch(f"/notebook/notes/{n['id']}", json={}, headers=H(u)).status_code == 422
    assert api.client.patch(f"/notebook/notes/{n['id']}", json={"title": "  "}, headers=H(u)).status_code == 422
    assert api.client.delete(f"/notebook/notes/{n['id']}", headers=H(u)).status_code == 204
    assert api.client.get(f"/notebook/notes/{n['id']}", headers=H(u)).status_code == 404
    assert api.client.get("/notebook/notes", headers=H(u)).json()["notes"] == []


def test_note_validation(api):
    u = api.register()
    for bad in ({"title": ""}, {"title": "x" * 121 + ""}, {"title": "ok", "body": "y" * 60_001}, {"title": "ok", "extra": 1}, {"body": "no title"}):
        assert api.client.post("/notebook/notes", json=bad, headers=H(u)).status_code == 422, bad
    assert api.client.post("/notebook/notes", json={"title": "ok"}, headers=H(u)).status_code == 201     # an empty body is allowed
    assert api.client.post("/notebook/notes", json={"title": "ok"}).status_code == 401


def test_notes_are_stored_as_plain_text_never_run_as_html(api):
    u = api.register()
    n = note(api, u, "<b>x</b>", "<script>alert(1)</script>")
    assert n["body"] == "<script>alert(1)</script>"         # kept as the student typed it; the page shows it as text, never as markup
    r = api.client.get(f"/notebook/notes/{n['id']}", headers=H(u))
    assert r.headers["content-type"].startswith("application/json") and r.headers["x-content-type-options"] == "nosniff"


def test_search_notes_by_title_and_text_case_insensitive_and_literal(api):
    u = api.register()
    note(api, u, "Biology cells", "Mitochondria make energy")
    note(api, u, "History", "The Roman Empire fell. 100% sure_ish")
    note(api, u, "Maths", "Algebra")

    def find(q):
        return sorted(n["title"] for n in api.client.get("/notebook/notes", params={"q": q}, headers=H(u)).json()["notes"])
    assert find("biology") == ["Biology cells"]
    assert find("MITOCHONDRIA") == ["Biology cells"]
    assert find("roman") == ["History"]
    assert find("100%") == ["History"] and find("sure_") == ["History"]          # % and _ are normal letters, not wildcards
    assert find("%") == ["History"] and find("_") == ["History"]
    assert find("nothing here") == []
    assert find("") == ["Biology cells", "History", "Maths"]
    assert find("'; DROP TABLE s_notes; --") == []
    assert api.client.get("/notebook/notes", params={"q": "x" * 101}, headers=H(u)).status_code == 422


def test_notes_are_listed_newest_edit_first(api):
    u = api.register()
    a, b = note(api, u, "A"), note(api, u, "B")
    api.client.patch(f"/notebook/notes/{a['id']}", json={"body": "edited"}, headers=H(u))
    assert [n["title"] for n in api.client.get("/notebook/notes", headers=H(u)).json()["notes"]] == ["A", "B"]


def test_download_note_as_pdf_and_word(api):
    u = api.register()
    n = note(api, u, "Study / notes: week 1?", "Café crème – naïve façade\nSecond line with <tags> & ampersand\n\tTabbed\n" + "word " * 2000)
    pdf = api.client.get(f"/notebook/notes/{n['id']}/download", params={"format": "pdf"}, headers=H(u))
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF") and pdf.headers["content-type"] == "application/pdf"
    cd = pdf.headers["content-disposition"]
    assert cd.startswith("attachment") and '.pdf"' in cd and "/" not in cd.split("filename=")[1].split(";")[0] and "?" not in cd
    from pypdf import PdfReader
    text = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "Study / notes" in text and "Second line" in text and "&" in text and len(PdfReader(io.BytesIO(pdf.content)).pages) >= 2
    word = api.client.get(f"/notebook/notes/{n['id']}/download", params={"format": "docx"}, headers=H(u))
    assert word.status_code == 200 and word.content[:2] == b"PK" and '.docx"' in word.headers["content-disposition"]
    import docx
    d = docx.Document(io.BytesIO(word.content))
    assert d.paragraphs[0].text.startswith("Study / notes") and any("Café crème" in p.text for p in d.paragraphs)
    assert api.client.get(f"/notebook/notes/{n['id']}/download", params={"format": "exe"}, headers=H(u)).status_code == 422
    assert api.client.get(f"/notebook/notes/{n['id']}/download", headers=H(u)).status_code == 422


def test_download_works_for_text_the_pdf_font_cannot_draw(api):
    u = api.register()
    n = note(api, u, "Urdu سلام", "مرحبا Hello 你好")
    assert api.client.get(f"/notebook/notes/{n['id']}/download", params={"format": "pdf"}, headers=H(u)).status_code == 200
    assert api.client.get(f"/notebook/notes/{n['id']}/download", params={"format": "docx"}, headers=H(u)).status_code == 200


def test_students_cannot_touch_each_others_notes(api):
    a, b = api.register(), api.register()
    n = note(api, a)
    nid = n["id"]
    assert api.client.get(f"/notebook/notes/{nid}", headers=H(b)).status_code == 404
    assert api.client.patch(f"/notebook/notes/{nid}", json={"title": "x"}, headers=H(b)).status_code == 404
    assert api.client.delete(f"/notebook/notes/{nid}", headers=H(b)).status_code == 404
    assert api.client.get(f"/notebook/notes/{nid}/download", params={"format": "pdf"}, headers=H(b)).status_code == 404
    assert api.client.get("/notebook/notes", params={"q": "Cells"}, headers=H(b)).json()["notes"] == []
    assert api.client.get(f"/notebook/notes/{nid}", headers=H(a)).status_code == 200


def test_notes_survive_logout_and_login(api):
    u = api.register()
    note(api, u, "Keep me", "important")
    h = {"Authorization": f"Bearer {api.client.post('/auth/login', json={'email': u['email'], 'password': u['password']}).json()['access_token']}"}
    assert [n["title"] for n in api.client.get("/notebook/notes", headers=h).json()["notes"]] == ["Keep me"]


# ------------------------------------------------------------------ documents
FILES = {"a.txt": b"Plain text study material. " * 20, "b.pdf": make_pdf("Photosynthesis in chloroplasts"), "c.docx": make_docx("Word text here, long enough to read"),
         "d.pptx": make_pptx("Slide text about the Calvin cycle")}


def test_upload_list_view_download_rename_delete_each_type(api):
    u = api.register()
    ids = {}
    for name, data in FILES.items():
        r = upload(api, u, name, data)
        assert r.status_code == 201, (name, r.text)
        assert r.json()["name"] == name and r.json()["size"] == len(data)
        ids[name] = r.json()["id"]
    docs = api.client.get("/notebook/documents", headers=H(u)).json()
    assert sorted(d["name"] for d in docs["documents"]) == sorted(FILES) and docs["max_mb"] == settings.simple_doc_max_mb
    for name, did in ids.items():
        dl = api.client.get(f"/notebook/documents/{did}/download", headers=H(u))
        assert dl.status_code == 200 and dl.content == FILES[name]                                 # byte for byte
        assert dl.headers["content-disposition"].startswith("attachment") and dl.headers["x-content-type-options"] == "nosniff"
        assert "default-src 'none'" in dl.headers["content-security-policy"]
    view = api.client.get(f"/notebook/documents/{ids['b.pdf']}/view", headers=H(u))
    assert view.headers["content-disposition"].startswith("inline") and view.headers["content-type"] == "application/pdf"
    assert api.client.get(f"/notebook/documents/{ids['c.docx']}/view", headers=H(u)).headers["content-disposition"].startswith("attachment")
    txt = api.client.get(f"/notebook/documents/{ids['d.pptx']}/text", headers=H(u)).json()
    assert "Calvin cycle" in txt["text"]
    ren = api.client.patch(f"/notebook/documents/{ids['a.txt']}", json={"name": "Week 1 summary"}, headers=H(u))
    assert ren.status_code == 200 and ren.json()["name"] == "Week 1 summary.txt"                 # the file type is kept
    assert api.client.patch(f"/notebook/documents/{ids['a.txt']}", json={"name": "../../etc/passwd.txt"}, headers=H(u)).json()["name"] == "passwd.txt"
    assert api.client.patch(f"/notebook/documents/{ids['a.txt']}", json={"name": "  "}, headers=H(u)).status_code == 422
    for did in ids.values():
        assert api.client.delete(f"/notebook/documents/{did}", headers=H(u)).status_code == 204
        assert api.client.get(f"/notebook/documents/{did}/download", headers=H(u)).status_code == 404
    assert api.client.get("/notebook/documents", headers=H(u)).json()["documents"] == []


def test_upload_refuses_wrong_empty_fake_and_oversized_files(api, monkeypatch):
    u = api.register()
    assert upload(api, u, "virus.exe", b"MZ" + b"\x00" * 100).status_code == 422
    assert upload(api, u, "page.html", b"<script>alert(1)</script>").status_code == 422
    assert upload(api, u, "noext", b"hello").status_code == 422
    assert upload(api, u, "empty.txt", b"").status_code == 422
    assert upload(api, u, "fake.pdf", b"this is not a pdf at all").status_code == 422
    assert upload(api, u, "fake.docx", b"this is not an office file").status_code == 422
    assert upload(api, u, "trick.txt.exe", b"abc").status_code == 422
    monkeypatch.setattr(settings, "simple_doc_max_mb", 1)
    assert upload(api, u, "big.txt", b"a" * (1024 * 1024 + 5)).status_code == 413
    assert upload(api, u, "ok.txt", b"a" * 2000).status_code == 201
    assert api.client.post("/notebook/documents", headers=H(u)).status_code == 422
    assert api.client.post("/notebook/documents", files={"file": ("a.txt", b"abc" * 10)}).status_code == 401


def test_filename_tricks_are_neutralised(api):
    u = api.register()
    r = upload(api, u, "../../../etc/passwd.txt", b"text " * 10)
    assert r.status_code == 201 and r.json()["name"] == "passwd.txt"
    r = upload(api, u, 'evil"; filename="x.exe.txt', b"text " * 10)
    did = r.json()["id"]
    cd = api.client.get(f"/notebook/documents/{did}/download", headers=H(u)).headers["content-disposition"]
    assert cd.count('"') == 2 and "\n" not in cd and "evil" in cd


def test_document_count_limit(api, monkeypatch):
    from app.simple import notebook
    monkeypatch.setattr(notebook, "MAX_DOCS", 2)
    u = api.register()
    assert upload(api, u, "1.txt", b"abc " * 10).status_code == 201 and upload(api, u, "2.txt", b"abc " * 10).status_code == 201
    r = upload(api, u, "3.txt", b"abc " * 10)
    assert r.status_code == 409 and "can keep 2" in r.json()["detail"]


def test_students_cannot_touch_each_others_documents(api):
    a, b = api.register(), api.register()
    did = upload(api, a, "secret.txt", b"private study notes " * 5).json()["id"]
    for method, path, kw in (("get", f"/notebook/documents/{did}/download", {}), ("get", f"/notebook/documents/{did}/view", {}),
                             ("get", f"/notebook/documents/{did}/text", {}), ("delete", f"/notebook/documents/{did}", {}),
                             ("patch", f"/notebook/documents/{did}", {"json": {"name": "mine"}})):
        assert getattr(api.client, method)(path, headers=H(b), **kw).status_code == 404, path
    assert api.client.get("/notebook/documents", headers=H(b)).json()["documents"] == []
    assert api.client.get(f"/notebook/documents/{did}/download").status_code == 401


def test_documents_survive_logout_and_login(api):
    u = api.register()
    did = upload(api, u, "keep.txt", b"keep me " * 10).json()["id"]
    h = {"Authorization": f"Bearer {api.client.post('/auth/login', json={'email': u['email'], 'password': u['password']}).json()['access_token']}"}
    assert api.client.get(f"/notebook/documents/{did}/download", headers=h).content == b"keep me " * 10


def test_text_endpoint_explains_documents_without_readable_text(api):
    u = api.register()
    scanned = make_pdf("")                      # a page with no text, like a scanned page
    did = upload(api, u, "scan.pdf", scanned).json()["id"]
    r = api.client.get(f"/notebook/documents/{did}/text", headers=H(u))
    assert r.status_code == 422 and "No readable text" in r.json()["detail"]["message"]


# ------------------------------------------------------------------ Create Quiz from a stored document
def test_create_quiz_from_a_saved_document_end_to_end(api, monkeypatch):
    u = api.register()
    monkeypatch.setattr(settings, "studio_cooldown_seconds", 0)
    ai_service.set_provider(MockProvider({"learning_pack": lambda s, usr: fake_pack()}))
    did = upload(api, u, "photosynthesis.txt", SOURCE.encode()).json()["id"]
    text = api.client.get(f"/notebook/documents/{did}/text", headers=H(u)).json()
    pack = api.client.post("/studio/packs", json={"text": text["text"], "title": "photosynthesis", "source_name": text["name"], "consent": True}, headers=H(u))
    assert pack.status_code == 201, pack.text
    pid = pack.json()["pack"]["id"]
    quiz = api.client.post(f"/studio/packs/{pid}/quiz", json={"count": 10, "difficulty": "mixed"}, headers=H(u)).json()
    assert quiz["total"] == 10 and "answer_index" not in json_text(quiz)                      # answers are not sent before the student answers
    answers = [{"question_id": q["id"], "chosen": 0} for q in quiz["questions"]]
    res = api.client.post(f"/studio/packs/{pid}/quiz/submit", json={"answers": answers}, headers=H(u)).json()
    assert res["total"] == 10 and res["correct"] == 10 and res["review"][0]["explanation"]


def json_text(x):
    import json
    return json.dumps(x)
