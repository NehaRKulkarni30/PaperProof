import React, { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  UploadCloud,
  FileText,
  X,
  Sparkles,
  ArrowRight,
  Loader2,
  ShieldCheck,
  History,
  AlertCircle,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import { api } from "../api/client";

const MAX_BYTES = 15 * 1024 * 1024;
const ALLOWED_EXT = [".pdf", ".docx", ".txt"];

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function VerifyPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [pastedText, setPastedText] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [runningSample, setRunningSample] = useState(false);
  const [error, setError] = useState("");

  const validateAndSelectFile = (candidate) => {
    setError("");
    if (!candidate) return;
    const lower = candidate.name.toLowerCase();
    const okExt = ALLOWED_EXT.some((ext) => lower.endsWith(ext));
    if (!okExt) {
      setError("Unsupported file format. Please upload a PDF, DOCX, or TXT document.");
      return;
    }
    if (candidate.size > MAX_BYTES) {
      setError("File exceeds the 15 MB limit. Please upload a smaller manuscript.");
      return;
    }
    setFile(candidate);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer?.files?.[0];
    if (dropped) validateAndSelectFile(dropped);
  };

  const handleVerify = async () => {
    setError("");
    if (!file && pastedText.trim().length < 20) {
      setError("Please upload a PDF/DOCX/TXT file or paste at least a short paragraph with citations.");
      return;
    }

    setSubmitting(true);
    try {
      const res = file
        ? await api.verifyFile(file)
        : await api.verifyText(pastedText.trim(), "Pasted_Manuscript.txt");
      toast("Document submitted. Running verification pipeline…", "info");
      navigate(`/report/${res.id}`);
    } catch (err) {
      setError(err.message || "Could not start verification.");
      toast(err.message || "Verification failed to start.", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSample = async () => {
    setError("");
    setRunningSample(true);
    try {
      const res = await api.runSample();
      toast("Sample Transformer & BERT manuscript launched!", "success");
      navigate(`/report/${res.id}`);
    } catch (err) {
      setError(err.message || "Could not launch sample document.");
      toast(err.message || "Sample run failed.", "error");
    } finally {
      setRunningSample(false);
    }
  };

  return (
    <section className="plum-hero min-h-[calc(100vh-132px)] text-cream-50 flex items-center">
      <div className="mx-auto w-full max-w-7xl px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-12">
          {/* Left hero column */}
          <motion.div
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.45 }}
            className="lg:col-span-5 space-y-6"
          >
            <div>
              <span className="font-sans text-xs font-semibold uppercase tracking-[0.22em] text-gold">
                Welcome Back{user?.name ? `, ${user.name.split(" ")[0]}` : ""}
              </span>
              <h1 className="mt-3 font-display text-5xl font-bold leading-[1.03] sm:text-6xl lg:text-7xl">
                Check every{" "}
                <span className="text-gold italic">citation.</span>
              </h1>
              <p className="mt-5 font-serif text-lg leading-relaxed text-cream-100/85">
                Don&apos;t just cite, prove it. Evidence-backed verification of scientific claims against open scholarly literature.
              </p>
            </div>

            <div className="space-y-3 border-t border-white/15 pt-6 font-sans text-xs text-cream-100/80">
              <div className="flex items-center gap-2.5">
                <ShieldCheck className="h-4 w-4 text-gold shrink-0" />
                <span>Supports PDF (with page tracking), DOCX, TXT, or pasted text</span>
              </div>
              <div className="flex items-center gap-2.5">
                <Sparkles className="h-4 w-4 text-gold shrink-0" />
                <span>Queries arXiv, CrossRef, Semantic Scholar, and OpenAlex</span>
              </div>
              <div className="pt-2">
                <Link
                  to="/history"
                  className="inline-flex items-center gap-1.5 font-semibold text-gold hover:underline"
                >
                  <History className="h-4 w-4" /> View your verification history
                </Link>
              </div>
            </div>
          </motion.div>

          {/* Right Cream Card: Start a verification */}
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.08 }}
            className="lg:col-span-7"
          >
            <div className="rounded-3xl border border-sand-300 bg-cream-50 p-6 sm:p-8 text-ink shadow-journal-lg">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-5">
                <div>
                  <span className="label-caps text-burgundy">New Audit</span>
                  <h2 className="font-display text-3xl font-bold text-plum-900">
                    Start a verification
                  </h2>
                </div>
                <button
                  type="button"
                  disabled={runningSample || submitting}
                  onClick={handleSample}
                  className="inline-flex items-center gap-1.5 rounded-full border border-gold-amber/40 bg-gold/15 px-3.5 py-1.5 font-sans text-xs font-semibold text-plum-900 hover:bg-gold/30 transition-colors disabled:opacity-50"
                >
                  {runningSample ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5 text-burgundy" />
                  )}
                  Try sample document
                </button>
              </div>

              {error && (
                <div className="mb-4 flex items-start gap-2.5 rounded-xl border border-verdict-unsupported/35 bg-verdict-unsupported/10 px-4 py-3 font-sans text-xs text-verdict-unsupported">
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              {/* Drag and Drop Zone */}
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`group cursor-pointer rounded-2xl border-2 border-dashed p-6 text-center transition-all duration-200 ${
                  dragOver
                    ? "border-burgundy bg-burgundy/5 scale-[1.01]"
                    : "border-sand-300 bg-cream-100/80 hover:border-burgundy/60 hover:bg-sand-200/40"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
                  className="hidden"
                  onChange={(e) => validateAndSelectFile(e.target.files?.[0])}
                />

                <motion.div
                  animate={dragOver ? { y: -6, scale: 1.08 } : { y: 0, scale: 1 }}
                  className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-plum-900 text-gold shadow-sm group-hover:scale-105 transition-transform"
                >
                  <UploadCloud className="h-6 w-6" />
                </motion.div>

                <p className="font-serif text-base font-medium text-plum-900">
                  Drop a PDF, DOCX or TXT here or{" "}
                  <span className="text-burgundy underline decoration-gold underline-offset-4">
                    choose a file
                  </span>
                </p>
                <p className="mt-1 font-sans text-[11px] text-ink-soft">
                  Max 15 MB · Files are extracted in memory and deleted after processing
                </p>
              </div>

              {/* Selected File Chip */}
              {file && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-3 flex items-center justify-between gap-3 rounded-xl border border-burgundy/25 bg-cream-100 px-4 py-2.5"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <FileText className="h-4 w-4 text-burgundy shrink-0" />
                    <span className="truncate font-sans text-xs font-semibold text-plum-900">
                      {file.name}
                    </span>
                    <span className="shrink-0 font-sans text-[11px] text-ink-soft">
                      ({formatBytes(file.size)})
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                      if (fileInputRef.current) fileInputRef.current.value = "";
                    }}
                    className="rounded-md p-1 text-ink-soft hover:bg-sand-200 hover:text-verdict-unsupported"
                    aria-label="Remove file"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </motion.div>
              )}

              {/* Paste Textarea */}
              <div className="mt-5">
                <label htmlFor="paste-manuscript" className="label-caps block mb-1.5">
                  Or paste manuscript text
                </label>
                <textarea
                  id="paste-manuscript"
                  rows={6}
                  value={pastedText}
                  onChange={(e) => setPastedText(e.target.value)}
                  placeholder="Or paste text with a References section...&#10;&#10;Example:&#10;The Transformer relies entirely on attention mechanisms [1].&#10;&#10;References&#10;[1] Vaswani et al. (2017). Attention Is All You Need. arXiv:1706.03762"
                  className="w-full rounded-xl border border-sand-300 bg-white/90 p-3.5 font-serif text-sm leading-relaxed text-ink placeholder:text-ink-soft/65 focus:border-burgundy focus:outline-none focus:ring-2 focus:ring-burgundy/15"
                />
              </div>

              {/* Action Buttons */}
              <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="btn-secondary"
                >
                  <UploadCloud className="h-4 w-4" /> Upload
                </button>

                <button
                  type="button"
                  disabled={submitting || runningSample}
                  onClick={handleVerify}
                  className="btn-primary flex-1 sm:flex-none px-8"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" /> Starting…
                    </>
                  ) : (
                    <>
                      Verify <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
