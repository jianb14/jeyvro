import { cx } from "../../lib/cx";
import { InfoIcon, CheckCircleIcon, AlertTriangleIcon, XCircleIcon, XIcon } from "./Icons";

const TONES = {
  info: {
    wrap: "border-info-200 bg-info-50 text-info-900 dark:border-info-900 dark:bg-info-950/50 dark:text-info-100",
    iconColor: "text-info-500",
    icon: InfoIcon,
  },
  success: {
    wrap: "border-success-200 bg-success-50 text-success-900 dark:border-success-900 dark:bg-success-950/50 dark:text-success-100",
    iconColor: "text-success-500",
    icon: CheckCircleIcon,
  },
  warning: {
    wrap: "border-warning-200 bg-warning-50 text-warning-900 dark:border-warning-900 dark:bg-warning-950/50 dark:text-warning-100",
    iconColor: "text-warning-500",
    icon: AlertTriangleIcon,
  },
  danger: {
    wrap: "border-danger-200 bg-danger-50 text-danger-900 dark:border-danger-900 dark:bg-danger-950/50 dark:text-danger-100",
    iconColor: "text-danger-500",
    icon: XCircleIcon,
  },
};

export function Alert({ tone = "info", title, children, onDismiss, className }) {
  const t = TONES[tone];
  const Icon = t.icon;
  return (
    <div role="alert" className={cx("flex w-full items-start gap-3 rounded-xl border p-4", t.wrap, className)}>
      <Icon size={20} className={cx("mt-0.5 shrink-0", t.iconColor)} />
      <div className="flex-1 text-sm">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={cx("leading-relaxed opacity-80", title && "mt-0.5")}>{children}</div>}
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Dismiss"
          className="shrink-0 rounded-md p-1 opacity-50 transition-opacity hover:opacity-100"
        >
          <XIcon size={15} />
        </button>
      )}
    </div>
  );
}
