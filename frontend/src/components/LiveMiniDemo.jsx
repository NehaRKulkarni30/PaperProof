import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BookOpen, CheckCircle2, AlertCircle, XCircle, ExternalLink, Sparkles } from "lucide-react";
import { VERDICT_META } from "./DonutChart";

const DEMO_CLAIMS = [
  {
    id: 1,
    snippet: "The Transformer relies entirely on attention mechanisms instead of recurrence or convolutions [1].",
    verdict: "supported",
    confidence: 96,
    citation: "Vaswani et al. (2017) · Attention Is All You Need · NeurIPS 2017 · arXiv:1706.03762",
    quote:
      "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
    location: "Abstract · Page 1",
    reason:
      "Direct match in the original Vaswani et al. (2017) paper confirming recurrence and convolutions are dispensed with entirely.",
    url: "https://arxiv.org/abs/1706.03762",
  },
  {
    id: 2,
    snippet: "The Transformer was shown to improve image classification accuracy by 30% [1].",
    verdict: "partly_supported",
    confidence: 82,
    citation: "Vaswani et al. (2017) · Attention Is All You Need · NeurIPS 2017 · arXiv:1706.03762",
    quote:
      "We plan to extend the Transformer to problems involving input and output modalities other than text and to investigate local, restricted attention mechanisms to efficiently handle large inputs and outputs such as images, audio and video.",
    location: "Section 7 Conclusion · Page 10",
    reason:
      "Images are only mentioned as future work; the paper evaluates machine translation and constituency parsing and never reports a 30% accuracy gain.",
    url: "https://arxiv.org/abs/1706.03762",
  },
  {
    id: 3,
    snippet: "The Transformer introduced bidirectional masked language modelling for pre-training [1].",
    verdict: "unsupported",
    confidence: 92,
    citation: "Vaswani et al. (2017) · Attention Is All You Need (Reference Mismatch — belongs to BERT [2])",
    quote:
      "Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train.",
    location: "Abstract · Page 1",
    reason:
      "Reference mismatch: bidirectional masked language modelling (MLM) was introduced by Devlin et al. (2019, BERT [2]), not by Vaswani et al. (2017 [1]).",
    url: "https://arxiv.org/abs/1810.04805",
  },
];

export default function LiveMiniDemo() {
  const [selectedId, setSelectedId] = useState(1);
  const active = DEMO_CLAIMS.find((c) => c.id === selectedId) || DEMO_CLAIMS[0];
  const meta = VERDICT_META[active.verdict];

  const VerdictIcon =
    active.verdict === "supported"
      ? CheckCircle2
      : active.verdict === "partly_supported"
      ? AlertCircle
      : XCircle;

  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <div className="mb-10 flex flex-col items-start justify-between gap-4 md:flex-row md:items-end">
        <div>
          <span className="label-caps text-gold-amber inline-flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5" /> Interactive Evidence Preview
          </span>
          <h2 className="mt-2 font-display text-4xl font-bold text-plum-900 sm:text-5xl">
            Click a claim to inspect its proof.
          </h2>
        </div>
        <p className="max-w-md font-serif text-base text-ink-muted">
          See how PaperProof traces every assertion back to the exact passage in the cited study—catching inflated numbers and swapped citations.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left: Interactive manuscript excerpt */}
        <div className="journal-card paper-texture p-6 sm:p-8 lg:col-span-7 flex flex-col justify-between">
          <div>
            <div className="mb-5 flex items-center justify-between border-b border-sand-300/70 pb-3">
              <span className="label-caps flex items-center gap-2 text-burgundy">
                <BookOpen className="h-3.5 w-3.5" /> Excerpt · Manuscript Draft
              </span>
              <span className="font-sans text-[11px] text-ink-soft">
                Select any highlighted claim
              </span>
            </div>

            <div className="space-y-4 font-serif text-lg leading-relaxed text-ink">
              <p>
                Modern sequence modeling has rapidly moved away from recurrent architectures.{" "}
                {DEMO_CLAIMS.map((claim, idx) => {
                  const isSel = claim.id === selectedId;
                  const cMeta = VERDICT_META[claim.verdict];
                  return (
                    <React.Fragment key={claim.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedId(claim.id)}
                        className={`inline text-left rounded-md px-1.5 py-0.5 transition-all duration-200 border-b-2 ${
                          isSel
                            ? "bg-plum-900 text-cream-50 border-gold shadow-sm"
                            : "hover:bg-sand-200/90 text-ink"
                        }`}
                        style={{
                          borderBottomColor: isSel ? "#C9A06A" : cMeta.color,
                        }}
                      >
                        {claim.snippet}
                      </button>
                      {idx === 0 && " Later summaries have occasionally overstated empirical results: "}
                      {idx === 1 && " Similarly, lecture notes sometimes conflate pre-training milestones across papers. "}
                    </React.Fragment>
                  );
                })}
              </p>
            </div>
          </div>

          <div className="mt-7 flex flex-wrap items-center gap-2 border-t border-sand-300/70 pt-4">
            <span className="label-caps mr-1">Quick select:</span>
            {DEMO_CLAIMS.map((c) => {
              const m = VERDICT_META[c.verdict];
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setSelectedId(c.id)}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-sans text-[11px] font-semibold transition-all ${
                    c.id === selectedId
                      ? "bg-plum-900 text-cream-50 border-plum-900"
                      : "bg-cream-50 text-ink-muted border-sand-300 hover:border-burgundy/40"
                  }`}
                >
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: m.color }}
                  />
                  Claim {c.id}: {m.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Animated Evidence Verdict Card */}
        <div className="lg:col-span-5">
          <AnimatePresence mode="wait">
            <motion.div
              key={active.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25 }}
              className="h-full rounded-2xl border border-sand-300 bg-plum-900 p-6 sm:p-7 text-cream-50 shadow-journal-lg flex flex-col justify-between"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between gap-2">
                  <span
                    className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-sans text-[11px] font-bold uppercase tracking-[0.12em] text-white"
                    style={{ backgroundColor: meta.color }}
                  >
                    <VerdictIcon className="h-3.5 w-3.5" />
                    {meta.shortLabel}
                  </span>
                  <span className="font-sans text-xs font-semibold text-gold">
                    {active.confidence}% Confidence
                  </span>
                </div>

                <div>
                  <p className="font-sans text-[10px] font-semibold uppercase tracking-[0.16em] text-gold/90">
                    Matched Citation
                  </p>
                  <p className="mt-1 font-serif text-sm text-cream-100/95">
                    {active.citation}
                  </p>
                </div>

                <div className="rounded-xl border border-gold/25 bg-plum-950/60 p-4">
                  <p className="font-sans text-[10px] font-semibold uppercase tracking-[0.16em] text-gold">
                    Verbatim Evidence · {active.location}
                  </p>
                  <blockquote className="mt-2 border-l-2 border-gold pl-3 font-serif text-sm italic leading-relaxed text-cream-50/95">
                    “{active.quote}”
                  </blockquote>
                </div>

                <div>
                  <p className="font-sans text-[10px] font-semibold uppercase tracking-[0.16em] text-gold/90">
                    Verdict &amp; Reason
                  </p>
                  <p className="mt-1 font-serif text-sm leading-relaxed text-cream-100/90">
                    {active.reason}
                  </p>
                </div>
              </div>

              <div className="mt-5 flex items-center justify-between border-t border-white/10 pt-4">
                <span className="font-sans text-[11px] text-cream-100/65">
                  Source verified via arXiv full text
                </span>
                <a
                  href={active.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 font-sans text-xs font-semibold text-gold hover:underline"
                >
                  Open Paper <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}
