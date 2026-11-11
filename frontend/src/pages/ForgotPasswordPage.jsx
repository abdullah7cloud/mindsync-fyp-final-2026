import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api";
import BrandMark from "../components/BrandMark";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Step 1 of "I forgot my password": the student gives their e-mail address and we send a one-time link.
// The answer is the same whether or not the address has an account, so this page cannot be used to find out
// who is registered.
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(null);       // { message, delivery } once the request was accepted
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!EMAIL_RE.test(email.trim())) {
      setError("That does not look like an email address. It should look like name@example.com.");
      return;
    }
    setSubmitting(true);
    try {
      setDone(await api.forgotPassword(email.trim()));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sorry, something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-form" onSubmit={handleSubmit} noValidate>
        <div className="auth-brand">
          <BrandMark />
          <h1>MindSync</h1>
        </div>
        <p className="subtitle">Forgot your password? No problem.</p>
        {done ? (
          <>
            <div className="success-banner" role="status">
              <strong>Check your email</strong>
              <span>{done.message}</span>
            </div>
            {done.delivery === "demo" && (
              <p className="ap-text">
                Practice mode: this copy of MindSync cannot send real emails yet, so the message was saved on this computer instead (in the <code>backend/outbox</code> folder).
              </p>
            )}
            <p className="ap-text">Nothing arrived? Look in your spam folder, or ask for a new link.</p>
            <button type="button" onClick={() => setDone(null)}>Ask for another link</button>
          </>
        ) : (
          <>
            <p className="ap-text">Type the email address you signed up with. We will send you a link to choose a new password.</p>
            {error && <div className="error-banner" role="alert">{error}</div>}
            <label>
              Email
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
            </label>
            <button type="submit" disabled={submitting}>{submitting ? "Sending..." : "Send me the link"}</button>
          </>
        )}
        <p className="switch-link"><Link to="/login">← Back to log in</Link></p>
      </form>
    </div>
  );
}
