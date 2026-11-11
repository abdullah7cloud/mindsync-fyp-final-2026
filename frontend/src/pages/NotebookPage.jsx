import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import PageHeader from "../components/PageHeader";
import Modal from "../components/Modal";
import { niceDate, saveBlob, sizeWords } from "../lite/dates";
import "./mytasks.css";
import "./lite.css";

function safeName(s) {
  return (String(s || "note").replace(/[\\/:*?"<>|]+/g, " ").replace(/\s+/g, " ").trim() || "note").slice(0, 80);
}

// ---------- My Notes ----------
function NotesSection({ token, setError }) {
  const [list, setList] = useState(null);
  const [query, setQuery] = useState("");
  const [current, setCurrent] = useState(null);     // null = nothing open, { id: null } = new note
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [saved, setSaved] = useState({ title: "", body: "" });
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState("");
  const [confirmDel, setConfirmDel] = useState(false);
  const timer = useRef(null);

  const dirty = !!current && (title !== saved.title || body !== saved.body);

  const load = useCallback(async (q = "") => {
    try { const r = await api.notes(token, q); setList(r.notes); }
    catch (e) { setError(e.message); setList([]); }
  }, [token, setError]);

  useEffect(() => { load(""); }, [load]);
  useEffect(() => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => load(query.trim()), 250);
    return () => clearTimeout(timer.current);
  }, [query, load]);

  useEffect(() => {
    if (!dirty) return undefined;
    const warn = (e) => { e.preventDefault(); e.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  function leaveOk() {
    return !dirty || window.confirm("You have changes that are not saved. Leave without saving?");
  }

  function startNew() {
    if (!leaveOk()) return;
    setCurrent({ id: null }); setTitle(""); setBody(""); setSaved({ title: "", body: "" }); setMsg(""); setConfirmDel(false);
  }

  async function open(id) {
    if (current?.id === id || !leaveOk()) return;
    setBusy("open"); setMsg(""); setConfirmDel(false);
    try {
      const n = await api.note(token, id);
      setCurrent({ id: n.id }); setTitle(n.title); setBody(n.body); setSaved({ title: n.title, body: n.body });
    } catch (e) { setError(e.message); } finally { setBusy(""); }
  }

  async function save(e) {
    e?.preventDefault();
    if (!title.trim()) { setError("Please give your note a title."); return; }
    setBusy("save"); setError(""); setMsg("");
    try {
      let n;
      if (current.id) n = await api.editNote(token, current.id, { title: title.trim(), body });
      else n = await api.createNote(token, { title: title.trim(), body });
      setCurrent({ id: n.id }); setTitle(n.title); setBody(n.body); setSaved({ title: n.title, body: n.body });
      await load(query.trim());
      setMsg("Saved to your account.");
    } catch (err) { setError(err.message); } finally { setBusy(""); }
  }

  async function remove() {
    setBusy("delete"); setError("");
    try {
      await api.deleteNote(token, current.id);
      setCurrent(null); setTitle(""); setBody(""); setSaved({ title: "", body: "" }); setConfirmDel(false);
      await load(query.trim());
      setMsg("Note deleted.");
    } catch (err) { setError(err.message); } finally { setBusy(""); }
  }

  async function download(format) {
    if (dirty) { setError("Please save your note first, then download it."); return; }
    setBusy(format); setError("");
    try {
      const { blob } = await api.downloadNote(token, current.id, format);
      saveBlob(blob, `${safeName(title)}.${format === "pdf" ? "pdf" : "docx"}`);
    } catch (err) { setError(err.message); } finally { setBusy(""); }
  }

  return (
    <div className="lt-notebook">
      <aside className="card lt-note-list" aria-label="My notes list">
        <div className="lt-note-tools">
          <button type="button" className="landing-button" onClick={startNew}>New note</button>
          <label className="lt-search">
            <span className="visually-hidden">Search my notes</span>
            <input type="search" placeholder="Search my notes" value={query} maxLength={100} onChange={(e) => setQuery(e.target.value)} />
          </label>
        </div>
        {list === null && <p className="card-empty" role="status">Loading your notes…</p>}
        {list && list.length === 0 && (
          <p className="card-empty">{query.trim() ? "No notes match your search." : "You have no notes yet. Press “New note” to write your first one."}</p>
        )}
        {list && list.length > 0 && (
          <ul className="lt-notes" aria-label="Notes">
            {list.map((n) => (
              <li key={n.id}>
                <button type="button" className={`lt-note-item ${current?.id === n.id ? "is-open" : ""}`} onClick={() => open(n.id)} aria-current={current?.id === n.id ? "true" : undefined}>
                  <strong>{n.title}</strong>
                  <span className="card-meta">{niceDate(n.updated_at.slice(0, 10))}{n.preview ? ` · ${n.preview}` : ""}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      <section className="card lt-editor" aria-label="Note editor">
        {!current ? (
          <div className="mt-empty">
            <p className="card-empty">{msg || "Open a note from the list, or press “New note” to start writing."}</p>
          </div>
        ) : (
          <form onSubmit={save} className="lt-form">
            <label>Title
              <input value={title} disabled={busy === "open"} maxLength={120} onChange={(e) => setTitle(e.target.value)} placeholder="For example: Chapter 3 summary" required />
            </label>
            <label>Your note
              <textarea className="lt-write" disabled={busy === "open"} value={body} maxLength={60000} onChange={(e) => setBody(e.target.value)} placeholder="Write here…" rows={16} />
            </label>
            <p className="card-meta" aria-live="polite">{dirty ? "You have changes that are not saved yet." : (msg || (current.id ? "All changes are saved." : ""))}</p>
            <div className="builder-actions">
              <button type="submit" disabled={busy === "save" || (!dirty && !!current.id)}>{busy === "save" ? "Saving…" : "Save note"}</button>
              {current.id && (
                <>
                  <button type="button" className="ghost-button" disabled={!!busy} onClick={() => download("pdf")}>Download PDF</button>
                  <button type="button" className="ghost-button" disabled={!!busy} onClick={() => download("docx")}>Download Word</button>
                  {!confirmDel
                    ? <button type="button" className="ghost-button" onClick={() => setConfirmDel(true)}>Delete note</button>
                    : (
                      <span className="lt-confirm" role="group" aria-label="Confirm delete">
                        Delete this note for good?
                        <button type="button" onClick={remove} disabled={busy === "delete"}>Yes, delete</button>
                        <button type="button" className="ghost-button" onClick={() => setConfirmDel(false)}>No, keep it</button>
                      </span>
                    )}
                </>
              )}
            </div>
          </form>
        )}
      </section>
    </div>
  );
}

// ---------- My Documents ----------
function ViewModal({ token, doc, onClose, setError }) {
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [state, setState] = useState("loading");
  useEffect(() => {
    let made = "";
    let live = true;
    (async () => {
      try {
        if (doc.ext === ".pdf") {
          const { blob } = await api.documentFile(token, doc.id, "view");
          made = URL.createObjectURL(new Blob([blob], { type: "application/pdf" }));
          if (live) { setUrl(made); setState("pdf"); }
        } else {
          const r = await api.documentText(token, doc.id);
          if (live) { setText(r.text); setState("text"); }
        }
      } catch (e) {
        if (live) { setState("none"); setText(e.message); }
      }
    })();
    return () => { live = false; if (made) URL.revokeObjectURL(made); };
  }, [token, doc]);
  return (
    <Modal title={doc.name} titleId="view-title" onClose={onClose} wide>
      {state === "loading" && <p className="card-empty" role="status">Opening your document…</p>}
      {state === "pdf" && <iframe title={`View ${doc.name}`} src={url} className="lt-pdf" />}
      {state === "text" && <pre className="lt-doc-text" tabIndex={0}>{text.slice(0, 30000)}{text.length > 30000 ? "\n\n… (the rest is in the downloaded file)" : ""}</pre>}
      {state === "none" && <p className="card-empty">{text || "This document cannot be shown here."} You can still download it.</p>}
      <div className="builder-actions"><button type="button" onClick={onClose}>Close</button></div>
    </Modal>
  );
}

function DocumentsSection({ token, setError }) {
  const [info, setInfo] = useState(null);
  const [busy, setBusy] = useState("");
  const [renaming, setRenaming] = useState(null);   // { id, name }
  const [confirmId, setConfirmId] = useState(null);
  const [viewing, setViewing] = useState(null);
  const [msg, setMsg] = useState("");
  const fileRef = useRef(null);

  const load = useCallback(async () => {
    try { setInfo(await api.documents(token)); } catch (e) { setError(e.message); setInfo({ documents: [], max_mb: 10, types: [] }); }
  }, [token, setError]);
  useEffect(() => { load(); }, [load]);

  async function pick(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy("upload"); setError(""); setMsg("");
    try { await api.uploadDocument(token, f); await load(); setMsg(`“${f.name}” was saved to your account.`); }
    catch (err) { setError(err.message); } finally { setBusy(""); if (fileRef.current) fileRef.current.value = ""; }
  }

  async function download(d) {
    setBusy(d.id); setError("");
    try { saveBlob((await api.documentFile(token, d.id, "download")).blob, d.name); }
    catch (err) { setError(err.message); } finally { setBusy(""); }
  }

  async function rename(e) {
    e.preventDefault();
    const name = renaming.name.trim();
    if (!name) return;
    setBusy(renaming.id); setError("");
    try { await api.renameDocument(token, renaming.id, name); setRenaming(null); await load(); }
    catch (err) { setError(err.message); } finally { setBusy(""); }
  }

  async function remove(d) {
    setBusy(d.id); setError("");
    try { await api.deleteDocument(token, d.id); setConfirmId(null); await load(); setMsg(`“${d.name}” was deleted.`); }
    catch (err) { setError(err.message); } finally { setBusy(""); }
  }

  const docs = info?.documents;
  return (
    <section className="card" aria-labelledby="docs-h">
      <h2 id="docs-h" className="card-title">My Documents</h2>
      <p className="card-meta">Keep your study files here: PDF, Word, PowerPoint or text files up to {info?.max_mb || 10} MB. They stay in your account after you log out.</p>
      {msg && <div className="success-banner" role="status">{msg}</div>}
      <div className="builder-actions">
        <label className="landing-button lt-upload">
          {busy === "upload" ? "Uploading…" : "Upload a document"}
          <input ref={fileRef} type="file" accept=".pdf,.docx,.pptx,.txt" onChange={pick} disabled={busy === "upload"} className="visually-hidden" />
        </label>
      </div>
      {docs === undefined && <p className="card-empty" role="status">Loading your documents…</p>}
      {docs && docs.length === 0 && <p className="card-empty">You have no documents yet. Upload one to keep it here and make a quiz from it.</p>}
      {docs && docs.length > 0 && (
        <ul className="lt-docs" aria-label="My documents">
          {docs.map((d) => (
            <li key={d.id} className="lt-doc">
              {renaming?.id === d.id ? (
                <form className="lt-edit-row" onSubmit={rename}>
                  <label>New name<input value={renaming.name} maxLength={200} onChange={(e) => setRenaming({ id: d.id, name: e.target.value })} autoFocus /></label>
                  <button type="submit" disabled={busy === d.id}>Save name</button>
                  <button type="button" className="ghost-button" onClick={() => setRenaming(null)}>Cancel</button>
                </form>
              ) : (
                <>
                  <div className="lt-doc-main">
                    <strong>{d.name}</strong>
                    <span className="card-meta">{d.ext.slice(1).toUpperCase()} · {sizeWords(d.size)} · added {niceDate(d.created_at.slice(0, 10))}</span>
                  </div>
                  <div className="lt-task-actions">
                    <button type="button" className="ghost-button" onClick={() => setViewing(d)}>View</button>
                    <button type="button" className="ghost-button" disabled={busy === d.id} onClick={() => download(d)}>Download</button>
                    <button type="button" className="ghost-button" onClick={() => setRenaming({ id: d.id, name: d.name.replace(/\.[^.]+$/, "") })}>Rename</button>
                    <Link className="ghost-button lt-link-button" to={`/ai-zone?document=${d.id}`}>Create Quiz</Link>
                    {confirmId === d.id ? (
                      <span className="lt-confirm" role="group" aria-label={`Confirm delete ${d.name}`}>
                        Delete for good?
                        <button type="button" onClick={() => remove(d)} disabled={busy === d.id}>Yes, delete</button>
                        <button type="button" className="ghost-button" onClick={() => setConfirmId(null)}>No</button>
                      </span>
                    ) : <button type="button" className="ghost-button" onClick={() => setConfirmId(d.id)}>Delete</button>}
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
      {viewing && <ViewModal token={token} doc={viewing} setError={setError} onClose={() => setViewing(null)} />}
    </section>
  );
}

// ---------- The page ----------
export default function NotebookPage() {
  const { token } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") === "documents" ? "documents" : "notes";
  const [error, setError] = useState("");

  useEffect(() => { document.title = "My Notebook · MindSync"; }, []);

  function go(t) { setError(""); setParams(t === "documents" ? { tab: "documents" } : {}, { replace: true }); }

  return (
    <>
      <PageHeader
        title="My Notebook"
        subtitle="Your notes and your study documents, saved in your account."
        image={{ name: "planner", side: "right", focus: "50% 40%", alt: "A tidy study desk" }}
      />
      {error && <div className="error-banner" role="alert">{error} <button type="button" className="link-button" onClick={() => setError("")}>Close</button></div>}
      <div className="tabs" role="tablist" aria-label="Notebook sections">
        <button type="button" role="tab" id="tab-notes" aria-selected={tab === "notes"} aria-controls="panel-notes" className={tab === "notes" ? "on" : ""} onClick={() => go("notes")}>My Notes</button>
        <button type="button" role="tab" id="tab-documents" aria-selected={tab === "documents"} aria-controls="panel-documents" className={tab === "documents" ? "on" : ""} onClick={() => go("documents")}>My Documents</button>
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "notes" ? <NotesSection token={token} setError={setError} /> : <DocumentsSection token={token} setError={setError} />}
      </div>
    </>
  );
}
