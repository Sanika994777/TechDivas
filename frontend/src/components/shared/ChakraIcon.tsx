/** Ashoka Chakra — 24-spoke wheel in navy line-art SVG */

interface ChakraIconProps {
  size?: number;
  color?: string;
  spinning?: boolean;
  className?: string;
}

export function ChakraIcon({
  size = 32,
  color = "#000080",
  spinning = false,
  className = "",
}: ChakraIconProps) {
  const spokes = Array.from({ length: 24 }, (_, i) => {
    const angle = (i * 360) / 24;
    const rad = (angle * Math.PI) / 180;
    const cx = 16, cy = 16, r1 = 5, r2 = 13;
    const x1 = cx + r1 * Math.sin(rad);
    const y1 = cy - r1 * Math.cos(rad);
    const x2 = cx + r2 * Math.sin(rad);
    const y2 = cy - r2 * Math.cos(rad);
    return { x1, y1, x2, y2 };
  });

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`${spinning ? "animate-chakra" : ""} ${className}`}
      aria-hidden="true"
    >
      {/* Outer ring */}
      <circle cx="16" cy="16" r="13" stroke={color} strokeWidth="1.5" />
      {/* Inner hub */}
      <circle cx="16" cy="16" r="4" stroke={color} strokeWidth="1.5" />
      {/* 24 spokes */}
      {spokes.map((s, i) => (
        <line
          key={i}
          x1={s.x1} y1={s.y1}
          x2={s.x2} y2={s.y2}
          stroke={color}
          strokeWidth="0.7"
          strokeLinecap="round"
        />
      ))}
    </svg>
  );
}

/** Full-page loading overlay with spinning chakra */
export function ChakraSpinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24" role="status" aria-live="polite">
      <ChakraIcon size={56} spinning />
      <p className="text-navy-900/60 text-sm font-body">{label}</p>
    </div>
  );
}

/** Skeleton card placeholder */
export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="rounded-card bg-white shadow-card p-4 animate-pulse">
      <div className="h-40 bg-gray-200 rounded-lg mb-3" />
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
      {Array.from({ length: lines - 1 }).map((_, i) => (
        <div key={i} className={`h-3 bg-gray-100 rounded mb-2 ${i === lines - 2 ? "w-1/2" : "w-full"}`} />
      ))}
    </div>
  );
}
