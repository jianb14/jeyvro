import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { cx } from "../../lib/cx";
import { SearchIcon, XIcon } from "./Icons";
import { Kbd } from "./Kbd";

export function CommandPalette({ open, onClose, groups = [], placeholder = "Type a command or search..." }) {
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const listRef = useRef(null);

  const flat = useMemo(() => {
    const q = query.trim().toLowerCase();
    const out = [];
    groups.forEach((g) => {
      g.items.forEach((item) => {
        if (!q || item.label.toLowerCase().includes(q) || (g.group || "").toLowerCase().includes(q)) {
          out.push(item);
        }
      });
    });
    return out;
  }, [groups, query]);

  useEffect(() => {
    if (!open) return;
    return () => {
      // Reset on close so the next open starts fresh — avoids synchronous
      // setState inside the effect body (cascading render).
      setQuery("");
      setActiveIndex(0);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") onClose?.();
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, flat.length - 1));
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
      }
      if (e.key === "Enter") {
        const item = flat[activeIndex];
        if (item) {
          item.onSelect?.();
          onClose?.();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, flat, activeIndex, onClose]);

  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-index="${activeIndex}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  if (!open) return null;

  let running = -1;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[12vh]">
      <div
        aria-hidden="true"
        onClick={onClose}
        className="absolute inset-0 animate-fade-in bg-night-950/50 backdrop-blur-sm"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        className="relative w-full max-w-lg animate-scale-in overflow-hidden rounded-2xl border border-sand-200 bg-white shadow-pop dark:border-night-800 dark:bg-night-900"
      >
        <div className="flex items-center gap-3 border-b border-sand-200 px-4 dark:border-night-800">
          <SearchIcon size={17} className="shrink-0 text-sand-400" />
          <input
            autoFocus
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActiveIndex(0);
            }}
            placeholder={placeholder}
            className="h-12 w-full bg-transparent text-sm text-sand-900 outline-none placeholder:text-sand-400 dark:text-sand-100"
          />
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setActiveIndex(0);
              }}
              aria-label="Clear search"
              className="shrink-0 rounded-md p-1 text-sand-400 transition-colors hover:bg-sand-100 hover:text-sand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:hover:bg-night-800 dark:hover:text-sand-200"
            >
              <XIcon size={15} />
            </button>
          )}
          <Kbd>Esc</Kbd>
        </div>

        <div ref={listRef} className="max-h-80 overflow-y-auto p-2">
          {flat.length === 0 ? (
            <p className="p-6 text-center text-sm text-sand-400">No results for &quot;{query}&quot;</p>
          ) : (
            groups.map((group) => {
              const items = group.items.filter((item) => flat.includes(item));
              if (!items.length) return null;
              return (
                <div key={group.group}>
                  <p className="px-3 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-widest text-sand-400">
                    {group.group}
                  </p>
                  {items.map((item) => {
                    running += 1;
                    const idx = running;
                    return (
                      <button
                        key={item.label}
                        type="button"
                        data-index={idx}
                        onMouseEnter={() => setActiveIndex(idx)}
                        onClick={() => {
                          item.onSelect?.();
                          onClose?.();
                        }}
                        className={cx(
                          "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors",
                          idx === activeIndex
                            ? "bg-moss-100 font-medium text-moss-900 dark:bg-moss-900/60 dark:text-moss-100"
                            : "text-sand-700 dark:text-sand-300"
                        )}
                      >
                        {item.icon && <item.icon size={16} className="shrink-0 opacity-70" />}
                        <span className="flex-1 truncate">{item.label}</span>
                        {item.shortcut && (
                          <span className="shrink-0 text-[11px] tabular-nums text-sand-400">{item.shortcut}</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>

        <div className="flex items-center gap-4 border-t border-sand-200 px-4 py-2.5 text-[11px] text-sand-400 dark:border-night-800">
          <span className="flex items-center gap-1.5">
            <Kbd>↑</Kbd>
            <Kbd>↓</Kbd>
            navigate
          </span>
          <span className="flex items-center gap-1.5">
            <Kbd>↵</Kbd>
            select
          </span>
        </div>
      </div>
    </div>,
    document.body
  );
}
