import { cx } from "../../lib/cx";

export function Kbd({ className, children }) {
  return (
    <kbd
      className={cx(
        "inline-flex h-6 min-w-6 items-center justify-center rounded-md border border-sand-300 bg-sand-100 px-1.5 font-mono text-[11px] font-medium text-sand-600 shadow-[inset_0_-2px_0_0_rgb(0_0_0/0.06)] dark:border-night-700 dark:bg-night-800 dark:text-sand-300",
        className
      )}
    >
      {children}
    </kbd>
  );
}
