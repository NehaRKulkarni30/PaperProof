import React from "react";

export default function Logo({ light = false, size = "md" }) {
  const iconSize = size === "lg" ? 38 : size === "sm" ? 26 : 32;
  const textSize =
    size === "lg" ? "text-3xl" : size === "sm" ? "text-xl" : "text-2xl";

  return (
    <span className="inline-flex items-center gap-2.5 select-none">
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0"
      >
        {/* Document sheet */}
        <rect
          x="5"
          y="3"
          width="24"
          height="32"
          rx="4"
          fill={light ? "#FBF3EC" : "#5A1538"}
          stroke={light ? "#C9A06A" : "#3B1730"}
          strokeWidth="1.5"
        />
        {/* Folded corner / lines */}
        <path
          d="M11 12H23M11 17H23M11 22H18"
          stroke={light ? "#5A1538" : "#F5EBDD"}
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        {/* Gold medal check-mark badge */}
        <circle
          cx="29"
          cy="28"
          r="9"
          fill="#C9A06A"
          stroke={light ? "#3B1730" : "#FBF3EC"}
          strokeWidth="2.2"
        />
        <path
          d="M25.2 28.2L27.8 30.8L33 25.4"
          stroke="#2A1424"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span
        className={`font-display font-bold tracking-tight ${textSize} ${
          light ? "text-cream-50" : "text-plum-900"
        }`}
      >
        Paper<span className={light ? "text-gold" : "text-burgundy"}>Proof</span>
      </span>
    </span>
  );
}
