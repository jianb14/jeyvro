import { cx } from "../../lib/cx";

export function Label({ className, required = false, children, ...props }) {
  return (
    <label className={cx("text-sm font-medium text-sand-800 dark:text-sand-200", className)} {...props}>
      {children}
      {required && <span className="ml-0.5 text-danger-500">*</span>}
    </label>
  );
}
