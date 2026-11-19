import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  UploadCloud,
  Sparkles,
  Globe,
  Scale,
  FileCheck2,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

const STEPS = [
  {
    num: "01",
    title: "Upload Paper",
    icon: UploadCloud,
    desc: "Drop a PDF, DOCX, or TXT manuscript (up to 15 MB) or paste text with a References section. PaperProof extracts clean page-numbered text and automatically separates the body from the bibliography.",
    widget: (
      <div className="rounded-xl border border-dashed border-burgundy/40 bg-cream-50 p-4">
        <div className="flex items-center justify-between font-sans text-xs">
          <span className="font-semibold text-plum-900">manuscript_draft.pdf</span>
          <span className="rounded bg-verdict-supported/15 px-2 py-0.5 text-[10px] font-bold text-verdict-supported">
            12 Pages · Split OK
          </span>
        </div>
        <div className="mt-2.5 flex gap-2 font-sans text-[10px] uppercase tracking-wider text-ink-soft">
          <span className="rounded bg-sand-200 px-2 py-1">Body: pp. 1–10</span>
          <span className="rounded bg-gold/25 px-2 py-1 text-plum-900">References: pp. 11–12</span>
        </div>
      </div>
    ),
  },
  {
    num: "02",
    title: "Extract Claims",
    icon: Sparkles,
    desc: "Gemini identifies high-priority factual statements, statistics, and empirical conclusions—preserving verbatim wording and mapping inline markers like [1] or (Vaswani et al., 2017) to bibliography entries.",
    widget: (
      <div className="rounded-xl border border-sand-300 bg-cream-50 p-4 space-y-2">
        <p className="font-serif text-xs text-ink">
          “The Transformer relies entirely on attention mechanisms{" "}
          <span className="rounded bg-gold/35 px-1 font-sans font-bold text-plum-900">[1]</span>.”
        </p>
        <div className="flex items-center justify-between font-sans text-[10px] text-ink-soft">
          <span>Mapped → Vaswani et al. (2017)</span>
          <span className="font-semibold text-burgundy">arXiv:1706.03762</span>
        </div>
      </div>
    ),
  },
  {
    num: "03",
    title: "Find Sources",
    icon: Globe,
    desc: "A concurrent lookup cascade queries arXiv, CrossRef, Semantic Scholar, and OpenAlex—validating matches by fuzzy title similarity and year, checking retraction flags, and downloading open-access PDFs for full-text chunking.",
    widget: (
      <div className="grid grid-cols-2 gap-2">
        {["arXiv API", "CrossRef DOI", "Semantic Scholar", "OpenAlex OA"].map((db, i) => (
          <div
            key={db}
            className="flex items-center gap-1.5 rounded-lg border border-sand-300 bg-cream-50 px-2.5 py-2 font-sans text-[11px] font-medium text-plum-900"
          >
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: i === 0 ? "#3B7D3A" : "#C9A06A" }}
            />
            {db}
          </div>
        ))}
      </div>
    ),
  },
  {
    num: "04",
    title: "Compare Evidence",
    icon: Scale,
    desc: "BM25 passage ranking retrieves the top 3 relevant sections from the cited paper. Gemini evaluates strict entailment against ONLY those passages, and PaperProof programmatically verifies every verbatim quote.",
    widget: (
      <div className="rounded-xl border border-gold/40 bg-plum-900 p-4 text-cream-50 space-y-2">
        <div className="flex items-center justify-between font-sans text-[10px]">
          <span className="inline-flex items-center gap-1 text-verdict-supported font-bold bg-cream-50 px-2 py-0.5 rounded-full">
            <CheckCircle2 className="h-3 w-3" /> VERBATIM MATCH
          </span>
          <span className="text-gold font-semibold">96% Confidence</span>
        </div>
        <p className="font-serif text-xs italic text-cream-100/90 border-l-2 border-gold pl-2.5">
          “...based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.”
        </p>
      </div>
    ),
  },
  {
    num: "05",
    title: "Generate Report",
    icon: FileCheck2,
    desc: "Review a structured claim-by-claim report with interactive verdict filters, misleading-citation alerts, Accept/Reject/Needs-Review controls, JSON export, print-ready PDF, and shareable read-only links.",
    widget: (
      <div className="rounded-xl border border-sand-300 bg-cream-50 p-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-sans text-xs">
          <AlertTriangle className="h-4 w-4 text-verdict-partly shrink-0" />
          <span className="text-ink font-medium">1 mismatch · 1 missing ref</span>
        </div>
        <span className="rounded-md bg-burgundy px-2.5 py-1 font-sans text-[10px] font-bold uppercase tracking-wider text-cream-50">
          Review Ready
        </span>
      </div>
    ),
  },
];

export default function HowItWorksPage() {
  const { isAuthenticated } = useAuth();

  return (
    <div>
      <section className="plum-hero text-cream-50">
        <div className="mx-auto max-w-5xl px-4 py-16 text-center sm:px-6 lg:px-8">
          <span className="font-sans text-[11px] font-semibold uppercase tracking-[0.18em] text-gold">
            Architecture &amp; Workflow
          </span>
          <h1 className="mt-2 font-display text-5xl font-bold sm:text-6xl">
            From paper to proof, in five steps.
          </h1>
          <p className="mx-auto mt-4 max-w-2xl font-serif text-lg text-cream-100/85">
            Every verdict is grounded in real scholarly metadata and verbatim passages—with full transparency whenever only an abstract is accessible.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="relative space-y-10 before:hidden md:before:block before:absolute before:left-[27px] before:top-4 before:bottom-4 before:w-0.5 before:bg-gradient-to-b before:from-gold before:via-burgundy/40 before:to-gold">
          {STEPS.map((step, idx) => {
            const Icon = step.icon;
            return (
              <motion.div
                key={step.num}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.45, delay: idx * 0.06 }}
                className="relative flex flex-col gap-5 md:flex-row md:items-start md:pl-20"
              >
                {/* Numbered node */}
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border-2 border-gold bg-plum-900 font-display text-2xl font-bold text-gold shadow-journal md:absolute md:left-0 md:top-1">
                  {step.num}
                </div>

                {/* Card */}
                <div className="journal-card paper-texture flex-1 p-6 sm:p-7 grid grid-cols-1 gap-6 lg:grid-cols-12 items-center">
                  <div className="lg:col-span-7">
                    <div className="flex items-center gap-2 text-burgundy">
                      <Icon className="h-4 w-4" />
                      <span className="label-caps text-burgundy">Stage {step.num}</span>
                    </div>
                    <h2 className="mt-1 font-display text-3xl font-bold text-plum-900">
                      {step.title}
                    </h2>
                    <p className="mt-2 font-serif text-[15px] leading-relaxed text-ink-muted">
                      {step.desc}
                    </p>
                  </div>
                  <div className="lg:col-span-5">{step.widget}</div>
                </div>
              </motion.div>
            );
          })}
        </div>

        <div className="mt-14 text-center">
          <Link to={isAuthenticated ? "/verify" : "/signup"} className="btn-primary px-8 py-3.5">
            Run a Verification Now <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
