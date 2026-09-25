import { Children, forwardRef, useEffect, useId, useRef, useState } from "react";
import { cx } from "../../lib/cx";
import { Label } from "./Label";
import { ChevronDownIcon, AlertCircleIcon } from "./Icons";

const SIZES = {
  sm: "h-9 rounded-lg text-sm",
  md: "h-11 rounded-xl text-sm",
  lg: "h-12 rounded-xl text-base",
};

export const Select = forwardRef(function Select(
  {
    label,
    hint,
    error,
    size = "md",
    className,
    id,
    disabled,
    children,
    value: valueProp,
    defaultValue,
    onChange,
    ...props
  },
  ref
) {
  const generatedId = useId();
  const selectId = id || generatedId;
  const errorId = `${selectId}-error`;
  const hintId = `${selectId}-hint`;
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const listRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [internalValue, setInternalValue] = useState(defaultValue ?? "");

  const isControlled = valueProp !== undefined;
  const value = isControlled ? valueProp : internalValue;

  const options = Children.toArray(children)
    .filter((child) => typeof child.type === "string" && child.type === "option")
    .map((child) => ({
      value: child.props.value ?? child.props.children ?? "",
      label: child.props.children,
      disabled: Boolean(child.props.disabled),
    }));

  const placeholder = options.find((o) => o.disabled);
  const selected = options.find((o) => !o.disabled && o.value === value);
  const displayText = selected ? selected.label : placeholder ? placeholder.label : "Select…";

  const setTriggerRef = (node) => {
    triggerRef.current = node;
    if (typeof ref === "function") ref(node);
    else if (ref) ref.current = node;
  };

  const commit = (option) => {
    if (!isControlled) setInternalValue(option.value);
    onChange?.({ target: { name: props.name, value: option.value } });
  };

  const openDropdown = () => {
    if (disabled) return;
    const current = options.findIndex((o) => !o.disabled && o.value === value);
    setActiveIndex(current >= 0 ? current : options.findIndex((o) => !o.disabled));
    setOpen(true);
  };

  const selectOption = (option) => {
    if (option.disabled) return;
    commit(option);
    setOpen(false);
    triggerRef.current?.focus();
  };

  const onTriggerKeyDown = (e) => {
    if (disabled) return;
    if (!open) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) {
        e.preventDefault();
        openDropdown();
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(options.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(0, i - 1));
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (activeIndex >= 0) selectOption(options[activeIndex]);
    } else if (e.key === "Tab") {
      setOpen(false);
    }
  };

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false);
    };
    const onKeyDown = (e) => {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  useEffect(() => {
    if (!open || activeIndex < 0 || !listRef.current) return;
    listRef.current.children[activeIndex]?.scrollIntoView({ block: "nearest" });
  }, [open, activeIndex]);
  return (
    <div ref={rootRef} className={cx("relative flex w-full flex-col gap-1.5", className)}>
      {label && <Label htmlFor={selectId}>{label}</Label>}
      <div className="relative">
        <button
          ref={setTriggerRef}
          type="button"
          id={selectId}
          disabled={disabled}
          role="combobox"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-controls={`${selectId}-listbox`}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : hint ? hintId : undefined}
          onClick={() => (open ? setOpen(false) : openDropdown())}
          onKeyDown={onTriggerKeyDown}
          className={cx(
            "flex w-full items-center border bg-white pl-3.5 pr-9 text-left transition-[border-color] disabled:cursor-not-allowed disabled:bg-sand-100 disabled:opacity-70 dark:bg-night-900 dark:text-sand-100 dark:disabled:bg-night-800",
            SIZES[size],
            error
              ? "border-danger-400 focus:border-danger-500 dark:border-danger-800"
              : "border-sand-300 hover:border-sand-400 focus:border-moss-500 dark:border-night-700 dark:hover:border-night-600 dark:focus:border-moss-400"
          )}
          {...props}
        >
          <span className={cx("truncate", !selected && "text-sand-400 dark:text-sand-500")}>{displayText}</span>
        </button>
        <ChevronDownIcon
          size={16}
          className={cx(
            "pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sand-400 transition-transform",
            open && "rotate-180"
          )}
        />
        {open && (
          <ul
            ref={listRef}
            role="listbox"
            id={`${selectId}-listbox`}
            className="absolute top-full z-50 mt-1.5 max-h-60 w-full overflow-y-auto rounded-xl border border-sand-200 bg-white p-1 shadow-dropdown dark:border-night-800 dark:bg-night-900"
          >
            {options.map((option, i) => {
              const isSelected = !option.disabled && option.value === value;
              const isActive = i === activeIndex;
              return (
                <li
                  key={`${option.value}-${i}`}
                  role="option"
                  aria-selected={isSelected}
                  aria-disabled={option.disabled || undefined}
                  onClick={() => selectOption(option)}
                  onMouseEnter={() => {
                    if (!option.disabled) setActiveIndex(i);
                    }}
                  className={cx(
                    "cursor-pointer rounded-lg px-3 py-2 text-sm",
                    option.disabled && "cursor-default text-sand-400 dark:text-sand-500",
                    !option.disabled && isSelected && "bg-moss-50 font-medium text-moss-700 dark:bg-night-800 dark:text-moss-300",
                    !option.disabled && !isSelected && isActive && "bg-sand-100 text-sand-900 dark:bg-night-800 dark:text-sand-100",
                    !option.disabled && !isSelected && !isActive && "text-sand-700 dark:text-sand-300"
                  )}
                >
                  {option.label}
                </li>
              );
            })}
          </ul>
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
