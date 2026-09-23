import { cx } from "../../lib/cx";

export function Skeleton({ className }) {
  return (
    <div
      aria-hidden="true"
      className={cx("animate-pulse rounded-lg bg-sand-200/80 dark:bg-night-800", className)}
    />
  );
}
