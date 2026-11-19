import React from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./components/Toast";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import ProtectedRoute from "./components/ProtectedRoute";

import HomePage from "./pages/HomePage";
import FeaturesPage from "./pages/FeaturesPage";
import HowItWorksPage from "./pages/HowItWorksPage";
import AboutPage from "./pages/AboutPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import VerifyPage from "./pages/VerifyPage";
import ReportPage from "./pages/ReportPage";
import SharedReportPage from "./pages/SharedReportPage";
import HistoryPage from "./pages/HistoryPage";

function PageWrap({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      {children}
    </motion.div>
  );
}

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<PageWrap><HomePage /></PageWrap>} />
        <Route path="/features" element={<PageWrap><FeaturesPage /></PageWrap>} />
        <Route path="/how-it-works" element={<PageWrap><HowItWorksPage /></PageWrap>} />
        <Route path="/about" element={<PageWrap><AboutPage /></PageWrap>} />
        <Route path="/login" element={<PageWrap><LoginPage /></PageWrap>} />
        <Route path="/signup" element={<PageWrap><SignupPage /></PageWrap>} />
        <Route path="/shared/:token" element={<PageWrap><SharedReportPage /></PageWrap>} />

        <Route
          path="/verify"
          element={
            <ProtectedRoute>
              <PageWrap><VerifyPage /></PageWrap>
            </ProtectedRoute>
          }
        />
        <Route
          path="/report/:id"
          element={
            <ProtectedRoute>
              <PageWrap><ReportPage /></PageWrap>
            </ProtectedRoute>
          }
        />
        <Route
          path="/history"
          element={
            <ProtectedRoute>
              <PageWrap><HistoryPage /></PageWrap>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <div className="flex min-h-screen flex-col">
            <Navbar />
            <main className="flex-1">
              <AnimatedRoutes />
            </main>
            <Footer />
          </div>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
