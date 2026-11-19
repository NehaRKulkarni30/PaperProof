import React, { createContext, useCallback, useContext, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = "info", duration = 3800) => {
    const id = `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    setToasts((prev) => [...prev, { id, message, type }]);
    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
  }, []);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      <div className="no-print fixed bottom-5 right-5 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none px-4 sm:px-0">
        <AnimatePresence>
          {toasts.map((t) => {
            const Icon =
              t.type === "success"
                ? CheckCircle2
                : t.type === "error"
                ? AlertTriangle
                : Info;
            const accent =
              t.type === "success"
                ? "border-verdict-supported/40 bg-cream-50 text-ink"
                : t.type === "error"
                ? "border-verdict-unsupported/40 bg-cream-50 text-ink"
                : "border-gold/60 bg-plum-900 text-cream-50";
            const iconColor =
              t.type === "success"
                ? "text-verdict-supported"
                : t.type === "error"
                ? "text-verdict-unsupported"
                : "text-gold";

            return (
              <motion.div
                key={t.id}
                initial={{ opacity: 0, y: 18, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 12, scale: 0.96 }}
                className={`pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 shadow-journal-lg ${accent}`}
              >
                <Icon className={`h-5 w-5 shrink-0 mt-0.5 ${iconColor}`} />
                <p className="font-sans text-xs leading-relaxed flex-1">{t.message}</p>
                <button
                  onClick={() => dismiss(t.id)}
                  className="opacity-60 hover:opacity-100 transition-opacity"
                  aria-label="Dismiss notification"
                >
                  <X className="h-4 w-4" />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}
