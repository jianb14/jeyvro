import { cx } from "../../lib/cx";
import { Badge } from "./Badge";
import { PhoneIcon } from "./Icons";

export function AddressCard({ address, selected = false, onSelect, onEdit, className }) {
  const Comp = onSelect ? "button" : "div";

  return (
    <Comp
      onClick={onSelect ? () => onSelect(address.id) : undefined}
      aria-pressed={onSelect ? selected : undefined}
      className={cx(
        "flex w-full flex-col gap-1.5 rounded-2xl border p-4 text-left transition-all",
        onSelect && "cursor-pointer outline-offset-2 outline-moss-600/60 focus-visible:outline-2",
        selected
          ? "border-moss-600 bg-moss-50 ring-1 ring-moss-600 dark:border-moss-500 dark:bg-moss-950/40 dark:ring-moss-500"
          : "border-sand-300 bg-white hover:border-moss-400 dark:border-night-700 dark:bg-night-900 dark:hover:border-moss-600",
        className
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-sand-900 dark:text-sand-100">{address.name}</p>
        {address.isDefault && (
          <Badge tone="moss" variant="soft" size="sm">
            Default
          </Badge>
        )}
      </div>
      <p className="text-sm leading-relaxed text-sand-600 dark:text-sand-300">{address.line1}</p>
      <p className="text-sm text-sand-500 dark:text-sand-400">
        {address.city}, {address.province} {address.postal}
      </p>
      <p className="flex items-center gap-1.5 text-xs text-sand-500 dark:text-sand-400">
        <PhoneIcon size={12} /> {address.phone}
      </p>
      {onEdit && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onEdit(address.id);
          }}
          className="mt-1 w-fit text-xs font-medium text-moss-700 underline-offset-2 hover:underline dark:text-moss-300"
        >
          Edit address
        </button>
      )}
    </Comp>
  );
}

export function AddressList({ addresses = [], selectedId, onSelect, onEdit, className }) {
  return (
    <div className={cx("grid gap-3 sm:grid-cols-2", className)}>
      {addresses.map((a) => (
        <AddressCard
          key={a.id}
          address={a}
          selected={selectedId === a.id}
          onSelect={onSelect}
          onEdit={onEdit}
        />
      ))}
    </div>
  );
}
