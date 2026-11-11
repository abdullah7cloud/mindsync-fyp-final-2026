import { useState } from "react";
import { Link, useInRouterContext } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import { passwordRules } from "../passwordRules";
import { saveBlob } from "../lite/dates";
import Icon from "./Icon";
import Modal from "./Modal";

// Basic account settings in one small window: change your name, change your password, download your data, delete your account, log out.
export default function AccountModal({ onClose }) {
  const { token, user, logout, refreshUser } = useAuth();
  const inRouter = useInRouterContext();       // the links need the router; the window still works without it (as in its own tests)
  const [name, setName] = useState(user?.display_name || "");
  const [cur, setCur] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [del, setDel] = useState(false);
  const [delPw, setDelPw] = useState("");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(fn) {
    setBusy(true); setMsg(""); setError("");
    try { await fn(); } catch (e) { setError(e.message || "Sorry, something went wrong. Please try again."); } finally { setBusy(false); }
  }
  const saveName = (e) => { e.preventDefault(); return run(async () => { await api.changeName(token, name.trim()); await refreshUser(); setMsg("Your name was saved."); }); };
  const savePw = (e) => {
    e.preventDefault();
    if (passwordRules(pw).some((r) => !r.ok)) { setError("Your new password needs at least 8 characters, with a letter and a number."); setMsg(""); return; }
    if (pw !== pw2) { setError("The two new passwords are not the same."); setMsg(""); return; }
    return run(async () => { await api.changePassword(token, cur, pw); setCur(""); setPw(""); setPw2(""); setMsg("Your password was changed."); });
  };
  const exportData = () => run(async () => {
    const data = await api.exportMyData(token);
    saveBlob(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }), "mindsync-my-data.json");
    setMsg("Your data was saved to your downloads as mindsync-my-data.json.");
  });
  const removeAccount = (e) => { e.preventDefault(); return run(async () => { await api.deleteAccount(token, delPw); logout(); }); };

  return (
    <Modal title="My account" titleId="acct-title" onClose={onClose} wide>
      <p className="card-meta">Signed in as <strong>{user?.email}</strong></p>
      {inRouter && (
        <nav className="acct-links" aria-label="Account pages">
          <Link to="/profile" onClick={onClose}><Icon name="profile" size={18} /> My Profile</Link>
          <Link to="/settings" onClick={onClose}><Icon name="settings" size={18} /> Settings</Link>
        </nav>
      )}
      {msg && <div className="success-banner" role="status">{msg}</div>}
      {error && <div className="error-banner" role="alert">{error}</div>}

      <form className="acct-block" onSubmit={saveName}>
        <h3>Your name</h3>
        <label>Name shown in MindSync<input value={name} maxLength={100} onChange={(e) => setName(e.target.value)} required /></label>
        <button type="submit" disabled={busy || !name.trim() || name.trim() === user?.display_name}>Save name</button>
      </form>

      <form className="acct-block" onSubmit={savePw}>
        <h3>Change password</h3>
        <label>Current password<input type="password" autoComplete="current-password" value={cur} onChange={(e) => setCur(e.target.value)} required /></label>
        <label>New password<input type="password" autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} required /></label>
        <label>New password again<input type="password" autoComplete="new-password" value={pw2} onChange={(e) => setPw2(e.target.value)} required /></label>
        <button type="submit" disabled={busy || !cur || !pw || !pw2}>Change password</button>
      </form>

      <div className="acct-block">
        <h3>Your data</h3>
        <p className="card-meta">Download everything MindSync keeps about you (plans, tasks, notes and document names).</p>
        <button type="button" className="ghost-button" disabled={busy} onClick={exportData}>Download my data</button>
      </div>

      <div className="acct-block">
        <h3>Delete my account</h3>
        {!del ? (
          <button type="button" className="ghost-button danger" onClick={() => setDel(true)}>Delete my account…</button>
        ) : (
          <form onSubmit={removeAccount} className="acct-danger">
            <p className="field-note warn">This permanently erases your account, plans, tasks, notes and documents. It cannot be undone.</p>
            <label>Type your password to confirm<input type="password" autoComplete="current-password" value={delPw} onChange={(e) => setDelPw(e.target.value)} required /></label>
            <div className="builder-actions">
              <button type="submit" className="danger" disabled={busy || !delPw}>Yes, delete everything</button>
              <button type="button" className="ghost-button" onClick={() => { setDel(false); setDelPw(""); }}>Keep my account</button>
            </div>
          </form>
        )}
      </div>

      <div className="builder-actions acct-foot">
        <button type="button" className="ghost-button" onClick={() => logout()}>Log out</button>
        <button type="button" className="ghost-button" onClick={onClose}>Close</button>
      </div>
    </Modal>
  );
}
