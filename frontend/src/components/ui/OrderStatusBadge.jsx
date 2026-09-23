import { Badge } from "./Badge";

const STATUS = {
  "to-pay": { tone: "warning", label: "To Pay" },
  "to-ship": { tone: "info", label: "To Ship" },
  "to-receive": { tone: "moss", label: "To Receive" },
  completed: { tone: "success", label: "Completed" },
  cancelled: { tone: "neutral", label: "Cancelled" },
  refunded: { tone: "danger", label: "Refunded" },
};

export function OrderStatusBadge({ status, size = "sm", className }) {
  const s = STATUS[status] || STATUS["to-pay"];
  return (
    <Badge tone={s.tone} variant="soft" size={size} dot className={className}>
      {s.label}
    </Badge>
  );
}
