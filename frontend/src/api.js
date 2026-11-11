// Thin fetch-based API client for the MindSync backend. Every call that
// needs auth attaches the JWT stored by AuthContext (see
// context/AuthContext.jsx) as a Bearer token — the backend never sees a
// cookie or session id, matching the stateless-JWT design in the report's
// Methodology chapter.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status, fields = {}) {
    super(message);
    this.status = status;
    this.fields = fields; // { fieldName: "what is wrong" } for form validation errors
  }
}

const FIELD_LABELS = { email: "Email", password: "Password", display_name: "Name", new_password: "New password", current_password: "Current password" };

// Turns FastAPI/Pydantic validation messages into plain English.
function friendlyValidation(field, msg) {
  const m = String(msg || "");
  if (/at least (\d+) characters/i.test(m)) return `must be at least ${m.match(/at least (\d+)/i)[1]} characters`;
  if (/at most (\d+) characters/i.test(m)) return `must be at most ${m.match(/at most (\d+)/i)[1]} characters`;
  if (/valid email/i.test(m)) return "must be a valid email address, like name@example.com";
  if (/field required/i.test(m)) return "is required";
  return m.replace(/^Value error,\s*/i, "");
}

function parseDetail(detail, status) {
  // 422: detail is a list of {loc, msg}. Everything else: a plain string.
  if (Array.isArray(detail)) {
    const fields = {};
    const parts = [];
    for (const item of detail) {
      const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : null;
      const label = FIELD_LABELS[field] || (typeof field === "string" ? field : "Input");
      const text = friendlyValidation(field, item.msg);
      const sentence = /^(Password|Name|Email|New password|Current password)\b/.test(text) ? text : `${label} ${text}`;
      if (typeof field === "string") fields[field] = sentence;
      parts.push(sentence);
    }
    return { message: parts.join(". ") || "Please check what you typed.", fields };
  }
  if (typeof detail === "string") return { message: detail, fields: {} };
  if (detail && typeof detail === "object" && typeof detail.message === "string") return { message: detail.message, fields: {}, code: detail.code };
  return { message: status >= 500 ? "MindSync had a problem on its side. Please try again." : "Sorry, something went wrong.", fields: {} };
}

// When a logged-in request comes back "Invalid or expired token" (the login lasts 60 minutes), the student is told in plain words and the
// login screen is shown, instead of a raw technical message inside the page. AuthContext registers the handler.
const SESSION_MESSAGE = "Your login has ended for safety. Please log in again.";
let sessionEndedHandler = null;
export function onSessionEnded(fn) { sessionEndedHandler = fn; }
function sessionEnded(status, detail, hadToken) {
  if (status !== 401 || !hadToken || typeof detail !== "string") return false;
  if (detail !== "Invalid or expired token" && detail !== "Not authenticated") return false;
  try { if (sessionEndedHandler) sessionEndedHandler(SESSION_MESSAGE); } catch { /* never block the error */ }
  return true;
}

async function request(path, { method = "GET", body, token, timeoutMs = 0 } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  const ctl = timeoutMs && typeof AbortController !== "undefined" ? new AbortController() : null;
  const timer = ctl ? setTimeout(() => ctl.abort(), timeoutMs) : null;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctl ? ctl.signal : undefined,
    });
  } catch {
    throw new ApiError(
      "We cannot reach MindSync right now. Please try again in a moment. (If you run MindSync yourself, check that the backend window is open.)",
      0
    );
  }

  if (timer) clearTimeout(timer);
  if (!res.ok) {
    let detail = null;
    try {
      const data = await res.json();
      detail = data.detail ?? null;
    } catch {
      // response had no JSON body
    }
    if (sessionEnded(res.status, detail, !!token)) throw new ApiError(SESSION_MESSAGE, 401);
    const { message, fields, code } = parseDetail(detail ?? res.statusText, res.status);
    const err = new ApiError(message, res.status, fields);
    if (code) err.code = code;
    throw err;
  }

  if (res.status === 204) return null;
  return res.json();
}

// Download a file the server builds or stores (needs the login header, so it cannot be a plain link). Returns { blob, filename }.
async function requestBlob(path, token) {
  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  } catch {
    throw new ApiError("We cannot reach MindSync right now. Please try again in a moment.", 0);
  }
  if (!res.ok) {
    let detail = null;
    try { detail = (await res.json()).detail ?? null; } catch { /* no body */ }
    if (sessionEnded(res.status, detail, true)) throw new ApiError(SESSION_MESSAGE, 401);
    const { message } = parseDetail(detail ?? res.statusText, res.status);
    throw new ApiError(message, res.status);
  }
  const cd = res.headers.get("content-disposition") || "";
  const star = cd.match(/filename\*=UTF-8''([^;]+)/i);
  const plain = cd.match(/filename="([^"]+)"/i);
  let filename = plain ? plain[1] : "file";
  if (star) { try { filename = decodeURIComponent(star[1]); } catch { /* keep the plain name */ } }
  return { blob: await res.blob(), filename };
}

// Upload one file (multipart). Used for My Documents and for reading a file's text.
async function upload(path, token, file, timeoutMs = 60000) {
  const fd = new FormData();
  fd.append("file", file);
  const ctl = typeof AbortController !== "undefined" ? new AbortController() : null;
  const timer = ctl ? setTimeout(() => ctl.abort(), timeoutMs) : null;
  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd, signal: ctl ? ctl.signal : undefined });
  } catch {
    throw new ApiError("We cannot reach MindSync right now. Please try again in a moment.", 0);
  } finally {
    if (timer) clearTimeout(timer);
  }
  if (!res.ok) {
    let detail = null;
    try { detail = (await res.json()).detail ?? null; } catch { /* no body */ }
    if (sessionEnded(res.status, detail, true)) throw new ApiError(SESSION_MESSAGE, 401);
    const { message, fields } = parseDetail(detail ?? res.statusText, res.status);
    throw new ApiError(message, res.status, fields);
  }
  return res.json();
}

export const api = {
  // ---- Account ----
  register: (email, password, displayName) =>
    request("/auth/register", { method: "POST", body: { email, password, display_name: displayName } }),
  login: (email, password) => request("/auth/login", { method: "POST", body: { email, password } }),
  me: (token) => request("/auth/me", { token }),
  forgotPassword: (email) => request("/auth/forgot-password", { method: "POST", body: { email } }),
  resetPassword: (token, newPassword) =>
    request("/auth/reset-password", { method: "POST", body: { token, new_password: newPassword } }),
  changePassword: (token, currentPassword, newPassword) =>
    request("/account/password", { method: "POST", body: { current_password: currentPassword, new_password: newPassword }, token }),
  changeName: (token, displayName) => request("/profile", { method: "PUT", body: { display_name: displayName }, token }),
  exportMyData: (token) => request("/account/export", { token }),
  deleteAccount: (token, password) => request("/account", { method: "DELETE", body: { password }, token }),

  // ---- My Profile and Settings (Update 28) ----
  myProfile: (token) => request("/my/profile", { token }),
  saveMyName: (token, displayName) => request("/my/profile", { method: "PUT", body: { display_name: displayName }, token }),
  startEmailChange: (token, newEmail, password) => request("/my/email/start", { method: "POST", body: { new_email: newEmail, password }, token }),
  confirmEmailChange: (token, code) => request("/my/email/confirm", { method: "POST", body: { code }, token }),
  cancelEmailChange: (token) => request("/my/email/cancel", { method: "POST", token }),
  uploadMyPicture: (token, file) => upload("/my/avatar", token, file),
  removeMyPicture: (token) => request("/my/avatar", { method: "DELETE", token }),
  myPicture: (token) => requestBlob("/my/avatar", token),
  mySettings: (token) => request("/my/settings", { token }),
  saveMySettings: (token, body) => request("/my/settings", { method: "PUT", body, token }),
  sendTestReminder: (token) => request("/my/settings/test-email", { method: "POST", token }),

  // ---- Dashboard and Study Planner ----
  dashboard: (token, tz) => request(`/study/dashboard?tz=${encodeURIComponent(tz || "UTC")}`, { token }),
  plans: (token) => request("/study/plans", { token }),
  createPlan: (token, body) => request("/study/plans", { method: "POST", body, token, timeoutMs: 60000 }),
  editPlan: (token, id, body) => request(`/study/plans/${id}`, { method: "PATCH", body, token }),
  deletePlan: (token, id) => request(`/study/plans/${id}`, { method: "DELETE", token }),
  editTask: (token, id, body) => request(`/study/tasks/${id}`, { method: "PATCH", body, token }),
  deleteTask: (token, id) => request(`/study/tasks/${id}`, { method: "DELETE", token }),

  // ---- AI Learning Zone (the quiz) ----
  studioStatus: (token) => request("/studio/status", { token }),
  studioExtract: (token, file) => upload("/studio/extract", token, file),
  studioCreate: (token, body) => request("/studio/packs", { method: "POST", body, token, timeoutMs: 120000 }),
  studioQuiz: (token, id, body) => request(`/studio/packs/${id}/quiz`, { method: "POST", body, token }),
  studioSubmit: (token, id, body) => request(`/studio/packs/${id}/quiz/submit`, { method: "POST", body, token }),

  // ---- My Notebook ----
  notes: (token, q) => request(`/notebook/notes${q ? `?q=${encodeURIComponent(q)}` : ""}`, { token }),
  note: (token, id) => request(`/notebook/notes/${id}`, { token }),
  createNote: (token, body) => request("/notebook/notes", { method: "POST", body, token }),
  editNote: (token, id, body) => request(`/notebook/notes/${id}`, { method: "PATCH", body, token }),
  deleteNote: (token, id) => request(`/notebook/notes/${id}`, { method: "DELETE", token }),
  downloadNote: (token, id, format) => requestBlob(`/notebook/notes/${id}/download?format=${format}`, token),
  documents: (token) => request("/notebook/documents", { token }),
  uploadDocument: (token, file) => upload("/notebook/documents", token, file),
  renameDocument: (token, id, name) => request(`/notebook/documents/${id}`, { method: "PATCH", body: { name }, token }),
  deleteDocument: (token, id) => request(`/notebook/documents/${id}`, { method: "DELETE", token }),
  documentFile: (token, id, mode) => requestBlob(`/notebook/documents/${id}/${mode === "view" ? "view" : "download"}`, token),
  documentText: (token, id) => request(`/notebook/documents/${id}/text`, { token, timeoutMs: 40000 }),
};

export { API_BASE_URL };

export { ApiError };
