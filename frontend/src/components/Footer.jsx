import React from "react";
import { Link } from "react-router-dom";
import Logo from "./Logo";

export default function Footer() {
  return (
    <footer className="border-t border-sand-300/80 bg-cream-100">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 py-7 sm:flex-row sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <Logo size="sm" />
          <span className="hidden sm:inline text-sand-300">|</span>
          <span className="font-sans text-xs text-ink-soft">© 2026 PaperProof</span>
        </div>

        <p className="font-display text-lg italic text-burgundy">
          “Don&apos;t just cite, prove it.”
        </p>

        <div className="no-print flex items-center gap-5 font-sans text-xs text-ink-muted">
          <Link to="/features" className="hover:text-burgundy transition-colors">
            Features
          </Link>
          <Link to="/how-it-works" className="hover:text-burgundy transition-colors">
            How it Works
          </Link>
          <Link to="/about" className="hover:text-burgundy transition-colors">
            About
          </Link>
        </div>
      </div>
    </footer>
  );
}
