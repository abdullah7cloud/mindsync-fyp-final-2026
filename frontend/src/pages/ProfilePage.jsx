import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import PageHeader from "../components/PageHeader";
import Avatar from "../components/Avatar";
import Icon from "../components/Icon";
import { passwordRules } from "../passwordRules";
import "./lite.css";
import "./account.css";

const MAX_PICTURE = 3 * 1024 * 1024;

function Saved({ children }) {
  return children ? <span className="p28-saved" role="status"><Icon name="check" size={16} />{children}</span> : null;
}

// My Profile: name, picture, e-mail (changed with a code sent to the new address) and password. Each block saves on its own and says so clearly.
export default function ProfilePage() {
  const { token, user, refreshUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loadError, setLoadError] = useState("");

  async function load() {
    try { setProfile(await api.myProfile(token)); } catch (e) { setLoadError(e.message); }
  }
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function changed(p) {
    setProfile(p);
    window.dispatchEvent(new CustomEvent("mindsync:profile-changed"));
  }

  return (
    <div>
      <PageHeader title="My Profile" subtitle="Your name, picture, e-mail and password in one place." />
      {loadError && <div className="error-banner" role="alert">{loadError}</div>}
      {!profile && !loadError && <p className="card-meta" role="status">Loading your profile…</p>}
      {profile && (
        <div className="p28-wrap">
          <PictureCard token={token} profile={profile} onChange={changed} />
          <NameCard token={token} profile={profile} onChange={async (p) => { changed(p); await refreshUser(); }} />
          <EmailCard token={token} profile={profile} onChange={async (p) => { changed(p); await refreshUser(); }} reload={load} />
          <PasswordCard token={token} />
        </div>
      )}
    </div>
  );
}

function PictureCard({ token, profile, onChange }) {
  const input = useRef(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  async function pick(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setMsg(""); setError("");
    if (!/^image\/(jpeg|png|webp)$/.test(file.type)) { setError("Please choose a JPEG, PNG or WebP picture."); return; }
    if (file.size > MAX_PICTURE) { setError("That picture is bigger than 3 MB. Please choose a smaller one."); return; }
    setBusy(true);
    try { onChange(await api.uploadMyPicture(token, file)); setMsg("Your picture was saved."); } catch (x) { setError(x.message); } finally { setBusy(false); }
  }
  async function remove() {
    setBusy(true); setMsg(""); setError("");
    try { onChange(await api.removeMyPicture(token)); setMsg("Your picture was removed."); } catch (x) { setError(x.message); } finally { setBusy(false); }
  }
  return (
    <section className="card p28-card" aria-labelledby="p28-pic">
      <h2 id="p28-pic">Profile picture</h2>
      <div className="p28-row">
        <Avatar token={token} name={profile.display_name} version={profile.picture_version} size={96} className="p28-avatar-xl" />
        <div className="p28-row">
          <label className="ghost-button p28-filebtn">
            <Icon name="plus" size={16} /> {profile.has_picture ? "Change picture" : "Upload picture"}
            <input ref={input} className="p28-file" type="file" accept="image/jpeg,image/png,image/webp" onChange={pick} disabled={busy} aria-label={profile.has_picture ? "Change picture" : "Upload picture"} />
          </label>
          {profile.has_picture && <button type="button" className="ghost-button" onClick={remove} disabled={busy}>Remove picture</button>}
        </div>
      </div>
      <p className="card-meta">JPEG, PNG or WebP, up to 3 MB. MindSync makes it a small square and removes any hidden camera details.</p>
      {error && <div className="error-banner" role="alert">{error}</div>}
      <Saved>{msg}</Saved>
    </section>
  );
}

function NameCard({ token, profile, onChange }) {
  const [name, setName] = useState(profile.display_name);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const same = name.trim() === profile.display_name;
  async function save(e) {
    e.preventDefault();
    setBusy(true); setMsg(""); setError("");
    try { const p = await api.saveMyName(token, name.trim()); await onChange(p); setName(p.display_name); setMsg("Your name was saved."); } catch (x) { setError(x.message); } finally { setBusy(false); }
  }
  return (
    <section className="card p28-card" aria-labelledby="p28-name">
      <h2 id="p28-name">Your name</h2>
      <form onSubmit={save}>
        <label>Full name<input value={name} maxLength={100} required autoComplete="name" onChange={(e) => { setName(e.target.value); setMsg(""); }} /></label>
        {error && <div className="error-banner" role="alert">{error}</div>}
        <div className="p28-row"><button type="submit" disabled={busy || !name.trim() || same}>{busy ? "Saving…" : "Save name"}</button><Saved>{msg}</Saved></div>
      </form>
    </section>
  );
}

function EmailCard({ token, profile, onChange, reload }) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const pending = profile.pending_email;

  async function ask(e) {
    e.preventDefault();
    setBusy(true); setMsg(""); setError(""); setNote("");
    try {
      const r = await api.startEmailChange(token, email.trim(), pw);
      setPw("");
      setNote(r.message + (r.delivery === "demo" ? " (No mail server is set up on this computer, so the e-mail was saved as a file in the backend/outbox folder. Open that file to read the code.)" : ""));
      await reload();
    } catch (x) { setError(x.message); } finally { setBusy(false); }
  }
  async function confirm(e) {
    e.preventDefault();
    setBusy(true); setMsg(""); setError("");
    try { const r = await api.confirmEmailChange(token, code.trim()); await onChange(r.profile); setCode(""); setEmail(""); setNote(""); setOpen(false); setMsg("Your sign-in e-mail was changed. Use the new address next time you log in."); }
    catch (x) { setError(x.message); await reload(); } finally { setBusy(false); }
  }
  async function cancel() {
    setBusy(true); setError("");
    try { await api.cancelEmailChange(token); setCode(""); setNote(""); await reload(); } catch (x) { setError(x.message); } finally { setBusy(false); }
  }
  return (
    <section className="card p28-card" aria-labelledby="p28-mail">
      <h2 id="p28-mail">E-mail</h2>
      <p className="card-meta">You sign in with</p>
      <p className="p28-current">{profile.email}</p>
      <Saved>{msg}</Saved>
      {error && <div className="error-banner" role="alert">{error}</div>}
      {pending ? (
        <form className="p28-pending" onSubmit={confirm}>
          <p>We sent a 6-digit code to the new address. Type it here to finish the change. It works for 15 minutes.</p>
          {note && <p className="field-note" role="status">{note}</p>}
          <label>6-digit code<input className="p28-code" inputMode="numeric" autoComplete="one-time-code" pattern="\d{6}" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} required /></label>
          <div className="p28-row">
            <button type="submit" disabled={busy || code.length !== 6}>{busy ? "Checking…" : "Confirm new e-mail"}</button>
            <button type="button" className="ghost-button" onClick={cancel} disabled={busy}>Cancel the change</button>
          </div>
        </form>
      ) : !open ? (
        <div><button type="button" className="ghost-button" onClick={() => { setOpen(true); setMsg(""); }}>Change e-mail</button></div>
      ) : (
        <form onSubmit={ask}>
          <label>New e-mail address<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
          <label>Your password (to make sure it is you)<input type="password" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} required /></label>
          <p className="card-meta">We will send a 6-digit code to the new address. Your sign-in e-mail only changes after you type that code.</p>
          <div className="p28-row">
            <button type="submit" disabled={busy || !email || !pw}>{busy ? "Sending…" : "Send me a code"}</button>
            <button type="button" className="ghost-button" onClick={() => { setOpen(false); setError(""); }}>Close</button>
          </div>
        </form>
      )}
    </section>
  );
}

function PasswordCard({ token }) {
  const [cur, setCur] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const rules = passwordRules(pw);
  async function save(e) {
    e.preventDefault();
    setMsg(""); setError("");
    if (rules.some((r) => !r.ok)) { setError("Your new password needs at least 8 characters, with a letter and a number."); return; }
    if (pw !== pw2) { setError("The two new passwords are not the same."); return; }
    setBusy(true);
    try { await api.changePassword(token, cur, pw); setCur(""); setPw(""); setPw2(""); setMsg("Your password was changed."); } catch (x) { setError(x.message); } finally { setBusy(false); }
  }
  return (
    <section className="card p28-card" aria-labelledby="p28-pw">
      <h2 id="p28-pw">Password</h2>
      <form onSubmit={save}>
        <label>Current password<input type="password" autoComplete="current-password" value={cur} onChange={(e) => setCur(e.target.value)} required /></label>
        <label>New password<input type="password" autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} required /></label>
        {pw && <ul className="p28-pw-rules" aria-label="Password rules">{rules.map((r) => <li key={r.text} className={r.ok ? "ok" : ""}>{r.ok ? "✓" : "○"} {r.text}</li>)}</ul>}
        <label>New password again<input type="password" autoComplete="new-password" value={pw2} onChange={(e) => setPw2(e.target.value)} required /></label>
        {error && <div className="error-banner" role="alert">{error}</div>}
        <div className="p28-row"><button type="submit" disabled={busy || !cur || !pw || !pw2}>{busy ? "Saving…" : "Change password"}</button><Saved>{msg}</Saved></div>
      </form>
    </section>
  );
}
