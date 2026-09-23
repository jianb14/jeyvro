import { cx } from "../../lib/cx";

const TONES = {
  moss: "bg-moss-600",
  success: "bg-success-500",
  warning: "bg-warning-400",
  danger: "bg-danger-500",
  info: "bg-info-500",
  neutral: "bg-sand-400",
};

export function Timeline({ items = [], className }) {
  return (
    <ol className={cx("flex flex-col", className)}>
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <li key={i} className="relative flex gap-4 pb-6 last:pb-0">
            {!isLast && (
              <span
                aria-hidden="true"
                className="absolute left-[9px] top-6 h-[calc(100%-1.5rem)] w-px bg-sand-200 dark:bg-night-800"
              />
            )}
            <span
              className={cx(
                "relative z-10 mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full",
                TONES[item.tone || "moss"]
              )}
            >
              {item.icon && <item.icon size={12} strokeWidth={2.5} className="text-white" />}
            </span>
            <div className="flex min-w-0 flex-col gap-0.5">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                <p className="text-sm font-semibold text-sand-900 dark:text-sand-100">{item.title}</p>
                {item.time && <span className="text-xs tabular-nums text-sand-400">{item.time}</span>}
              </div>
              {item.description && (
                <p className="text-sm leading-relaxed text-sand-500 dark:text-sand-400">{item.description}</p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
