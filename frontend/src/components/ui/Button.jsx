import { forwardRef } from "react";
import { cx } from "../../lib/cx";
import { Spinner } from "./Spinner";

const VARIANTS = {
  primary:
    "bg-moss-600 text-white shadow-soft hover:bg-moss-700 active:bg-moss-800",
  secondary:
    "bg-moss-100 text-moss-800 hover:bg-moss-200 active:bg-moss-300/70 dark:bg-moss-900 dark:text-moss-100 dark:hover:bg-moss-800",
  outline:
    "border border-sand-300 bg-transparent text-sand-800 hover:border-moss-400 hover:bg-moss-50 dark:border-night-700 dark:text-sand-200 dark:hover:border-moss-600 dark:hover:bg-night-800",
  ghost:
    "text-sand-700 hover:bg-sand-100 hover:text-sand-900 dark:text-sand-300 dark:hover:bg-night-800 dark:hover:text-sand-100",
  destructive:
    "bg-danger-600 text-white shadow-soft hover:bg-danger-700 active:bg-danger-800",
  link: "text-moss-700 underline-offset-4 hover:underline dark:text-moss-300",
};

const SIZES = {
  sm: "h-8 gap-1.5 rounded-lg px-3 text-xs",
  md: "h-10 gap-2 rounded-xl px-4 text-sm",
  lg: "h-12 gap-2 rounded-xl px-6 text-base",
  icon: "h-10 w-10 rounded-xl",
  "icon-sm": "h-8 w-8 rounded-lg",
};

export const Button = forwardRef(function Button(
  {
    variant = "primary",
    size = "md",
    loading = false,
    disabled,
    leadingIcon: Leading,
    trailingIcon: Trailing,
    className,
    children,
    ...props
  },
  ref
) {
  return (
    <button
      ref={ref}
      type="button"
      disabled={disabled || loading}
      className={cx(
        "inline-flex select-none items-center justify-center whitespace-nowrap leading-none font-medium transition-[background-color,border-color,color,transform,translate,scale,rotate] duration-150 outline-offset-2 outline-moss-600/60 focus-visible:outline-2 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50",
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      {...props}
    >
      {loading ? (
        <Spinner size={size === "sm" ? 14 : 16} />
      ) : (
        <>
          {Leading && <Leading size={size === "sm" ? 14 : 16} className="shrink-0 opacity-90" />}
          {children}
          {Trailing && <Trailing size={size === "sm" ? 14 : 16} className="shrink-0 opacity-90" />}
        </>
      )}
    </button>
  );
});
