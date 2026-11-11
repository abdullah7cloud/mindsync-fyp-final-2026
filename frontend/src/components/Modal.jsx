import { useEffect, useRef } from "react";

// A small dialog: closes with Escape or a click outside, keeps keyboard focus inside while open and gives it back afterwards.
export default function Modal({ title, titleId, onClose, children, wide = false }) {
  const ref = useRef(null);
  useEffect(() => {
    const prev = document.activeElement;
    ref.current?.focus();
    const key = (e) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab" && ref.current) {
        const items = [...ref.current.querySelectorAll("button, [href], input, select, textarea, summary, [tabindex]:not([tabindex='-1'])")].filter((el) => !el.disabled && el.offsetParent !== null);
        if (!items.length) return;
        const first = items[0], last = items[items.length - 1];
        if (e.shiftKey && (document.activeElement === first || document.activeElement === ref.current)) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    window.addEventListener("keydown", key);
    return () => { window.removeEventListener("keydown", key); prev?.focus?.(); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const id = titleId || "modal-title";
  return (
    <div className="modal-scrim" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal" style={wide ? { maxWidth: "46rem" } : undefined} role="dialog" aria-modal="true" aria-labelledby={id} tabIndex={-1} ref={ref}>
        <h2 id={id}>{title}</h2>
        {children}
      </div>
    </div>
  );
}
