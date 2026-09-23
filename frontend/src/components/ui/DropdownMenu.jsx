import { useEffect, useRef, useState } from "react";
import { cx } from "../../lib/cx";
import { ChevronsUpDownIcon } from "./Icons";

export function DropdownMenu({ trigger, align = "start", items = [], className }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={rootRef} className={cx("relative inline-block", className)}>
      <div
        onClick={() => setOpen((o) => !o)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="inline-flex cursor-pointer outline-offset-2 outline-moss-600/60 focus-visible:outline-2"
      >
        {trigger}
      </div>
      {open && (
        <div
          role="menu"
          className={cx(
            "absolute top-full z-30 mt-2 min-w-52 animate-scale-in overflow-hidden rounded-xl border border-sand-200 bg-white p-1.5 shadow-dropdown dark:border-night-700 dark:bg-night-800",
            align === "start" ? "left-0" : "right-0"
          )}
        >
          {items.map((item, i) =>
            item.divider ? (
              <div key={item.key ?? `divider-${i}`} role="separator" className="mx-2 my-1.5 h-px bg-sand-200 dark:bg-night-700" />
            ) : (
              <button
                key={item.key}
                role="menuitem"
                onClick={() => {
                  item.onSelect?.();
                  setOpen(false);
                }}
                className={cx(
                  "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  item.tone === "danger"
                    ? "text-danger-600 hover:bg-danger-50 dark:text-danger-400 dark:hover:bg-danger-950/50"
                    : "text-sand-700 hover:bg-sand-100 dark:text-sand-300 dark:hover:bg-night-700"
                )}
              >
                {item.icon && <item.icon size={15} className="shrink-0 opacity-70" />}
                <span className="flex-1 text-left">{item.label}</span>
                {item.shortcut && (
                  <span className="text-[11px] tabular-nums text-sand-400">{item.shortcut}</span>
                )}
              </button>
            )
          )}
        </div>
      )}
    </div>
  );
}

export function MenuButton({ children, className }) {
  return (
    <button
      type="button"
      className={cx(
        "inline-flex items-center gap-2 rounded-xl border border-sand-300 bg-white px-4 text-sm font-medium text-sand-800 transition-colors hover:border-moss-400 hover:bg-moss-50 dark:border-night-700 dark:bg-night-900 dark:text-sand-200 dark:hover:border-moss-600 dark:hover:bg-night-800 h-10",
        className
      )}
    >
      {children}
      <ChevronsUpDownIcon size={15} className="text-sand-400" />
    </button>
  );
}
