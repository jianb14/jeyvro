import { cx } from "../../lib/cx";

const LOGOS = {
  gcash: { text: "GCash", cls: "bg-[#0075f6] text-white" },
  maya: { text: "Maya", cls: "bg-[#0bd477] text-night-950" },
  card: { text: "Card", cls: "bg-night-800 text-sand-100 dark:bg-sand-100 dark:text-night-900" },
  cod: { text: "COD", cls: "bg-warning-400 text-night-950" },
};

export function PaymentMethodCard({ method, label, description, selected = false, onSelect, disabled = false, className }) {
  const logo = LOGOS[method] || LOGOS.card;

  return (
    <button
      type="button"
      onClick={() => onSelect?.(method)}
      disabled={disabled}
      aria-pressed={selected}
      className={cx(
        "flex w-full items-center gap-4 rounded-2xl border p-4 text-left transition-all outline-offset-2 outline-moss-600/60 focus-visible:outline-2",
        disabled
          ? "cursor-not-allowed border-sand-200 bg-sand-100/70 opacity-60 dark:border-night-800 dark:bg-night-900/60"
          : selected
            ? "border-moss-600 bg-moss-50 ring-1 ring-moss-600 dark:border-moss-500 dark:bg-moss-950/40 dark:ring-moss-500"
            : "border-sand-300 bg-white hover:border-moss-400 dark:border-night-700 dark:bg-night-900 dark:hover:border-moss-600",
        className
      )}
    >
      <span
        className={cx(
          "flex h-9 w-14 shrink-0 items-center justify-center rounded-lg text-xs font-bold tracking-wide",
          logo.cls
        )}
      >
        {logo.text}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-semibold text-sand-900 dark:text-sand-100">{label}</span>
        {description && <span className="block text-xs text-sand-500 dark:text-sand-400">{description}</span>}
      </span>
      <span
        aria-hidden="true"
        className={cx(
          "flex size-5 shrink-0 items-center justify-center rounded-full border-2 transition-all",
          selected ? "border-moss-600 dark:border-moss-400" : "border-sand-300 dark:border-night-700"
        )}
      >
        {selected && <span className="size-2.5 rounded-full bg-moss-600 dark:bg-moss-400" />}
      </span>
    </button>
  );
}
