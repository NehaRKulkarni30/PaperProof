import React from "react";

export function PaperMagnifierIllustration({ className = "w-44 h-44" }) {
  return (
    <svg viewBox="0 0 200 200" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      <rect x="26" y="20" width="110" height="146" rx="12" fill="#FBF3EC" stroke="#C9A06A" strokeWidth="2.5" />
      <rect x="42" y="40" width="54" height="8" rx="4" fill="#5A1538" />
      <rect x="42" y="58" width="76" height="5" rx="2.5" fill="#D8C3A5" />
      <rect x="42" y="70" width="68" height="5" rx="2.5" fill="#D8C3A5" />
      <rect x="42" y="88" width="76" height="12" rx="4" fill="#C9A06A" fillOpacity="0.28" />
      <rect x="42" y="108" width="62" height="5" rx="2.5" fill="#D8C3A5" />
      <rect x="42" y="120" width="50" height="5" rx="2.5" fill="#D8C3A5" />
      {/* Magnifier */}
      <circle cx="132" cy="122" r="34" fill="#3B1730" stroke="#C9A06A" strokeWidth="4" />
      <circle cx="132" cy="122" r="26" fill="#4A1F3F" />
      <path d="M120 122.5L128.5 131L146 113.5" stroke="#C9A06A" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M156 146L176 166" stroke="#5A1538" strokeWidth="8" strokeLinecap="round" />
      <path d="M156 146L176 166" stroke="#C9A06A" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function StackedBooksPlantIllustration({ className = "w-56 h-48" }) {
  return (
    <svg viewBox="0 0 240 200" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      {/* Bottom book */}
      <rect x="26" y="146" width="168" height="28" rx="6" fill="#3B1730" stroke="#C9A06A" strokeWidth="2" />
      <rect x="40" y="154" width="60" height="4" rx="2" fill="#C9A06A" />
      <rect x="166" y="151" width="22" height="18" rx="2" fill="#F5EBDD" />
      {/* Middle book */}
      <rect x="42" y="116" width="142" height="28" rx="6" fill="#5A1538" stroke="#E8D9C3" strokeWidth="2" />
      <rect x="56" y="125" width="48" height="4" rx="2" fill="#FBF3EC" />
      <rect x="154" y="121" width="24" height="18" rx="2" fill="#FBF3EC" />
      {/* Top book */}
      <rect x="34" y="88" width="134" height="26" rx="6" fill="#C9A06A" stroke="#3B1730" strokeWidth="2" />
      <rect x="48" y="98" width="54" height="4" rx="2" fill="#3B1730" />
      {/* Ceramic pot */}
      <path d="M148 88H188L182 114H154L148 88Z" fill="#E8D9C3" stroke="#5A1538" strokeWidth="2" />
      <rect x="145" y="83" width="46" height="7" rx="3" fill="#5A1538" />
      {/* Botanical leaves */}
      <path d="M168 83C168 62 152 46 140 42C146 60 154 74 168 83Z" fill="#3B7D3A" />
      <path d="M168 83C170 58 186 40 200 36C194 56 184 72 168 83Z" fill="#2E9E7E" />
      <path d="M168 83C166 56 168 32 170 20C176 38 176 60 168 83Z" fill="#3B7D3A" />
      {/* Gold sparkles */}
      <circle cx="62" cy="48" r="4" fill="#C9A06A" />
      <circle cx="88" cy="36" r="2.5" fill="#C9A06A" fillOpacity="0.6" />
      <circle cx="206" cy="72" r="3" fill="#C9A06A" />
    </svg>
  );
}

export function DocumentMedalIllustration({ className = "w-16 h-16" }) {
  return (
    <svg viewBox="0 0 80 80" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      <rect x="12" y="8" width="44" height="58" rx="7" fill="#5A1538" stroke="#C9A06A" strokeWidth="2" />
      <path d="M22 24H46M22 33H46M22 42H36" stroke="#FBF3EC" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M51 56L46 72L54 67L62 72L57 56" fill="#B8862B" />
      <circle cx="54" cy="48" r="14" fill="#C9A06A" stroke="#FBF3EC" strokeWidth="2.5" />
      <path d="M48 48.5L52 52.5L60.5 44" stroke="#2A1424" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
