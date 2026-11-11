import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import PageHeader from "../components/PageHeader";
import { browserZone, minutesWords, niceDate, todayIso } from "../lite/dates";
import "./mytasks.css";
import "./lite.css";

const MOODS = [["good", "Good"], ["okay", "Okay"], ["tired", "Tired"]];
const STRESS = [["low", "Low"], ["medium", "Medium"], ["high", "High"]];

function Choice({ legend, name, options, value, onChange }) {
  return (
    <fieldset className="scale">
      <legend>{legend}</legend>
      <div className="mt-choices">
        {options.map(([id, label]) => (
          <label key={id} className={value === id ? "on" : ""}>
            <input type="radio" name={name} value={id} checked={value === id} onChange={() => onChange(id)} /> {label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

// ---------------------------------------------------------------- one task (tick, edit, delete)
function TaskLine({ t, onSave, onToggle, onDelete }) {
  const [edit, setEdit] = useState(false);
  const [askDel, setAskDel] = useState(false);
  const [f, setF] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  function open() { setF({ title: t.title, details: t.details, due_date: t.due_date, start_time: t.start_time || "", minutes: t.minutes }); setErr(""); setEdit(true); }
  async function save(e) {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const body = { title: f.title, details: f.details, due_date: f.due_date, minutes: Number(f.minutes) };
      if (f.start_time) body.start_time = f.start_time; else body.clear_time = true;
      await onSave(t, body);
      setEdit(false);
    } catch (x) { setErr(x.message); } finally { setBusy(false); }
  }

  if (edit) {
    return (
      <li className="lt-task lt-editing">
        <form onSubmit={save} className="lt-edit">
          <label>Task<input value={f.title} maxLength={160} required onChange={(e) => setF({ ...f, title: e.target.value })} /></label>
          <label>Details<textarea rows={2} value={f.details} maxLength={400} onChange={(e) => setF({ ...f, details: e.target.value })} /></label>
          <div className="lt-edit-row">
            <label>Day<input type="date" value={f.due_date} required onChange={(e) => setF({ ...f, due_date: e.target.value })} /></label>
            <label>Start time <small>(optional)</small><input type="time" value={f.start_time} onChange={(e) => setF({ ...f, start_time: e.target.value })} /></label>
            <label>Minutes<input type="number" min={5} max={480} value={f.minutes} required onChange={(e) => setF({ ...f, minutes: e.target.value })} /></label>
          </div>
          {err && <p className="field-note bad" role="alert">{err}</p>}
          <div className="builder-actions">
            <button type="submit" disabled={busy}>{busy ? "Saving…" : "Save task"}</button>
            <button type="button" className="ghost-button" onClick={() => setEdit(false)}>Cancel</button>
          </div>
        </form>
      </li>
    );
  }
  return (
    <li className={`lt-task ${t.done ? "is-done" : ""}`}>
      <label className="lt-check">
        <input type="checkbox" checked={t.done} onChange={(e) => onToggle(t, e.target.checked)} aria-label={`${t.done ? "Mark as not done" : "Mark as done"}: ${t.title}`} />
        <span className="lt-task-main">
          <strong className="lt-task-title">{t.title}</strong>
          <span className="lt-task-meta"><span>{niceDate(t.due_date)}{t.start_time ? ` at ${t.start_time}` : ""}</span><span>{minutesWords(t.minutes)}</span></span>
          {t.details && <span className="lt-task-details">{t.details}</span>}
        </span>
      </label>
      <div className="lt-task-actions">
        {askDel ? (
          <>
            <span className="card-meta">Delete this task?</span>
            <button type="button" className="ghost-button danger" onClick={() => onDelete(t)}>Yes, delete</button>
            <button type="button" className="ghost-button" onClick={() => setAskDel(false)}>No</button>
          </>
        ) : (
          <>
            <button type="button" className="ghost-button" onClick={open} aria-label={`Edit task: ${t.title}`}>Edit</button>
            <button type="button" className="ghost-button danger" onClick={() => setAskDel(true)} aria-label={`Delete task: ${t.title}`}>Delete</button>
          </>
        )}
      </div>
    </li>
  );
}

// ---------------------------------------------------------------- one plan (roadmap + tasks + edit plan)
function PlanCard({ p, onChanged, onError }) {
  const { token } = useAuth();
  const [edit, setEdit] = useState(false);
  const [f, setF] = useState(null);
  const [askDel, setAskDel] = useState(false);
  const [warn, setWarn] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  function open() { setF({ subject: p.subject, topic: p.topic, goal: p.goal, target_date: p.target_date, roadmap: p.roadmap.map((r) => ({ ...r })) }); setErr(""); setEdit(true); }
  async function save(e) {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const r = await api.editPlan(token, p.id, { ...f, roadmap: f.roadmap.filter((x) => x.title.trim()), timezone: browserZone() });
      setWarn(r.warning || "");
      setEdit(false);
      await onChanged();
    } catch (x) { setErr(x.message); } finally { setBusy(false); }
  }
  async function saveTask(t, body) { await api.editTask(token, t.id, body); await onChanged(); }
  async function toggle(t, done) { try { await api.editTask(token, t.id, { done }); } catch (x) { onError(x.message); } await onChanged(); }
  async function delTask(t) { try { await api.deleteTask(token, t.id); } catch (x) { onError(x.message); } await onChanged(); }
  async function delPlan() { try { await api.deletePlan(token, p.id); } catch (x) { onError(x.message); } await onChanged(); }

  const pct = p.total ? Math.round((100 * p.done) / p.total) : 0;
  return (
    <article className="card lt-plan" id={`plan-${p.id}`} aria-labelledby={`pt-${p.id}`}>
      <div className="lt-plan-head">
        <div>
          <h3 id={`pt-${p.id}`}>{p.subject}: {p.topic}</h3>
          <p className="card-meta">Target date {niceDate(p.target_date)} · {p.done} of {p.total} tasks done · <span className={`pill ${p.source === "ai" ? "pill-good" : "pill-warn"}`}>{p.source === "ai" ? "Made by AI" : "Made offline"}</span></p>
        </div>
        <div className="lt-plan-actions">
          {!edit && <button type="button" className="ghost-button" onClick={open}>Edit plan</button>}
          {askDel ? (
            <>
              <button type="button" className="ghost-button danger" onClick={delPlan}>Yes, delete plan</button>
              <button type="button" className="ghost-button" onClick={() => setAskDel(false)}>No</button>
            </>
          ) : <button type="button" className="ghost-button danger" onClick={() => setAskDel(true)}>Delete plan</button>}
        </div>
      </div>
      {askDel && <p className="field-note warn">This deletes the plan and all of its tasks.</p>}
      <div className="mt-bar lt-bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label={`${p.subject} progress`}><span style={{ width: `${pct}%` }} /></div>
      {p.note && <p className="source-line">{p.note}</p>}
      {warn && <p className="field-note warn" role="status">{warn}</p>}

      {edit && (
        <form className="lt-edit lt-plan-edit" onSubmit={save}>
          <div className="lt-edit-row">
            <label>Subject Name<input value={f.subject} maxLength={80} required onChange={(e) => setF({ ...f, subject: e.target.value })} /></label>
            <label>Topic Name<input value={f.topic} maxLength={120} required onChange={(e) => setF({ ...f, topic: e.target.value })} /></label>
            <label>Target Completion Date<input type="date" value={f.target_date} required onChange={(e) => setF({ ...f, target_date: e.target.value })} /></label>
          </div>
          <label>Learning Goal / Notes<textarea rows={3} value={f.goal} maxLength={1500} onChange={(e) => setF({ ...f, goal: e.target.value })} /></label>
          <fieldset className="lt-road-edit">
            <legend>Roadmap steps</legend>
            {f.roadmap.map((r, i) => (
              <div key={i} className="lt-edit-row">
                <label>Step {i + 1}<input value={r.title} maxLength={80} onChange={(e) => setF({ ...f, roadmap: f.roadmap.map((x, n) => (n === i ? { ...x, title: e.target.value } : x)) })} /></label>
                <label>What to do<input value={r.text} maxLength={260} onChange={(e) => setF({ ...f, roadmap: f.roadmap.map((x, n) => (n === i ? { ...x, text: e.target.value } : x)) })} /></label>
              </div>
            ))}
          </fieldset>
          {err && <p className="field-note bad" role="alert">{err}</p>}
          <div className="builder-actions">
            <button type="submit" disabled={busy}>{busy ? "Saving…" : "Save plan"}</button>
            <button type="button" className="ghost-button" onClick={() => setEdit(false)}>Cancel</button>
          </div>
        </form>
      )}

      <h4 className="lt-sub">Learning roadmap</h4>
      <ol className="lt-road">{p.roadmap.map((r, i) => <li key={i}><strong>{r.title}</strong>{r.text ? <span> — {r.text}</span> : null}</li>)}</ol>
      {p.goal && <p className="card-meta"><strong>Your notes:</strong> {p.goal}</p>}

      <h4 className="lt-sub">Study tasks</h4>
      {p.tasks.length === 0 ? <p className="card-empty">This plan has no tasks left.</p> : (
        <ul className="lt-tasks">{p.tasks.map((t) => <TaskLine key={t.id} t={t} onSave={saveTask} onToggle={toggle} onDelete={delTask} />)}</ul>
      )}
    </article>
  );
}

// ---------------------------------------------------------------- the page
export default function PlannerPage() {
  const { token } = useAuth();
  const tz = browserZone();
  const today = todayIso(tz);
  const [plans, setPlans] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [made, setMade] = useState(null);
  const [form, setForm] = useState({ subject: "", topic: "", goal: "", target_date: "", mood: "okay", stress: "medium" });
  const madeRef = useRef(null);

  useEffect(() => { document.title = "Study Planner · MindSync"; }, []);
  const load = useCallback(async () => {
    try { setPlans((await api.plans(token)).plans); } catch (e) { setError(e.message || "We could not load your plans."); }
  }, [token]);
  useEffect(() => { load(); }, [load]);

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError(""); setMade(null);
    try {
      const p = await api.createPlan(token, { ...form, subject: form.subject.trim(), topic: form.topic.trim(), timezone: tz });
      setMade(p);
      setForm({ ...form, subject: "", topic: "", goal: "" });
      await load();
      setTimeout(() => madeRef.current?.focus(), 50);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <>
      <PageHeader
        title="Study Planner"
        subtitle="Tell us what you want to learn. MindSync makes a simple plan with tasks and study times before your deadline."
        image={{ name: "planner", side: "left", focus: "55% 40%", alt: "Two friends smiling as they plan their work together on a laptop in a café" }}
      />
      {error && <div className="error-banner" role="alert">{error} <button type="button" className="link-button" onClick={() => setError("")}>Close</button></div>}

      <section className="card" aria-labelledby="form-h">
        <h2 id="form-h" className="card-title">Make a new study plan</h2>
        <form className="lt-form" onSubmit={submit}>
          <label>Subject Name<input value={form.subject} maxLength={80} required placeholder="For example: Databases" onChange={set("subject")} /></label>
          <label>Topic Name — What do you want to learn?<input value={form.topic} maxLength={120} required placeholder="For example: SQL joins" onChange={set("topic")} /></label>
          <label>Learning Goal / Notes<textarea rows={4} value={form.goal} maxLength={1500} placeholder="Explain in your own words what you want to learn or what is hard for you." onChange={set("goal")} /></label>
          <label>Target Completion Date<input type="date" value={form.target_date} min={today} required onChange={set("target_date")} /></label>
          <Choice legend="Current Mood" name="mood" options={MOODS} value={form.mood} onChange={(v) => setForm({ ...form, mood: v })} />
          <Choice legend="Stress Level" name="stress" options={STRESS} value={form.stress} onChange={(v) => setForm({ ...form, stress: v })} />
          <p className="card-meta" id="ai-privacy-note">When the AI is on, your subject, topic and learning goal are sent to the AI service to help write your plan. Your mood and stress answers stay in MindSync and are never sent. Please do not type private details.</p>
          <div className="builder-actions">
            <button type="submit" disabled={busy || !form.subject.trim() || !form.topic.trim() || !form.target_date}>{busy ? "Making your plan… this can take up to half a minute" : "Generate My Study Plan"}</button>
          </div>
        </form>
      </section>

      {made && (
        <div className="success-banner" role="status" tabIndex={-1} ref={madeRef}>
          Your plan is ready: <strong>{made.subject}: {made.topic}</strong> with {made.total} tasks. {made.note}{" "}
          <a href={`#plan-${made.id}`}>Go to my plan</a>
        </div>
      )}

      <section aria-labelledby="plans-h" className="lt-plans">
        <h2 id="plans-h" className="lt-h2">My study plans</h2>
        {!plans ? <p className="card-empty" role="status">Loading…</p> : plans.length === 0 ? (
          <p className="card-empty">You have no study plans yet. Fill in the form above and press “Generate My Study Plan”.</p>
        ) : plans.map((p) => <PlanCard key={p.id} p={p} onChanged={load} onError={setError} />)}
      </section>
    </>
  );
}
