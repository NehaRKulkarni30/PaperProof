import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Sparkles,
  Globe,
  Scale,
  FileCheck2,
  Check,
  Loader2,
} from "lucide-react";

const STAGES = [
  { key: "upload", label: "Upload", desc: "Ingest & split", icon: FileText },
  { key: "extract", label: "Extract", desc: "Claims & refs", icon: Sparkles },
  { key: "retrieve", label: "Retrieve", desc: "Scholarly APIs", icon: Globe },
  { key: "compare", label: "Compare", desc: "Evidence check", icon: Scale },
  { key: "report", label: "Report", desc: "Audit assembly", icon: FileCheck2 },
];

export default function ProcessingStepper({ statusData, filename }) {
  const currentStage = statusData?.stage || "upload";
  const progress = statusData?.progress ?? 8;
  const message = statusData?.status_message || "Starting verification pipeline…";
  const partialClaims = statusData?.partial_claims || [];
  const currentIndex = Math.max(
    0,
    STAGES.findIndex((s) => s.key === currentStage)
  );

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <div className="rounded-3xl border border-gold/25 bg-plum-900 p-7 sm:p-10 text-cream-50 shadow-journal-lg">
        <div className="flex flex-col items-center text-center">
          {/* Scanning document SVG graphic */}
          <div className="relative mb-6 flex h-44 w-36 items-center justify-center rounded-2xl border border-gold/40 bg-cream-50/95 p-4 shadow-journal overflow-hidden">
            <div className="w-full space-y-2.5 opacity-80">
              <div className="h-3 w-3/4 rounded bg-burgundy/80" />
              <div className="h-2 w-full rounded bg-sand-300" />
              <div className="h-2 w-5/6 rounded bg-sand-300" />
              <div className="h-2.5 w-full rounded bg-gold/45" />
              <div className="h-2 w-4/5 rounded bg-sand-300" />
              <div className="h-2 w-full rounded bg-sand-300" />
              <div className="h-2.5 w-2/3 rounded bg-verdict-supported/35" />
              <div className="h-2 w-5/6 rounded bg-sand-300" />
            </div>
            {/* Animated gold scanning laser line */}
            <div className="animate-scan-line pointer-events-none absolute left-0 right-0 top-0 h-1 bg-gradient-to-r from-transparent via-gold to-transparent shadow-[0_0_16px_4px_rgba(201,160,106,0.75)]" />
          </div>

          <span className="font-sans text-[11px] font-semibold uppercase tracking-[0.2em] text-gold">
            Automated Evidence Pipeline Running
          </span>
          <h2 className="mt-2 font-display text-3xl font-bold text-cream-50 sm:text-4xl">
            Verifying {filename || "your manuscript"}
          </h2>
          <p className="mt-2 font-serif text-base text-cream-100/85 min-h-[26px]">
            {message}
          </p>
        </div>

        {/* 5-step horizontal stepper */}
        <div className="mt-8 grid grid-cols-5 gap-2 sm:gap-4">
          {STAGES.map((stage, idx) => {
            const Icon = stage.icon;
            const isDone = idx < currentIndex || progress >= 100;
            const isActive = idx === currentIndex && progress < 100;
            return (
              <div key={stage.key} className="flex flex-col items-center text-center">
                <div
                  className={`flex h-11 w-11 items-center justify-center rounded-full border-2 transition-all duration-300 ${
                    isDone
                      ? "border-gold bg-gold text-plum-950"
                      : isActive
                      ? "border-gold bg-plum-800 text-gold shadow-[0_0_18px_rgba(201,160,106,0.45)]"
                      : "border-white/20 bg-white/5 text-cream-100/40"
                  }`}
                >
                  {isDone ? (
                    <Check className="h-5 w-5" />
                  ) : isActive ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </div>
                <span
                  className={`mt-2 font-sans text-[11px] font-semibold uppercase tracking-[0.12em] ${
                    isDone || isActive ? "text-cream-50" : "text-cream-100/40"
                  }`}
                >
                  {stage.label}
                </span>
                <span className="hidden sm:block font-sans text-[10px] text-cream-100/55">
                  {stage.desc}
                </span>
              </div>
            );
          })}
        </div>

        {/* Progress bar */}
        <div className="mt-7">
          <div className="mb-1.5 flex items-center justify-between font-sans text-xs">
            <span className="text-cream-100/75">
              {statusData?.references_found > 0
                ? `${statusData.references_found} references · ${statusData.claims_found} claims extracted`
                : "Analyzing document structure…"}
            </span>
            <span className="font-semibold text-gold tabular-nums">{progress}%</span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/10">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-gold-amber via-gold to-gold-light"
              initial={{ width: "4%" }}
              animate={{ width: `${Math.max(5, progress)}%` }}
              transition={{ duration: 0.45, ease: "easeOut" }}
            />
          </div>
        </div>

        {/* Live claims popping in */}
        {partialClaims.length > 0 && (
          <div className="mt-7 border-t border-white/10 pt-5">
            <p className="mb-3 font-sans text-[11px] font-semibold uppercase tracking-[0.16em] text-gold">
              Claims Detected ({statusData.claims_found})
            </p>
            <div className="max-h-48 space-y-2 overflow-y-auto pr-1">
              <AnimatePresence>
                {partialClaims.map((cl) => (
                  <motion.div
                    key={cl.idx}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-start gap-2.5 rounded-xl border border-white/10 bg-white/5 px-3.5 py-2.5"
                  >
                    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gold/20 font-sans text-[10px] font-bold text-gold">
                      {cl.idx}
                    </span>
                    <p className="font-serif text-sm text-cream-100/90 leading-snug">
                      {cl.text}
                    </p>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
