import { Badge } from "./Badge";

/**
 * Payment lifecycle badge (§6 v1.8) — mirrors the server's Payment statuses;
 * the label always renders API state, never a guessed one.
 */
const STATUS = {
  pending: { tone: "warning", label: "Payment pending" },
  paid: { tone: "success", label: "Paid" },
  failed: { tone: "danger", label: "Payment failed" },
  expired: { tone: "neutral", label: "Payment expired" },
  cancelled: { tone: "neutral", label: "Payment cancelled" },
  partially_refunded: { tone: "info", label: "Partially refunded" },
  refunded: { tone: "danger", label: "Refunded" },
};

export function PaymentStatusBadge({ status, size = "sm", className }) {
  const s = STATUS[status] || { tone: "neutral", label: status };
  return (
    <Badge tone={s.tone} variant="soft" size={size} dot className={className}>
      {s.label}
    </Badge>
  );
}
