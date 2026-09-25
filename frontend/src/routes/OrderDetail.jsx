/**
 * Order detail (Phase 8; payments Phase 9; account tools Phase 11).
 *
 * Every value comes from the order API (snapshots never re-read the
 * catalog); cancelling releases the stock reservation server-side, and the
 * payment card renders the server's payment state (§6 v1.8) — never a
 * client-side guess. Phase 11 adds the lifecycle timeline, parcel
 * tracking, the receipt link, reorder, and request intake.
 */
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { Navbar } from "../components/layout/Navbar";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Breadcrumb } from "../components/ui/Breadcrumb";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";
import { OrderStatusBadge } from "../components/ui/OrderStatusBadge";
import { PaymentStatusBadge } from "../components/ui/PaymentStatusBadge";
import { Price } from "../components/ui/Price";
import { Select } from "../components/ui/Select";
import { Skeleton } from "../components/ui/Skeleton";
import { Textarea } from "../components/ui/Textarea";
import { Timeline } from "../components/ui/Timeline";
import { useToast } from "../components/ui/ToastProvider";
import * as ordersApi from "../data/orders";

/**
 * Request intake options (Phase 11.3). Eligibility is the server's call —
 * these are only the choices offered; the API may still refuse and the
 * server's message is what the customer sees.
 */
const REQUEST_KINDS = [
  { id: "return", label: "Request a return" },
  { id: "refund", label: "Request a refund" },
  { id: "issue", label: "Report an issue" },
];

const REQUEST_REASONS = {
  return: [
    "Changed my mind",
    "Item not as described",
    "Item arrived damaged",
    "Wrong item received",
    "Other",
  ],
  refund: [
    "Order cancelled after payment",
    "Item not as described",
    "Item arrived damaged",
    "Duplicate payment",
    "Other",
  ],
  issue: [
    "Delivery is late",
    "Item missing from the parcel",
    "Parcel arrived damaged",
    "Delivery problem",
    "Other",
  ],
};

const REQUEST_STATUS = {
  pending: { tone: "warning", label: "Pending review" },
  withdrawn: { tone: "neutral", label: "Withdrawn" },
};

const SHIPMENT_STATUS = {
  pending: { tone: "neutral", label: "Pending" },
  packed: { tone: "info", label: "Packed" },
  picked_up: { tone: "info", label: "Picked up" },
  in_transit: { tone: "info", label: "In transit" },
  out_for_delivery: { tone: "warning", label: "Out for delivery" },
  delivered: { tone: "success", label: "Delivered" },
  failed: { tone: "danger", label: "Delivery failed" },
  cancelled: { tone: "neutral", label: "Cancelled" },
};

function formatDateTime(value) {
  return new Date(value).toLocaleString("en-PH", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function OrderDetail() {
  const { number } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { push } = useToast();
  const [order, setOrder] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reordering, setReordering] = useState(false);
  const [requestOpen, setRequestOpen] = useState(false);
  const [requestBusy, setRequestBusy] = useState(false);
  const [requestError, setRequestError] = useState(null);
  const [withdrawingId, setWithdrawingId] = useState(null);
  const [requestForm, setRequestForm] = useState({
    kind: "return",
    reason: REQUEST_REASONS.return[0],
    description: "",
    sellerOrderId: "",
  });

  useEffect(() => {
    let cancelled = false;
    ordersApi
      .fetchOrder(number)
      .then((data) => {
        if (!cancelled) setOrder(data);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err.data?.detail || err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [number]);

  async function cancelOrder() {
    setConfirmCancel(false);
    setBusy(true);
    try {
      const updated = await ordersApi.cancelOrder(number);
      setOrder(updated);
      push({ tone: "success", title: "Order cancelled" });
    } catch (err) {
      push({
        tone: "danger",
        title: "Could not cancel the order",
        description: err.data?.detail || err.message,
      });
    } finally {
      setBusy(false);
    }
  }

  async function reorder() {
    setReordering(true);
    try {
      const result = await ordersApi.reorderOrder(number);
      if (result.added.length === 0) {
        push({
          tone: "warning",
          title: "Nothing could be re-added",
          description: result.skipped[0]?.reason,
        });
      } else {
        push({
          tone: "success",
          title: `${result.added.length} ${
            result.added.length === 1 ? "item" : "items"
          } added to your cart`,
          description: result.skipped.length
            ? `${result.skipped.length} skipped — ${result.skipped[0].reason}`
            : undefined,
        });
        navigate("/cart");
      }
    } catch (err) {
      push({
        tone: "danger",
        title: "Could not reorder",
        description: err.data?.detail || err.message,
      });
    } finally {
      setReordering(false);
    }
  }

  function openRequest(kind) {
    const stores = order?.sellerOrders ?? [];
    setRequestError(null);
    setRequestForm({
      kind,
      reason: REQUEST_REASONS[kind][0],
      description: "",
      sellerOrderId: stores.length === 1 ? String(stores[0].id) : "",
    });
    setRequestOpen(true);
  }

  async function submitRequest(event) {
    event.preventDefault();
    setRequestBusy(true);
    setRequestError(null);
    try {
      const created = await ordersApi.createOrderRequest(number, {
        kind: requestForm.kind,
        reason: requestForm.reason,
        description: requestForm.description,
        sellerOrderId: requestForm.sellerOrderId
          ? Number(requestForm.sellerOrderId)
          : null,
      });
      setOrder((current) => ({
        ...current,
        requests: [created, ...current.requests],
      }));
      setRequestOpen(false);
      push({
        tone: "success",
        title: "Request submitted",
        description: "We'll keep you posted on its status.",
      });
    } catch (err) {
      setRequestError(err.data?.detail || err.message);
    } finally {
      setRequestBusy(false);
    }
  }

  async function withdrawRequest(requestId) {
    setWithdrawingId(requestId);
    try {
      const updated = await ordersApi.withdrawOrderRequest(number, requestId);
      setOrder((current) => ({
        ...current,
        requests: current.requests.map((request) =>
          request.id === requestId ? updated : request
        ),
      }));
      push({ tone: "success", title: "Request withdrawn" });
    } catch (err) {
      push({
        tone: "danger",
        title: "Could not withdraw the request",
        description: err.data?.detail || err.message,
      });
    } finally {
      setWithdrawingId(null);
    }
  }

  const justPlaced = Boolean(location.state?.justPlaced);
  const cancellable = Boolean(order?.canCancel);
  const placedLabel = order
    ? new Date(order.placedAt).toLocaleString("en-PH", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "";

  return (
    <div className="min-h-dvh bg-sand-50 dark:bg-night-950">
      <Navbar />

      <main className="mx-auto max-w-4xl px-4 pb-24 pt-6 sm:px-6 lg:px-8">
        <Breadcrumb
          className="mb-6"
          items={[{ label: "Home", to: "/" }, { label: "Order" }]}
        />

        {loadError && (
          <Alert tone="danger" title="Could not load the order" className="mb-6">
            {loadError}
          </Alert>
        )}

        {!order && !loadError ? (
          <div className="flex flex-col gap-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        ) : order ? (
          <div className="flex flex-col gap-6">
            {justPlaced && (
              <Alert tone="success" title="Order placed">
                Your order was recorded and stock is reserved. Keep your order
                number for follow-ups.
              </Alert>
            )}

            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-sand-200 bg-white p-5 dark:border-night-800 dark:bg-night-900">
              <div className="flex flex-col gap-1">
                <span className="text-xs uppercase tracking-wide text-sand-500 dark:text-sand-400">
                  Order
                </span>
                <span className="font-display text-xl font-semibold text-sand-900 dark:text-sand-100">
                  {order.number}
                </span>
                <span className="text-xs text-sand-500 dark:text-sand-400">
                  Placed {placedLabel}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <OrderStatusBadge status={order.status} />
                {cancellable && (
                  <Button
                    variant="outline"
                    size="sm"
                    loading={busy}
                    onClick={() => setConfirmCancel(true)}
                  >
                    Cancel order
                  </Button>
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Link to={`/orders/${order.number}/receipt`}>
                <Button variant="outline" size="sm">
                  Receipt
                </Button>
              </Link>
              <Button
                variant="outline"
                size="sm"
                loading={reordering}
                onClick={reorder}
              >
                Buy again
              </Button>
              <Button variant="ghost" size="sm" onClick={() => openRequest("return")}>
                Request a return
              </Button>
              <Button variant="ghost" size="sm" onClick={() => openRequest("refund")}>
                Request a refund
              </Button>
              <Button variant="ghost" size="sm" onClick={() => openRequest("issue")}>
                Report an issue
              </Button>
            </div>

            {order.sellerOrders.map((so) => (
              <div
                key={so.id}
                className="rounded-2xl border border-sand-200 bg-white p-5 dark:border-night-800 dark:bg-night-900"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <Link
                    to={`/store/${so.storeSlug}`}
                    className="text-sm font-semibold text-sand-900 transition-colors hover:text-moss-700 dark:text-sand-100 dark:hover:text-moss-300"
                  >
                    {so.storeName}
                  </Link>
                  <OrderStatusBadge status={so.status} />
                </div>
                <ul className="mt-4 flex flex-col gap-3">
                  {so.items.map((item) => (
                    <li
                      key={item.id}
                      className="flex items-start justify-between gap-4"
                    >
                      <div className="flex min-w-0 flex-col">
                        <Link
                          to={`/product/${item.productSlug}`}
                          className="truncate text-sm text-sand-800 transition-colors hover:text-moss-700 dark:text-sand-200 dark:hover:text-moss-300"
                        >
                          {item.title}
                        </Link>
                        <span className="text-xs text-sand-500 dark:text-sand-400">
                          {item.variant || item.sku} · ×{item.qty}
                        </span>
                      </div>
                      <Price amount={item.lineTotal} size="sm" />
                    </li>
                  ))}
                </ul>
                <div className="mt-4 flex flex-col gap-1.5 border-t border-sand-200 pt-3 text-sm dark:border-night-800">
                  <div className="flex items-center justify-between text-sand-600 dark:text-sand-300">
                    <span>Store subtotal</span>
                    <Price amount={so.subtotal} size="sm" />
                  </div>
                  <div className="flex items-center justify-between text-sand-600 dark:text-sand-300">
                    <span>Shipping</span>
                    {so.shippingFee > 0 ? (
                      <Price amount={so.shippingFee} size="sm" />
                    ) : (
                      <span className="text-sm font-medium text-success-700 dark:text-success-400">
                        Free
                      </span>
                    )}
                  </div>
                </div>

                {so.shipments.length > 0 && (
                  <div className="mt-4 flex flex-col gap-3 border-t border-sand-200 pt-3 dark:border-night-800">
                    {so.shipments.map((shipment) => {
                      const meta = SHIPMENT_STATUS[shipment.status] ?? {
                        tone: "neutral",
                        label: shipment.status,
                      };
                      return (
                        <div
                          key={shipment.id}
                          className="rounded-xl bg-sand-50 p-3 dark:bg-night-950"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="text-sm font-medium text-sand-900 dark:text-sand-100">
                              {shipment.carrierName}
                            </span>
                            <Badge tone={meta.tone} variant="soft" size="sm">
                              {meta.label}
                            </Badge>
                          </div>
                          <p className="mt-1 font-mono text-xs text-sand-500 dark:text-sand-400">
                            {shipment.trackingNumber}
                          </p>
                          {shipment.deliveredAt ? (
                            <p className="mt-1 text-xs text-sand-500 dark:text-sand-400">
                              Delivered {formatDateTime(shipment.deliveredAt)}
                            </p>
                          ) : shipment.estimatedDelivery ? (
                            <p className="mt-1 text-xs text-sand-500 dark:text-sand-400">
                              Estimated delivery{" "}
                              {new Date(shipment.estimatedDelivery).toLocaleDateString(
                                "en-PH",
                                { dateStyle: "medium" }
                              )}
                            </p>
                          ) : null}
                          {shipment.events.length > 0 && (
                            <ul className="mt-3 flex flex-col gap-2">
                              {shipment.events.map((event) => (
                                <li key={event.id} className="flex flex-col">
                                  <span className="text-xs font-medium text-sand-700 dark:text-sand-300">
                                    {event.description}
                                  </span>
                                  <span className="text-[11px] text-sand-400">
                                    {formatDateTime(event.occurredAt)}
                                    {event.location ? ` · ${event.location}` : ""}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-sand-200 bg-white p-5 dark:border-night-800 dark:bg-night-900">
                <p className="text-sm font-semibold text-sand-900 dark:text-sand-100">
                  Ship to
                </p>
                <p className="mt-2 text-sm text-sand-700 dark:text-sand-300">
                  {order.address.fullName} · {order.address.phone}
                </p>
                <p className="text-sm text-sand-500 dark:text-sand-400">
                  {[order.address.line1, order.address.line2]
                    .filter(Boolean)
                    .join(", ")}
                  , {order.address.city}, {order.address.province}{" "}
                  {order.address.postalCode}
                </p>
              </div>
              <div className="rounded-2xl border border-sand-200 bg-white p-5 dark:border-night-800 dark:bg-night-900">
                <p className="text-sm font-semibold text-sand-900 dark:text-sand-100">
                  Totals
                </p>
                <div className="mt-2 flex flex-col gap-1.5 text-sm">
                  <div className="flex items-center justify-between text-sand-600 dark:text-sand-300">
                    <span>Subtotal</span>
                    <Price amount={order.totals.subtotal} size="sm" />
                  </div>
                  {order.totals.savings > 0 && (
                    <div className="flex items-center justify-between font-medium text-success-700 dark:text-success-400">
                      <span>You save</span>
                      <Price amount={order.totals.savings} size="sm" />
                    </div>
                  )}
                  <div className="flex items-center justify-between text-sand-600 dark:text-sand-300">
                    <span>Shipping</span>
                    <Price amount={order.totals.shipping} size="sm" />
                  </div>
                  <div className="mt-1 flex items-center justify-between border-t border-sand-200 pt-2.5 dark:border-night-800">
                    <span className="font-medium text-sand-900 dark:text-sand-100">
                      Total
                    </span>
                    <Price amount={order.totals.grandTotal} size="lg" />
                  </div>
                </div>
              </div>
            </div>

            {order.payment && (
              <div className="rounded-2xl border border-sand-200 bg-white p-5 dark:border-night-800 dark:bg-night-900">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-sand-900 dark:text-sand-100">
                    Payment
                  </p>
                  <PaymentStatusBadge status={order.payment.status} />
                </div>
                <p className="mt-2 flex items-center gap-2 text-sm text-sand-700 dark:text-sand-300">
                  <span>{order.payment.methodLabel}</span>
                  <span aria-hidden="true">·</span>
                  <Price amount={order.payment.amount} size="sm" />
                </p>
                {order.payment.status === "pending" &&
                  order.payment.method === "cod" && (
                    <p className="text-sm text-sand-500 dark:text-sand-400">
                      Pay in cash when your order arrives — no online payment
                      needed.
                    </p>
                  )}
                {order.payment.status === "pending" &&
                  order.payment.method !== "cod" &&
                  order.payment.expiresAt && (
                    <p className="text-sm text-sand-500 dark:text-sand-400">
                      Pay before{" "}
                      {new Date(order.payment.expiresAt).toLocaleString(
                        "en-PH",
                        { dateStyle: "medium", timeStyle: "short" }
                      )}{" "}
                      or the order is released.
                    </p>
                  )}
                {order.payment.paidAt && (
                  <p className="text-sm text-sand-500 dark:text-sand-400">
                    Paid{" "}
                    {new Date(order.payment.paidAt).toLocaleString("en-PH", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </p>
                )}
                {order.payment.refundedTotal > 0 && (
                  <p className="flex items-center gap-2 text-sm text-sand-500 dark:text-sand-400">
                    <span>Refunded</span>
                    <Price amount={order.payment.refundedTotal} size="sm" />
                  </p>
                )}
              </div>
            )}

            {order.timeline.length > 0 && (
              <div className="rounded-2xl border border-sand-200 bg-white p-5 dark:border-night-800 dark:bg-night-900">
                <p className="text-sm font-semibold text-sand-900 dark:text-sand-100">
                  Order timeline
                </p>
                <Timeline
                  className="mt-4"
                  items={order.timeline.map((step) => ({
                    title: step.title,
                    description: step.description,
                    tone: step.tone,
                    time: formatDateTime(step.time),
                  }))}
                />
              </div>
            )}

            {order.requests.length > 0 && (
              <div className="rounded-2xl border border-sand-200 bg-white p-5 dark:border-night-800 dark:bg-night-900">
                <p className="text-sm font-semibold text-sand-900 dark:text-sand-100">
                  Your requests
                </p>
                <ul className="mt-3 flex flex-col gap-4">
                  {order.requests.map((request) => {
                    const meta = REQUEST_STATUS[request.status] ?? {
                      tone: "neutral",
                      label: request.status,
                    };
                    return (
                      <li
                        key={request.id}
                        className="flex flex-wrap items-start justify-between gap-3"
                      >
                        <div className="flex min-w-0 flex-col">
                          <span className="text-sm text-sand-800 dark:text-sand-200">
                            {request.kindLabel}
                            {request.storeName ? ` · ${request.storeName}` : ""}
                          </span>
                          <span className="text-xs text-sand-500 dark:text-sand-400">
                            {request.reason}
                          </span>
                          <span className="text-[11px] text-sand-400">
                            {formatDateTime(request.createdAt)}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge tone={meta.tone} variant="soft" size="sm">
                            {meta.label}
                          </Badge>
                          {request.status === "pending" && (
                            <Button
                              variant="ghost"
                              size="sm"
                              loading={withdrawingId === request.id}
                              onClick={() => withdrawRequest(request.id)}
                            >
                              Withdraw
                            </Button>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            {order.status === "cancelled" && (
              <Alert tone="info" title="This order was cancelled">
                The reserved stock was released back to the stores.
              </Alert>
            )}
          </div>
        ) : null}
      </main>

      <Modal
        open={requestOpen}
        onClose={() => setRequestOpen(false)}
        title="Tell us what you need"
        description="Your request is recorded against this order — the store or our team follows up from here."
        footer={
          <>
            <Button variant="outline" onClick={() => setRequestOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="order-request-form" loading={requestBusy}>
              Submit request
            </Button>
          </>
        }
      >
        <form
          id="order-request-form"
          onSubmit={submitRequest}
          className="flex flex-col gap-4"
          noValidate
        >
          {requestError && (
            <Alert tone="danger" title="Could not submit the request">
              {requestError}
            </Alert>
          )}
          <Select
            label="What do you need?"
            value={requestForm.kind}
            onChange={(event) =>
              setRequestForm((form) => ({
                ...form,
                kind: event.target.value,
                reason: REQUEST_REASONS[event.target.value][0],
              }))
            }
          >
            {REQUEST_KINDS.map((kind) => (
              <option key={kind.id} value={kind.id}>
                {kind.label}
              </option>
            ))}
          </Select>
          {order && order.sellerOrders.length > 1 && (
            <Select
              label="Which store?"
              value={requestForm.sellerOrderId}
              onChange={(event) =>
                setRequestForm((form) => ({
                  ...form,
                  sellerOrderId: event.target.value,
                }))
              }
            >
              <option value="">The whole order</option>
              {order.sellerOrders.map((store) => (
                <option key={store.id} value={String(store.id)}>
                  {store.storeName}
                </option>
              ))}
            </Select>
          )}
          <Select
            label="Reason"
            value={requestForm.reason}
            onChange={(event) =>
              setRequestForm((form) => ({ ...form, reason: event.target.value }))
            }
          >
            {REQUEST_REASONS[requestForm.kind].map((reason) => (
              <option key={reason} value={reason}>
                {reason}
              </option>
            ))}
          </Select>
          <Textarea
            label="Details (optional)"
            rows={3}
            value={requestForm.description}
            onChange={(event) =>
              setRequestForm((form) => ({
                ...form,
                description: event.target.value,
              }))
            }
            placeholder="Add anything that helps us understand the request."
          />
        </form>
      </Modal>

      <Modal
        open={confirmCancel}
        onClose={() => setConfirmCancel(false)}
        title="Cancel this order?"
        description="The reservation is released back to the stores. A cancelled order cannot be reopened."
        footer={
          <>
            <Button variant="outline" onClick={() => setConfirmCancel(false)}>
              Keep order
            </Button>
            <Button variant="destructive" onClick={cancelOrder}>
              Cancel order
            </Button>
          </>
        }
      />
    </div>
  );
}
