import { forwardRef, useId } from "react";
import { cx } from "../../lib/cx";
import { Label } from "./Label";
import { AlertCircleIcon } from "./Icons";

const SIZES = {
  sm: "rounded-lg text-sm",
  md: "rounded-xl text-sm",
};

export const Textarea = forwardRef(function Textarea(
  { label, hint, error, size = "md", className, id, ...props },
  ref
) {
  const generatedId = useId();
  const areaId = id || generatedId;
  const errorId = `${areaId}-error`;
  const hintId = `${areaId}-hint`;
  return (
    <div className="flex w-full flex-col gap-1.5">
      {label && <Label htmlFor={areaId}>{label}</Label>}
      <textarea
        ref={ref}
        id={areaId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : hint ? hintId : undefined}
        className={cx(
          "w-full resize-y border bg-white px-3.5 py-2.5 text-sand-900 transition-[border-color] placeholder:text-sand-400 disabled:cursor-not-allowed disabled:bg-sand-100 disabled:opacity-70 dark:bg-night-900 dark:text-sand-100 dark:placeholder:text-sand-500 dark:disabled:bg-night-800",
          SIZES[size],
          error
            ? "border-danger-400 focus:outline-2 focus:outline-offset-2 focus:outline-danger-500 dark:border-danger-800"
            : "border-sand-300 hover:border-sand-400 focus:outline-2 focus:outline-offset-2 focus:outline-moss-500 dark:border-night-700 dark:hover:border-night-600 dark:focus:outline-moss-400",
          className
        )}
        {...props}
      />
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
