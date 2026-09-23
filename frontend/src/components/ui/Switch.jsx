import { useState } from "react";
import { cx } from "../../lib/cx";

const TRACK = {
  sm: "h-5 w-9",
  md: "h-6 w-11",
};

const KNOB = {
  sm: "size-3.5",
  md: "size-[18px]",
};

const SHIFT = {
  sm: { off: "translate-x-[3px]", on: "translate-x-[20px]" },
  md: { off: "translate-x-[3px]", on: "translate-x-[23px]" },
};

export function Switch({
  checked,
  defaultChecked = false,
  onChange,
  label,
  description,
  size = "md",
  disabled,
  className,
}) {
  const [internal, setInternal] = useState(Boolean(defaultChecked));
  const isOn = checked !== undefined ? checked : internal;

  const toggle = () => {
    if (disabled) return;
    if (checked === undefined) setInternal(!isOn);
    onChange?.(!isOn);
  };

  return (
    <label
      className={cx(
        "flex select-none items-center gap-3",
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
        className
      )}
    >
      <button
        type="button"
        role="switch"
        aria-checked={isOn}
        disabled={disabled}
        onClick={toggle}
        className={cx(
          "relative inline-flex shrink-0 items-center rounded-full transition-colors duration-200 outline-offset-2 outline-moss-600/60 focus-visible:outline-2",
          TRACK[size],
          isOn ? "bg-moss-600" : "bg-sand-300 dark:bg-night-700"
        )}
      >
        <span
          className={cx(
            "inline-block transform rounded-full bg-white shadow transition-transform duration-200",
            KNOB[size],
            isOn ? SHIFT[size].on : SHIFT[size].off
          )}
        />
      </button>
      {(label || description) && (
        <span className="flex flex-col">
          <span className="text-sm font-medium text-sand-800 dark:text-sand-200">{label}</span>
          {description && <span className="text-xs text-sand-500 dark:text-sand-400">{description}</span>}
        </span>
      )}
    </label>
  );
}
