import { cx } from "../../lib/cx";

const SIZES = {
  sm: "text-sm",
  md: "text-lg",
  lg: "text-2xl",
  xl: "text-3xl",
};

const BADGE_SIZES = {
  sm: "text-[9px] px-1.5 py-0.5",
  md: "text-[10px] px-2 py-0.5",
  lg: "text-xs px-2.5 py-1",
  xl: "text-xs px-2.5 py-1",
};

export function Price({
  amount = 0,
  currency = "₱",
  originalAmount,
  installment,
  discount,
  size = "md",
  className,
}) {
  const format = (n) =>
    currency + n.toLocaleString("en-PH", { minimumFractionDigits: n % 1 === 0 ? 0 : 2 });

  return (
    <div className={cx("flex flex-wrap items-baseline gap-x-2 gap-y-0.5", className)}>
      <span className={cx("font-display font-semibold tabular-nums text-moss-700 dark:text-moss-300", SIZES[size])}>
        {format(amount)}
      </span>
      {originalAmount !== undefined && originalAmount > amount && (
        <span className="text-xs tabular-nums text-sand-400 line-through">{format(originalAmount)}</span>
      )}
      {discount !== undefined && (
        <span
          className={cx(
            "rounded-md bg-danger-100 font-semibold text-danger-700 dark:bg-danger-900/60 dark:text-danger-300",
            BADGE_SIZES[size]
          )}
        >
          -{discount}%
        </span>
      )}
      {installment && (
        <span className="w-full text-[11px] text-sand-500 dark:text-sand-400">{installment}</span>
      )}
    </div>
  );
}
