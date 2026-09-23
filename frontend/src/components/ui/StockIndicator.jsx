import { cx } from "../../lib/cx";

const STATES = {
  "in-stock": {
    dot: "bg-success-500",
    text: "text-success-700 dark:text-success-400",
    label: "In stock",
  },
  "low-stock": {
    dot: "bg-warning-400",
    text: "text-warning-700 dark:text-warning-400",
    label: "Low stock",
  },
  "out-of-stock": {
    dot: "bg-sand-400",
    text: "text-sand-500 dark:text-sand-500",
    label: "Out of stock",
  },
};

export function StockIndicator({ count = 0, threshold = 10, showCount = true, className }) {
  const state =
    count === 0 ? "out-of-stock" : count <= threshold ? "low-stock" : "in-stock";
  const s = STATES[state];

  return (
    <span className={cx("inline-flex items-center gap-1.5 text-xs font-medium", s.text, className)}>
      <span className={cx("size-1.5 rounded-full", s.dot)} />
      {state === "low-stock" && showCount ? `${count} left!` : s.label}
    </span>
  );
}
