// A photograph from /images (see CREDITS.md for who took it and the licence). Several sizes are offered to the
// browser so phones download the small one. Alt text is required, not optional.
// "focus" says which part of the picture must stay visible when the frame crops it (CSS object-position).
const SIZES = {
  hero: { widths: [800, 1280, 1920], w: 1920, h: 1078 },
  friends: { widths: [640, 1100], w: 1100, h: 733 },
  grass: { widths: [640, 1100], w: 1100, h: 733 },
  dashboard: { widths: [640, 1100], w: 1100, h: 733 },
  planner: { widths: [640, 1100], w: 1100, h: 733 },
  wellbeing: { widths: [640, 1100], w: 1100, h: 733 },
  progress: { widths: [640, 1100], w: 1100, h: 733 },
};

export default function Photo({ name, alt, className = "", sizes = "(max-width: 700px) 100vw, 520px", priority = false, focus }) {
  const s = SIZES[name];
  if (!s) return null;
  const src = (w) => `/images/${name}-${w}.webp`;
  return (
    <img
      className={`photo ${className}`}
      src={src(s.widths[s.widths.length - 1])}
      srcSet={s.widths.map((w) => `${src(w)} ${w}w`).join(", ")}
      sizes={sizes}
      width={s.w}
      height={s.h}
      alt={alt}
      loading={priority ? "eager" : "lazy"}
      fetchpriority={priority ? "high" : "auto"}
      decoding="async"
      style={focus ? { objectPosition: focus } : undefined}
    />
  );
}
