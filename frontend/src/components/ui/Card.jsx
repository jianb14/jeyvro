import { cx } from "../../lib/cx";

export function Card({ hover = false, className, children, ...props }) {
  return (
    <div
      className={cx(
        "rounded-2xl border border-sand-200 bg-white shadow-soft dark:border-night-800 dark:bg-night-900",
        hover && "transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lift",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className, children }) {
  return <div className={cx("flex flex-col gap-1 p-6 pb-4", className)}>{children}</div>;
}

export function CardTitle({ className, children }) {
  return <h3 className={cx("font-display text-lg font-semibold text-sand-900 dark:text-sand-100", className)}>{children}</h3>;
}

export function CardDescription({ className, children }) {
  return <p className={cx("text-sm text-sand-500 dark:text-sand-400", className)}>{children}</p>;
}

export function CardContent({ className, children }) {
  return <div className={cx("p-6 pt-0", className)}>{children}</div>;
}

export function CardFooter({ className, children }) {
  return (
    <div className={cx("flex flex-wrap items-center gap-3 border-t border-sand-200 px-6 py-4 dark:border-night-800", className)}>
      {children}
    </div>
  );
}
