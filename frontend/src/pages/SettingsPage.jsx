import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import PageHeader from "../components/PageHeader";
import Icon from "../components/Icon";
import { browserZone } from "../lite/dates";
import { getTheme, setTheme } from "../theme";
import "./lite.css";
import "./account.css";

const THEMES = [["light", "Light", "Bright and clean"], ["dark", "Dark", "Easy on the eyes at night"], ["system", "System default", "Follows your device"]];
const FALLBACK_ZONES = ["UTC", "Europe/Copenhagen", "Europe/London", "Europe/Berlin", "Europe/Paris", "Europe/Stockholm", "Europe/Helsinki", "Asia/Karachi", "Asia/Dubai", "Asia/Kolkata",
  "Asia/Singapore", "Asia/Tokyo", "Australia/Sydney", "Pacific/Auckland", "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "America/Toronto"];

function zoneList(current) {
  let zones = FALLBACK_ZONES;
  try { if (typeof Intl.supportedValuesOf === "function") zones = Intl.supportedValuesOf("timeZone"); } catch { /* use the short list */ }
  const set = new Set(zones);
  set.add("UTC");
  if (current) set.add(current);
  return [...set].sort();
}

// What a reminder means, in plain numbers: "10 days to finish, 30% left" -> the e-mail arrives when 3 days remain.
function exampleText(percent) {
  const days = 10;
  const left = (days * percent) / 100;
  return `Example: if you have ${days} days to finish a task, a ${percent}% reminder arrives when ${left} days remain.`;
}

export default function SettingsPage() {
  const { token } = useAuth();
  const [theme, setThemeState] = useState(getTheme());
  const [s, setS] = useState(null);
  const [form, setForm] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [testMsg, setTestMsg] = useState("");
  const [testError, setTestError] = useState("");
  const device = useMemo(() => browserZone(), []);

  useEffect(() => {
    api.mySettings(token).then((r) => {
      // a student who has never saved yet starts with this device's time zone instead of UTC
      const start = r.timezone === "UTC" && device && device !== "UTC" ? { ...r, timezone: device, _fresh: true } : r;
      setS(r); setForm({ remind_enabled: start.remind_enabled, remind_percent: start.remind_percent, timezone: start.timezone });
    }).catch((e) => setLoadError(e.message));
  }, [token, device]);

  const zones = useMemo(() => zoneList(form?.timezone), [form?.timezone]);
  const dirty = s && form && (form.remind_enabled !== s.remind_enabled || form.remind_percent !== s.remind_percent || form.timezone !== s.timezone);

  function chooseTheme(t) { setTheme(t); setThemeState(t); }
  function edit(patch) { setForm((f) => ({ ...f, ...patch })); setMsg(""); setError(""); }

  async function save(e) {
    e.preventDefault();
    setBusy(true); setMsg(""); setError("");
    try { const r = await api.saveMySettings(token, form); setS(r); setForm({ remind_enabled: r.remind_enabled, remind_percent: r.remind_percent, timezone: r.timezone }); setMsg("Your settings were saved."); }
    catch (x) { setError(x.message); } finally { setBusy(false); }
  }
  async function test() {
    setTestMsg(""); setTestError("");
    try { const r = await api.sendTestReminder(token); setTestMsg(r.message); } catch (x) { setTestError(x.message); }
  }

  return (
    <div>
      <PageHeader title="Settings" subtitle="Choose how MindSync looks and when it reminds you." />
      {loadError && <div className="error-banner" role="alert">{loadError}</div>}
      <div className="p28-wrap">
        <section className="card p28-card" aria-labelledby="p28-look">
          <h2 id="p28-look">Appearance</h2>
          <fieldset className="p28-themes">
            <legend className="visually-hidden">Colour mode</legend>
            {THEMES.map(([id, label, hint]) => (
              <label key={id} className="p28-theme">
                <input type="radio" name="theme" value={id} checked={theme === id} onChange={() => chooseTheme(id)} />
                <span className={`p28-swatch ${id}`} aria-hidden="true" />
                <span>{label}<br /><small className="card-meta">{hint}</small></span>
              </label>
            ))}
          </fieldset>
          <p className="card-meta">MindSync remembers your choice on this device.</p>
        </section>

        {!s && !loadError && <p className="card-meta" role="status">Loading your settings…</p>}
        {form && (
          <form onSubmit={save} className="p28-wrap" style={{ maxWidth: "none" }}>
            <section className="card p28-card" aria-labelledby="p28-mail">
              <h2 id="p28-mail">E-mail reminders</h2>
              <label className="p28-switch">
                <input type="checkbox" role="switch" checked={form.remind_enabled} onChange={(e) => edit({ remind_enabled: e.target.checked })} />
                <span className="p28-switch-track" aria-hidden="true" />
                <span>Remind me by e-mail before a task is due</span>
              </label>
              <div className={form.remind_enabled ? "" : "p28-off"} aria-disabled={!form.remind_enabled}>
                <fieldset className="p28-choice">
                  <legend className="card-meta">Send the reminder when this much of the time is still left</legend>
                  {(s.percent_choices || [30, 35]).map((p) => (
                    <label key={p}><input type="radio" name="percent" value={p} checked={form.remind_percent === p} disabled={!form.remind_enabled} onChange={() => edit({ remind_percent: p })} /> {p}%</label>
                  ))}
                </fieldset>
                <p className="p28-example" style={{ marginTop: "0.7rem" }}>{exampleText(form.remind_percent)}</p>
              </div>
              <ul className="card-meta" style={{ margin: 0, paddingLeft: "1.2rem", lineHeight: 1.6 }}>
                <li>You get one friendly e-mail per task, with its name, deadline and the time left.</li>
                <li>Tasks you have finished or deleted never get a reminder.</li>
                <li>If you change a task's day, its reminder is set again.</li>
                <li>Reminders are sent by the MindSync server, so you do not need to keep the website open.</li>
              </ul>
              {s.delivery === "demo" && <div className="field-note warn" role="note">No mail server is set up on this computer yet, so reminders are saved as files in the backend/outbox folder instead of being sent to your inbox.</div>}
              <div className="p28-row">
                <button type="button" className="ghost-button" onClick={test}><Icon name="bell" size={16} /> Send me a test e-mail</button>
              </div>
              {testMsg && <p className="p28-saved" role="status"><Icon name="check" size={16} />{testMsg}</p>}
              {testError && <div className="error-banner" role="alert">{testError}</div>}
            </section>

            <section className="card p28-card" aria-labelledby="p28-pref">
              <h2 id="p28-pref">Basic preferences</h2>
              <label>Time zone
                <select value={form.timezone} onChange={(e) => edit({ timezone: e.target.value })}>
                  {zones.map((z) => <option key={z} value={z}>{z.replace(/_/g, " ")}</option>)}
                </select>
              </label>
              <p className="card-meta">Your task deadlines end at 23:59 on the due day in this time zone, and reminders show times in it.
                {device && device !== form.timezone && <> This device is set to <button type="button" className="link-button" onClick={() => edit({ timezone: device })}>{device.replace(/_/g, " ")}</button>.</>}</p>
            </section>

            {error && <div className="error-banner" role="alert">{error}</div>}
            <div className="p28-row">
              <button type="submit" disabled={busy || !dirty}>{busy ? "Saving…" : "Save settings"}</button>
              {msg && <span className="p28-saved" role="status"><Icon name="check" size={16} />{msg}</span>}
              {!msg && dirty && <span className="card-meta">You have changes that are not saved yet.</span>}
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
