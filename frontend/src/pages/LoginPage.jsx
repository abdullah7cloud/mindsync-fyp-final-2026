import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api";
import { useAuth } from "../context/AuthContext";
import BrandMark from "../components/BrandMark";
import AuthPhoto from "../components/AuthPhoto";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showPw, setShowPw] = useState(false);
  // A one-time note ("password changed", "your login has ended"). It is read once, then removed after the page is shown.
  const [flash] = useState(() => {
    try { return sessionStorage.getItem("mindsync_reset_flash"); } catch { return null; }
  });
  useEffect(() => {
    try { sessionStorage.removeItem("mindsync_reset_flash"); } catch { /* ignore */ }
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const { access_token } = await api.login(email, password);
      login(access_token);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sorry, something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page auth-split">
      <AuthPhoto />
      <form className="auth-form" onSubmit={handleSubmit}>
        <div className="auth-brand">
          <BrandMark />
          <h1>MindSync</h1>
        </div>
        <p className="subtitle">Welcome back! Log in to carry on.</p>
        {flash && <div className="success-banner" role="status">{flash}</div>}
        {error && <div className="error-banner" role="alert">{error}</div>}
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
        </label>
        <label>
          Password
          <div className="password-row">
            <input
              type={showPw ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              maxLength={128}
              required
            />
            <button type="button" className="ghost-button" onClick={() => setShowPw((v) => !v)} aria-pressed={showPw}>
              {showPw ? "Hide" : "Show"}
            </button>
          </div>
        </label>
        <p className="forgot-link"><Link to="/forgot-password">Forgot your password?</Link></p>
        <button type="submit" disabled={submitting}>
          {submitting ? "Logging in..." : "Log in"}
        </button>
        <p className="switch-link">
          New here? <Link to="/register">Create a free account</Link>
        </p>
        <p className="switch-link">
          <Link to="/">← Back to the home page</Link>
        </p>
      </form>
    </div>
  );
}
