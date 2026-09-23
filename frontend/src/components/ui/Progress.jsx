import { cx } from "../../lib/cx";

const TONES = {
  moss: "bg-moss-600",
  success: "bg-success-500",
  warning: "bg-warning-500",
  danger: "bg-danger-500",
  info: "bg-info-500",
};

const SIZES = {
  sm: "h-1.5",
  md: "h-2.5",
  lg: "h-4",
};

export function Progress({ value = 0, max = 100, tone = "moss", size = "md", indeterminate = false, className, showLabel = false }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className={cx("flex w-full items-center gap-3", className)}>
      <div
        role="progressbar"
        aria-valuenow={indeterminate ? undefined : Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
        className={cx("relative w-full overflow-hidden rounded-full bg-sand-200 dark:bg-night-800", SIZES[size])}
      >
        {indeterminate ? (
          <div className="absolute inset-y-0 left-0 w-1/3 animate-indeterminate rounded-full bg-moss-600" />
        ) : (
          <div
            className={cx("h-full rounded-full transition-[width] duration-500", TONES[tone])}
            style={{ width: `${pct}%` }}
          />
        )}
      </div>
      {showLabel && !indeterminate && (
        <span className="w-9 shrink-0 text-right text-xs font-medium tabular-nums text-sand-500 dark:text-sand-400">
          {Math.round(pct)}%
        </span>
      )}
    </div>
  );
}
