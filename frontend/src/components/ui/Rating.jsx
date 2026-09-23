import { useState } from "react";
import { cx } from "../../lib/cx";
import { StarIcon } from "./Icons";

const SIZES = { sm: 15, md: 19, lg: 25 };

export function Rating({
  value,
  defaultValue = 0,
  onChange,
  max = 5,
  size = "md",
  readonly = false,
  showValue = false,
  className,
}) {
  const [internal, setInternal] = useState(defaultValue);
  const [hover, setHover] = useState(null);
  const current = value !== undefined ? value : internal;
  const shown = hover ?? current;

  const select = (v) => {
    if (readonly) return;
    if (value === undefined) setInternal(v);
    onChange?.(v);
  };

  return (
    <div
      className={cx("inline-flex items-center gap-1", className)}
      role="radiogroup"
      aria-label="Rating"
      onMouseLeave={() => setHover(null)}
    >
      {Array.from({ length: max }, (_, i) => {
        const filled = i < shown;
        return (
          <button
            key={i}
            type="button"
            disabled={readonly}
            aria-label={`${i + 1} of ${max} stars`}
            onClick={() => select(i + 1)}
            onMouseEnter={() => !readonly && setHover(i + 1)}
            className={cx(
              "transition-transform duration-100",
              readonly ? "cursor-default" : "cursor-pointer hover:scale-110 active:scale-95"
            )}
          >
            <StarIcon
              size={SIZES[size]}
              className={cx(
                "transition-colors duration-100",
                filled ? "fill-current text-warning-400" : "text-sand-300 dark:text-night-700"
              )}
            />
          </button>
        );
      })}
      {showValue && (
        <span className="ml-1.5 text-sm font-medium tabular-nums text-sand-500 dark:text-sand-400">
          {shown > 0 ? `${shown}/${max}` : `-/${max}`}
        </span>
      )}
    </div>
  );
}
