import { useId } from "react";

// The MindSync "M" logo mark. useId keeps each gradient id unique when the
// mark appears more than once on a page.
export default function BrandMark({ className = "brand-mark" }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg className={className} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <defs>
        <linearGradient id={`bg${id}`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#7c93ff" />
          <stop offset="45%" stopColor="#5a73ee" />
          <stop offset="100%" stopColor="#3b55d9" />
        </linearGradient>
      </defs>
      <path
        d="M12 72 C 26 22, 38 22, 50 56 C 62 22, 74 22, 88 72"
        fill="none"
        stroke={`url(#bg${id})`}
        strokeWidth="11"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
