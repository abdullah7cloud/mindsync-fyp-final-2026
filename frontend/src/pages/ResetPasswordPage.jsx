import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api";
import BrandMark from "../components/BrandMark";
import { passwordRules } from "../passwordRules";

// Step 2: the student opened the link from the email and chooses a new password.
// The secret in the link is read once and then removed from the address bar, so it does not stay in the
// browser history or get copied when the address is shared.
export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [token] = useState(() => params.get("token") || "");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (token) window.history.replaceState(null, "", window.location.pathname);
  }, [token]);

  const rules = passwordRules(password);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (rules.some((r) => !r.ok)) {
      setError("Your password does not follow all the rules below yet.");
      return;
    }
    if (password !== confirm) {
      setError("The two passwords do not match.");
      return;
    }
    setSubmitting(true);
    try {
      const { message } = await api.resetPassword(token, password);
      try { sessionStorage.setItem("mindsync_reset_flash", message); } catch { /* ignore */ }
      navigate("/login");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sorry, something went wrong. Please try again.");
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <div className="auth-page">
        <div className="auth-form">
          <div className="auth-brand"><BrandMark /><h1>MindSync</h1></div>
          <div className="error-banner" role="alert">This page only works from the link in your email. Please ask for a new link.</div>
          <p className="switch-link"><Link to="/forgot-password">Ask for a new link</Link></p>
          <p className="switch-link"><Link to="/login">← Back to log in</Link></p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <form className="auth-form" onSubmit={handleSubmit} noValidate>
        <div className="auth-brand"><BrandMark /><h1>MindSync</h1></div>
        <p className="subtitle">Choose a new password</p>
        {error && (
          <div className="error-banner" role="alert">
            {error} {/not valid|expired/i.test(error) && <Link to="/forgot-password">Ask for a new link</Link>}
          </div>
        )}
        <label>
          New password
          <div className="password-row">
            <input type={showPw ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password" maxLength={128} />
            <button type="button" className="ghost-button" onClick={() => setShowPw((v) => !v)}>{showPw ? "Hide" : "Show"}</button>
          </div>
        </label>
        <ul className="pw-rules" aria-label="Password rules">
          {rules.map((r) => (
            <li key={r.text} className={r.ok ? "pw-ok" : ""}><span aria-hidden="true">{r.ok ? "✓" : "○"}</span> {r.text}</li>
          ))}
        </ul>
        <label>
          Confirm new password
          <input type={showPw ? "text" : "password"} value={confirm} onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password" maxLength={128} />
        </label>
        <button type="submit" disabled={submitting}>{submitting ? "Saving..." : "Save new password"}</button>
        <p className="switch-link"><Link to="/login">← Back to log in</Link></p>
      </form>
    </div>
  );
}
