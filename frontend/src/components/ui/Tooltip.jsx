import { cx } from "../../lib/cx";

const POSITIONS = {
  top: "bottom-full left-1/2 mb-2.5 -translate-x-1/2",
  bottom: "top-full left-1/2 mt-2.5 -translate-x-1/2",
  left: "right-full top-1/2 mr-2.5 -translate-y-1/2",
  right: "left-full top-1/2 ml-2.5 -translate-y-1/2",
};

const ARROWS = {
  top: "top-full left-1/2 -translate-x-1/2 -mt-1",
  bottom: "bottom-full left-1/2 -translate-x-1/2 -mb-1",
  left: "left-full top-1/2 -translate-y-1/2 -ml-1",
  right: "right-full top-1/2 -translate-y-1/2 -mr-1",
};

export function Tooltip({ content, placement = "top", className, children }) {
  return (
    <span className={cx("group/tt relative inline-flex", className)}>
      {children}
      <span
        role="tooltip"
        className={cx(
          "pointer-events-none absolute z-40 w-max max-w-56 whitespace-nowrap rounded-lg bg-night-900 px-2.5 py-1.5 text-xs font-medium text-sand-100 opacity-0 shadow-lift transition-all duration-150 group-hover/tt:opacity-100 dark:bg-sand-100 dark:text-night-900",
          POSITIONS[placement]
        )}
      >
        {content}
        <span className={cx("absolute size-2 rotate-45 bg-night-900 dark:bg-sand-100", ARROWS[placement])} />
      </span>
    </span>
  );
}
