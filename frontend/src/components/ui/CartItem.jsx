import { Link } from "react-router-dom";
import { cx } from "../../lib/cx";
import { QuantityStepper } from "./QuantityStepper";
import { Price } from "./Price";
import { ProductArt } from "./ProductArt";
import { AlertTriangleIcon, TrashIcon } from "./Icons";

/**
 * CartItem (Phase 7) — one server-truth cart line: live price and stock
 * from the cart API, line total computed server-side. Quantity edits
 * leave through the caller, which calls the cart service (every change is
 * revalidated). Warnings surface the revalidation result per line.
 */
export function CartItem({ item, onQtyChange, onRemove, busy = false, className }) {
  const unavailable = !item.purchasable;
  const maxQty = Math.max(item.stock, 1);

  return (
    <li
      className={cx(
        "flex gap-4 rounded-2xl border border-sand-200 bg-white p-4 dark:border-night-800 dark:bg-night-900",
        unavailable && "opacity-80",
        className
      )}
    >
      <Link to={`/product/${item.productSlug}`} className="shrink-0" aria-label={item.title}>
        {item.image ? (
          <img
            src={item.image}
            alt={item.title}
            loading="lazy"
            className="size-20 rounded-xl object-cover"
          />
        ) : (
          <ProductArt seed={item.seed || 0} className="size-20 rounded-xl" />
        )}
      </Link>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <Link
              to={`/product/${item.productSlug}`}
              className="line-clamp-2 text-sm font-medium text-sand-900 transition-colors hover:text-moss-700 dark:text-sand-100 dark:hover:text-moss-300"
            >
              {item.title}
            </Link>
            {item.variant && (
              <p className="mt-0.5 text-xs text-sand-500 dark:text-sand-400">{item.variant}</p>
            )}
          </div>
          <button
            type="button"
            onClick={() => onRemove?.(item.id)}
            disabled={busy}
            aria-label={`Remove ${item.title} from cart`}
            className="shrink-0 rounded-md p-1.5 text-sand-400 transition-colors hover:bg-danger-50 hover:text-danger-600 disabled:opacity-40 dark:hover:bg-danger-950/50 dark:hover:text-danger-400"
          >
            <TrashIcon size={15} />
          </button>
        </div>

        {(unavailable || item.stockLimited) && (
          <p className="flex items-center gap-1.5 text-xs text-warning-700 dark:text-warning-400">
            <AlertTriangleIcon size={13} className="shrink-0" />
            {unavailable
              ? `${item.unavailableReason || "This item is no longer available."} Remove it to continue.`
              : `Only ${item.stock} left — reduce the quantity to continue.`}
          </p>
        )}

        <div className="mt-auto flex flex-wrap items-center justify-between gap-3">
          <QuantityStepper
            value={item.qty}
            onChange={(q) => onQtyChange?.(item.id, q)}
            min={1}
            max={maxQty}
            disabled={busy || unavailable}
            size="sm"
          />
          <Price amount={item.lineTotal} size="sm" />
        </div>
      </div>
    </li>
  );
}

