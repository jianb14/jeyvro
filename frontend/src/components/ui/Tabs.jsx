import { useState } from "react";
import { cx } from "../../lib/cx";

export function Tabs({ tabs = [], defaultTab, variant = "line", className, onChange }) {
  const [active, setActive] = useState(defaultTab ?? tabs[0]?.id);
  const current = active;

  const select = (id) => {
    setActive(id);
    onChange?.(id);
  };

  return (
    <div
      role="tablist"
      className={cx(
        variant === "line"
          ? "flex gap-1 border-b border-sand-200 dark:border-night-800"
          : "inline-flex gap-1 rounded-xl bg-sand-100 p-1 dark:bg-night-800",
        className
      )}
    >
      {tabs.map((tab) => {
        const isActive = current === tab.id;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => select(tab.id)}
            className={cx(
              "inline-flex items-center gap-2 text-sm font-medium transition-all outline-offset-2 outline-moss-600/60 focus-visible:outline-2",
              variant === "line"
                ? cx(
                    "-mb-px border-b-2 px-4 py-2.5",
                    isActive
                      ? "border-moss-600 text-moss-700 dark:border-moss-400 dark:text-moss-300"
                      : "border-transparent text-sand-500 hover:border-sand-300 hover:text-sand-800 dark:text-sand-400 dark:hover:text-sand-200"
                  )
                : cx(
                    "rounded-lg px-4 py-2",
                    isActive
                      ? "bg-white text-moss-700 shadow-soft dark:bg-night-900 dark:text-moss-300"
                      : "text-sand-500 hover:text-sand-800 dark:text-sand-400 dark:hover:text-sand-200"
                  )
            )}
          >
            {tab.icon && <tab.icon size={15} />}
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

export function TabPanel({ children, className }) {
  return (
    <div role="tabpanel" className={cx("animate-fade-in pt-4 text-sm text-sand-600 dark:text-sand-300", className)}>
      {children}
    </div>
  );
}
