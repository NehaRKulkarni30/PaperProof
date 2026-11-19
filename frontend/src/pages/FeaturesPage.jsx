import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Columns2,
  AlertTriangle,
  Gauge,
  UserCheck,
  Share2,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { PaperMagnifierIllustration } from "../components/Illustrations";

const TOOLS = [
  {
    icon: Columns2,
    badge: "Verbatim Grounding",
    title: "Side-by-Side Evidence",
    desc: "Compare every extracted claim directly next to the exact highlighted passage from the cited study, complete with section name and page number.",
    points: [
      "Programmatic substring check ensures quotes are never fabricated",
      "Full-text open-access PDF chunking (arXiv & OpenAlex OA links)",
      "Instant toggle between compact card view and split-pane passage view",
    ],
  },
  {
    icon: AlertTriangle,
    badge: "Integrity Guardrails",
    title: "Misleading Citation Detection",
    desc: "Automatically surfaces the subtle failure modes that slip past superficial peer review and automated reference managers.",
    points: [
      "Reference mismatch alerts when a finding belongs to a different paper",
      "Missing reference & possible fabricated citation detection",
      "CrossRef & OpenAlex retraction status and outdated-source checks",
    ],
  },
  {
    icon: Gauge,
    badge: "Calibrated Uncertainty",
    title: "Confidence and Uncertainty",
    desc: "Every finding displays an animated confidence score paired with a transparent explanation of what was—and wasn't—available to check.",
    points: [
      "Automatic confidence cap when only the abstract is publicly accessible",
      "Explicit 'number not found' and 'scope mismatch' indicators",
      "Honest fallback to heuristic TF-IDF/BM25 mode if LLM quotas lapse",
    ],
  },
  {
    icon: UserCheck,
    badge: "Human-in-the-Loop",
    title: "Human Review Controls",
    desc: "PaperProof assists researchers rather than replacing academic judgment. Record formal decisions on every claim with a timestamped audit log.",
    points: [
      "One-click ACCEPTED, REJECTED, and NEEDS REVIEW workflow",
      "Optional reviewer notes saved persistently to SQLite",
      "Live Review History sidebar tracking every decision",
    ],
  },
  {
    icon: Share2,
    badge: "Collaboration & Export",
    title: "Reports and Sharing",
    desc: "Hand off a verifiable evidence trail to co-authors, thesis advisors, or journal editors in seconds.",
    points: [
      "One-click structured JSON report export for downstream audits",
      "Clean print stylesheet for saving formatted PDF reports",
      "Toggleable public read-only share links (/shared/:token)",
    ],
  },
];

export default function FeaturesPage() {
  const { isAuthenticated } = useAuth();

  return (
    <div>
      {/* Header band */}
      <section className="plum-hero text-cream-50">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center justify-between gap-8 md:flex-row">
            <div className="max-w-2xl">
              <span className="font-sans text-[11px] font-semibold uppercase tracking-[0.18em] text-gold">
                Capabilities
              </span>
              <h1 className="mt-2 font-display text-5xl font-bold leading-tight sm:text-6xl">
                Key tools for reliable verification.
              </h1>
              <p className="mt-4 font-serif text-lg text-cream-100/85">
                Designed for students, researchers, and peer reviewers who demand primary-source proof behind every citation.
              </p>
            </div>
            <PaperMagnifierIllustration className="w-40 h-40 shrink-0" />
          </div>
        </div>
      </section>

      {/* Feature cards grid */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-7 md:grid-cols-2 lg:grid-cols-3">
          {TOOLS.map((tool, idx) => {
            const Icon = tool.icon;
            return (
              <motion.div
                key={tool.title}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: idx * 0.06 }}
                whileHover={{ y: -4 }}
                className={`journal-card paper-texture p-7 flex flex-col justify-between ${
                  idx === 0 ? "lg:col-span-2" : ""
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-burgundy text-gold shadow-sm">
                      <Icon className="h-6 w-6" />
                    </div>
                    <span className="rounded-full border border-gold/40 bg-gold/10 px-3 py-1 font-sans text-[10px] font-bold uppercase tracking-[0.14em] text-burgundy">
                      {tool.badge}
                    </span>
                  </div>
                  <h2 className="mt-5 font-display text-3xl font-bold text-plum-900">
                    {tool.title}
                  </h2>
                  <p className="mt-2.5 font-serif text-base leading-relaxed text-ink-muted">
                    {tool.desc}
                  </p>
                  <ul className="mt-5 space-y-2">
                    {tool.points.map((pt) => (
                      <li key={pt} className="flex items-start gap-2 font-sans text-xs text-ink">
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-verdict-supported mt-0.5" />
                        <span>{pt}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </motion.div>
            );
          })}
        </div>

        <div className="mt-14 text-center">
          <Link to={isAuthenticated ? "/verify" : "/signup"} className="btn-primary px-8 py-3.5">
            Try PaperProof Free <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
