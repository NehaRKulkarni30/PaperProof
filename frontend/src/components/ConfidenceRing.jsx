import React from "react";
import { motion } from "framer-motion";

export default function ConfidenceRing({ value = 0, size = 56, strokeWidth = 5 }) {
  const clamped = Math.max(0, Math.min(100, Number(value) || 0));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;

  const color =
    clamped >= 80 ? "#3B7D3A" : clamped >= 55 ? "#B8862B" : "#A63030";

  return (
    <div className="relative inline-flex items-center justify-center shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#E8D9C3"
          strokeWidth={strokeWidth}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.85, ease: "easeOut" }}
        />
      </svg>
      <span className="absolute font-sans text-xs font-bold text-plum-900 tabular-nums">
        {clamped}%
      </span>
    </div>
  );
}
