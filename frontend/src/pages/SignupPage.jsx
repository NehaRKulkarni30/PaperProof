import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Eye, EyeOff, Loader2, Mail, Lock, User, Sparkles } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import { api } from "../api/client";
import { DocumentMedalIllustration } from "../components/Illustrations";

export default function SignupPage() {
  const { signup, demoLogin } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [agree, setAgree] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [error, setError] = useState("");

  const handleDemoLogin = async () => {
    setError("");
    setDemoLoading(true);
    try {
      await demoLogin();
      toast("Signed in as Demo Reviewer — no credentials needed!", "success");
      navigate("/verify", { replace: true });
    } catch (err) {
      setError(err.message || "Unable to start demo session.");
    } finally {
      setDemoLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }
    if (password !== confirmPw) {
      setError("Passwords do not match.");
      return;
    }
    if (!agree) {
      setError("Please accept the Terms and Privacy Policy to continue.");
      return;
    }

    setSubmitting(true);
    try {
      await signup({ name, email, password });
      toast("Account created! Welcome to PaperProof.", "success");
      navigate("/verify", { replace: true });
    } catch (err) {
      setError(err.message || "Could not create account.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleClick = async () => {
    try {
      await api.googleAuth(null);
    } catch (err) {
      toast(
        err.message || "Google Sign-Up is not configured yet. Please sign up with email and password.",
        "info",
        4500
      );
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-140px)] items-center justify-center px-4 py-12">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md rounded-2xl border border-sand-300 bg-cream-100/95 p-7 sm:p-9 shadow-journal-lg"
      >
        <div className="flex flex-col items-center text-center">
          <DocumentMedalIllustration className="h-16 w-16 mb-2" />
          <h1 className="font-display text-4xl font-bold text-plum-900">
            Create your account
          </h1>
          <p className="mt-1 font-serif text-sm text-ink-muted">
            Start verifying scientific claims and citations with primary-source proof.
          </p>
        </div>

        {error && (
          <div className="mt-5 rounded-xl border border-verdict-unsupported/35 bg-verdict-unsupported/10 px-4 py-3 font-sans text-xs text-verdict-unsupported">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="signup-name" className="label-caps block mb-1.5">
              Full Name
            </label>
            <div className="relative">
              <User className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-soft" />
              <input
                id="signup-name"
                type="text"
                required
                minLength={2}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Dr. Ada Lovelace"
                className="w-full rounded-xl border border-sand-300 bg-cream-50 pl-10 pr-4 py-2.5 font-sans text-sm text-ink placeholder:text-ink-soft/60 focus:border-burgundy focus:outline-none focus:ring-2 focus:ring-burgundy/15"
              />
            </div>
          </div>

          <div>
            <label htmlFor="signup-email" className="label-caps block mb-1.5">
              Email Address
            </label>
            <div className="relative">
              <Mail className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-soft" />
              <input
                id="signup-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="researcher@university.edu"
                className="w-full rounded-xl border border-sand-300 bg-cream-50 pl-10 pr-4 py-2.5 font-sans text-sm text-ink placeholder:text-ink-soft/60 focus:border-burgundy focus:outline-none focus:ring-2 focus:ring-burgundy/15"
              />
            </div>
          </div>

          <div>
            <label htmlFor="signup-password" className="label-caps block mb-1.5">
              Password
            </label>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-soft" />
              <input
                id="signup-password"
                type={showPw ? "text" : "password"}
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 6 characters"
                className="w-full rounded-xl border border-sand-300 bg-cream-50 pl-10 pr-10 py-2.5 font-sans text-sm text-ink placeholder:text-ink-soft/60 focus:border-burgundy focus:outline-none focus:ring-2 focus:ring-burgundy/15"
              />
              <button
                type="button"
                onClick={() => setShowPw((s) => !s)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-soft hover:text-burgundy"
                aria-label={showPw ? "Hide password" : "Show password"}
              >
                {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div>
            <label htmlFor="signup-confirm" className="label-caps block mb-1.5">
              Confirm Password
            </label>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-soft" />
              <input
                id="signup-confirm"
                type={showPw ? "text" : "password"}
                required
                value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)}
                placeholder="Re-enter your password"
                className="w-full rounded-xl border border-sand-300 bg-cream-50 pl-10 pr-4 py-2.5 font-sans text-sm text-ink placeholder:text-ink-soft/60 focus:border-burgundy focus:outline-none focus:ring-2 focus:ring-burgundy/15"
              />
            </div>
          </div>

          <label className="flex items-start gap-2.5 font-sans text-xs text-ink-muted cursor-pointer">
            <input
              type="checkbox"
              checked={agree}
              onChange={(e) => setAgree(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-sand-300 accent-burgundy"
            />
            <span>
              I agree to the{" "}
              <span className="font-semibold text-burgundy">Terms of Use</span> and{" "}
              <span className="font-semibold text-burgundy">Privacy Policy</span>, and understand PaperProof is an automated research aid.
            </span>
          </label>

          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full py-3"
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Sign Up"}
          </button>
        </form>

        <div className="my-5 flex items-center gap-3">
          <div className="h-px flex-1 bg-sand-300" />
          <span className="font-sans text-[11px] font-semibold uppercase tracking-widest text-ink-soft">
            OR
          </span>
          <div className="h-px flex-1 bg-sand-300" />
        </div>

        <div className="space-y-2.5">
          <button
            type="button"
            disabled={demoLoading || submitting}
            onClick={handleDemoLogin}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-gold-amber/50 bg-gold/20 px-4 py-2.5 font-sans text-xs font-semibold text-plum-900 shadow-sm hover:bg-gold/35 transition-colors disabled:opacity-50"
          >
            {demoLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4 text-burgundy" />
            )}
            Demo Login (No Sign-Up Needed)
          </button>

          <button
            type="button"
            onClick={handleGoogleClick}
            className="flex w-full items-center justify-center gap-2.5 rounded-xl border border-sand-300 bg-cream-50 px-4 py-2.5 font-sans text-xs font-semibold text-ink shadow-sm hover:bg-white hover:border-burgundy/40 transition-colors"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M23.49 12.27c0-.79-.07-1.54-.2-2.27H12v4.51h6.47c-.29 1.48-1.14 2.73-2.4 3.58v3h3.86c2.26-2.09 3.56-5.17 3.56-8.82z" />
              <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.86-3c-1.08.72-2.45 1.16-4.07 1.16-3.13 0-5.78-2.11-6.73-4.96H1.29v3.09C3.26 21.3 7.31 24 12 24z" />
              <path fill="#FBBC05" d="M5.27 14.29c-.25-.72-.38-1.49-.38-2.29s.14-1.57.38-2.29V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.98-3.09z" />
              <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.98 3.09c.95-2.85 3.6-4.96 6.73-4.96z" />
            </svg>
            Sign up with Google
          </button>
        </div>

        <p className="mt-6 text-center font-sans text-xs text-ink-muted">
          Already have an account?{" "}
          <Link to="/login" className="font-semibold text-burgundy hover:underline">
            Log In
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
