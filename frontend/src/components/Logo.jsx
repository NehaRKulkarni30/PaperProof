import React from "react";

export default function Logo({ light = false, size = "md" }) {
  const iconSize = size === "lg" ? 42 : size === "sm" ? 28 : 36;
  const textSize =
    size === "lg" ? "text-3xl" : size === "sm" ? "text-xl" : "text-2xl";

  return (
    <span className="inline-flex items-center gap-2.5 select-none">
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 80 80"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0"
      >
        {/* Gold-bordered plum document sheet */}
        <rect
          x="12"
          y="8"
          width="44"
          height="58"
          rx="7"
          fill="#5A1538"
          stroke="#C9A06A"
          strokeWidth="2.4"
        />
        {/* Three cream text lines */}
        <path
          d="M22 24H46M22 33H46M22 42H36"
          stroke="#FBF3EC"
          strokeWidth="2.8"
          strokeLinecap="round"
        />
        {/* Ribbon tails beneath seal */}
        <path d="M51 56L46 72L54 67L62 72L57 56" fill="#B8862B" />
        {/* Gold checkmark seal with cream ring */}
        <circle
          cx="54"
          cy="48"
          r="14"
          fill="#C9A06A"
          stroke="#FBF3EC"
          strokeWidth="2.8"
        />
        <path
          d="M48 48.5L52 52.5L60.5 44"
          stroke="#2A1424"
          strokeWidth="3"
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
