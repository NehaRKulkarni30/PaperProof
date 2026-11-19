import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Eye, EyeOff, Loader2, Mail, Lock } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import { api } from "../api/client";
import { DocumentMedalIllustration } from "../components/Illustrations";

export default function LoginPage() {
  const { login } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from || "/verify";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login({ email, password, remember_me: rememberMe });
      toast("Welcome back to PaperProof.", "success");
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || "Unable to log in. Please check your credentials.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleClick = async () => {
    try {
      await api.googleAuth(null);
    } catch (err) {
      toast(
        err.message || "Google OAuth is not configured yet. Please log in with email and password.",
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
            Welcome back
          </h1>
          <p className="mt-1 font-serif text-sm text-ink-muted">
            Log in to continue verifying claims and reviewing reports.
          </p>
        </div>

        {error && (
          <div className="mt-5 rounded-xl border border-verdict-unsupported/35 bg-verdict-unsupported/10 px-4 py-3 font-sans text-xs text-verdict-unsupported">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="login-email" className="label-caps block mb-1.5">
              Email Address
            </label>
            <div className="relative">
              <Mail className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-soft" />
              <input
                id="login-email"
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
            <label htmlFor="login-password" className="label-caps block mb-1.5">
              Password
            </label>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-soft" />
              <input
                id="login-password"
                type={showPw ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
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

          <div className="flex items-center justify-between">
            <label className="inline-flex items-center gap-2 font-sans text-xs text-ink-muted cursor-pointer">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="h-4 w-4 rounded border-sand-300 accent-burgundy"
              />
              Remember me
            </label>
            <button
              type="button"
              onClick={() =>
                toast("Password reset emails are disabled in hackathon demo mode. Create a fresh account or use your saved credentials.", "info")
              }
              className="font-sans text-xs font-medium text-burgundy hover:underline"
            >
              Forgot password?
            </button>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full py-3"
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Log In"}
          </button>
        </form>

        <div className="my-5 flex items-center gap-3">
          <div className="h-px flex-1 bg-sand-300" />
          <span className="font-sans text-[11px] font-semibold uppercase tracking-widest text-ink-soft">
            OR
          </span>
          <div className="h-px flex-1 bg-sand-300" />
        </div>

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
          Continue with Google
        </button>

        <p className="mt-6 text-center font-sans text-xs text-ink-muted">
          New to PaperProof?{" "}
          <Link to="/signup" className="font-semibold text-burgundy hover:underline">
            Sign Up
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
