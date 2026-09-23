import { cx } from "../../lib/cx";
import { XIcon } from "./Icons";

const TONES = {
  neutral: {
    soft: "bg-sand-100 text-sand-700 dark:bg-night-800 dark:text-sand-300",
    solid: "bg-sand-500 text-white",
    outline: "border border-sand-300 text-sand-600 dark:border-night-700 dark:text-sand-300",
  },
  moss: {
    soft: "bg-moss-100 text-moss-800 dark:bg-moss-900 dark:text-moss-200",
    solid: "bg-moss-600 text-white",
    outline: "border border-moss-300 text-moss-700 dark:border-moss-700 dark:text-moss-300",
  },
  success: {
    soft: "bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-300",
    solid: "bg-success-600 text-white",
    outline: "border border-success-300 text-success-700 dark:border-success-800 dark:text-success-300",
  },
  warning: {
    soft: "bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-300",
    solid: "bg-warning-500 text-white",
    outline: "border border-warning-300 text-warning-700 dark:border-warning-800 dark:text-warning-300",
  },
  danger: {
    soft: "bg-danger-100 text-danger-800 dark:bg-danger-900 dark:text-danger-300",
    solid: "bg-danger-600 text-white",
    outline: "border border-danger-300 text-danger-700 dark:border-danger-800 dark:text-danger-300",
  },
  info: {
    soft: "bg-info-100 text-info-800 dark:bg-info-900 dark:text-info-300",
    solid: "bg-info-600 text-white",
    outline: "border border-info-300 text-info-700 dark:border-info-800 dark:text-info-300",
  },
};

const DOTS = {
  neutral: "bg-sand-400",
  moss: "bg-moss-500",
  success: "bg-success-500",
  warning: "bg-warning-400",
  danger: "bg-danger-500",
  info: "bg-info-500",
};

const SIZES = {
  sm: "h-6 gap-1 px-2 text-[11px]",
  md: "h-7 gap-1.5 px-2.5 text-xs",
};

export function Chip({
  tone = "neutral",
  variant = "soft",
  size = "md",
  label,
  icon: Icon,
  dot = false,
  removable = false,
  selected = false,
  disabled = false,
  onRemove,
  onClick,
  className,
}) {
  const isSelectable = typeof onClick === "function" && !disabled;

  const handleClick = () => {
    if (!isSelectable) return;
    onClick();
  };

  const handleRemove = (e) => {
    e.stopPropagation();
    onRemove?.();
  };

  const Comp = isSelectable ? "button" : "span";

  return (
    <Comp
      onClick={handleClick}
      disabled={isSelectable ? undefined : disabled}
      aria-pressed={isSelectable ? selected : undefined}
      className={cx(
        "inline-flex select-none items-center rounded-full font-medium transition-all",
        SIZES[size],
        selected
          ? "bg-moss-600 text-white shadow-soft"
          : TONES[tone][variant],
        isSelectable && !selected && "hover:border-moss-400 hover:text-moss-800 dark:hover:text-moss-200 cursor-pointer",
        isSelectable && "outline-offset-2 outline-moss-600/60 focus-visible:outline-2",
        disabled && "cursor-not-allowed opacity-50",
        className
      )}
    >
      {dot && <span className={cx("size-1.5 shrink-0 rounded-full", selected ? "bg-white" : DOTS[tone])} />}
      {Icon && <Icon size={12} className="shrink-0" />}
      <span className="truncate">{label}</span>
      {removable && !disabled && (
        <button
          type="button"
          onClick={handleRemove}
          aria-label={`Remove ${label}`}
          className={cx(
            "shrink-0 rounded-full p-0.5 transition-colors hover:bg-black/10",
            selected ? "hover:bg-white/20" : ""
          )}
        >
          <XIcon size={size === "sm" ? 10 : 11} strokeWidth={2.5} />
        </button>
      )}
    </Comp>
  );
}
