import { cx } from "../../lib/cx";
import { Button } from "./Button";
import { TruckIcon, ShieldCheckIcon, TagIcon, PercentIcon } from "./Icons";

function formatP(n) {
  return "₱" + Number(n).toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * CartSummary (Phase 7, §16.2) — renders the totals the cart API computed:
 * subtotal, savings, item count and the promotion engine's auto-discount
 * arrive as server truth; shipping is priced by checkout (Phase 8). This
 * component adds no money math of its own (marketplace-orders rule 1) — the
 * promotion line is a label + a server number, nothing else.
 */
export function CartSummary({ totals = {}, onCheckout, checkoutDisabled = false, checkoutNote, className }) {
  const {
    itemCount = 0,
    subtotal = 0,
    savings = 0,
    promotionDiscount = 0,
    itemsTotal = subtotal,
    maxOrderUnits = null,
    overUnitCeiling = false,
  } = totals;

  return (
    <div
      className={cx(
        "flex flex-col gap-4 rounded-2xl border border-sand-200 bg-white p-5 shadow-soft dark:border-night-800 dark:bg-night-900",
        className
      )}
    >
      <p className="font-display text-lg font-semibold text-sand-900 dark:text-sand-100">Order Summary</p>

      <div className="flex flex-col gap-2.5 text-sm">
        <div className="flex justify-between text-sand-600 dark:text-sand-300">
          <span>
            Subtotal ({itemCount} {itemCount === 1 ? "item" : "items"})
          </span>
          <span className="tabular-nums">{formatP(subtotal)}</span>
        </div>
        {savings > 0 && (
          <div className="flex justify-between font-medium text-success-700 dark:text-success-400">
            <span className="flex items-center gap-1.5">
              <TagIcon size={14} /> You save
            </span>
            <span className="tabular-nums">-{formatP(savings)}</span>
          </div>
        )}
        {promotionDiscount > 0 && (
          <div className="flex justify-between font-medium text-moss-700 dark:text-moss-400">
            <span className="flex items-center gap-1.5">
              <PercentIcon size={14} /> Promotions
            </span>
            <span className="tabular-nums">-{formatP(promotionDiscount)}</span>
          </div>
        )}
        <div className="flex justify-between text-sand-600 dark:text-sand-300">
          <span className="flex items-center gap-1.5">
            <TruckIcon size={14} /> Shipping
          </span>
          <span>Calculated at checkout</span>
        </div>
      </div>

      <div className="flex items-baseline justify-between border-t border-sand-200 pt-4 dark:border-night-800">
        <span className="text-sm font-medium text-sand-600 dark:text-sand-300">Items total</span>
        <span className="font-display text-2xl font-semibold tabular-nums text-moss-700 dark:text-moss-300">
          {formatP(itemsTotal)}
        </span>
      </div>

      {checkoutNote && (
        <p className="text-xs leading-relaxed text-sand-500 dark:text-sand-400">{checkoutNote}</p>
      )}

      {overUnitCeiling && (
        <p
          role="status"
          className="rounded-xl bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
        >
          This cart has {itemCount} items. One order can hold at most {maxOrderUnits} —
          remove some items, or check out in two orders.
        </p>
      )}

      <Button size="lg" onClick={onCheckout} disabled={checkoutDisabled || overUnitCeiling}>
        Proceed to checkout
      </Button>

      <p className="flex items-center justify-center gap-1.5 text-[11px] text-sand-400">
        <ShieldCheckIcon size={13} /> Buyer protection guaranteed
      </p>
    </div>
  );
}

