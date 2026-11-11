import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";
import "./shared.css";

// remembered theme, applied before the first paint so the page does not flash
try {
  const t = localStorage.getItem("mindsync_theme");
  if (t === "light" || t === "dark") document.documentElement.dataset.theme = t;
  const look = JSON.parse(localStorage.getItem("mindsync_look") || "null");
  if (look) {
    if (look.accent && look.accent !== "blue") document.documentElement.dataset.accent = look.accent;
    if (look.text === "larger") document.documentElement.dataset.text = "larger";
    if (look.contrast) document.documentElement.dataset.contrast = "high";
  }
} catch { /* storage blocked: the device setting is used */ }

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
