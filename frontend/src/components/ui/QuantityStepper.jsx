import { cx } from "../../lib/cx";
import { MinusIcon, PlusIcon } from "./Icons";

export function QuantityStepper({
  value = 1,
  onChange,
  min = 1,
  max = 99,
  size = "md",
  variant = "boxed",
  disabled = false,
  className,
}) {
  const clamp = (n) => Math.min(max, Math.max(min, n));

  const SIZES = {
    sm: { btn: "size-6", icon: 14, wrap: "gap-0.5 text-xs", boxed: "rounded-lg" },
    md: { btn: "size-8", icon: 16, wrap: "gap-1 text-sm", boxed: "rounded-xl" },
  };

  const s = SIZES[size];
  const isBoxed = variant === "boxed";

  const btnCls = cx(
    "inline-flex items-center justify-center font-medium transition-all outline-offset-1 outline-moss-600/60 focus-visible:outline-2 disabled:pointer-events-none disabled:opacity-35",
    s.btn,
    isBoxed
      ? "bg-sand-100 text-sand-700 hover:bg-sand-200 dark:bg-night-800 dark:text-sand-300 dark:hover:bg-night-700"
      : "text-sand-500 hover:bg-sand-100 hover:text-sand-800 dark:hover:bg-night-800 dark:hover:text-sand-200"
  );

  return (
    <div
      className={cx(
        "inline-flex select-none items-center",
        s.wrap,
        isBoxed && cx("border border-sand-300 p-0.5 dark:border-night-700", s.boxed),
        disabled && "pointer-events-none opacity-50",
        className
      )}
    >
      <button
        type="button"
        aria-label="Decrease quantity"
        disabled={disabled || value <= min}
        onClick={() => onChange?.(clamp(value - 1))}
        className={cx(btnCls, "rounded-lg")}
      >
        <MinusIcon size={s.icon} strokeWidth={2.5} />
      </button>
      <span
        aria-live="polite"
        className={cx(
          "inline-flex min-w-7 items-center justify-center font-medium tabular-nums text-sand-900 dark:text-sand-100",
          isBoxed && "px-1"
        )}
      >
        {value}
      </span>
      <button
        type="button"
        aria-label="Increase quantity"
        disabled={disabled || value >= max}
        onClick={() => onChange?.(clamp(value + 1))}
        className={cx(btnCls, "rounded-lg")}
      >
        <PlusIcon size={s.icon} strokeWidth={2.5} />
      </button>
    </div>
  );
}
