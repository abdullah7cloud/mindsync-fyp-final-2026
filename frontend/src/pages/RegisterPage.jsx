import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api";
import { useAuth } from "../context/AuthContext";
import BrandMark from "../components/BrandMark";
import AuthPhoto from "../components/AuthPhoto";
import { passwordRules } from "../passwordRules";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validate({ displayName, email, password, confirm }) {
  const errors = {};
  if (!displayName.trim()) errors.display_name = "Please enter your name.";
  if (!email.trim()) errors.email = "Please enter your email.";
  else if (!EMAIL_RE.test(email.trim())) errors.email = "That does not look like an email address. It should look like name@example.com.";
  if (!password) errors.password = "Please choose a password.";
  else if (passwordRules(password).some((r) => !r.ok)) errors.password = "Your password does not follow all the rules below yet.";
  if (!confirm) errors.confirm = "Please type the password again.";
  else if (confirm !== password) errors.confirm = "The two passwords do not match.";
  return errors;
}

export default function RegisterPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [touched, setTouched] = useState(false);

  const rules = passwordRules(password);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setTouched(true);
    const errors = validate({ displayName, email, password, confirm });
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      setError("Please check the boxes marked in red below.");
      return;
    }
    setSubmitting(true);
    try {
      const { access_token } = await api.register(email.trim(), password, displayName.trim());
      setSuccess(true);
      setTimeout(() => {
        login(access_token);
        navigate("/dashboard");
      }, 1400);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        const next = {};
        if (err.fields?.email) next.email = err.fields.email;
        if (err.fields?.password) next.password = err.fields.password;
        if (err.fields?.display_name) next.display_name = err.fields.display_name;
        if (err.status === 409) next.email = "There is already an account with this email. Try logging in instead.";
        setFieldErrors(next);
      } else {
        setError("Sorry, something went wrong. Please try again.");
      }
      setSubmitting(false);
    }
  }

  const err = (k) => (touched || fieldErrors[k] ? fieldErrors[k] : undefined);

  if (success) {
    return (
      <div className="auth-page">
        <div className="auth-form">
          <div className="auth-brand"><BrandMark /><h1>MindSync</h1></div>
          <div className="success-banner" role="status">
            <strong>Account created!</strong>
            <span>Welcome, {displayName.trim()}. Taking you to your home page...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page auth-split">
      <AuthPhoto />
      <form className="auth-form" onSubmit={handleSubmit} noValidate>
        <div className="auth-brand">
          <BrandMark />
          <h1>MindSync</h1>
        </div>
        <p className="subtitle">Create your free account</p>
        {error && <div className="error-banner" role="alert">{error}</div>}

        <label>
          Name
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            autoComplete="name"
            className={err("display_name") ? "input-error" : ""}
            maxLength={100}
          />
          {err("display_name") && <span className="field-error">{err("display_name")}</span>}
        </label>

        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            className={err("email") ? "input-error" : ""}
          />
          {err("email") && <span className="field-error">{err("email")}</span>}
        </label>

        <label>
          Password
          <div className="password-row">
            <input
              type={showPw ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              className={err("password") ? "input-error" : ""}
              maxLength={128}
            />
            <button type="button" className="ghost-button" onClick={() => setShowPw((v) => !v)}>
              {showPw ? "Hide" : "Show"}
            </button>
          </div>
          {err("password") && <span className="field-error">{err("password")}</span>}
        </label>

        <ul className="pw-rules" aria-label="Password rules">
          {rules.map((r) => (
            <li key={r.text} className={r.ok ? "pw-ok" : ""}>
              <span aria-hidden="true">{r.ok ? "✓" : "○"}</span> {r.text}
            </li>
          ))}
        </ul>

        <label>
          Confirm password
          <input
            type={showPw ? "text" : "password"}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
            className={err("confirm") ? "input-error" : ""}
            maxLength={128}
          />
          {err("confirm") && <span className="field-error">{err("confirm")}</span>}
        </label>

        <button type="submit" disabled={submitting}>
          {submitting ? "Creating your account..." : "Create my account"}
        </button>
        <p className="switch-link">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
        <p className="switch-link">
          <Link to="/">← Back to the home page</Link>
        </p>
      </form>
    </div>
  );
}
