import { useState } from "react";
import { cx } from "../../lib/cx";
import { ChevronDownIcon } from "./Icons";

export function Accordion({ items = [], allowMultiple = false, className }) {
  const [open, setOpen] = useState(() => new Set());

  const toggle = (id) => {
    setOpen((prev) => {
      const next = new Set(allowMultiple ? prev : []);
      if (prev.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className={cx("divide-y divide-sand-200 overflow-hidden rounded-2xl border border-sand-200 bg-white dark:divide-night-800 dark:border-night-800 dark:bg-night-900", className)}>
      {items.map((item) => {
        const isOpen = open.has(item.id);
        return (
          <div key={item.id}>
            <button
              onClick={() => toggle(item.id)}
              aria-expanded={isOpen}
              className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left text-sm font-medium text-sand-800 transition-colors hover:bg-sand-50 dark:text-sand-200 dark:hover:bg-night-800/60"
            >
              {item.title}
              <ChevronDownIcon
                size={16}
                className={cx("shrink-0 text-sand-400 transition-transform duration-200", isOpen && "rotate-180")}
              />
            </button>
            {isOpen && (
              <div className="animate-fade-in px-5 pb-5 text-sm leading-relaxed text-sand-600 dark:text-sand-400">
                {item.content}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
