import { Badge } from "./Badge";

/**
 * Order lifecycle badge (§6 v1.7) — mirrors the server's Order/SellerOrder
 * statuses; the label always renders API state, never a guessed one.
 */
const STATUS = {
  placed: { tone: "info", label: "Placed" },
  awaiting_payment: { tone: "warning", label: "Awaiting payment" },
  paid: { tone: "success", label: "Paid" },
  shipped: { tone: "info", label: "Shipped" },
  delivered: { tone: "moss", label: "Delivered" },
  completed: { tone: "success", label: "Completed" },
  cancelled: { tone: "neutral", label: "Cancelled" },
  refunded: { tone: "danger", label: "Refunded" },
};

export function OrderStatusBadge({ status, size = "sm", className }) {
  const s = STATUS[status] || { tone: "neutral", label: status };
  return (
    <Badge tone={s.tone} variant="soft" size={size} dot className={className}>
      {s.label}
    </Badge>
  );
}
