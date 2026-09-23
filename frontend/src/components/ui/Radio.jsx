import { createContext, useContext, useState } from "react";
import { cx } from "../../lib/cx";

const RadioGroupContext = createContext(null);

export function RadioGroup({ value, defaultValue, onChange, children, className }) {
  const [internal, setInternal] = useState(defaultValue);
  const isControlled = value !== undefined;
  const current = isControlled ? value : internal;

  const select = (v) => {
    if (!isControlled) setInternal(v);
    onChange?.(v);
  };

  return (
    <RadioGroupContext.Provider value={{ current, select }}>
      <div role="radiogroup" className={cx("flex flex-col gap-3", className)}>
        {children}
      </div>
    </RadioGroupContext.Provider>
  );
}

export function Radio({ value, label, description, disabled, className }) {
  const ctx = useContext(RadioGroupContext);
  const [local, setLocal] = useState(false);
  const checked = ctx ? ctx.current === value : local;

  const toggle = () => {
    if (disabled) return;
    if (ctx) ctx.select(value);
    else setLocal(true);
  };

  return (
    <label
      className={cx(
        "group flex select-none items-start gap-3",
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
        className
      )}
    >
      <input
        type="radio"
        checked={checked}
        onChange={toggle}
        disabled={disabled}
        className="peer sr-only"
      />
      <span
        aria-hidden="true"
        className={cx(
          "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border-2 bg-white transition-all peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-moss-600/60",
          "border-sand-300 group-hover:border-moss-400 dark:border-night-700 dark:bg-night-900",
          checked && "border-moss-600 dark:border-moss-400"
        )}
      >
        <span
          className={cx(
            "size-3 rounded-full bg-moss-600 transition-transform duration-150 dark:bg-moss-400",
            checked ? "scale-100" : "scale-0"
          )}
        />
      </span>
      <span className="flex flex-col">
        <span className="text-sm font-medium text-sand-800 dark:text-sand-200">{label}</span>
        {description && <span className="text-xs text-sand-500 dark:text-sand-400">{description}</span>}
      </span>
    </label>
  );
}
