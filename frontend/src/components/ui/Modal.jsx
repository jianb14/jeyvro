import { useEffect } from "react";
import { cx } from "../../lib/cx";
import { XIcon } from "./Icons";

const SIZES = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
};

export function Modal({ open, onClose, title, description, size = "md", footer, children, closeOnBackdrop = true }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose?.();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        aria-hidden="true"
        onClick={closeOnBackdrop ? onClose : undefined}
        className="absolute inset-0 animate-fade-in bg-night-950/50 backdrop-blur-sm"
      />
      <div
        role="dialog"
        aria-modal="true"
        className={cx(
          "relative w-full animate-scale-in rounded-2xl border border-sand-200 bg-white shadow-pop dark:border-night-800 dark:bg-night-900",
          SIZES[size]
        )}
      >
        <div className="flex items-start justify-between gap-4 p-6 pb-0">
          <div className="flex flex-col gap-1">
            {title && <h2 className="font-display text-xl font-semibold text-sand-900 dark:text-sand-100">{title}</h2>}
            {description && <p className="text-sm text-sand-500 dark:text-sand-400">{description}</p>}
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="shrink-0 rounded-lg p-1.5 text-sand-400 transition-colors hover:bg-sand-100 hover:text-sand-700 dark:hover:bg-night-800 dark:hover:text-sand-200"
          >
            <XIcon size={17} />
          </button>
        </div>
        <div className="p-6 text-sm text-sand-600 dark:text-sand-300">{children}</div>
        {footer && (
          <div className="flex justify-end gap-3 border-t border-sand-200 px-6 py-4 dark:border-night-800">{footer}</div>
        )}
      </div>
    </div>
  );
}
