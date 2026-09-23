import { cx } from "../../lib/cx";

export function Divider({ label, vertical = false, className }) {
  if (vertical) {
    return (
      <span
        role="separator"
        aria-orientation="vertical"
        className={cx("inline-block h-full w-px shrink-0 bg-sand-200 dark:bg-night-800", className)}
      />
    );
  }
  if (label) {
    return (
      <div className={cx("flex w-full items-center gap-4", className)}>
        <span className="h-px flex-1 bg-sand-200 dark:bg-night-800" />
        <span className="text-xs font-medium uppercase tracking-wider text-sand-400">{label}</span>
        <span className="h-px flex-1 bg-sand-200 dark:bg-night-800" />
      </div>
    );
  }
  return <span role="separator" className={cx("block h-px w-full bg-sand-200 dark:bg-night-800", className)} />;
}
