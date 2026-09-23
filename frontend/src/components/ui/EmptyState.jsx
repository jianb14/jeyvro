import { cx } from "../../lib/cx";

export function EmptyState({ icon: Icon, title, description, action, compact = false, className }) {
  return (
    <div
      className={cx(
        "flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed border-sand-300 text-center dark:border-night-700",
        compact ? "p-8" : "p-14",
        className
      )}
    >
      {Icon && (
        <span className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-sand-100 text-sand-400 dark:bg-night-800 dark:text-sand-500">
          <Icon size={26} />
        </span>
      )}
      <div className="max-w-sm">
        <p className="font-display text-lg font-semibold text-sand-900 dark:text-sand-100">{title}</p>
        {description && <p className="mt-1.5 text-sm leading-relaxed text-sand-500 dark:text-sand-400">{description}</p>}
      </div>
      {action}
    </div>
  );
}
