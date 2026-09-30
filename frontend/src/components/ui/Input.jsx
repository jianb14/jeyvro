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
    // An interactive node for the right-hand gutter — the password reveal
    // button. It is a prop rather than something callers position themselves
    // because only Input knows where that gutter is: the same `pr-10` that
    // keeps text clear of `Trailing` has to clear this too, and a caller
    // absolutely positioning a button over the field would have to re-derive
    // the offsets and would break the moment the input size changed.
    trailingAction,
    // A control rendered on the right of the label row — "Forgot password?".
    // The alternative, a right-aligned button on its own line under the field,
    // is what this replaced: it cost a whole row of vertical space and read as
    // loose debris, because a link that acts on *this* field sitting below
    // *that* field looks like it belongs to whatever comes next. The label is
    // the field's own header, so a recovery link belongs on it.
    labelAction,
    onClear,
    size = "md",
    className,
    id,
    ...props
  },
  ref
) {
  const generatedId = useId();
  const inputId = id || generatedId;
  const errorId = `${inputId}-error`;
  const hintId = `${inputId}-hint`;
  // Only offer the affordance when there is something to clear — an always-on
  // X on an empty box is noise. Derived during render, never from an effect.
  const showClear = Boolean(onClear) && String(props.value ?? "").length > 0;
  return (
    <div className="flex w-full flex-col gap-1.5">
      {label && (
        // The row exists only when there is something to put on the right. A
        // lone label in a `justify-between` flex is harmless, but rendering the
        // wrapper conditionally keeps the DOM identical to the common case
        // instead of adding a flex container to every input on the site.
        labelAction ? (
          <div className="flex items-baseline justify-between gap-3">
            <Label htmlFor={inputId}>{label}</Label>
            {labelAction}
          </div>
        ) : (
          <Label htmlFor={inputId}>{label}</Label>
        )
      )}
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
            // The trailing button sits in the same right-hand gutter as the
            // clear "X", so only one of the three may claim the padding.
            (Trailing || showClear || trailingAction) && "pr-10",
            error
              ? "border-danger-400 focus:outline-2 focus:outline-offset-2 focus:outline-danger-500 dark:border-danger-800"
              : "border-sand-300 hover:border-sand-400 focus:outline-2 focus:outline-offset-2 focus:outline-moss-500 dark:border-night-700 dark:hover:border-night-600 dark:focus:outline-moss-400",
            className
          )}
          {...props}
        />
        {Trailing && (
          <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-sand-400">
            <Trailing size={17} />
          </span>
        )}
        {/* The interactive counterpart to `Trailing`. Positioned one notch
            further in than the static icon (right-2.5, not right-3.5) because a
            button needs a real hit target around its glyph, not just optical
            alignment with the leading icon. It is not wrapped in a span: the
            caller owns the button's own classes and its focus ring, and an
            extra wrapper here would fight both. */}
        {trailingAction}
        {showClear && (
          // type="button" keeps it from submitting the surrounding <form> —
          // every search field on the seller and staff consoles lives in one.
          <button
            type="button"
            onClick={onClear}
            aria-label="Clear search"
            className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-sand-400 transition-colors hover:bg-sand-100 hover:text-sand-700 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-moss-500 dark:hover:bg-night-800 dark:hover:text-sand-100 dark:focus-visible:outline-moss-400"
          >
            <XIcon size={15} />
          </button>
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
