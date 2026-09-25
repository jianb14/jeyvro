import { cx } from "../../lib/cx";
import { CheckIcon } from "./Icons";

function Marker({ done, current, index }) {
  return (
    <span
      className={cx(
        "relative z-10 flex size-9 shrink-0 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors",
        done && "border-moss-600 bg-moss-600 text-white dark:border-moss-500 dark:bg-moss-500",
        current && "border-moss-600 bg-white text-moss-700 dark:border-moss-400 dark:bg-night-900 dark:text-moss-300",
        !done && !current && "border-sand-300 bg-white text-sand-400 dark:border-night-700 dark:bg-night-900 dark:text-sand-500"
      )}
    >
      {done ? <CheckIcon size={16} strokeWidth={2.5} /> : index + 1}
    </span>
  );
}

export function Stepper({ steps = [], current = 0, orientation = "horizontal", className }) {
  if (orientation === "vertical") {
    return (
      <ol className={cx("flex flex-col", className)}>
        {steps.map((step, i) => {
          const done = i < current;
          const isCurrent = i === current;
          return (
            <li key={step.label} className="relative flex gap-4 pb-8 last:pb-0">
              {i < steps.length - 1 && (
                <span
                  aria-hidden="true"
                  className={cx(
                    "absolute left-4 top-10 h-[calc(100%-2.5rem)] w-0.5 rounded-full",
                    done ? "bg-moss-500" : "bg-sand-200 dark:bg-night-800"
                  )}
                />
              )}
              <Marker done={done} current={isCurrent} index={i} />
              <div className="flex flex-col pt-1.5">
                <p
                  className={cx(
                    "text-sm font-semibold",
                    isCurrent ? "text-moss-700 dark:text-moss-300" : "text-sand-800 dark:text-sand-200"
                  )}
                >
                  {step.label}
                </p>
                {step.description && <p className="mt-0.5 text-xs text-sand-500 dark:text-sand-400">{step.description}</p>}
              </div>
            </li>
          );
        })}
      </ol>
    );
  }

  return (
    <ol className={cx("flex w-full items-start", className)}>
      {steps.map((step, i) => {
        const done = i < current;
        const isCurrent = i === current;
        const isLast = i === steps.length - 1;
        return (
          <li key={step.label} className="relative flex flex-1 flex-col items-center">
            <div className="relative flex w-full items-center justify-center">
              {/* Connector line extending to the right step center */}
              {!isLast && (
                <span
                  aria-hidden="true"
                  className={cx(
                    "absolute left-1/2 top-1/2 h-0.5 w-full -translate-y-1/2 rounded-full",
                    i < current ? "bg-moss-500" : "bg-sand-200 dark:bg-night-800"
                  )}
                />
              )}
              <Marker done={done} current={isCurrent} index={i} />
            </div>
            <div className="mt-2 w-full max-w-28 px-1 text-center">
              <p
                className={cx(
                  "text-sm font-medium",
                  isCurrent ? "text-moss-700 dark:text-moss-300" : "text-sand-600 dark:text-sand-300"
                )}
              >
                {step.label}
              </p>
              {step.description && <p className="mt-0.5 text-xs text-sand-400">{step.description}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
