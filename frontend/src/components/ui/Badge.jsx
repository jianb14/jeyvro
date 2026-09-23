import { cx } from "../../lib/cx";

const TONES = {
  neutral: {
    solid: "bg-sand-500 text-white",
    soft: "bg-sand-100 text-sand-700 dark:bg-night-800 dark:text-sand-300",
    outline: "border border-sand-300 text-sand-600 dark:border-night-700 dark:text-sand-300",
  },
  moss: {
    solid: "bg-moss-600 text-white",
    soft: "bg-moss-100 text-moss-800 dark:bg-moss-900 dark:text-moss-200",
    outline: "border border-moss-300 text-moss-700 dark:border-moss-700 dark:text-moss-300",
  },
  success: {
    solid: "bg-success-600 text-white",
    soft: "bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-300",
    outline: "border border-success-300 text-success-700 dark:border-success-800 dark:text-success-300",
  },
  warning: {
    solid: "bg-warning-500 text-white",
    soft: "bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-300",
    outline: "border border-warning-300 text-warning-700 dark:border-warning-800 dark:text-warning-300",
  },
  danger: {
    solid: "bg-danger-600 text-white",
    soft: "bg-danger-100 text-danger-800 dark:bg-danger-900 dark:text-danger-300",
    outline: "border border-danger-300 text-danger-700 dark:border-danger-800 dark:text-danger-300",
  },
  info: {
    solid: "bg-info-600 text-white",
    soft: "bg-info-100 text-info-800 dark:bg-info-900 dark:text-info-300",
    outline: "border border-info-300 text-info-700 dark:border-info-800 dark:text-info-300",
  },
};

const DOT_COLORS = {
  neutral: "bg-sand-400",
  moss: "bg-moss-500",
  success: "bg-success-500",
  warning: "bg-warning-400",
  danger: "bg-danger-500",
  info: "bg-info-500",
};

const SIZES = {
  sm: "h-5 gap-1 px-2 text-[10px]",
  md: "h-6 gap-1.5 px-2.5 text-xs",
};

export function Badge({ tone = "moss", variant = "soft", size = "md", dot = false, icon: Icon, className, children }) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full font-medium",
        TONES[tone][variant],
        SIZES[size],
        className
      )}
    >
      {dot && <span className={cx("size-1.5 shrink-0 rounded-full", DOT_COLORS[tone])} />}
      {Icon && <Icon size={12} className="shrink-0" />}
      {children}
    </span>
  );
}
