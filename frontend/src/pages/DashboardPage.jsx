import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import PageHeader from "../components/PageHeader";
import { browserZone, minutesWords, niceDate, whenWords } from "../lite/dates";
import "./mytasks.css";
import "./lite.css";

// Dashboard: the numbers come only from the student's own saved tasks. Ticking a task here (or on the Study Planner)
// changes the saved task, and this page is then loaded again from the database, so every number is always the saved truth.
function TaskRow({ t, today, busy, onToggle }) {
  const late = !t.done && t.due_date < today;
  return (
    <li className={`lt-task ${t.done ? "is-done" : ""} ${late ? "is-late" : ""}`}>
      <label className="lt-check">
        <input type="checkbox" checked={t.done} disabled={busy} onChange={(e) => onToggle(t, e.target.checked)} aria-label={`${t.done ? "Mark as not done" : "Mark as done"}: ${t.title}`} />
        <span className="lt-task-main">
          <strong className="lt-task-title">{t.title}</strong>
          <span className="lt-task-meta">
            {t.subject && <span>{t.subject}</span>}
            <span>{niceDate(t.due_date)}{t.start_time ? ` at ${t.start_time}` : ""}</span>
            <span>{minutesWords(t.minutes)}</span>
            {late && <span className="pill pill-bad">Overdue</span>}
            {!late && !t.done && t.due_date === today && <span className="pill pill-warn">Today</span>}
          </span>
        </span>
      </label>
    </li>
  );
}

export default function DashboardPage() {
  const { token } = useAuth();
  const tz = browserZone();
  const [d, setD] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => { document.title = "Dashboard · MindSync"; }, []);
  const load = useCallback(async () => {
    try { setD(await api.dashboard(token, tz)); setError(""); } catch (e) { setError(e.message || "We could not load your dashboard."); }
  }, [token, tz]);
  useEffect(() => { load(); }, [load]);

  async function toggle(t, done) {
    setBusy(t.id); setError("");
    setD((old) => old && { ...old, tasks: old.tasks.map((x) => (x.id === t.id ? { ...x, done } : x)) });     // the tick shows at once; the numbers follow the saved data below
    try { await api.editTask(token, t.id, { done }); } catch (e) { setError(e.message); }
    await load();
    setBusy("");
  }

  const pending = d ? d.tasks.filter((t) => !t.done) : [];
  const finished = d ? d.tasks.filter((t) => t.done) : [];
  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="See how your studying is going, and tick off tasks as you finish them."
        image={{ name: "dashboard", side: "left", focus: "75% 22%", alt: "A smiling student laughing as he works on a laptop at a bright white desk" }}
      >
        <Link to="/planner" className="landing-button">Create Study Plan</Link>
      </PageHeader>
      {error && <div className="error-banner" role="alert">{error} <button type="button" className="link-button" onClick={() => setError("")}>Close</button></div>}
      {!d && !error && <p className="card-empty" role="status">Loading your dashboard…</p>}
      {d && (
        <>
          <div className="stats-row lt-stats" aria-label="Your numbers">
            <div className="stat-tile"><span className="stat-value" data-testid="total">{d.total}</span><span className="stat-label">Total tasks</span></div>
            <div className="stat-tile"><span className="stat-value" data-testid="completed">{d.completed}</span><span className="stat-label">Completed tasks</span></div>
            <div className="stat-tile"><span className="stat-value" data-testid="remaining">{d.remaining}</span><span className="stat-label">Remaining tasks</span></div>
          </div>

          <section className="card" aria-labelledby="prog-h">
            <h2 id="prog-h" className="card-title">Study progress: {d.progress}%</h2>
            <div className="mt-bar lt-bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={d.progress} aria-labelledby="prog-h"><span style={{ width: `${d.progress}%` }} /></div>
            <p className="card-meta">{d.total ? `${d.completed} of ${d.total} tasks are done. This counts finished tasks. It shows effort, not how well you understand the subject.` : "Your progress starts when you make your first study plan."}</p>
          </section>

          <div className="lt-two">
            <section className="card" aria-labelledby="dl-h">
              <h2 id="dl-h" className="card-title">Upcoming deadlines</h2>
              {d.deadlines.length === 0 ? <p className="card-empty">No deadlines coming up.</p> : (
                <ul className="lt-list">
                  {d.deadlines.map((x) => (
                    <li key={x.plan_id}>
                      <strong>{x.subject}: {x.topic}</strong>
                      <span className="card-meta">Due {niceDate(x.target_date)} ({whenWords(x.target_date, d.today)}) · {x.left} of {x.total} tasks left</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section className={`card ${d.overdue.length ? "lt-card-warn" : ""}`} aria-labelledby="od-h">
              <h2 id="od-h" className="card-title">Overdue tasks</h2>
              {d.overdue.length === 0 ? <p className="card-empty">Nothing is overdue. Well done!</p> : (
                <ul className="lt-list">
                  {d.overdue.map((x) => (
                    <li key={x.id}>
                      <strong>{x.title}</strong>
                      <span className="card-meta">{x.subject} · was due {niceDate(x.due_date)} ({x.days_late} day{x.days_late === 1 ? "" : "s"} ago)</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <section className="card" aria-labelledby="tl-h">
            <h2 id="tl-h" className="card-title">My tasks</h2>
            {d.total === 0 ? (
              <div className="mt-empty">
                <p className="card-empty">You have no tasks yet. Make a study plan and your tasks will appear here.</p>
                <Link to="/planner" className="landing-button">Create Study Plan</Link>
              </div>
            ) : (
              <>
                {pending.length === 0 ? <p className="card-empty">All tasks are done. Great work!</p> : (
                  <ul className="lt-tasks" aria-label="Tasks to do">{pending.map((t) => <TaskRow key={t.id} t={t} today={d.today} busy={busy === t.id} onToggle={toggle} />)}</ul>
                )}
                {finished.length > 0 && (
                  <details className="lt-finished">
                    <summary>Completed tasks ({finished.length})</summary>
                    <ul className="lt-tasks" aria-label="Completed tasks">{finished.map((t) => <TaskRow key={t.id} t={t} today={d.today} busy={busy === t.id} onToggle={toggle} />)}</ul>
                  </details>
                )}
              </>
            )}
          </section>
        </>
      )}
    </>
  );
}
