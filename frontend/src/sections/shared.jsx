import { cx } from "../lib/cx";

export function Section({ id, title, description, children }) {
  return (
    <section id={id} className="scroll-mt-24 border-t border-sand-200 py-12 first:border-t-0 first:pt-0 dark:border-night-800">
      <div className="mb-8 max-w-2xl">
        <h2 className="font-display text-2xl font-semibold tracking-tight text-sand-900 dark:text-sand-100">{title}</h2>
        {description && <p className="mt-2 text-sm leading-relaxed text-sand-500 dark:text-sand-400">{description}</p>}
      </div>
      <div className="flex flex-col gap-8">{children}</div>
    </section>
  );
}

export function Demo({ label, align = "left", className, children }) {
  return (
    <div>
      {label && (
        <p className="mb-2.5 text-[11px] font-semibold uppercase tracking-widest text-sand-400">{label}</p>
      )}
      <div
        className={cx(
          "flex flex-wrap items-center gap-4 rounded-xl border border-dashed border-sand-300 bg-white/60 p-5 dark:border-night-700 dark:bg-night-900/40",
          align === "center" && "justify-center",
          align === "column" && "flex-col items-stretch",
          className
        )}
      >
        {children}
      </div>
    </div>
  );
}
