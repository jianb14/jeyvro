/**
 * Order history (Phase 11.2) — /orders.
 *
 * Rows are the server's snapshot summaries ({count, items}); the page is
 * URL-driven so the list is shareable and back-button friendly. Status and
 * money are rendered as received — never recomputed here.
 */
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Navbar } from "../components/layout/Navbar";
import { Alert } from "../components/ui/Alert";
import { Breadcrumb } from "../components/ui/Breadcrumb";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { OrderStatusBadge } from "../components/ui/OrderStatusBadge";
import { Pagination } from "../components/ui/Pagination";
import { Price } from "../components/ui/Price";
import { Skeleton } from "../components/ui/Skeleton";
import { PackageIcon } from "../components/ui/Icons";
import * as ordersApi from "../data/orders";

const PAGE_SIZE = 10;

function formatDate(value) {
  return new Date(value).toLocaleDateString("en-PH", { dateStyle: "medium" });
}

function OrderRow({ order }) {
  return (
    <li className="rounded-2xl border border-sand-200 bg-white p-5 transition-shadow hover:shadow-soft dark:border-night-800 dark:bg-night-900">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <Link
            to={`/orders/${order.number}`}
            className="font-display text-base font-semibold text-sand-900 transition-colors hover:text-moss-700 dark:text-sand-100 dark:hover:text-moss-300"
          >
            {order.number}
          </Link>
          <span className="text-xs text-sand-500 dark:text-sand-400">
            Placed {formatDate(order.placedAt)} · {order.itemCount}{" "}
            {order.itemCount === 1 ? "item" : "items"}
          </span>
        </div>
        <OrderStatusBadge status={order.status} />
      </div>

      {order.storeNames.length > 0 && (
        <p className="mt-3 text-sm text-sand-600 dark:text-sand-300">
          {order.storeNames.join(" · ")}
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-sand-200 pt-3 dark:border-night-800">
        <Price amount={order.grandTotal} size="md" />
        <Link to={`/orders/${order.number}`}>
          <Button variant="outline" size="sm">
            View order
          </Button>
        </Link>
      </div>
    </li>
  );
}

export function Orders() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, Number(searchParams.get("page") || 1));
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    ordersApi
      .fetchOrders({ page, pageSize: PAGE_SIZE })
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.data?.detail || err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;

  return (
    <div className="min-h-dvh bg-sand-50 dark:bg-night-950">
      <Navbar />

      <main className="mx-auto max-w-3xl px-4 pb-24 pt-6 sm:px-6 lg:px-8">
        <Breadcrumb
          className="mb-6"
          items={[
            { label: "Home", to: "/" },
            { label: "My account", to: "/account" },
            { label: "Orders" },
          ]}
        />

        <div className="mb-8">
          <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
            Your orders
          </h1>
          <p className="mt-1 text-sm text-sand-500 dark:text-sand-400">
            Track deliveries, view receipts, and buy again.
          </p>
        </div>

        {error && (
          <Alert tone="danger" title="Could not load your orders" className="mb-6">
            {error}
          </Alert>
        )}

        {!data && !error ? (
          <div className="flex flex-col gap-4">
            {[0, 1, 2].map((key) => (
              <Skeleton key={key} className="h-40 w-full" />
            ))}
          </div>
        ) : data && data.count === 0 ? (
          <EmptyState
            icon={PackageIcon}
            title="No orders yet"
            description="When you place an order, it will show up here with its delivery status."
            action={
              <Link to="/products">
                <Button>Start shopping</Button>
              </Link>
            }
          />
        ) : data ? (
          <>
            <ul className="flex flex-col gap-4">
              {data.items.map((order) => (
                <OrderRow key={order.number} order={order} />
              ))}
            </ul>

            {totalPages > 1 && (
              <div className="mt-8 flex justify-center">
                <Pagination
                  total={totalPages}
                  current={page}
                  onChange={(next) =>
                    setSearchParams(next > 1 ? { page: String(next) } : {})
                  }
                />
              </div>
            )}
          </>
        ) : null}
      </main>
    </div>
  );
}