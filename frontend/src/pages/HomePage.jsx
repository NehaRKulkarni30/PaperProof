import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import {
  ArrowRight,
  FileSearch,
  Link2,
  Scale,
  FileCheck2,
  CheckCircle2,
  Sparkles,
  BookMarked,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import LiveMiniDemo from "../components/LiveMiniDemo";

const FEATURE_CARDS = [
  {
    icon: FileSearch,
    title: "Extract Claims",
    desc: "Pinpoints checkable factual statements, numerical findings, and citation markers while preserving page numbers.",
  },
  {
    icon: Link2,
    title: "Verify Citations",
    desc: "Matches every inline marker to its bibliography entry and retrieves the original study via arXiv, CrossRef, Semantic Scholar, and OpenAlex.",
  },
  {
    icon: Scale,
    title: "Assess Evidence",
    desc: "Compares each claim strictly against verbatim passages from the cited source, flagging mismatches, missing figures, and retractions.",
  },
  {
    icon: FileCheck2,
    title: "Generate Reports",
    desc: "Produces an interactive, reviewer-ready audit report with confidence rings, side-by-side passages, JSON export, and print-ready PDF.",
  },
];

const SOURCES = [
  { name: "Semantic Scholar", tag: "200M+ Papers & Graph API" },
  { name: "CrossRef", tag: "DOI & Retraction Registry" },
  { name: "OpenAlex", tag: "Open Scholarly Catalog" },
  { name: "arXiv", tag: "Full-Text Open Preprints" },
];

export default function HomePage() {
  const { isAuthenticated } = useAuth();
  const [pct, setPct] = useState(0);

  // Subtle mouse-parallax for the hero paper graphic
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const smoothX = useSpring(mouseX, { stiffness: 90, damping: 18 });
  const smoothY = useSpring(mouseY, { stiffness: 90, damping: 18 });
  const paperX = useTransform(smoothX, [-1, 1], [-12, 12]);
  const paperY = useTransform(smoothY, [-1, 1], [-8, 8]);
  const cardX = useTransform(smoothX, [-1, 1], [10, -10]);
  const cardY = useTransform(smoothY, [-1, 1], [6, -6]);

  useEffect(() => {
    let cur = 0;
    const id = setInterval(() => {
      cur += 3;
      if (cur >= 92) {
        setPct(92);
        clearInterval(id);
      } else {
        setPct(cur);
      }
    }, 22);
    return () => clearInterval(id);
  }, []);

  const handleHeroMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const nx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    const ny = ((e.clientY - rect.top) / rect.height) * 2 - 1;
    mouseX.set(nx);
    mouseY.set(ny);
  };

  const donutRadius = 46;
  const donutCirc = 2 * Math.PI * donutRadius;

  return (
    <div className="overflow-x-hidden">
      {/* PLUM HERO */}
      <section
        onMouseMove={handleHeroMove}
        className="plum-hero relative text-cream-50"
      >
        <div className="mx-auto max-w-7xl px-4 pb-20 pt-14 sm:px-6 lg:px-8 lg:pb-24 lg:pt-20">
          {/* Center headline */}
          <div className="mx-auto max-w-3xl text-center">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45 }}
              className="mb-5 inline-flex items-center gap-2 rounded-full border border-gold/35 bg-white/5 px-4 py-1.5 font-sans text-[11px] font-semibold uppercase tracking-[0.18em] text-gold"
            >
              <Sparkles className="h-3.5 w-3.5" /> CiteVerify · Scientific Claim &amp; Citation Verification
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55, delay: 0.05 }}
              className="font-display text-5xl font-bold leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl"
            >
              Verify Research.
              <br />
              Trust the{" "}
              <span className="relative inline-block text-gold">
                Evidence.
                <svg
                  viewBox="0 0 260 16"
                  className="absolute -bottom-2 left-0 w-full h-3"
                  fill="none"
                >
                  <motion.path
                    d="M4 11C68 3 188 2 256 10"
                    stroke="#C9A06A"
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 0.9, delay: 0.35 }}
                  />
                </svg>
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55, delay: 0.14 }}
              className="mx-auto mt-6 max-w-2xl font-serif text-lg leading-relaxed text-cream-100/85 sm:text-xl"
            >
              Don&apos;t just cite, prove it. Upload any manuscript to extract claims, locate original cited studies across open scholarly databases, and inspect verbatim passage-level proof.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55, delay: 0.22 }}
              className="mt-8 flex flex-wrap items-center justify-center gap-4"
            >
              <Link
                to={isAuthenticated ? "/verify" : "/signup"}
                className="btn-gold px-8 py-3.5 text-xs"
              >
                Get Started <ArrowRight className="h-4 w-4" />
              </Link>
              <Link to="/how-it-works" className="btn-outline-light px-7 py-3.5">
                How it Works
              </Link>
            </motion.div>
          </div>

          {/* Left & Right Floating Visual Showcase */}
          <div className="mt-14 grid grid-cols-1 items-center gap-8 lg:grid-cols-12">
            {/* LEFT: Tilted Research Paper Graphic with bobbing tags */}
            <motion.div
              style={{ x: paperX, y: paperY }}
              initial={{ opacity: 0, y: 26, rotate: -3 }}
              animate={{ opacity: 1, y: 0, rotate: -2.5 }}
              transition={{ duration: 0.7, delay: 0.2 }}
              className="relative mx-auto w-full max-w-md lg:col-span-6"
            >
              {/* Back shadow paper */}
              <div className="absolute -inset-2 rotate-3 rounded-2xl border border-gold/20 bg-cream-100/10 backdrop-blur-sm" />

              {/* Main manuscript sheet */}
              <div className="relative rounded-2xl border border-sand-300 bg-cream-50 p-6 text-ink shadow-journal-lg">
                <div className="flex items-center justify-between border-b border-sand-200 pb-3">
                  <div>
                    <p className="font-sans text-[10px] font-bold uppercase tracking-[0.16em] text-burgundy">
                      Manuscript Audit · Page 2
                    </p>
                    <p className="font-display text-xl font-bold text-plum-900">
                      Attention &amp; Sequence Transduction
                    </p>
                  </div>
                  <BookMarked className="h-6 w-6 text-gold-amber shrink-0" />
                </div>

                <div className="mt-4 space-y-3 font-serif text-sm leading-relaxed text-ink-muted">
                  <p>
                    <span className="rounded bg-verdict-supported/15 px-1 text-ink font-medium border-b border-verdict-supported">
                      The Transformer relies entirely on attention mechanisms instead of recurrence [1].
                    </span>{" "}
                    This design achieves superior parallelization during training.
                  </p>
                  <p>
                    <span className="rounded bg-verdict-partly/15 px-1 text-ink font-medium border-b border-verdict-partly">
                      It was reported to boost image classification accuracy by 30% [1].
                    </span>
                  </p>
                  <div className="pt-2 border-t border-sand-200 font-sans text-[11px] text-ink-soft">
                    [1] Vaswani et al. (2017). <em>Attention Is All You Need</em>. arXiv:1706.03762
                  </div>
                </div>
              </div>

              {/* Floating Bobbing Tags */}
              <motion.div
                animate={{ y: [0, -7, 0] }}
                transition={{ duration: 3.4, repeat: Infinity, ease: "easeInOut" }}
                className="absolute -left-3 -top-4 inline-flex items-center gap-1.5 rounded-full border border-verdict-supported/40 bg-cream-50 px-3.5 py-1.5 font-sans text-[11px] font-bold text-verdict-supported shadow-journal"
              >
                <CheckCircle2 className="h-3.5 w-3.5" /> Claim Verified
              </motion.div>

              <motion.div
                animate={{ y: [0, 8, 0] }}
                transition={{ duration: 4.1, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
                className="absolute -right-3 top-10 inline-flex items-center gap-1.5 rounded-full border border-gold bg-plum-800 px-3.5 py-1.5 font-sans text-[11px] font-bold text-gold shadow-journal"
              >
                <Link2 className="h-3.5 w-3.5" /> Citation Found
              </motion.div>

              <motion.div
                animate={{ y: [0, -6, 0] }}
                transition={{ duration: 3.8, repeat: Infinity, ease: "easeInOut", delay: 0.9 }}
                className="absolute -bottom-4 right-8 inline-flex items-center gap-1.5 rounded-full border border-burgundy/30 bg-cream-100 px-3.5 py-1.5 font-sans text-[11px] font-bold text-burgundy shadow-journal"
              >
                <ShieldCheck className="h-3.5 w-3.5" /> Evidence Matched
              </motion.div>
            </motion.div>

            {/* RIGHT: Tilted Verification Summary Card (92% Verified Donut + Legend + Bar Chart) */}
            <motion.div
              style={{ x: cardX, y: cardY }}
              initial={{ opacity: 0, y: 26, rotate: 3 }}
              animate={{ opacity: 1, y: 0, rotate: 2 }}
              transition={{ duration: 0.7, delay: 0.3 }}
              className="mx-auto w-full max-w-md lg:col-span-6"
            >
              <div className="rounded-2xl border border-gold/30 bg-cream-50 p-6 text-ink shadow-journal-lg">
                <div className="flex items-center justify-between border-b border-sand-200 pb-3">
                  <span className="label-caps text-burgundy">Verification Snapshot</span>
                  <span className="rounded-full bg-verdict-supported/12 px-2.5 py-0.5 font-sans text-[10px] font-bold uppercase tracking-wider text-verdict-supported">
                    Mode: Gemini
                  </span>
                </div>

                <div className="mt-5 flex flex-col sm:flex-row items-center gap-6">
                  {/* Animated 92% Gold Donut */}
                  <div className="relative h-32 w-32 shrink-0">
                    <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
                      <circle
                        cx="60"
                        cy="60"
                        r={donutRadius}
                        fill="none"
                        stroke="#E8D9C3"
                        strokeWidth="13"
                      />
                      <motion.circle
                        cx="60"
                        cy="60"
                        r={donutRadius}
                        fill="none"
                        stroke="#C9A06A"
                        strokeWidth="13"
                        strokeLinecap="round"
                        strokeDasharray={donutCirc}
                        initial={{ strokeDashoffset: donutCirc }}
                        animate={{ strokeDashoffset: donutCirc * (1 - 0.92) }}
                        transition={{ duration: 1.2, ease: "easeOut" }}
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="font-display text-3xl font-bold text-plum-900 tabular-nums">
                        {pct}%
                      </span>
                      <span className="font-sans text-[9px] font-bold uppercase tracking-[0.14em] text-ink-soft">
                        Verified
                      </span>
                    </div>
                  </div>

                  {/* Legend + mini bar chart */}
                  <div className="flex-1 w-full space-y-2.5">
                    {[
                      { label: "Supported", pctVal: 74, color: "#3B7D3A" },
                      { label: "Partially Supported", pctVal: 18, color: "#B8741A" },
                      { label: "Unsupported", pctVal: 8, color: "#A63030" },
                    ].map((row, idx) => (
                      <div key={row.label}>
                        <div className="flex items-center justify-between font-sans text-xs">
                          <span className="flex items-center gap-1.5 text-ink">
                            <span
                              className="h-2.5 w-2.5 rounded-full"
                              style={{ backgroundColor: row.color }}
                            />
                            {row.label}
                          </span>
                          <span className="font-semibold text-plum-900 tabular-nums">
                            {row.pctVal}%
                          </span>
                        </div>
                        <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-sand-200">
                          <motion.div
                            className="h-full rounded-full"
                            style={{ backgroundColor: row.color }}
                            initial={{ width: 0 }}
                            animate={{ width: `${row.pctVal}%` }}
                            transition={{ duration: 0.9, delay: 0.35 + idx * 0.12 }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Small column bar chart footer */}
                <div className="mt-5 flex items-end justify-between gap-2 rounded-xl bg-cream-100/90 px-4 py-3 border border-sand-200">
                  <div>
                    <p className="font-sans text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-soft">
                      Passage Grounding Score
                    </p>
                    <p className="font-serif text-xs text-ink-muted">
                      Verbatim quote match across cited PDFs
                    </p>
                  </div>
                  <div className="flex items-end gap-1.5 h-10">
                    {[42, 68, 55, 86, 94, 78, 92].map((h, i) => (
                      <motion.div
                        key={i}
                        initial={{ height: 0 }}
                        animate={{ height: `${h}%` }}
                        transition={{ duration: 0.6, delay: 0.4 + i * 0.06 }}
                        className="w-2 rounded-t bg-burgundy/80"
                        style={{ backgroundColor: i === 6 ? "#C9A06A" : undefined }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* FOUR FEATURE CARDS */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="mb-10 text-center">
          <span className="label-caps text-burgundy">The Verification Pipeline</span>
          <h2 className="mt-2 font-display text-4xl font-bold text-plum-900 sm:text-5xl">
            Rigor at every step of your bibliography.
          </h2>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURE_CARDS.map((f, idx) => {
            const Icon = f.icon;
            return (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.45, delay: idx * 0.08 }}
                whileHover={{ y: -5 }}
                className="journal-card paper-texture p-6 flex flex-col justify-between transition-shadow hover:shadow-journal-lg"
              >
                <div>
                  <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-plum-900 text-gold shadow-sm">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="font-display text-2xl font-bold text-plum-900">
                    {f.title}
                  </h3>
                  <p className="mt-2.5 font-serif text-sm leading-relaxed text-ink-muted">
                    {f.desc}
                  </p>
                </div>
                <div className="mt-5 h-0.5 w-10 rounded-full bg-gold/70" />
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* INTERACTIVE LIVE MINI-DEMO */}
      <div className="border-y border-sand-300/70 bg-cream-100/70">
        <LiveMiniDemo />
      </div>

      {/* WHERE SOURCES COME FROM STRIP */}
      <section className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <span className="label-caps text-gold-amber">Open Scholarly Infrastructure</span>
          <h3 className="mt-1.5 font-display text-3xl font-bold text-plum-900">
            Where sources come from
          </h3>
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {SOURCES.map((s) => (
            <div
              key={s.name}
              className="rounded-xl border border-sand-300 bg-cream-100/80 px-5 py-4 text-center shadow-sm"
            >
              <p className="font-display text-2xl font-bold text-burgundy">{s.name}</p>
              <p className="mt-1 font-sans text-[11px] text-ink-soft">{s.tag}</p>
            </div>
          ))}
        </div>
      </section>

      {/* BOTTOM CTA */}
      <section className="mx-auto max-w-7xl px-4 pb-20 sm:px-6 lg:px-8">
        <div className="plum-hero rounded-3xl px-6 py-14 text-center text-cream-50 shadow-journal-lg sm:px-12">
          <h2 className="font-display text-4xl font-bold sm:text-5xl">
            Ready to audit your next paper?
          </h2>
          <p className="mx-auto mt-3 max-w-xl font-serif text-lg text-cream-100/85">
            Run our built-in Transformer &amp; BERT sample in one click, or upload your own PDF, DOCX, or manuscript draft.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link to={isAuthenticated ? "/verify" : "/signup"} className="btn-gold px-8 py-3.5">
              Start Verifying Now <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/features" className="btn-outline-light px-7 py-3.5">
              Explore Features
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
