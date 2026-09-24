import { useState } from "react";
import { cx } from "../../lib/cx";
import { ChevronLeftIcon, ChevronRightIcon, MoreHorizontalIcon } from "./Icons";

function pageList(total, current, siblingCount) {
  const pages = [];
  const start = Math.max(2, current - siblingCount);
  const end = Math.min(total - 1, current + siblingCount);

  pages.push(1);
  if (start > 2) pages.push("ellipsis-start");
  for (let p = start; p <= end; p++) pages.push(p);
  if (end < total - 1) pages.push("ellipsis-end");
  if (total > 1) pages.push(total);
  return pages;
}

function PageButton({ page, active, onClick, disabled, className }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-current={active ? "page" : undefined}
      aria-label={typeof page === "number" ? `Page ${page}` : undefined}
      className={cx(
        "inline-flex size-9 items-center justify-center rounded-lg text-sm font-medium transition-all outline-offset-2 outline-moss-600/60 focus-visible:outline-2 disabled:pointer-events-none disabled:opacity-40",
        active
          ? "bg-moss-600 text-white shadow-soft"
          : "text-sand-600 hover:bg-sand-100 hover:text-sand-900 dark:text-sand-300 dark:hover:bg-night-800 dark:hover:text-sand-100",
        className
      )}
    >
      {page}
    </button>
  );
}

export function Pagination({ total = 10, initial = 1, current: currentProp, siblingCount = 1, className, onChange }) {
  const [internal, setInternal] = useState(Math.min(initial, total));

  // Controlled like the other primitives (Rating/VariantPicker): pass
  // `current` + `onChange` to drive it from the URL (frontend-state rule
  // 6); leave `current` undefined for self-managed state.
  const isControlled = currentProp !== undefined;
  const current = Math.min(Math.max(isControlled ? currentProp : internal, 1), Math.max(total, 1));

  const go = (page) => {
    if (page < 1 || page > total || page === current) return;
    if (!isControlled) setInternal(page);
    onChange?.(page);
  };

  return (
    <nav aria-label="Pagination" className={cx("flex flex-wrap items-center gap-1.5", className)}>
      <PageButton
        page={<ChevronLeftIcon size={16} />}
        onClick={() => go(current - 1)}
        disabled={current === 1}
        className="size-9"
      />
      {pageList(total, current, siblingCount).map((p) =>
        typeof p === "number" ? (
          <PageButton key={p} page={p} active={p === current} onClick={() => go(p)} />
        ) : (
          <span key={p} className="inline-flex size-9 items-center justify-center text-sand-400">
            <MoreHorizontalIcon size={16} />
          </span>
        )
      )}
      <PageButton
        page={<ChevronRightIcon size={16} />}
        onClick={() => go(current + 1)}
        disabled={current === total}
      />
    </nav>
  );
}
