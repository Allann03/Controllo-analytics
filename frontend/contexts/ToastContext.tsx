"use client";
import { createContext, useContext, useState, useCallback, useRef, useEffect, type ReactElement } from "react";

export type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  removing?: boolean;
}

interface ToastContextValue {
  show: (opts: { type?: ToastType; title: string; message?: string; duration?: number }) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextValue>({
  show: () => {},
  success: () => {},
  error: () => {},
  info: () => {},
  warning: () => {},
});

export function useToast() { return useContext(ToastContext); }

const ICONS: Record<ToastType, ReactElement> = {
  success: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  ),
  error: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  warning: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
    </svg>
  ),
  info: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
    </svg>
  ),
};

// Light-first palette — dark: variant applied via CSS class
const CFG: Record<ToastType, {
  bar: string;
  iconBg: string;
  iconColor: string;
  darkIconBg: string;
  label: string;
}> = {
  success: {
    bar: "#059669",
    iconBg: "#d1fae5",
    iconColor: "#065f46",
    darkIconBg: "rgba(16,185,129,0.15)",
    label: "Sucesso",
  },
  error: {
    bar: "#dc2626",
    iconBg: "#fee2e2",
    iconColor: "#7f1d1d",
    darkIconBg: "rgba(239,68,68,0.15)",
    label: "Erro",
  },
  warning: {
    bar: "#d97706",
    iconBg: "#fef3c7",
    iconColor: "#78350f",
    darkIconBg: "rgba(245,158,11,0.15)",
    label: "Atenção",
  },
  info: {
    bar: "#102a43",
    iconBg: "#dbeafe",
    iconColor: "#1e3a5f",
    darkIconBg: "rgba(59,130,246,0.15)",
    label: "Info",
  },
};

function ToastItem({ toast, onRemove, isLight }: {
  toast: Toast;
  onRemove: (id: string) => void;
  isLight: boolean;
}) {
  const cfg = CFG[toast.type];

  return (
    <div
      className={`
        relative flex items-start gap-3 overflow-hidden
        rounded-xl border shadow-lg
        min-w-[300px] max-w-[400px]
        transition-all duration-200
        ${isLight
          ? "bg-white border-slate-200"
          : "bg-slate-800 border-slate-700"
        }
      `}
      style={{
        boxShadow: isLight
          ? "0 4px 16px rgba(0,0,0,0.10), 0 1px 4px rgba(0,0,0,0.06)"
          : "0 4px 24px rgba(0,0,0,0.35), 0 1px 6px rgba(0,0,0,0.25)",
      }}
    >
      {/* Left accent bar */}
      <div
        className="absolute left-0 top-0 bottom-0 w-1 rounded-r-sm"
        style={{ background: cfg.bar }}
      />

      {/* Content */}
      <div className="flex items-start gap-3 pl-5 pr-3 py-3.5 w-full">
        {/* Icon circle */}
        <div
          className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center mt-0.5"
          style={{
            background: isLight ? cfg.iconBg : cfg.darkIconBg,
            color: isLight ? cfg.iconColor : cfg.bar,
          }}
        >
          {ICONS[toast.type]}
        </div>

        {/* Text */}
        <div className="flex-1 min-w-0 pt-0.5">
          <p className={`text-sm font-semibold leading-snug ${isLight ? "text-slate-800" : "text-slate-100"}`}>
            {toast.title}
          </p>
          {toast.message && (
            <p className={`text-xs mt-0.5 leading-relaxed ${isLight ? "text-slate-500" : "text-slate-400"}`}>
              {toast.message}
            </p>
          )}
        </div>

        {/* Close */}
        <button
          onClick={() => onRemove(toast.id)}
          className={`
            flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-md transition-colors mt-0.5
            ${isLight
              ? "text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              : "text-slate-500 hover:bg-slate-700 hover:text-slate-300"
            }
          `}
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [isLight, setIsLight] = useState(false);
  const counterRef = useRef(0);

  useEffect(() => {
    const check = () => setIsLight(document.documentElement.classList.contains("light"));
    check();
    const obs = new MutationObserver(check);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);

  const remove = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const show = useCallback((opts: { type?: ToastType; title: string; message?: string; duration?: number }) => {
    const id = `toast-${++counterRef.current}`;
    const type = opts.type ?? "info";
    const duration = opts.duration ?? (type === "error" || type === "warning" ? 15000 : 4500);
    setToasts(prev => [...prev.slice(-4), { id, type, title: opts.title, message: opts.message }]);
    setTimeout(() => remove(id), duration);
  }, [remove]);

  const success = useCallback((title: string, message?: string) => show({ type: "success", title, message }), [show]);
  const error   = useCallback((title: string, message?: string) => show({ type: "error",   title, message }), [show]);
  const info    = useCallback((title: string, message?: string) => show({ type: "info",    title, message }), [show]);
  const warning = useCallback((title: string, message?: string) => show({ type: "warning", title, message }), [show]);

  return (
    <ToastContext.Provider value={{ show, success, error, info, warning }}>
      {children}
      <div
        className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-2.5 pointer-events-none"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map(t => (
          <div
            key={t.id}
            className="pointer-events-auto"
            style={{
              animation: "toast-slide-in 0.25s cubic-bezier(0.16,1,0.3,1) both",
            }}
          >
            <ToastItem toast={t} onRemove={remove} isLight={isLight} />
          </div>
        ))}
      </div>
      <style>{`
        @keyframes toast-slide-in {
          from { opacity: 0; transform: translateX(24px) scale(0.97); }
          to   { opacity: 1; transform: translateX(0)    scale(1); }
        }
      `}</style>
    </ToastContext.Provider>
  );
}
