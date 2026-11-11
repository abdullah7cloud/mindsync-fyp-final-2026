// Small line icons for the menu and buttons (inline SVG: no extra files, no network). Decorative: aria-hidden.
const PATHS = {
  dashboard: "M3 3h8v8H3V3Zm10 0h8v5h-8V3ZM3 13h8v8H3v-8Zm10-3h8v11h-8V10Z",
  tasks: "M9 6h11M9 12h11M9 18h11M3.5 6l1.5 1.5L7 5M3.5 12l1.5 1.5L7 11M3.5 18l1.5 1.5L7 17",
  planner: "M7 3v3M17 3v3M4 8h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Zm3 7h3m2 0h3m-8 4h3",
  wellbeing: "M12 20.5S4 15.6 4 9.8A4.3 4.3 0 0 1 8.3 5.5c1.6 0 2.9.8 3.7 2.1.8-1.3 2.1-2.1 3.7-2.1A4.3 4.3 0 0 1 20 9.8c0 5.8-8 10.7-8 10.7Z",
  analytics: "M4 20V10m6 10V4m6 16v-7m5 7H3",
  settings: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm7.4-3a7.4 7.4 0 0 0-.1-1.2l2-1.5-2-3.5-2.3.9a7.6 7.6 0 0 0-2-1.2L14.6 3h-4l-.4 2.5a7.6 7.6 0 0 0-2 1.2l-2.3-.9-2 3.5 2 1.5a7.4 7.4 0 0 0 0 2.4l-2 1.5 2 3.5 2.3-.9a7.6 7.6 0 0 0 2 1.2l.4 2.5h4l.4-2.5a7.6 7.6 0 0 0 2-1.2l2.3.9 2-3.5-2-1.5c.1-.4.1-.8.1-1.2Z",
  plus: "M12 5v14M5 12h14",
  menu: "M4 7h16M4 12h16M4 17h16",
  bell: "M6 9a6 6 0 0 1 12 0c0 6 2 7 2 7H4s2-1 2-7Zm4.5 10a1.8 1.8 0 0 0 3 0",
  close: "M6 6l12 12M18 6L6 18",
  timer: "M12 8v5l3 2M9 2h6M12 21a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z",
  chevron: "M9 6l6 6-6 6",
  check: "M5 12.5l4.5 4.5L19 7.5",
  info: "M12 11v5M12 8h.01M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z",
  sun: "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0-14v2m0 14v2M3 12h2m14 0h2M5.6 5.6l1.4 1.4m10 10 1.4 1.4m0-12.8L17 7M7 17l-1.4 1.4",
  leaf: "M5 19c0-8 5-13 14-14 0 9-5 14-13 14Zm0 0c2-4 5-7 9-9",
  help: "M9.5 9a2.5 2.5 0 1 1 3.6 2.2c-.8.4-1.1 1-1.1 1.8M12 17h.01M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z",
  toolkit: "M5 4h9a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3V4Zm0 13a3 3 0 0 1 3-3h9M9 8h5",
  profile: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0",
  sparkle: "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Zm7 12l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z",
  play: "M7 4.5v15l12-7.5-12-7.5Z",
  pause: "M8 5v14M16 5v14",
  clock: "M12 7v5l3 2M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z",
  refresh: "M20 11a8 8 0 0 0-14.5-4M4 4v4h4M4 13a8 8 0 0 0 14.5 4M20 20v-4h-4",
  logout: "M15 17l5-5-5-5M20 12H9m4 8H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h8",
};

export default function Icon({ name, size = 20 }) {
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d={PATHS[name] || PATHS.dashboard} />
    </svg>
  );
}
