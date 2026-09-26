/**
 * Receipt (Phase 11.2) — /orders/:number/receipt.
 *
 * Renders the order's immutable snapshots exactly as the API returns them.
 * "Download" is the browser's print dialog (Save as PDF) — no extra
 * dependency — and the on-screen chrome is hidden from print.
 */
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { OrderStatusBadge } from "../components/ui/OrderStatusBadge";
import { PaymentStatusBadge } from "../components/ui/PaymentStatusBadge";
import { Price } from "../components/ui/Price";
import { Skeleton } from "../components/ui/Skeleton";
import { ArrowLeftIcon, LogoMark } from "../components/ui/Icons";
import * as ordersApi from "../data/orders";

function formatDate(value, withTime = false) {
  return new Date(value).toLocaleString("en-PH", {
    dateStyle: "medium",
    ...(withTime ? { timeStyle: "short" } : {}),
  });
}

function Section({ title, children }) {
  return (
    <section className="border-t border-sand-200 px-6 py-5 dark:border-night-800">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-sand-500 dark:text-sand-400">
        {title}
      </h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

export function Receipt() {
  const { number } = useParams();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    ordersApi
      .fetchOrder(number)
      .then((data) => {
        if (!cancelled) setOrder(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.data?.detail || err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [number]);

  return (
    <div className="min-h-dvh bg-sand-50 print:bg-white dark:bg-night-950">
      <main className="mx-auto max-w-2xl px-4 py-8 print:max-w-none print:px-0 print:py-0">
        <div className="mb-4 flex items-center justify-between gap-3 print:hidden">
          <Link
            to={`/orders/${number}`}
            className="inline-flex items-center gap-1 text-sm text-sand-600 transition-colors hover:text-moss-700 dark:text-sand-300 dark:hover:text-moss-300"
          >
            <ArrowLeftIcon size={14} />
            Back to order
          </Link>
          <Button onClick={() => window.print()} disabled={!order}>
            Download / Print
          </Button>
        </div>

        {error && (
          <Alert tone="danger" title="Could not load the receipt">
            {error}
          </Alert>
        )}

        {!order && !error ? (
          <Skeleton className="h-96 w-full" />
        ) : order ? (
          <article className="overflow-hidden rounded-2xl border border-sand-200 bg-white shadow-soft print:rounded-none print:border-0 print:shadow-none dark:border-night-800 dark:bg-night-900">
            <header className="flex flex-wrap items-start justify-between gap-4 px-6 py-6">
              <div className="flex items-center gap-3">
                <LogoMark size={34} />
                <div>
                  <p className="font-display text-lg font-semibold text-sand-900 dark:text-sand-100">
                    Jeyvro
                  </p>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    Official receipt
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="font-mono text-sm text-sand-900 dark:text-sand-100">
                  {order.number}
                </p>
                <p className="text-xs text-sand-500 dark:text-sand-400">
                  Placed {formatDate(order.placedAt, true)}
                </p>
                <div className="mt-1 flex justify-end">
                  <OrderStatusBadge status={order.status} />
                </div>
              </div>
            </header>

            {order.sellerOrders.map((store) => (
              <Section key={store.id} title={store.storeName}>
                <ul className="flex flex-col gap-2">
                  {store.items.map((item) => (
                    <li
                      key={item.id}
                      className="flex items-start justify-between gap-4 text-sm"
                    >
                      <div className="flex min-w-0 flex-col">
                        <span className="text-sand-800 dark:text-sand-200">
                          {item.title}
                        </span>
                        <span className="text-xs text-sand-500 dark:text-sand-400">
                          {item.variant || item.sku} · {item.qty} ×{" "}
                          <Price amount={item.price} size="sm" />
                        </span>
                      </div>
                      <Price amount={item.lineTotal} size="sm" />
                    </li>
                  ))}
                </ul>
                <div className="mt-3 flex flex-col gap-1 border-t border-dashed border-sand-200 pt-2 text-sm dark:border-night-800">
                  <div className="flex justify-between text-sand-500 dark:text-sand-400">
                    <span>Store subtotal</span>
                    <Price amount={store.subtotal} size="sm" />
                  </div>
                  <div className="flex justify-between text-sand-500 dark:text-sand-400">
                    <span>Shipping</span>
                    {store.shippingFee > 0 ? (
                      <Price amount={store.shippingFee} size="sm" />
                    ) : (
                      <span>Free</span>
                    )}
                  </div>
                </div>
              </Section>
            ))}

            <Section title="Ship to">
              <p className="text-sm text-sand-700 dark:text-sand-300">
                {order.address.fullName} · {order.address.phone}
              </p>
              <p className="text-sm text-sand-500 dark:text-sand-400">
                {[order.address.line1, order.address.line2]
                  .filter(Boolean)
                  .join(", ")}
                , {order.address.city}, {order.address.province}{" "}
                {order.address.postalCode}
              </p>
            </Section>

            <Section title="Payment">
              {order.payment ? (
                <div className="flex flex-col gap-1.5 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-sand-600 dark:text-sand-300">
                      {order.payment.methodLabel}
                    </span>
                    <PaymentStatusBadge status={order.payment.status} />
                  </div>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    Reference {order.payment.reference}
                  </p>
                  {order.payment.paidAt && (
                    <p className="text-xs text-sand-500 dark:text-sand-400">
                      Paid {formatDate(order.payment.paidAt, true)}
                    </p>
                  )}
                  {order.payment.refundedTotal > 0 && (
                    <p className="flex items-center gap-2 text-xs text-sand-500 dark:text-sand-400">
                      <span>Refunded</span>
                      <Price amount={order.payment.refundedTotal} size="sm" />
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-sand-500 dark:text-sand-400">
                  No payment recorded.
                </p>
              )}
            </Section>

            <Section title="Totals">
              <div className="flex flex-col gap-1.5 text-sm">
                <div className="flex justify-between text-sand-600 dark:text-sand-300">
                  <span>Subtotal</span>
                  <Price amount={order.totals.subtotal} size="sm" />
                </div>
                {order.totals.savings > 0 && (
                  <div className="flex justify-between font-medium text-success-700 dark:text-success-400">
                    <span>You saved</span>
                    <Price amount={order.totals.savings} size="sm" />
                  </div>
                )}
                <div className="flex justify-between text-sand-600 dark:text-sand-300">
                  <span>Shipping</span>
                  <Price amount={order.totals.shipping} size="sm" />
                </div>
                <div className="flex justify-between border-t border-sand-200 pt-2 text-base font-semibold text-sand-900 dark:border-night-800 dark:text-sand-100">
                  <span>Total</span>
                  <Price amount={order.totals.grandTotal} size="lg" />
                </div>
              </div>
            </Section>

            <footer className="border-t border-sand-200 bg-sand-50 px-6 py-4 text-xs text-sand-500 print:bg-white dark:border-night-800 dark:bg-night-950 dark:text-sand-400">
              This receipt reflects the order exactly as placed — item
              titles, prices, and the shipping address are immutable
              snapshots and never change with the catalog.
            </footer>
          </article>
        ) : null}
      </main>
    </div>
  );
}