import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import PageHeader from "../components/PageHeader";
import QuizRunner from "../aizone/QuizRunner";
import "./mytasks.css";
import "./lite.css";
import "../studio/studio.css";

// AI Learning Zone: one job. Read a document, ask the AI for multiple-choice questions, let the student answer, show the score
// and the correct answers with short explanations. The quiz is saved, so trying again never calls the AI a second time.
export default function AiZonePage() {
  const { token } = useAuth();
  const [params, setParams] = useSearchParams();
  const docId = params.get("document");
  const [status, setStatus] = useState(null);
  const [doc, setDoc] = useState(null);                 // { name, text, chars }
  const [pack, setPack] = useState(null);               // { id, title }
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState("");
  const fileRef = useRef(null);

  useEffect(() => { document.title = "AI Learning Zone · MindSync"; }, []);
  useEffect(() => { api.studioStatus(token).then(setStatus).catch(() => setStatus({ ai_available: false, message: "We could not check the AI service." })); }, [token]);

  const loadFromNotebook = useCallback(async (id) => {
    setBusy("read"); setError("");
    try { const r = await api.documentText(token, id); setDoc({ name: r.name, text: r.text, chars: r.chars }); }
    catch (e) { setError(e.message); setDoc(null); } finally { setBusy(""); }
  }, [token]);
  useEffect(() => { if (docId) loadFromNotebook(docId); }, [docId, loadFromNotebook]);

  const min = status?.limits?.min_chars || 300;
  const max = status?.limits?.max_chars || 24000;
  const aiOn = !!status?.ai_available;
  const tooShort = doc && doc.chars < min;
  const tooLong = doc && doc.chars > max;

  async function pickFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy("read"); setError(""); setInfo(""); setPack(null);
    if (docId) setParams({}, { replace: true });
    try {
      const r = await api.studioExtract(token, f);
      setDoc({ name: r.filename || f.name, text: r.text, chars: r.chars });
    } catch (err) { setError(err.message); setDoc(null); } finally { setBusy(""); if (fileRef.current) fileRef.current.value = ""; }
  }

  async function generate() {
    setBusy("make"); setError(""); setInfo("");
    try {
      const r = await api.studioCreate(token, { text: doc.text, title: doc.name.replace(/\.[^.]+$/, "").slice(0, 120), source_name: doc.name, consent: true });
      if (r.reused) setInfo("You already made a quiz from this document, so the saved quiz was opened. No new AI request was used.");
      setPack({ id: r.pack.id, title: r.pack.title });
    } catch (err) { setError(err.message); } finally { setBusy(""); }
  }

  function again() { setPack(null); setDoc(null); setInfo(""); setError(""); if (docId) setParams({}, { replace: true }); }

  return (
    <>
      <PageHeader
        title="AI Learning Zone"
        subtitle="Upload a document and take a quiz made from what is really in it."
        image={{ name: "grass", side: "right", focus: "50% 45%", alt: "Two women sitting together on the grass, relaxed and smiling" }}
      />
      {error && <div className="error-banner" role="alert">{error} <button type="button" className="link-button" onClick={() => setError("")}>Close</button></div>}
      {info && <div className="success-banner" role="status">{info}</div>}

      {pack ? <QuizRunner token={token} packId={pack.id} title={pack.title} onNew={again} /> : (
        <>
          {status && !aiOn && (
            <section className="card st-status off" aria-labelledby="ai-off-h">
              <h2 id="ai-off-h" className="card-title">The AI quiz is not available right now</h2>
              <p>The AI service is not switched on, or it cannot be reached right now. Quizzes need the AI, so no quiz can be made at the moment. Your plans, tasks, notes and documents work as normal. MindSync never shows a fake quiz.</p>
            </section>
          )}
          <section className="card" aria-labelledby="up-h">
            <h2 id="up-h" className="card-title">1. Choose a document</h2>
            <label>Upload a PDF, Word or TXT file <small>(up to {status?.limits?.max_upload_mb || 5} MB)</small>
              <input ref={fileRef} type="file" accept=".pdf,.docx,.pptx,.txt" disabled={busy !== ""} onChange={pickFile} />
            </label>
            <p className="card-meta">You can also open a saved document from <Link to="/notebook?tab=documents">My Notebook</Link> and press “Create Quiz”.</p>
            {busy === "read" && <p className="card-empty" role="status">Reading your document…</p>}
            {doc && (
              <p className="lt-chosen" role="status"><strong>{doc.name}</strong> · {doc.chars.toLocaleString()} characters read
                {tooShort && <span className="field-note bad"> This is too short for a quiz. At least {min} characters are needed.</span>}
                {tooLong && <span className="field-note bad"> This is too long. The limit is {max.toLocaleString()} characters, so please upload a shorter part.</span>}
              </p>
            )}
          </section>
          <section className="card" aria-labelledby="gen-h">
            <h2 id="gen-h" className="card-title">2. Make the quiz</h2>
            <p className="card-meta">The AI reads the text of your document and writes multiple-choice questions. The text is sent to the AI service for this. Please do not use private or sensitive material.</p>
            <div className="builder-actions">
              <button type="button" disabled={!doc || tooShort || tooLong || !aiOn || busy !== ""} onClick={generate}>{busy === "make" ? "Making your quiz… this can take about a minute" : "Generate Quiz"}</button>
            </div>
          </section>
        </>
      )}
    </>
  );
}
