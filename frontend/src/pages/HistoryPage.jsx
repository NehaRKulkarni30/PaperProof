import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  FileText,
  ExternalLink,
  Trash2,
  RotateCcw,
  Plus,
  Loader2,
  Clock,
} from "lucide-react";
import { api } from "../api/client";
import { useToast } from "../components/Toast";
import { VERDICT_META } from "../components/DonutChart";

function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString([], {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function HistoryPage() {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);

  const load = async () => {
    try {
      const data = await api.listReports();
      setReports(data || []);
    } catch (err) {
      toast(err.message || "Could not load history.", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (id, filename) => {
    setBusyId(id);
    try {
      await api.deleteReport(id);
      setReports((prev) => prev.filter((r) => r.id !== id));
      toast(`Deleted "${filename}".`, "info");
    } catch (err) {
      toast(err.message || "Delete failed.", "error");
    } finally {
      setBusyId(null);
    }
  };

  const handleRerun = async (id) => {
    setBusyId(id);
    try {
      const res = await api.rerunReport(id);
      toast("Re-running verification pipeline…", "success");
      navigate(`/report/${res.id}`);
    } catch (err) {
      toast(err.message || "Re-run failed.", "error");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      <section className="plum-hero text-cream-50">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <span className="font-sans text-[11px] font-semibold uppercase tracking-[0.2em] text-gold">
              Audit Archive
            </span>
            <h1 className="mt-1.5 font-display text-4xl font-bold sm:text-5xl">
              Verification History
            </h1>
            <p className="mt-2 font-serif text-base text-cream-100/80">
              Reopen past verification reports, re-run analyses, or manage saved audits.
            </p>
          </div>
          <Link to="/verify" className="btn-gold">
            <Plus className="h-4 w-4" /> New Verification
          </Link>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((k) => (
              <div key={k} className="h-24 animate-pulse rounded-2xl bg-sand-200/70" />
            ))}
          </div>
        ) : reports.length === 0 ? (
          <div className="journal-card p-12 text-center space-y-4">
            <FileText className="mx-auto h-10 w-10 text-burgundy/60" />
            <h2 className="font-display text-3xl font-bold text-plum-900">
              No verification reports yet
            </h2>
            <p className="font-serif text-sm text-ink-muted max-w-md mx-auto">
              Upload your first PDF, DOCX, or TXT manuscript—or launch the built-in Transformer &amp; BERT sample document.
            </p>
            <Link to="/verify" className="btn-primary">
              Start First Verification
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {reports.map((r, idx) => {
              const vc = r.verdict_counts || {};
              const total = Math.max(r.claim_count || 0, 1);
              return (
                <motion.div
                  key={r.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.04 }}
                  className="journal-card p-5 flex flex-col gap-4 md:flex-row md:items-center md:justify-between hover:shadow-journal-lg transition-shadow"
                >
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap items-center gap-2.5">
                      <Link
                        to={`/report/${r.id}`}
                        className="font-display text-2xl font-bold text-plum-900 hover:text-burgundy transition-colors truncate"
                      >
                        {r.filename}
                      </Link>
                      <span
                        className={`rounded-full px-2.5 py-0.5 font-sans text-[10px] font-bold uppercase tracking-wider ${
                          r.status === "completed"
                            ? "bg-verdict-supported/15 text-verdict-supported"
                            : r.status === "failed"
                            ? "bg-verdict-unsupported/15 text-verdict-unsupported"
                            : "bg-gold/25 text-plum-900"
                        }`}
                      >
                        {r.status}
                      </span>
                      <span className="rounded-full bg-sand-200 px-2.5 py-0.5 font-sans text-[10px] font-semibold uppercase tracking-wider text-ink-muted">
                        Mode: {r.mode}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-sans text-xs text-ink-soft">
                      <span className="inline-flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5" /> {formatDate(r.created_at)}
                      </span>
                      <span>Report #{r.short_id}</span>
                      <span>
                        {r.claim_count} claims · {r.reference_count} references
                      </span>
                    </div>

                    {/* Verdict mini stacked bar */}
                    {r.status === "completed" && r.claim_count > 0 && (
                      <div className="max-w-md pt-1">
                        <div className="flex h-2 w-full overflow-hidden rounded-full bg-sand-200">
                          {Object.keys(VERDICT_META).map((vk) => {
                            const val = vc[vk] || 0;
                            if (!val) return null;
                            return (
                              <div
                                key={vk}
                                style={{
                                  width: `${(val / total) * 100}%`,
                                  backgroundColor: VERDICT_META[vk].color,
                                }}
                                title={`${VERDICT_META[vk].label}: ${val}`}
                              />
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    <Link to={`/report/${r.id}`} className="btn-primary py-2 px-4">
                      Open <ExternalLink className="h-3.5 w-3.5" />
                    </Link>
                    <button
                      type="button"
                      disabled={busyId === r.id}
                      onClick={() => handleRerun(r.id)}
                      className="btn-secondary py-2 px-3.5"
                      title="Re-run verification"
                    >
                      {busyId === r.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <RotateCcw className="h-3.5 w-3.5" />
                      )}
                      Re-run
                    </button>
                    <button
                      type="button"
                      disabled={busyId === r.id}
                      onClick={() => handleDelete(r.id, r.filename)}
                      className="inline-flex items-center justify-center rounded-lg border border-verdict-unsupported/30 p-2 text-verdict-unsupported hover:bg-verdict-unsupported/10 transition-colors"
                      aria-label={`Delete ${r.filename}`}
                      title="Delete report"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
