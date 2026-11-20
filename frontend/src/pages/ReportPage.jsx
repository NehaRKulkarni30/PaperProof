import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Download,
  Printer,
  Share2,
  Search,
  AlertTriangle,
  ArrowUpDown,
  Clock,
  Check,
  Copy,
  Link2,
  AlertCircle,
  ArrowLeft,
  Cpu,
} from "lucide-react";
import { api } from "../api/client";
import { useToast } from "../components/Toast";
import DonutChart, { VERDICT_META } from "../components/DonutChart";
import ClaimCard from "../components/ClaimCard";
import ProcessingStepper from "../components/ProcessingStepper";

function formatTime(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

export function ReportView({ report, readOnly = false, onRefresh }) {
  const { toast } = useToast();
  const [filterTab, setFilterTab] = useState("all");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("order");
  const [shareOpen, setShareOpen] = useState(false);
  const [shareState, setShareState] = useState({
    is_public: report.is_public,
    share_token: report.share_token,
  });
  const [copied, setCopied] = useState(false);
  const [localReport, setLocalReport] = useState(report);

  useEffect(() => {
    setLocalReport(report);
    setShareState({ is_public: report.is_public, share_token: report.share_token });
  }, [report]);

  const summary = localReport.summary || {};
  const counts = summary.verdict_counts || {};
  const misleading = summary.misleading_references || {};
  const claims = localReport.claims || [];

  const needsReviewCount = useMemo(
    () =>
      claims.filter(
        (c) =>
          c.verdict === "partly_supported" ||
          c.verdict === "contradictory" ||
          c.verdict === "possibly_outdated" ||
          c.latest_decision?.decision === "needs_review"
      ).length,
    [claims]
  );

  const filteredClaims = useMemo(() => {
    let list = [...claims];
    if (filterTab === "needs_review") {
      list = list.filter(
        (c) =>
          c.verdict === "partly_supported" ||
          c.verdict === "contradictory" ||
          c.verdict === "possibly_outdated" ||
          c.latest_decision?.decision === "needs_review"
      );
    } else if (filterTab !== "all") {
      list = list.filter((c) => c.verdict === filterTab);
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (c) =>
          (c.text || "").toLowerCase().includes(q) ||
          (c.reason || "").toLowerCase().includes(q) ||
          (c.evidence_quote || "").toLowerCase().includes(q) ||
          (c.reference?.raw_text || "").toLowerCase().includes(q)
      );
    }

    if (sortBy === "conf_desc") {
      list.sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
    } else if (sortBy === "conf_asc") {
      list.sort((a, b) => (a.confidence || 0) - (b.confidence || 0));
    } else {
      list.sort((a, b) => a.idx - b.idx);
    }
    return list;
  }, [claims, filterTab, search, sortBy]);

  const handleReview = async (claimId, decision, note) => {
    try {
      const saved = await api.reviewClaim(localReport.id, claimId, { decision, note });
      // Update local state immediately for instant UI responsiveness
      setLocalReport((prev) => {
        const updatedClaims = prev.claims.map((c) =>
          c.id === claimId
            ? { ...c, latest_decision: saved, decisions: [saved, ...(c.decisions || [])] }
            : c
        );
        return {
          ...prev,
          claims: updatedClaims,
          review_history: [saved, ...(prev.review_history || [])],
        };
      });
      toast(
        `Claim ${saved.claim_idx || ""} marked as ${decision.replace("_", " ")}.`,
        "success"
      );
    } catch (err) {
      toast(err.message || "Failed to save review decision.", "error");
    }
  };

  const handleDownloadJson = async () => {
    try {
      await api.downloadReportJson(localReport.id, localReport.filename);
      toast("Report JSON downloaded.", "success");
    } catch (err) {
      toast(err.message || "JSON download failed.", "error");
    }
  };

  const handleToggleShare = async () => {
    try {
      const next = !shareState.is_public;
      const res = await api.toggleShare(localReport.id, next);
      setShareState({ is_public: res.is_public, share_token: res.share_token });
      toast(
        res.is_public ? "Public read-only share link enabled." : "Share link revoked.",
        "info"
      );
    } catch (err) {
      toast(err.message || "Could not update share settings.", "error");
    }
  };

  const shareUrl =
    shareState.is_public && shareState.share_token
      ? `${window.location.origin}/#/shared/${shareState.share_token}`
      : "";

  const copyShareUrl = () => {
    if (!shareUrl) return;
    navigator.clipboard?.writeText(shareUrl);
    setCopied(true);
    toast("Share link copied to clipboard.", "success");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDonutSelect = (verdictKey) => {
    setFilterTab(verdictKey);
    const firstMatch = claims.find((c) => verdictKey === "all" || c.verdict === verdictKey);
    if (firstMatch) {
      const el = document.getElementById(`claim-card-${firstMatch.idx}`);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <div className="pb-16">
      {/* PLUM HEADER BAND */}
      <section className="plum-hero print-header text-cream-50">
        <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
          <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
            <div>
              {readOnly && (
                <span className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-gold/40 bg-gold/15 px-3 py-1 font-sans text-[10px] font-bold uppercase tracking-[0.16em] text-gold">
                  <Link2 className="h-3 w-3" /> Shared Read-Only Report
                </span>
              )}
              <p className="font-sans text-[11px] font-semibold uppercase tracking-[0.2em] text-gold">
                Uploaded by {localReport.uploaded_by}
              </p>
              <h1 className="mt-1.5 font-display text-4xl font-bold sm:text-5xl">
                Verification report
              </h1>
              <p className="mt-2 font-sans text-xs text-cream-100/80 flex flex-wrap items-center gap-2">
                <span>Report {localReport.short_id}</span>
                <span>·</span>
                <span className="font-medium text-cream-50">{localReport.filename}</span>
                <span>·</span>
                <span className="inline-flex items-center gap-1 rounded-full bg-white/10 px-2.5 py-0.5 text-[11px] font-semibold text-gold">
                  <Cpu className="h-3 w-3" /> Mode: {localReport.mode}
                </span>
              </p>
            </div>

            <div className="no-print flex flex-wrap items-center gap-2.5 relative">
              {!readOnly && (
                <button
                  type="button"
                  onClick={handleDownloadJson}
                  className="btn-outline-light py-2.5 px-4"
                >
                  <Download className="h-3.5 w-3.5" /> Download JSON
                </button>
              )}
              <button
                type="button"
                onClick={() => window.print()}
                className="btn-gold py-2.5 px-4"
              >
                <Printer className="h-3.5 w-3.5" /> Print / Save PDF
              </button>
              {!readOnly && (
                <button
                  type="button"
                  onClick={() => setShareOpen((o) => !o)}
                  className="btn-outline-light py-2.5 px-4"
                >
                  <Share2 className="h-3.5 w-3.5" /> Share
                </button>
              )}

              {/* Share popover */}
              {shareOpen && !readOnly && (
                <div className="absolute right-0 top-12 z-30 w-80 rounded-2xl border border-sand-300 bg-cream-50 p-4 text-ink shadow-journal-lg">
                  <div className="flex items-center justify-between">
                    <span className="label-caps text-burgundy">Public Read-Only Link</span>
                    <button
                      type="button"
                      onClick={handleToggleShare}
                      className={`rounded-full px-3 py-1 font-sans text-[10px] font-bold uppercase tracking-wider transition-colors ${
                        shareState.is_public
                          ? "bg-verdict-supported text-white"
                          : "bg-sand-200 text-ink-muted"
                      }`}
                    >
                      {shareState.is_public ? "Public ON" : "Enable"}
                    </button>
                  </div>
                  <p className="mt-1.5 font-sans text-[11px] text-ink-muted">
                    Share a read-only verification report with a supervisor or reviewer—no login required.
                  </p>
                  {shareUrl && (
                    <div className="mt-3 flex items-center gap-1.5">
                      <input
                        type="text"
                        readOnly
                        value={shareUrl}
                        className="flex-1 rounded-lg border border-sand-300 bg-white px-2.5 py-1.5 font-sans text-[11px] text-ink"
                      />
                      <button
                        type="button"
                        onClick={copyShareUrl}
                        className="rounded-lg bg-burgundy p-2 text-cream-50 hover:bg-burgundy-dark"
                        aria-label="Copy link"
                      >
                        {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* MAIN TWO-COLUMN LAYOUT */}
      <div className="mx-auto max-w-7xl px-4 pt-8 sm:px-6 lg:px-8">
        <div className="print-grid-single grid grid-cols-1 gap-8 lg:grid-cols-12 items-start">
          {/* LEFT STICKY SIDEBAR */}
          <aside className="lg:col-span-4 lg:sticky lg:top-20 space-y-5">
            {/* LATEST REPORT CARD */}
            <div className="journal-card p-6">
              <div className="flex items-center justify-between border-b border-sand-300/70 pb-3">
                <span className="label-caps text-burgundy">Latest Report</span>
                <span className="rounded-full bg-plum-900/10 px-2.5 py-0.5 font-sans text-[10px] font-bold uppercase tracking-wider text-plum-900">
                  Mode: {localReport.mode}
                </span>
              </div>

              <h2 className="mt-3 font-display text-2xl font-bold text-plum-900 break-words">
                {localReport.filename}
              </h2>
              <p className="mt-0.5 font-sans text-xs text-ink-muted">
                {claims.length} claims · {(localReport.references || []).length} references · Mode: {localReport.mode}
              </p>

              <div className="mt-6">
                <DonutChart
                  counts={counts}
                  total={claims.length}
                  centerValue={claims.length}
                  centerLabel="Claims"
                  activeFilter={filterTab}
                  onSelectVerdict={handleDonutSelect}
                />
              </div>

              {/* Misleading references box */}
              <div className="mt-5 rounded-xl border border-verdict-unsupported/30 bg-verdict-unsupported/8 p-4">
                <p className="flex items-center gap-1.5 font-sans text-[11px] font-bold uppercase tracking-[0.12em] text-verdict-unsupported">
                  <AlertTriangle className="h-3.5 w-3.5" /> Misleading References
                </p>
                <p className="mt-1.5 font-sans text-xs leading-relaxed text-ink">
                  <strong className="text-verdict-unsupported">
                    {misleading.mismatched_citations || 0}
                  </strong>{" "}
                  mismatched citation,{" "}
                  <strong className="text-plum-900">
                    {misleading.missing_references || 0}
                  </strong>{" "}
                  missing reference,{" "}
                  <strong className="text-verdict-unsupported">
                    {misleading.retracted || 0}
                  </strong>{" "}
                  retracted
                  {misleading.uncited_claims > 0
                    ? `, ${misleading.uncited_claims} uncited`
                    : ""}
                </p>
              </div>
            </div>

            {/* REVIEW HISTORY CARD */}
            <div className="journal-card p-6">
              <div className="flex items-center justify-between border-b border-sand-300/70 pb-3">
                <span className="label-caps text-burgundy">Review History</span>
                <Clock className="h-3.5 w-3.5 text-ink-soft" />
              </div>

              {localReport.review_history?.length > 0 ? (
                <ul className="mt-3 max-h-56 space-y-2.5 overflow-y-auto pr-1">
                  {localReport.review_history.map((d) => (
                    <li
                      key={d.id}
                      className="rounded-lg border border-sand-300/70 bg-cream-50 px-3 py-2 font-sans text-xs"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-plum-900">
                          Claim {d.claim_idx} →{" "}
                          <span className="capitalize text-burgundy">
                            {d.decision.replace("_", " ")}
                          </span>
                        </span>
                        <span className="text-[10px] text-ink-soft tabular-nums">
                          {formatTime(d.created_at)}
                        </span>
                      </div>
                      {d.note && (
                        <p className="mt-1 text-[11px] italic text-ink-muted">
                          “{d.note}”
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 font-serif text-sm italic text-ink-soft">
                  No decisions yet. Use the review buttons on each claim card to record your audit trail.
                </p>
              )}
            </div>

            {/* Sidebar disclaimer */}
            <p className="px-2 font-sans text-[11px] leading-relaxed text-ink-soft">
              Automated evidence check, not a final academic judgment. Review every finding.
            </p>
          </aside>

          {/* MAIN CLAIMS COLUMN */}
          <div className="lg:col-span-8 space-y-5">
            {/* Filter Tabs + Search + Sort Bar */}
            <div className="filter-bar journal-card p-4 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                {[
                  { key: "all", label: `ALL (${claims.length})` },
                  { key: "needs_review", label: `NEEDS REVIEW (${needsReviewCount})` },
                  {
                    key: "unsupported",
                    label: `UNSUPPORTED (${counts.unsupported || 0})`,
                  },
                  {
                    key: "reference_not_found",
                    label: `REFERENCE NOT FOUND (${counts.reference_not_found || 0})`,
                  },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => setFilterTab(tab.key)}
                    className={`rounded-lg px-3 py-1.5 font-sans text-[11px] font-bold uppercase tracking-[0.11em] transition-all ${
                      filterTab === tab.key
                        ? "bg-plum-900 text-gold shadow-sm"
                        : "bg-cream-50 text-ink-muted border border-sand-300 hover:border-burgundy/40"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}

                {filterTab !== "all" &&
                  !["needs_review", "unsupported", "reference_not_found"].includes(
                    filterTab
                  ) && (
                    <button
                      type="button"
                      onClick={() => setFilterTab("all")}
                      className="rounded-lg bg-burgundy px-3 py-1.5 font-sans text-[11px] font-bold uppercase tracking-[0.11em] text-cream-50"
                    >
                      {VERDICT_META[filterTab]?.shortLabel || filterTab} ×
                    </button>
                  )}
              </div>

              <div className="flex flex-col sm:flex-row gap-2.5">
                <div className="relative flex-1">
                  <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-soft" />
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Filter claims, quotes, or references…"
                    className="w-full rounded-xl border border-sand-300 bg-cream-50 pl-9 pr-3 py-2 font-sans text-xs text-ink placeholder:text-ink-soft/70 focus:border-burgundy focus:outline-none"
                  />
                </div>
                <div className="relative flex items-center">
                  <ArrowUpDown className="pointer-events-none absolute left-3 h-3.5 w-3.5 text-ink-soft" />
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="rounded-xl border border-sand-300 bg-cream-50 pl-8 pr-7 py-2 font-sans text-xs font-medium text-ink focus:border-burgundy focus:outline-none"
                  >
                    <option value="order">Sort: Paper Order</option>
                    <option value="conf_desc">Confidence: High → Low</option>
                    <option value="conf_asc">Confidence: Low → High</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Claims list */}
            {filteredClaims.length > 0 ? (
              <div className="space-y-5">
                {filteredClaims.map((claim) => (
                  <ClaimCard
                    key={claim.id}
                    claim={claim}
                    totalClaims={claims.length}
                    readOnly={readOnly}
                    onReview={handleReview}
                  />
                ))}
              </div>
            ) : (
              <div className="journal-card p-10 text-center">
                <p className="font-display text-2xl font-bold text-plum-900">
                  No matching claims
                </p>
                <p className="mt-1 font-serif text-sm text-ink-muted">
                  Try clearing your search query or switching back to ALL claims.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setFilterTab("all");
                    setSearch("");
                  }}
                  className="btn-secondary mt-4"
                >
                  Show All Claims
                </button>
              </div>
            )}

            {/* CORE PRINCIPLE REPORT FOOTER */}
            <div className="rounded-2xl border border-gold/40 bg-cream-100 p-5 text-center shadow-sm">
              <p className="font-serif text-sm italic text-plum-900">
                “A citation is not proof by itself. This is an automated evidence check, not a final academic judgment. Review every finding.”
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ReportPage() {
  const { id } = useParams();
  const [report, setReport] = useState(null);
  const [statusData, setStatusData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchFullReport = useCallback(async () => {
    try {
      const data = await api.getReport(id);
      setReport(data);
      setStatusData({
        stage: data.stage,
        progress: data.progress,
        status_message: data.status_message,
        claims_found: data.claims?.length || 0,
        references_found: data.references?.length || 0,
      });
    } catch (err) {
      setError(err.message || "Could not load verification report.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    let timer = null;
    let cancelled = false;

    const poll = async () => {
      try {
        const st = await api.getReportStatus(id);
        if (cancelled) return;
        setStatusData(st);
        if (st.status === "completed" || st.status === "failed") {
          await fetchFullReport();
        } else {
          setLoading(false);
          timer = setTimeout(poll, 1200);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to fetch report status.");
          setLoading(false);
        }
      }
    };

    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [id, fetchFullReport]);

  if (loading && !statusData) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16 space-y-4">
        <div className="h-36 animate-pulse rounded-2xl bg-sand-200/80" />
        <div className="grid grid-cols-1 gap-6 md:grid-cols-12">
          <div className="h-80 animate-pulse rounded-2xl bg-sand-200/70 md:col-span-4" />
          <div className="space-y-4 md:col-span-8">
            <div className="h-44 animate-pulse rounded-2xl bg-sand-200/70" />
            <div className="h-44 animate-pulse rounded-2xl bg-sand-200/70" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-xl px-4 py-20 text-center">
        <div className="journal-card p-8 space-y-4">
          <AlertCircle className="mx-auto h-10 w-10 text-verdict-unsupported" />
          <h1 className="font-display text-3xl font-bold text-plum-900">
            Report unavailable
          </h1>
          <p className="font-serif text-sm text-ink-muted">{error}</p>
          <Link to="/verify" className="btn-primary">
            <ArrowLeft className="h-4 w-4" /> Back to Verify
          </Link>
        </div>
      </div>
    );
  }

  if (statusData?.status === "processing" || (report && report.status === "processing")) {
    return <ProcessingStepper statusData={statusData} filename={statusData?.filename} />;
  }

  if (report?.status === "failed") {
    return (
      <div className="mx-auto max-w-xl px-4 py-20 text-center">
        <div className="journal-card p-8 space-y-4">
          <AlertCircle className="mx-auto h-10 w-10 text-verdict-unsupported" />
          <h1 className="font-display text-3xl font-bold text-plum-900">
            Verification failed
          </h1>
          <p className="font-serif text-sm text-ink-muted">
            {report.error_message || "An unexpected error occurred during processing."}
          </p>
          <Link to="/verify" className="btn-primary">
            Try Another Document
          </Link>
        </div>
      </div>
    );
  }

  if (!report) return null;
  return <ReportView report={report} readOnly={false} onRefresh={fetchFullReport} />;
}
