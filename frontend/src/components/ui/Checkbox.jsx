import { forwardRef, useEffect, useId, useRef } from "react";
import { cx } from "../../lib/cx";
import { CheckIcon, MinusIcon } from "./Icons";

export const Checkbox = forwardRef(function Checkbox(
  { label, description, indeterminate, className, id, disabled, ...props },
  forwardedRef
) {
  const autoId = useId();
  const inputId = id || autoId;
  const innerRef = useRef(null);

  const setRefs = (el) => {
    innerRef.current = el;
    if (typeof forwardedRef === "function") forwardedRef(el);
    else if (forwardedRef) forwardedRef.current = el;
  };

  useEffect(() => {
    if (innerRef.current) innerRef.current.indeterminate = Boolean(indeterminate);
  }, [indeterminate]);

  return (
    <label
      htmlFor={inputId}
      className={cx(
        "flex select-none items-start gap-3",
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
        className
      )}
    >
      <span className="relative mt-0.5 grid size-5 shrink-0 place-items-center">
        <input
          ref={setRefs}
          id={inputId}
          type="checkbox"
          disabled={disabled}
          className="peer absolute inset-0 size-full appearance-none rounded-[7px] border border-sand-300 bg-white transition-all checked:border-moss-600 checked:bg-moss-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-600/60 hover:border-moss-400 indeterminate:border-moss-600 indeterminate:bg-moss-600 dark:border-night-700 dark:bg-night-900 dark:checked:border-moss-500 dark:checked:bg-moss-500 dark:hover:border-night-600 dark:indeterminate:border-moss-500 dark:indeterminate:bg-moss-500"
          {...props}
        />
        <CheckIcon
          size={13}
          strokeWidth={3}
          className="pointer-events-none relative z-10 col-start-1 row-start-1 text-white opacity-0 transition-opacity peer-checked:opacity-100"
        />
        <MinusIcon
          size={13}
          strokeWidth={3}
          className="pointer-events-none relative z-10 col-start-1 row-start-1 text-white opacity-0 transition-opacity peer-indeterminate:opacity-100"
        />
      </span>
      {(label || description) && (
        <span className="flex flex-col">
          <span className="text-sm font-medium text-sand-800 dark:text-sand-200">{label}</span>
          {description && <span className="text-xs text-sand-500 dark:text-sand-400">{description}</span>}
        </span>
      )}
    </label>
  );
});
