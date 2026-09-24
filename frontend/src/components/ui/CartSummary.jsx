import { cx } from "../../lib/cx";
import { Button } from "./Button";
import { TruckIcon, ShieldCheckIcon, TagIcon } from "./Icons";

function formatP(n) {
  return "₱" + Number(n).toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * CartSummary (Phase 7) — renders the totals the cart API computed (§6):
 * subtotal, savings, and item count arrive as server truth; shipping is
 * priced by checkout (Phase 8) and promo codes arrive with Phase 16, so
 * this component adds no money math of its own (marketplace-orders rule 1).
 */
export function CartSummary({ totals = {}, onCheckout, checkoutDisabled = false, checkoutNote, className }) {
  const { itemCount = 0, subtotal = 0, savings = 0 } = totals;

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
          {formatP(subtotal)}
        </span>
      </div>

      {checkoutNote && (
        <p className="text-xs leading-relaxed text-sand-500 dark:text-sand-400">{checkoutNote}</p>
      )}

      <Button size="lg" onClick={onCheckout} disabled={checkoutDisabled}>
        Proceed to checkout
      </Button>

      <p className="flex items-center justify-center gap-1.5 text-[11px] text-sand-400">
        <ShieldCheckIcon size={13} /> Buyer protection guaranteed
      </p>
    </div>
  );
}

