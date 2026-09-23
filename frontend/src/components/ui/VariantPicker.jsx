import { useState } from "react";
import { cx } from "../../lib/cx";

export function VariantPicker({
  label,
  options = [],
  value,
  defaultValue,
  onChange,
  type = "pill",
  className,
}) {
  const [internal, setInternal] = useState(defaultValue);
  const current = value !== undefined ? value : internal;

  const pick = (opt) => {
    if (opt.disabled) return;
    if (value === undefined) setInternal(opt.label);
    onChange?.(opt.label);
  };

  return (
    <div className={cx("flex flex-col gap-2", className)}>
      {label && (
        <p className="text-sm text-sand-600 dark:text-sand-300">
          {label}: <span className="font-semibold text-sand-900 dark:text-sand-100">{current}</span>
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => {
          const active = current === opt.label;
          if (type === "swatch") {
            return (
              <button
                key={opt.label}
                type="button"
                title={opt.label}
                disabled={opt.disabled}
                onClick={() => pick(opt)}
                aria-label={opt.label}
                aria-pressed={active}
                className={cx(
                  "size-8 rounded-full border-2 transition-all outline-offset-2 outline-moss-600/60 focus-visible:outline-2 disabled:cursor-not-allowed disabled:opacity-40",
                  active ? "border-moss-600 dark:border-moss-400" : "border-transparent ring-1 ring-sand-300 hover:ring-moss-400 dark:ring-night-700 dark:hover:ring-moss-600"
                )}
              >
                <span
                  className="block size-full scale-[0.72] rounded-full"
                  style={{ backgroundColor: opt.color || "#84a471" }}
                />
              </button>
            );
          }
          return (
            <button
              key={opt.label}
              type="button"
              disabled={opt.disabled}
              onClick={() => pick(opt)}
              aria-pressed={active}
              className={cx(
                "inline-flex h-9 select-none items-center rounded-lg border px-3.5 text-sm font-medium transition-all outline-offset-2 outline-moss-600/60 focus-visible:outline-2 disabled:cursor-not-allowed",
                active
                  ? "border-moss-600 bg-moss-600 text-white shadow-soft dark:border-moss-500 dark:bg-moss-500"
                  : "border-sand-300 text-sand-700 hover:border-moss-400 dark:border-night-700 dark:text-sand-300 dark:hover:border-moss-600",
                opt.disabled && "border-sand-200 text-sand-300 line-through dark:border-night-800 dark:text-sand-600"
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
