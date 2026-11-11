// Appearance: "light", "dark" or "system" (follow the device). Remembered on this device and applied straight away.
const KEY = "mindsync_theme";

export function getTheme() {
  try {
    const t = localStorage.getItem(KEY);
    return t === "light" || t === "dark" ? t : "system";
  } catch { return "system"; }
}

export function applyTheme(choice) {
  const root = document.documentElement;
  if (choice === "light" || choice === "dark") root.dataset.theme = choice; else delete root.dataset.theme;
}

export function setTheme(choice) {
  try {
    if (choice === "light" || choice === "dark") localStorage.setItem(KEY, choice); else localStorage.removeItem(KEY);
  } catch { /* storage blocked: the choice still applies until the page is closed */ }
  applyTheme(choice);
}
