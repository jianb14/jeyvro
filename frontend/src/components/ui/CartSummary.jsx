import { useState } from "react";
import { cx } from "../../lib/cx";
import { Button } from "./Button";
import { TagIcon, TruckIcon, ShieldCheckIcon } from "./Icons";

function formatP(n) {
  return "₱" + n.toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function CartSummary({ subtotal = 0, shipping = 60, discount = 0, fee = 0, onCheckout, className }) {
  const [promo, setPromo] = useState("");
  const [applied, setApplied] = useState(null);

  const applyPromo = () => {
    if (!promo.trim()) return;
    setApplied({ code: promo.trim().toUpperCase(), amount: Math.round(subtotal * 0.1) });
  };

  const promoAmount = applied ? applied.amount : 0;
  const total = Math.max(0, subtotal + shipping + fee - discount - promoAmount);

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
          <span>Subtotal</span>
          <span className="tabular-nums">{formatP(subtotal)}</span>
        </div>
        <div className="flex justify-between text-sand-600 dark:text-sand-300">
          <span className="flex items-center gap-1.5">
            <TruckIcon size={14} /> Shipping
          </span>
          <span className="tabular-nums">{shipping === 0 ? "Free" : formatP(shipping)}</span>
        </div>
        {fee > 0 && (
          <div className="flex justify-between text-sand-600 dark:text-sand-300">
            <span>Service fee</span>
            <span className="tabular-nums">{formatP(fee)}</span>
          </div>
        )}
        {discount > 0 && (
          <div className="flex justify-between font-medium text-success-700 dark:text-success-400">
            <span className="flex items-center gap-1.5">
              <TagIcon size={14} /> Discount
            </span>
            <span className="tabular-nums">-{formatP(discount)}</span>
          </div>
        )}
        {applied && (
          <div className="flex justify-between font-medium text-success-700 dark:text-success-400">
            <span className="flex items-center gap-1.5">
              <TagIcon size={14} /> {applied.code}
            </span>
            <span className="tabular-nums">-{formatP(promoAmount)}</span>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-2 border-t border-dashed border-sand-300 pt-3 dark:border-night-700">
        <div className="flex gap-2">
          <input
            value={promo}
            onChange={(e) => setPromo(e.target.value)}
            placeholder="Promo code (try JEYVRO10)"
            className="h-9 flex-1 rounded-lg border border-sand-300 bg-white px-3 text-sm transition-[border-color] placeholder:text-sand-400 focus:outline-2 focus:outline-offset-2 focus:outline-moss-500 dark:border-night-700 dark:bg-night-900 dark:text-sand-100 dark:focus:outline-moss-400"
          />
          <Button size="sm" variant="secondary" onClick={applyPromo}>
            Apply
          </Button>
        </div>
      </div>

      <div className="flex items-baseline justify-between border-t border-sand-200 pt-4 dark:border-night-800">
        <span className="text-sm font-medium text-sand-600 dark:text-sand-300">Total</span>
        <span className="font-display text-2xl font-semibold tabular-nums text-moss-700 dark:text-moss-300">
          {formatP(total)}
        </span>
      </div>

      <Button size="lg" onClick={onCheckout}>
        Proceed to checkout
      </Button>

      <p className="flex items-center justify-center gap-1.5 text-[11px] text-sand-400">
        <ShieldCheckIcon size={13} /> Buyer protection guaranteed
      </p>
    </div>
  );
}
