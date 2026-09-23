import { cx } from "../../lib/cx";

export function Table({ className, children }) {
  return (
    <div className={cx("w-full overflow-x-auto rounded-2xl border border-sand-200 bg-white shadow-soft dark:border-night-800 dark:bg-night-900", className)}>
      <table className="w-full min-w-max border-collapse text-left text-sm">{children}</table>
    </div>
  );
}

export function THead({ children }) {
  return (
    <thead className="border-b border-sand-200 bg-sand-50/70 dark:border-night-800 dark:bg-night-800/50">
      {children}
    </thead>
  );
}

export function TH({ className, children }) {
  return (
    <th scope="col" className={cx("px-5 py-3 text-xs font-semibold uppercase tracking-wider text-sand-500 dark:text-sand-400", className)}>
      {children}
    </th>
  );
}

export function TBody({ children }) {
  return <tbody className="divide-y divide-sand-200 dark:divide-night-800">{children}</tbody>;
}

export function TR({ className, children }) {
  return <tr className={cx("transition-colors hover:bg-sand-50 dark:hover:bg-night-800/60", className)}>{children}</tr>;
}

export function TD({ className, children }) {
  return <td className={cx("px-5 py-3.5 text-sand-700 dark:text-sand-300", className)}>{children}</td>;
}
