/**
 * Order detail (Phase 8, payments in Phase 9) — the immutable snapshot.
 *
 * Every value comes from the order API (snapshots never re-read the
 * catalog); cancelling releases the stock reservation server-side, and the
 * payment card renders the server's payment state (§6 v1.8) — never a
 * client-side guess. The full order history arrives with Phase 11.
 */
import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { Navbar } from "../components/layout/Navbar";
import { Alert } from "../components/ui/Alert";
import { Breadcrumb } from "../components/ui/Breadcrumb";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";
import { OrderStatusBadge } from "../components/ui/OrderStatusBadge";
import { PaymentStatusBadge } from "../components/ui/PaymentStatusBadge";
import { Price } from "../components/ui/Price";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../components/ui/ToastProvider";
import * as ordersApi from "../data/orders";

const CANCELLABLE = new Set(["placed", "awaiting_payment"]);

export function OrderDetail() {
  const { number } = useParams();
  const location = useLocation();
  const { push } = useToast();
  const [order, setOrder] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [busy, setBusy] = useState(false);

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

  const justPlaced = Boolean(location.state?.justPlaced);
  const cancellable = order ? CANCELLABLE.has(order.status) : false;
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

            {order.status === "cancelled" && (
              <Alert tone="info" title="This order was cancelled">
                The reserved stock was released back to the stores.
              </Alert>
            )}
          </div>
        ) : null}
      </main>

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
