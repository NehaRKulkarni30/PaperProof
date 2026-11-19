import React from "react";
import { motion } from "framer-motion";
import { Target, Eye, ShieldCheck, Award, BookOpen } from "lucide-react";
import { StackedBooksPlantIllustration } from "../components/Illustrations";

const VALUES = [
  {
    icon: Target,
    title: "Accuracy",
    desc: "Every verdict is strictly grounded in retrieved passages from the cited study—never guessed from parametric memory. Quotes are programmatically verified verbatim.",
  },
  {
    icon: Eye,
    title: "Transparency",
    desc: "We show exact source traces, direct paper and PDF links, processing mode (Gemini or Heuristic), and explicit confidence caps when only an abstract is open-access.",
  },
  {
    icon: ShieldCheck,
    title: "Research Integrity",
    desc: "A citation is not proof by itself. PaperProof empowers human reviewers with structured evidence controls rather than issuing opaque automated judgments.",
  },
];

const SOURCE_CHIPS = [
  { name: "Semantic Scholar", desc: "Graph API metadata & abstracts" },
  { name: "CrossRef", desc: "DOI resolution & retraction notices" },
  { name: "OpenAlex", desc: "Open catalog & OA locations" },
  { name: "arXiv", desc: "Full-text open preprint PDFs" },
];

export default function AboutPage() {
  return (
    <div>
      {/* Burgundy Hero */}
      <section className="bg-burgundy text-cream-50 relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-20"
          style={{
            background:
              "radial-gradient(circle at 80% 20%, #C9A06A, transparent 50%), radial-gradient(circle at 15% 85%, #3B1730, transparent 55%)",
          }}
        />
        <div className="relative mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-10">
          <div className="max-w-2xl">
            <span className="font-sans text-[11px] font-semibold uppercase tracking-[0.18em] text-gold">
              About PaperProof
            </span>
            <h1 className="mt-2 font-display text-5xl font-bold leading-tight sm:text-6xl">
              Building trust in every citation.
            </h1>
            <p className="mt-4 font-serif text-lg leading-relaxed text-cream-100/90">
              Academic literature moves fast, and misquoted statistics, mismatched citations, and phantom references erode scientific credibility. PaperProof turns bibliography checking into a fast, evidence-backed review workflow.
            </p>
          </div>
          <StackedBooksPlantIllustration className="w-56 h-48 shrink-0" />
        </div>
      </section>

      {/* Our Story & Our Mission */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="journal-card paper-texture p-8"
          >
            <span className="label-caps text-burgundy flex items-center gap-1.5">
              <BookOpen className="h-3.5 w-3.5" /> Our Story
            </span>
            <h2 className="mt-2 font-display text-3xl font-bold text-plum-900">
              Why we built PaperProof
            </h2>
            <p className="mt-3 font-serif text-base leading-relaxed text-ink-muted">
              Students, researchers, and reviewers spend hours chasing down cited studies—only to discover that a referenced paper never reported the claimed percentage, studied a completely different task, or does not exist at all. We built PaperProof during INNOVEDGE Hackathon 2026 to bridge the gap between citing a source and actually proving a claim against it.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.08 }}
            className="journal-card paper-texture p-8"
          >
            <span className="label-caps text-gold-amber flex items-center gap-1.5">
              <Target className="h-3.5 w-3.5" /> Our Mission
            </span>
            <h2 className="mt-2 font-display text-3xl font-bold text-plum-900">
              Evidence-first scholarship
            </h2>
            <p className="mt-3 font-serif text-base leading-relaxed text-ink-muted">
              Our mission is to make rigorous primary-source verification accessible to every author and educator using open scholarly infrastructure—combining structured retrieval, calibrated uncertainty, and human-in-the-loop review so every published claim stands on solid ground.
            </p>
          </motion.div>
        </div>

        {/* Our Values */}
        <div className="mt-16">
          <div className="text-center mb-10">
            <span className="label-caps text-burgundy">Core Principles</span>
            <h2 className="mt-2 font-display text-4xl font-bold text-plum-900">
              Our Values
            </h2>
          </div>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {VALUES.map((v, idx) => {
              const Icon = v.icon;
              return (
                <motion.div
                  key={v.title}
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.07 }}
                  className="journal-card p-6"
                >
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-plum-900 text-gold">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="mt-4 font-display text-2xl font-bold text-plum-900">
                    {v.title}
                  </h3>
                  <p className="mt-2 font-serif text-sm leading-relaxed text-ink-muted">
                    {v.desc}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Where sources come from */}
        <div className="mt-16 rounded-2xl border border-sand-300 bg-cream-100/90 p-8 text-center shadow-journal">
          <span className="label-caps text-gold-amber">Open Scholarly APIs</span>
          <h2 className="mt-1.5 font-display text-3xl font-bold text-plum-900">
            Where sources come from
          </h2>
          <p className="mx-auto mt-2 max-w-xl font-serif text-sm text-ink-muted">
            PaperProof queries only open, respected scholarly registries and respects polite API rate limits and caching.
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            {SOURCE_CHIPS.map((chip) => (
              <div
                key={chip.name}
                className="rounded-full border border-burgundy/25 bg-cream-50 px-5 py-2.5 shadow-sm"
              >
                <span className="font-sans text-xs font-bold text-burgundy">
                  {chip.name}
                </span>
                <span className="mx-2 text-sand-300">·</span>
                <span className="font-sans text-xs text-ink-muted">{chip.desc}</span>
              </div>
            ))}
          </div>
        </div>

        {/* The Team */}
        <div className="mt-16 plum-hero rounded-3xl p-8 sm:p-12 text-center text-cream-50 shadow-journal-lg">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-gold/50 bg-gold/15 text-gold">
            <Award className="h-7 w-7" />
          </div>
          <span className="font-sans text-[11px] font-semibold uppercase tracking-[0.2em] text-gold">
            The Team
          </span>
          <h2 className="mt-2 font-display text-4xl font-bold sm:text-5xl">
            AI INNOVATORS
          </h2>
          <p className="mt-3 font-sans text-xs uppercase tracking-[0.16em] text-cream-100/80">
            Built for INNOVEDGE Hackathon 2026 · Problem Statement 03 (CiteVerify)
          </p>
          <p className="mx-auto mt-4 max-w-2xl font-serif text-base italic text-gold-light">
            “A citation is not proof by itself. This is an automated evidence check, not a final academic judgment. Review every finding.”
          </p>
        </div>
      </section>
    </div>
  );
}
