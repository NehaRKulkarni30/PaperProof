import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  FileText,
  Columns2,
  Check,
  X,
  AlertCircle,
  MessageSquare,
  AlertTriangle,
} from "lucide-react";
import { VERDICT_META } from "./DonutChart";
import ConfidenceRing from "./ConfidenceRing";

const FLAG_LABELS = {
  reference_mismatch: { label: "Reference mismatch", tone: "red" },
  missing_reference: { label: "Missing reference", tone: "red" },
  retracted: { label: "Retracted source", tone: "red" },
  scope_mismatch: { label: "Scope mismatch", tone: "amber" },
  number_not_found: { label: "Number not found", tone: "amber" },
  outdated: { label: "Possibly outdated", tone: "amber" },
  uncited_claim: { label: "Uncited claim", tone: "amber" },
  implicit_citation: { label: "Matched via bibliography", tone: "amber" },
  metadata_only: { label: "Paywalled / metadata only", tone: "amber" },
  needs_manual_review: { label: "Needs manual review", tone: "amber" },
};

function highlightMarkers(text, markers = []) {
  if (!text) return text;
  const regex = /(\[\d+(?:\s*[,;\-–]\s*\d+)*\]|\([A-Z][A-Za-z'\-]+(?:\s+(?:et\s+al\.|&|and)\s*[A-Za-z'\-\.]*)?,?\s*(?:19|20)\d{2}[a-z]?(?:;\s*[^)]+)?\))/g;
  const parts = text.split(regex);
  return parts.map((part, i) => {
    if (regex.test(part) || markers.includes(part)) {
      regex.lastIndex = 0;
      return (
        <mark
          key={i}
          className="mx-0.5 rounded bg-gold/30 px-1.5 py-0.5 font-sans text-xs font-bold text-plum-900"
        >
          {part}
        </mark>
      );
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
}

function highlightQuoteInPassage(passage, quote) {
  if (!passage) return null;
  if (!quote) return passage;
  const idx = passage.toLowerCase().indexOf(quote.toLowerCase().trim());
  if (idx === -1) return passage;
  const before = passage.slice(0, idx);
  const match = passage.slice(idx, idx + quote.length);
  const after = passage.slice(idx + quote.length);
  return (
    <>
      {before}
      <mark className="rounded bg-gold/35 px-1 text-plum-950 font-medium">
        {match}
      </mark>
      {after}
    </>
  );
}

export default function ClaimCard({
  claim,
  totalClaims,
  readOnly = false,
  onReview,
}) {
  const [expanded, setExpanded] = useState(true);
  const [sideBySide, setSideBySide] = useState(false);
  const [showNote, setShowNote] = useState(Boolean(claim.latest_decision?.note));
  const [note, setNote] = useState(claim.latest_decision?.note || "");
  const [saving, setSaving] = useState(false);

  const meta = VERDICT_META[claim.verdict] || VERDICT_META.unsupported;
  const activeDecision = claim.latest_decision?.decision || null;
  const confidenceLevel =
    claim.confidence >= 80 ? "High" : claim.confidence >= 55 ? "Medium" : "Low";

  const handleDecision = async (decision) => {
    if (readOnly || !onReview) return;
    setSaving(true);
    try {
      await onReview(claim.id, decision, note);
    } finally {
      setSaving(false);
    }
  };

  const refParsed = claim.reference?.parsed || {};
  const refResolved = claim.reference?.resolved || {};
  const refTitle = refResolved.title || refParsed.title;
  const refAuthors = refResolved.authors || refParsed.authors || [];
  const refYear = refResolved.year || refParsed.year;
  const refVenue = refResolved.venue || refParsed.venue;
  const refDoi = claim.source_links?.doi || refResolved.doi || refParsed.doi;
  const refArxiv = claim.source_links?.arxiv_id || refResolved.arxiv_id || refParsed.arxiv_id;

  return (
    <motion.article
      id={`claim-card-${claim.idx}`}
      layout
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28 }}
      className="print-break-avoid rounded-2xl border border-sand-300/80 bg-cream-100/95 shadow-journal overflow-hidden"
    >
      {/* Top bar: Verdict badge, Claim index, collapse toggle */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-sand-300/70 bg-sand-200/50 px-5 py-3.5">
        <div className="flex flex-wrap items-center gap-2.5">
          <span
            className="inline-flex items-center rounded-full px-3 py-1 font-sans text-[11px] font-bold uppercase tracking-[0.12em] text-white shadow-sm"
            style={{ backgroundColor: meta.color }}
          >
            {meta.shortLabel}
          </span>
          <span className="font-sans text-xs font-medium text-ink-muted">
            Claim {claim.idx} of {totalClaims}
            {claim.page ? ` · Page ${claim.page}` : ""}
          </span>
          {activeDecision && (
            <span className="inline-flex items-center gap-1 rounded-full border border-plum-900/20 bg-plum-900/10 px-2.5 py-0.5 font-sans text-[10px] font-semibold uppercase tracking-wider text-plum-900">
              Reviewer: {activeDecision.replace("_", " ")}
            </span>
          )}
        </div>

        <div className="no-print flex items-center gap-2">
          {(claim.evidence_quote || claim.evidence_passage) && (
            <button
              type="button"
              onClick={() => {
                setExpanded(true);
                setSideBySide((s) => !s);
              }}
              className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 font-sans text-[11px] font-semibold transition-colors ${
                sideBySide
                  ? "border-burgundy bg-burgundy text-cream-50"
                  : "border-sand-300 bg-cream-50 text-ink-muted hover:border-burgundy/40 hover:text-burgundy"
              }`}
            >
              <Columns2 className="h-3.5 w-3.5" />
              Side-by-Side
            </button>
          )}
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            className="rounded-lg p-1 text-ink-soft hover:bg-sand-200 hover:text-plum-900"
            aria-label={expanded ? "Collapse claim" : "Expand claim"}
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Main body */}
      <div className="p-5 sm:p-6 space-y-5">
        {/* Side-by-side mode vs stacked mode */}
        {sideBySide && expanded ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-sand-300 bg-cream-50 p-4">
              <p className="label-caps mb-2 text-burgundy">Claim from Manuscript</p>
              <p className="font-serif text-base leading-relaxed text-ink">
                {highlightMarkers(claim.text, claim.markers)}
              </p>
            </div>
            <div className="rounded-xl border border-gold/40 bg-cream-50 p-4">
              <p className="label-caps mb-2 text-gold-amber">
                Source Passage · {claim.evidence_location?.section || "Excerpt"}
                {claim.evidence_location?.page ? `, p. ${claim.evidence_location.page}` : ""}
              </p>
              <p className="font-serif text-sm leading-relaxed text-ink">
                {highlightQuoteInPassage(
                  claim.evidence_passage || claim.evidence_quote,
                  claim.evidence_quote
                )}
              </p>
            </div>
          </div>
        ) : (
          <div>
            <p className="label-caps mb-1.5">Claim</p>
            <p className="font-serif text-lg leading-relaxed text-plum-950 font-medium">
              {highlightMarkers(claim.text, claim.markers)}
            </p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {expanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-5 overflow-hidden"
            >
              {/* Citation Matched */}
              <div className="rounded-xl border border-sand-300/80 bg-cream-50/80 px-4 py-3">
                <p className="label-caps mb-1">Citation Matched</p>
                {claim.reference ? (
                  <div className="space-y-0.5">
                    <p className="font-serif text-sm font-semibold text-plum-900">
                      <span className="font-sans text-xs font-bold text-burgundy mr-1.5">
                        {claim.reference.marker}
                      </span>
                      {refTitle || claim.reference.raw_text}
                    </p>
                    <p className="font-sans text-xs text-ink-muted">
                      {refAuthors.length > 0 && (
                        <span>
                          {refAuthors.slice(0, 4).join(", ")}
                          {refAuthors.length > 4 ? " et al." : ""}
                        </span>
                      )}
                      {refYear ? ` · ${refYear}` : ""}
                      {refVenue ? ` · ${refVenue}` : ""}
                      {refArxiv ? ` · arXiv:${refArxiv}` : ""}
                      {refDoi && !refArxiv ? ` · DOI:${refDoi}` : ""}
                    </p>
                  </div>
                ) : (
                  <p className="font-sans text-xs font-semibold text-verdict-unsupported">
                    (no matching reference in bibliography)
                  </p>
                )}
              </div>

              {/* Verbatim Evidence Quote (shown when not in side-by-side) */}
              {!sideBySide && claim.evidence_quote && (
                <div>
                  <p className="label-caps mb-2">
                    Evidence · {claim.evidence_location?.section || "Excerpt"}
                    {claim.evidence_location?.page ? `, Page ${claim.evidence_location.page}` : ""}
                  </p>
                  <blockquote className="rounded-r-xl border-l-4 border-gold bg-cream-50/90 px-4 py-3 font-serif text-[15px] italic leading-relaxed text-ink">
                    “{claim.evidence_quote}”
                  </blockquote>
                </div>
              )}

              {/* Verdict & Reason + Confidence Ring */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-12 items-start">
                <div className="md:col-span-8">
                  <p className="label-caps mb-1.5">Verdict and Reason</p>
                  <p className="font-serif text-[15px] leading-relaxed text-ink">
                    {claim.reason}
                  </p>
                </div>

                <div className="md:col-span-4 rounded-xl border border-sand-300/70 bg-cream-50/80 p-3.5 flex items-center gap-3.5">
                  <ConfidenceRing value={claim.confidence} size={56} />
                  <div className="min-w-0">
                    <p className="label-caps">Confidence</p>
                    <p className="mt-0.5 font-sans text-xs font-semibold text-plum-900">
                      {confidenceLevel}.
                    </p>
                    <p className="mt-0.5 font-sans text-[11px] leading-snug text-ink-muted">
                      {claim.confidence_note || "Automated evidence check."}
                    </p>
                  </div>
                </div>
              </div>

              {/* Source Trace & Flags */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-sand-300/70 pt-4">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 font-sans text-xs text-ink-muted">
                  <span className="label-caps text-ink-soft">Source Trace:</span>
                  <span>Found via {claim.source_links?.found_via || "bibliography lookup"}</span>
                  {claim.source_links?.evidence_level === "abstract_only" && (
                    <span className="rounded bg-sand-200 px-2 py-0.5 text-[10px] font-semibold uppercase text-ink-muted">
                      Abstract only
                    </span>
                  )}
                  {claim.source_links?.landing_url && (
                    <a
                      href={claim.source_links.landing_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 font-semibold text-burgundy hover:underline"
                    >
                      Open paper <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                  {claim.source_links?.pdf_url && (
                    <a
                      href={claim.source_links.pdf_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 font-semibold text-burgundy hover:underline"
                    >
                      PDF <FileText className="h-3 w-3" />
                    </a>
                  )}
                </div>

                {/* Red/Amber Flags */}
                {claim.flags?.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5">
                    {claim.flags.map((flag) => {
                      const info = FLAG_LABELS[flag] || {
                        label: flag.replace(/_/g, " "),
                        tone: "amber",
                      };
                      return (
                        <span
                          key={flag}
                          className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-sans text-[10px] font-bold uppercase tracking-wider ${
                            info.tone === "red"
                              ? "border-verdict-unsupported/35 bg-verdict-unsupported/10 text-verdict-unsupported"
                              : "border-verdict-partly/35 bg-verdict-partly/12 text-[#8F5810]"
                          }`}
                        >
                          <AlertTriangle className="h-3 w-3" />
                          {info.label}
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Human Review Action Controls */}
              {!readOnly && (
                <div className="review-controls-bar rounded-xl border border-sand-300 bg-cream-50/90 p-3.5 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        disabled={saving}
                        onClick={() => handleDecision("accepted")}
                        className={`inline-flex items-center gap-1.5 rounded-lg border px-3.5 py-1.5 font-sans text-[11px] font-bold uppercase tracking-[0.12em] transition-all ${
                          activeDecision === "accepted"
                            ? "border-verdict-supported bg-verdict-supported text-white shadow-sm"
                            : "border-verdict-supported/40 bg-white text-verdict-supported hover:bg-verdict-supported/10"
                        }`}
                      >
                        <Check className="h-3.5 w-3.5" /> Accepted
                      </button>

                      <button
                        type="button"
                        disabled={saving}
                        onClick={() => handleDecision("rejected")}
                        className={`inline-flex items-center gap-1.5 rounded-lg border px-3.5 py-1.5 font-sans text-[11px] font-bold uppercase tracking-[0.12em] transition-all ${
                          activeDecision === "rejected"
                            ? "border-verdict-unsupported bg-verdict-unsupported text-white shadow-sm"
                            : "border-verdict-unsupported/40 bg-white text-verdict-unsupported hover:bg-verdict-unsupported/10"
                        }`}
                      >
                        <X className="h-3.5 w-3.5" /> Rejected
                      </button>

                      <button
                        type="button"
                        disabled={saving}
                        onClick={() => handleDecision("needs_review")}
                        className={`inline-flex items-center gap-1.5 rounded-lg border px-3.5 py-1.5 font-sans text-[11px] font-bold uppercase tracking-[0.12em] transition-all ${
                          activeDecision === "needs_review"
                            ? "border-verdict-partly bg-verdict-partly text-white shadow-sm"
                            : "border-verdict-partly/40 bg-white text-[#945B11] hover:bg-verdict-partly/10"
                        }`}
                      >
                        <AlertCircle className="h-3.5 w-3.5" /> Needs Review
                      </button>
                    </div>

                    <button
                      type="button"
                      onClick={() => setShowNote((s) => !s)}
                      className="inline-flex items-center gap-1.5 font-sans text-xs font-medium text-ink-muted hover:text-burgundy"
                    >
                      <MessageSquare className="h-3.5 w-3.5" />
                      {showNote ? "Hide note" : "Add reviewer note"}
                    </button>
                  </div>

                  {showNote && (
                    <div className="flex flex-col sm:flex-row gap-2">
                      <input
                        type="text"
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="Optional note for the audit trail (e.g., 'Check Table 2 in final draft')…"
                        className="flex-1 rounded-lg border border-sand-300 bg-white px-3 py-1.5 font-sans text-xs text-ink placeholder:text-ink-soft/70 focus:border-burgundy focus:outline-none"
                      />
                      {activeDecision && (
                        <button
                          type="button"
                          disabled={saving}
                          onClick={() => handleDecision(activeDecision)}
                          className="rounded-lg bg-plum-900 px-3.5 py-1.5 font-sans text-[11px] font-semibold uppercase tracking-wider text-cream-50 hover:bg-burgundy"
                        >
                          Save Note
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.article>
  );
}
