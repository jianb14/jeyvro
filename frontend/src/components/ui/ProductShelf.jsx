/**
 * ProductShelf (Phase 6) — a titled product rail for discovery pages
 * (Home sections, related products). Presentation-only: the caller owns
 * the data and its states (frontend-feature reuse-first).
 */
import { Link } from "react-router-dom";
import { cx } from "../../lib/cx";
import { Alert } from "./Alert";
import { EmptyState } from "./EmptyState";
import { ProductGrid, ProductGridSkeleton } from "./ProductCard";
import { ArrowRightIcon, InboxIcon } from "./Icons";

export function ProductShelf({
  title,
  subtitle,
  viewAllHref,
  products,
  loading = false,
  error = null,
  columns = 4,
  onAddToCart,
  emptyTitle = "Nothing here yet",
  emptyDescription,
  className,
}) {
  const list = products ?? [];
  return (
    <section className={cx("flex flex-col gap-4", className)} aria-busy={loading}>
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="font-display text-xl font-semibold tracking-tight text-sand-900 dark:text-sand-100">
            {title}
          </h2>
          {subtitle && (
            <p className="mt-0.5 text-sm text-sand-500 dark:text-sand-400">{subtitle}</p>
          )}
        </div>
        {viewAllHref && !loading && (
          <Link
            to={viewAllHref}
            className="inline-flex items-center gap-1 text-sm font-medium text-moss-700 transition-colors hover:text-moss-800 dark:text-moss-300 dark:hover:text-moss-200"
          >
            See all <ArrowRightIcon size={14} />
          </Link>
        )}
      </div>
      {loading ? (
        <ProductGridSkeleton count={columns === 4 ? 4 : 3} columns={columns} />
      ) : error ? (
        <Alert tone="danger" title={`Could not load ${title.toLowerCase()}`}>
          {error}
        </Alert>
      ) : list.length === 0 ? (
        <EmptyState
          compact
          icon={InboxIcon}
          title={emptyTitle}
          description={emptyDescription}
        />
      ) : (
        <ProductGrid products={list} onAddToCart={onAddToCart} columns={columns} />
      )}
    </section>
  );
}