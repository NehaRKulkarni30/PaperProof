import React from "react";
import { motion } from "framer-motion";

export const VERDICT_META = {
  supported: {
    label: "Supported",
    shortLabel: "SUPPORTED",
    color: "#3B7D3A",
    bg: "bg-[#3B7D3A]/12",
    text: "text-[#2E632D]",
    border: "border-[#3B7D3A]/35",
  },
  partly_supported: {
    label: "Partly supported",
    shortLabel: "PARTLY SUPPORTED",
    color: "#B8741A",
    bg: "bg-[#B8741A]/12",
    text: "text-[#945B11]",
    border: "border-[#B8741A]/35",
  },
  unsupported: {
    label: "Unsupported",
    shortLabel: "UNSUPPORTED",
    color: "#A63030",
    bg: "bg-[#A63030]/12",
    text: "text-[#8C2424]",
    border: "border-[#A63030]/35",
  },
  reference_not_found: {
    label: "Reference not found",
    shortLabel: "REFERENCE NOT FOUND",
    color: "#5A5A5A",
    bg: "bg-[#5A5A5A]/12",
    text: "text-[#464646]",
    border: "border-[#5A5A5A]/35",
  },
  contradictory: {
    label: "Contradictory",
    shortLabel: "CONTRADICTORY",
    color: "#5B4FC4",
    bg: "bg-[#5B4FC4]/12",
    text: "text-[#473CA3]",
    border: "border-[#5B4FC4]/35",
  },
  possibly_outdated: {
    label: "Possibly outdated",
    shortLabel: "POSSIBLY OUTDATED",
    color: "#2E9E7E",
    bg: "bg-[#2E9E7E]/12",
    text: "text-[#227A61]",
    border: "border-[#2E9E7E]/35",
  },
};

export default function DonutChart({
  counts = {},
  total = 0,
  centerValue,
  centerLabel = "Claims",
  size = 180,
  strokeWidth = 22,
  activeFilter = null,
  onSelectVerdict = null,
  showLegend = true,
  dark = false,
}) {
  const keys = Object.keys(VERDICT_META);
  const sum =
    total || keys.reduce((acc, k) => acc + (Number(counts[k]) || 0), 0);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  let cumulative = 0;
  const segments = keys
    .map((key) => {
      const value = Number(counts[key]) || 0;
      if (value <= 0 || sum <= 0) return null;
      const frac = value / sum;
      const segLen = frac * circumference;
      const offset = cumulative;
      cumulative += segLen;
      return {
        key,
        value,
        segLen,
        offset,
        color: VERDICT_META[key].color,
      };
    })
    .filter(Boolean);

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
          {/* Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={dark ? "rgba(251,243,236,0.12)" : "#E8D9C3"}
            strokeWidth={strokeWidth}
          />
          {segments.map((seg, i) => {
            const isDimmed = activeFilter && activeFilter !== "all" && activeFilter !== seg.key;
            const gap = segments.length > 1 ? 2.5 : 0;
            const dashLen = Math.max(seg.segLen - gap, 2);
            const dashRest = Math.max(circumference - dashLen, 0);
            return (
              <motion.circle
                key={`${seg.key}-${sum}`}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={seg.color}
                strokeWidth={strokeWidth}
                strokeDashoffset={-seg.offset}
                strokeLinecap="butt"
                pointerEvents="stroke"
                initial={{
                  opacity: 0,
                  strokeDasharray: `0 ${circumference}`,
                }}
                animate={{
                  opacity: isDimmed ? 0.3 : 1,
                  strokeDasharray: `${dashLen} ${dashRest}`,
                }}
                transition={{ duration: 0.7, delay: i * 0.08, ease: "easeOut" }}
                className={onSelectVerdict ? "cursor-pointer transition-opacity" : ""}
                onClick={() => onSelectVerdict && onSelectVerdict(seg.key)}
              />
            );
          })}
        </svg>

        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
          <span
            className={`font-display text-4xl font-bold leading-none ${
              dark ? "text-cream-50" : "text-plum-900"
            }`}
          >
            {centerValue !== undefined ? centerValue : sum}
          </span>
          <span
            className={`mt-1 font-sans text-[10px] font-semibold uppercase tracking-[0.16em] ${
              dark ? "text-gold" : "text-ink-soft"
            }`}
          >
            {centerLabel}
          </span>
        </div>
      </div>

      {showLegend && (
        <div className="w-full space-y-1.5">
          {keys.map((key) => {
            const meta = VERDICT_META[key];
            const val = Number(counts[key]) || 0;
            const isActive = activeFilter === key;
            return (
              <button
                key={key}
                type="button"
                disabled={!onSelectVerdict}
                onClick={() => onSelectVerdict && onSelectVerdict(isActive ? "all" : key)}
                className={`flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left transition-colors ${
                  onSelectVerdict
                    ? isActive
                      ? "bg-burgundy/10 ring-1 ring-burgundy/30"
                      : "hover:bg-sand-200/70 cursor-pointer"
                    : "cursor-default"
                }`}
              >
                <span className="flex items-center gap-2 font-sans text-xs">
                  <span
                    className="h-2.5 w-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: meta.color }}
                  />
                  <span className={dark ? "text-cream-100" : "text-ink"}>{meta.label}</span>
                </span>
                <span
                  className={`font-sans text-xs font-semibold tabular-nums ${
                    dark ? "text-gold" : "text-ink-muted"
                  }`}
                >
                  {val}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
