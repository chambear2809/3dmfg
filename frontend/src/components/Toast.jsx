import { createContext, useContext, useState, useCallback } from "react";
import { Check, X, AlertTriangle, Info } from "lucide-react";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = "info", duration = 4000) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);

    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }

    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = {
    success: (msg, duration) => addToast(msg, "success", duration),
    error: (msg, duration) => addToast(msg, "error", duration),
    warning: (msg, duration) => addToast(msg, "warning", duration),
    info: (msg, duration) => addToast(msg, "info", duration),
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </ToastContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

function ToastContainer({ toasts, removeToast }) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
      ))}
    </div>
  );
}

const toastStyles = {
  success: {
    bg: "border-[var(--success)]/30",
    text: "text-[var(--success)]",
    bgColor: "rgba(0, 200, 83, 0.1)",
    icon: <Check size={20} />,
  },
  error: {
    bg: "border-[var(--error)]/30",
    text: "text-[var(--error)]",
    bgColor: "rgba(239, 68, 68, 0.1)",
    icon: <X size={20} />,
  },
  warning: {
    bg: "border-[var(--warning)]/30",
    text: "text-[var(--warning)]",
    bgColor: "rgba(238, 122, 8, 0.1)",
    icon: <AlertTriangle size={20} />,
  },
  info: {
    bg: "border-[var(--info)]/30",
    text: "text-[var(--info)]",
    bgColor: "rgba(2, 109, 248, 0.1)",
    icon: <Info size={20} />,
  },
};

function ToastItem({ toast, onClose }) {
  const style = toastStyles[toast.type] || toastStyles.info;

  return (
    <div
      data-testid="toast"
      role="status"
      aria-live="polite"
      className={`${style.bg} border rounded-lg p-4 shadow-lg backdrop-blur-sm animate-slide-in flex items-start gap-3`}
      style={{ backgroundColor: style.bgColor }}
    >
      <span className={style.text}>{style.icon}</span>
      <p className={`${style.text} text-sm flex-1`}>{toast.message}</p>
      <button
        onClick={onClose}
        className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
        aria-label="Close"
      >
        <X size={16} />
      </button>
    </div>
  );
}
