import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

const letters = ["A", "B", "C", "D"];

function Bar({ percent, label }) {
  return <div className="mt-bar" role="img" aria-label={label}><span style={{ width: `${Math.max(0, Math.min(100, percent || 0))}%` }} /></div>;
}

// Takes a quiz from a SAVED learning pack: nothing here calls the AI. Questions arrive without their answers; the server marks the quiz.
export default function QuizRunner({ token, packId, title, onNew }) {
  const [quiz, setQuiz] = useState(null);
  const [i, setI] = useState(0);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const start = useCallback(async () => {
    setError(""); setBusy(true); setResult(null); setAnswers({}); setI(0);
    try { setQuiz(await api.studioQuiz(token, packId, { count: 10, difficulty: "mixed" })); }
    catch (e) { setError(e.message); setQuiz(null); } finally { setBusy(false); }
  }, [token, packId]);
  useEffect(() => { start(); }, [start]);

  async function finish() {
    setBusy(true); setError("");
    try {
      setResult(await api.studioSubmit(token, packId, { difficulty: quiz.difficulty, answers: quiz.questions.map((q) => ({ question_id: q.id, chosen: answers[q.id] })) }));
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  if (result) {
    return (
      <section className="card" aria-labelledby="qz-result">
        <h2 id="qz-result" tabIndex={-1}>Your score: {result.correct} out of {result.total} ({result.percent}%)</h2>
        <p className="source-line">{result.note}</p>
        <div className="builder-actions">
          <button type="button" disabled={busy} onClick={start}>Try the quiz again</button>
          <button type="button" className="ghost-button" onClick={onNew}>Make a quiz from another document</button>
        </div>
        <h3>Correct answers</h3>
        <ol className="st-review">
          {result.review.map((r) => (
            <li key={r.question_id} className={r.correct ? "right" : "wrong"}>
              <p><strong>{r.question}</strong> <span className={`pill pill-${r.correct ? "good" : "bad"}`}>{r.correct ? "Correct" : "Not quite"}</span></p>
              <p>Your answer: {letters[r.chosen]}. {r.options[r.chosen]}</p>
              {!r.correct && <p>Correct answer: {letters[r.answer_index]}. {r.options[r.answer_index]}</p>}
              <p className="insight-note">{r.explanation}</p>
            </li>
          ))}
        </ol>
      </section>
    );
  }
  if (!quiz) {
    return (
      <section className="card" aria-live="polite">
        {error ? <><p className="field-note bad" role="alert">{error}</p><div className="builder-actions"><button type="button" onClick={start}>Try again</button><button type="button" className="ghost-button" onClick={onNew}>Back</button></div></> : <p className="card-empty" role="status">Getting your questions…</p>}
      </section>
    );
  }
  const q = quiz.questions[i];
  const last = i === quiz.questions.length - 1;
  return (
    <section className="card" aria-labelledby="qz-q">
      <p className="card-meta">{title ? `${title} · ` : ""}Question {i + 1} of {quiz.total}</p>
      {quiz.note && i === 0 && <p className="insight-note">{quiz.note}</p>}
      <Bar percent={(100 * i) / quiz.total} label={`Question ${i + 1} of ${quiz.total}`} />
      <fieldset className="st-options">
        <legend id="qz-q">{q.question}</legend>
        {q.options.map((o, n) => (
          <label key={n} className={answers[q.id] === n ? "on" : ""}>
            <input type="radio" name={`q-${q.id}`} checked={answers[q.id] === n} onChange={() => setAnswers({ ...answers, [q.id]: n })} />
            <span><b>{letters[n]}.</b> {o}</span>
          </label>
        ))}
      </fieldset>
      {error && <p className="field-note bad" role="alert">{error}</p>}
      <div className="builder-actions">
        <button type="button" className="ghost-button" disabled={i === 0} onClick={() => setI(i - 1)}>Back</button>
        {!last ? <button type="button" disabled={answers[q.id] == null} onClick={() => setI(i + 1)}>Next</button>
          : <button type="button" disabled={busy || quiz.questions.some((x) => answers[x.id] == null)} onClick={finish}>{busy ? "Marking…" : "Finish and see my score"}</button>}
      </div>
    </section>
  );
}
