import { cx } from "../../lib/cx";
import { QuantityStepper } from "./QuantityStepper";
import { Price } from "./Price";
import { TrashIcon } from "./Icons";

function Thumb({ seed, className }) {
  const palettes = [
    { bg: "#e4ecdc", fg: "#84a471" },
    { bg: "#f2f0ea", fg: "#b7ad97" },
    { bg: "#e3edf4", fg: "#7aa9cd" },
    { bg: "#f5ebd6", fg: "#d0a054" },
  ];
  const p = palettes[seed % palettes.length];
  return (
    <svg viewBox="0 0 100 100" className={className} aria-hidden="true">
      <rect width="100" height="100" rx="12" fill={p.bg} />
      <rect x="32" y="30" width="36" height="40" rx="5" fill={p.fg} />
    </svg>
  );
}

export function CartItem({ item, onQtyChange, onRemove, className }) {
  return (
    <li
      className={cx(
        "flex gap-4 rounded-2xl border border-sand-200 bg-white p-4 dark:border-night-800 dark:bg-night-900",
        className
      )}
    >
      <Thumb seed={item.seed || 0} className="size-20 shrink-0 rounded-xl" />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-sand-900 dark:text-sand-100">{item.title}</p>
            {item.variant && <p className="mt-0.5 text-xs text-sand-500 dark:text-sand-400">{item.variant}</p>}
          </div>
          <button
            type="button"
            onClick={() => onRemove?.(item.id)}
            aria-label={`Remove ${item.title} from cart`}
            className="shrink-0 rounded-md p-1.5 text-sand-400 transition-colors hover:bg-danger-50 hover:text-danger-600 dark:hover:bg-danger-950/50 dark:hover:text-danger-400"
          >
            <TrashIcon size={15} />
          </button>
        </div>
        <div className="mt-auto flex flex-wrap items-center justify-between gap-3">
          <QuantityStepper
            value={item.qty}
            onChange={(q) => onQtyChange?.(item.id, q)}
            size="sm"
          />
          <Price amount={item.price * item.qty} size="sm" />
        </div>
      </div>
    </li>
  );
}
