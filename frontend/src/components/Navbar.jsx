import React, { useEffect, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { LogOut, Menu, X, ChevronDown, FileCheck2, History, ShieldCheck, FileText } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../api/client";
import Logo from "./Logo";

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [latestReportId, setLatestReportId] = useState(null);

  useEffect(() => {
    if (!isAuthenticated) {
      setLatestReportId(null);
      return;
    }
    const match = location.pathname.match(/^\/report\/([^/]+)/);
    if (match) {
      setLatestReportId(match[1]);
      return;
    }
    api
      .listReports()
      .then((list) => {
        if (list && list.length > 0) setLatestReportId(list[0].id);
      })
      .catch(() => {});
  }, [isAuthenticated, location.pathname]);

  const handleLogout = () => {
    logout();
    setMenuOpen(false);
    setMobileOpen(false);
    navigate("/");
  };

  const navLinkClass = ({ isActive }) =>
    `font-sans text-xs font-medium uppercase tracking-[0.13em] transition-colors ${
      isActive ? "text-burgundy font-semibold" : "text-ink-muted hover:text-burgundy"
    }`;

  const initials = (user?.name || "U")
    .split(" ")
    .map((s) => s[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <header className="no-print sticky top-0 z-40 border-b border-sand-300/70 bg-cream-100/95 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6 lg:px-8">
        <Link to={isAuthenticated ? "/verify" : "/"} className="flex items-center">
          <Logo />
        </Link>

        {/* Desktop navigation */}
        <nav className="hidden md:flex items-center gap-7">
          {!isAuthenticated ? (
            <>
              <NavLink to="/" end className={navLinkClass}>
                Home
              </NavLink>
              <NavLink to="/features" className={navLinkClass}>
                Features
              </NavLink>
              <NavLink to="/how-it-works" className={navLinkClass}>
                How it Works
              </NavLink>
              <NavLink to="/about" className={navLinkClass}>
                About
              </NavLink>
            </>
          ) : (
            <>
              <NavLink to="/verify" className={navLinkClass}>
                Verify
              </NavLink>
              <NavLink
                to={latestReportId ? `/report/${latestReportId}` : "/history"}
                className={({ isActive }) =>
                  `font-sans text-xs font-medium uppercase tracking-[0.13em] transition-colors ${
                    isActive || location.pathname.startsWith("/report/")
                      ? "text-burgundy font-semibold"
                      : "text-ink-muted hover:text-burgundy"
                  }`
                }
              >
                Report
              </NavLink>
              <NavLink to="/history" className={navLinkClass}>
                History
              </NavLink>
            </>
          )}
        </nav>

        {/* Desktop actions */}
        <div className="hidden md:flex items-center gap-3">
          {!isAuthenticated ? (
            <>
              <Link
                to="/login"
                className="font-sans text-xs font-semibold uppercase tracking-[0.14em] text-burgundy px-4 py-2 rounded-lg hover:bg-burgundy/5 transition-colors"
              >
                Log In
              </Link>
              <Link to="/signup" className="btn-primary py-2.5 px-5">
                Sign Up
              </Link>
            </>
          ) : (
            <div className="relative">
              <button
                onClick={() => setMenuOpen((o) => !o)}
                className="flex items-center gap-2.5 rounded-full border border-sand-300 bg-cream-50 pl-1.5 pr-3 py-1.5 shadow-sm hover:border-burgundy/40 transition-colors"
              >
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-plum-900 font-sans text-xs font-semibold text-gold">
                  {initials}
                </span>
                <span className="font-sans text-xs font-medium text-ink max-w-[140px] truncate">
                  {user?.name}
                </span>
                <ChevronDown className="h-3.5 w-3.5 text-ink-soft" />
              </button>

              {menuOpen && (
                <div
                  onMouseLeave={() => setMenuOpen(false)}
                  className="absolute right-0 mt-2 w-56 rounded-xl border border-sand-300 bg-cream-50 p-1.5 shadow-journal-lg"
                >
                  <div className="border-b border-sand-200 px-3 py-2">
                    <p className="font-sans text-xs font-semibold text-ink truncate">{user?.name}</p>
                    <p className="font-sans text-[11px] text-ink-soft truncate">{user?.email}</p>
                  </div>
                  <Link
                    to="/verify"
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-2 rounded-lg px-3 py-2 font-sans text-xs text-ink hover:bg-sand-200/60"
                  >
                    <ShieldCheck className="h-4 w-4 text-burgundy" />
                    New Verification
                  </Link>
                  <Link
                    to="/history"
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-2 rounded-lg px-3 py-2 font-sans text-xs text-ink hover:bg-sand-200/60"
                  >
                    <History className="h-4 w-4 text-burgundy" />
                    Verification History
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 font-sans text-xs text-verdict-unsupported hover:bg-verdict-unsupported/10"
                  >
                    <LogOut className="h-4 w-4" />
                    Log Out
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Mobile menu button */}
        <button
          onClick={() => setMobileOpen((o) => !o)}
          className="md:hidden rounded-lg p-2 text-plum-900 hover:bg-sand-200/60"
          aria-label="Toggle navigation menu"
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="md:hidden border-t border-sand-300 bg-cream-50 px-4 py-4 space-y-3">
          {!isAuthenticated ? (
            <>
              <NavLink to="/" end onClick={() => setMobileOpen(false)} className="block py-1.5 font-sans text-xs uppercase tracking-widest text-ink">
                Home
              </NavLink>
              <NavLink to="/features" onClick={() => setMobileOpen(false)} className="block py-1.5 font-sans text-xs uppercase tracking-widest text-ink">
                Features
              </NavLink>
              <NavLink to="/how-it-works" onClick={() => setMobileOpen(false)} className="block py-1.5 font-sans text-xs uppercase tracking-widest text-ink">
                How it Works
              </NavLink>
              <NavLink to="/about" onClick={() => setMobileOpen(false)} className="block py-1.5 font-sans text-xs uppercase tracking-widest text-ink">
                About
              </NavLink>
              <div className="pt-2 flex gap-2">
                <Link to="/login" onClick={() => setMobileOpen(false)} className="btn-secondary flex-1">
                  Log In
                </Link>
                <Link to="/signup" onClick={() => setMobileOpen(false)} className="btn-primary flex-1">
                  Sign Up
                </Link>
              </div>
            </>
          ) : (
            <>
              <NavLink to="/verify" onClick={() => setMobileOpen(false)} className="flex items-center gap-2 py-1.5 font-sans text-xs uppercase tracking-widest text-ink">
                <FileCheck2 className="h-4 w-4 text-burgundy" /> Verify
              </NavLink>
              <NavLink to="/history" onClick={() => setMobileOpen(false)} className="flex items-center gap-2 py-1.5 font-sans text-xs uppercase tracking-widest text-ink">
                <History className="h-4 w-4 text-burgundy" /> History
              </NavLink>
              <NavLink to="/about" onClick={() => setMobileOpen(false)} className="block py-1.5 font-sans text-xs uppercase tracking-widest text-ink">
                About
              </NavLink>
              <div className="pt-2 border-t border-sand-200 flex items-center justify-between">
                <span className="font-sans text-xs text-ink-muted">{user?.name}</span>
                <button onClick={handleLogout} className="font-sans text-xs font-semibold text-verdict-unsupported">
                  Log Out
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </header>
  );
}
