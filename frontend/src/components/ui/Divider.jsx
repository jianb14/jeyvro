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
        {/* Sentence case, not `uppercase`. Shouting a low-importance separator
            in tracked capitals pulled the eye harder than the actual sign-in
            button above it; this line only has to say which options follow, so
            it is set like body copy. */}
        <span className="text-xs font-medium text-sand-400 dark:text-sand-500">{label}</span>
        <span className="h-px flex-1 bg-sand-200 dark:bg-night-800" />
      </div>
    );
  }
  return <span role="separator" className={cx("block h-px w-full bg-sand-200 dark:bg-night-800", className)} />;
}
