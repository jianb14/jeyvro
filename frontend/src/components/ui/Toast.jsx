import { useState } from "react";
import { cx } from "../../lib/cx";
import { AlertCircleIcon, CheckCircleIcon, InfoIcon, XIcon } from "./Icons";
const ICONS = {
  success: { icon: CheckCircleIcon, color: "text-success-500" },
  danger: { icon: AlertCircleIcon, color: "text-danger-500" },
  info: { icon: InfoIcon, color: "text-info-500" },
};

export function Toast({ toast, onDismiss }) {
  const [leaving, setLeaving] = useState(false);
  const { icon: Icon, color } = ICONS[toast.tone] || ICONS.info;

  const dismiss = () => {
    setLeaving(true);
    setTimeout(() => onDismiss?.(toast.id), 180);
  };

  return (
    <div
      role="status"
      className={cx(
        "pointer-events-auto flex w-80 items-start gap-3 rounded-xl border border-sand-200 bg-white p-4 shadow-lift transition-all duration-200 dark:border-night-700 dark:bg-night-800",
        leaving ? "translate-x-4 opacity-0" : "animate-slide-up"
      )}
    >
      <Icon size={19} className={cx("mt-0.5 shrink-0", color)} />
      <div className="flex-1 text-sm">
        <p className="font-medium text-sand-900 dark:text-sand-100">{toast.title}</p>
        {toast.description && <p className="mt-0.5 text-sand-500 dark:text-sand-400">{toast.description}</p>}
      </div>
      <button onClick={dismiss} aria-label="Dismiss notification" className="shrink-0 rounded-md p-1 text-sand-400 transition-colors hover:bg-sand-100 hover:text-sand-600 dark:hover:bg-night-700">
        <XIcon size={14} />
      </button>
    </div>
  );
}

export function ToastViewport({ toasts, onDismiss, className }) {
  if (!toasts.length) return null;
  return (
    <div aria-live="polite" className={cx("pointer-events-none fixed bottom-5 right-5 z-50 flex flex-col gap-3", className)}>
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

