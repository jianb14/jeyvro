import { forwardRef, useId } from "react";
import { cx } from "../../lib/cx";
import { Label } from "./Label";
import { AlertCircleIcon, XIcon } from "./Icons";

const SIZES = {
  sm: "h-9 rounded-lg text-sm",
  md: "h-11 rounded-xl text-sm",
  lg: "h-12 rounded-xl text-base",
};

export const Input = forwardRef(function Input(
  {
    label,
    hint,
    error,
    leadingIcon: Leading,
    trailingIcon: Trailing,
    clearable = false,
    clearLabel = "Clear input",
    onClear,
    size = "md",
    className,
    id,
    value,
    onChange,
    ...props
  },
  ref
) {
  const generatedId = useId();
  const inputId = id || generatedId;
  const errorId = `${inputId}-error`;
  const hintId = `${inputId}-hint`;
  const showClear = clearable && Boolean(value);

  const handleClear = () => {
    if (onClear) {
      onClear();
      return;
    }
    // Controlled fields here wire onChange as (event) => setState(event.target.value),
    // so an event-shaped object empties the value without a synthetic DOM event.
    onChange?.({ target: { value: "" } });
  };

  return (
    <div className="flex w-full flex-col gap-1.5">
      {label && <Label htmlFor={inputId}>{label}</Label>}
      <div className="relative">
        {Leading && (
          <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-sand-400">
            <Leading size={17} />
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : hint ? hintId : undefined}
          className={cx(
            "w-full border bg-white px-3.5 text-sand-900 transition-[border-color] placeholder:text-sand-400 disabled:cursor-not-allowed disabled:bg-sand-100 disabled:opacity-70 dark:bg-night-900 dark:text-sand-100 dark:placeholder:text-sand-500 dark:disabled:bg-night-800",
            SIZES[size],
            Leading && "pl-10",
            (Trailing || showClear) && "pr-10",
            error
              ? "border-danger-400 focus:outline-2 focus:outline-offset-2 focus:outline-danger-500 dark:border-danger-800"
              : "border-sand-300 hover:border-sand-400 focus:outline-2 focus:outline-offset-2 focus:outline-moss-500 dark:border-night-700 dark:hover:border-night-600 dark:focus:outline-moss-400",
            className
          )}
          value={value}
          onChange={onChange}
          {...props}
        />
        {showClear ? (
          <button
            type="button"
            onClick={handleClear}
            aria-label={clearLabel}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-sand-400 transition-colors hover:bg-sand-100 hover:text-sand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:hover:bg-night-800 dark:hover:text-sand-200"
          >
            <XIcon size={15} />
          </button>
        ) : (
          Trailing && (
            <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-sand-400">
              <Trailing size={17} />
            </span>
          )
        )}
      </div>
      {error ? (
        <p
          id={errorId}
          className="flex items-center gap-1.5 text-xs font-medium text-danger-600 dark:text-danger-400"
        >
          <AlertCircleIcon size={14} className="shrink-0" />
          {error}
        </p>
      ) : hint ? (
        <p id={hintId} className="text-xs text-sand-500 dark:text-sand-400">
          {hint}
        </p>
      ) : null}
    </div>
  );
});
