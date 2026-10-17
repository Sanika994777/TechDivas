import { useState, useRef } from "react";

interface BeforeAfterProps {
  beforeSrc: string;
  afterSrc: string;
  beforeLabel?: string;
  afterLabel?: string;
}

export function BeforeAfter({
  beforeSrc,
  afterSrc,
  beforeLabel = "Before",
  afterLabel = "After",
}: BeforeAfterProps) {
  const [pos, setPos] = useState(50); // 0–100 %
  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  function updatePos(clientX: number) {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const pct = Math.min(100, Math.max(0, ((clientX - rect.left) / rect.width) * 100));
    setPos(pct);
  }

  return (
    <div
      ref={containerRef}
      className="relative select-none overflow-hidden rounded-card cursor-col-resize"
      style={{ touchAction: "none" }}
      onMouseDown={() => { dragging.current = true; }}
      onMouseUp={() => { dragging.current = false; }}
      onMouseLeave={() => { dragging.current = false; }}
      onMouseMove={(e) => { if (dragging.current) updatePos(e.clientX); }}
      onTouchMove={(e) => updatePos(e.touches[0].clientX)}
      aria-label="Before and after comparison slider"
    >
      {/* After image (full) */}
      <img src={afterSrc} alt={afterLabel} className="w-full h-56 sm:h-72 object-cover block" />

      {/* Before image (clipped by slider position) */}
      <div
        className="absolute inset-0 overflow-hidden"
        style={{ width: `${pos}%` }}
      >
        <img
          src={beforeSrc}
          alt={beforeLabel}
          className="absolute inset-0 w-full h-full object-cover"
          style={{ width: `${10000 / pos}%`, maxWidth: "none" }}
        />
      </div>

      {/* Divider line + handle */}
      <div
        className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg"
        style={{ left: `${pos}%` }}
      >
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 bg-white rounded-full shadow-lg flex items-center justify-center text-navy font-bold text-xs">
          ⇔
        </div>
      </div>

      {/* Labels */}
      <span className="absolute bottom-2 left-2 bg-black/50 text-white text-xs px-2 py-0.5 rounded-badge">
        {beforeLabel}
      </span>
      <span className="absolute bottom-2 right-2 bg-black/50 text-white text-xs px-2 py-0.5 rounded-badge">
        {afterLabel}
      </span>
    </div>
  );
}
