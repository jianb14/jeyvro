import { Link } from "react-router-dom";
import { cx } from "../../lib/cx";
import { ChevronRightIcon } from "./Icons";

export function Breadcrumb({ items = [], className }) {
  return (
    <nav aria-label="Breadcrumb" className={cx("flex flex-wrap items-center gap-1.5 text-sm", className)}>
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && <ChevronRightIcon size={14} className="text-sand-400" />}
            {isLast ? (
              <span aria-current="page" className="font-medium text-sand-900 dark:text-sand-100">
                {item.label}
              </span>
            ) : item.to ? (
              <Link
                to={item.to}
                className="text-sand-500 transition-colors hover:text-moss-700 dark:text-sand-400 dark:hover:text-moss-300"
              >
                {item.label}
              </Link>
            ) : (
              <a href={item.href || "#"} className="text-sand-500 transition-colors hover:text-moss-700 dark:text-sand-400 dark:hover:text-moss-300">
                {item.label}
              </a>
            )}
          </span>
        );
      })}
    </nav>
  );
}
