/**
 * Seller dashboard (Phase 12.1) — /seller.
 *
 * Every number is server truth from GET /api/v1/stores/my/dashboard
 * (marketplace-sellers rule 5); this page renders, never estimates.
 * Recent reviews render their empty state until Phase 14 ships reviews.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { OrderStatusBadge } from "../../components/ui/OrderStatusBadge";
import { Price } from "../../components/ui/Price";
import { Skeleton } from "../../components/ui/Skeleton";
import { StockIndicator } from "../../components/ui/StockIndicator";
import { InboxIcon, PackageIcon, StarIcon } from "../../components/ui/Icons";
import * as sellerApi from "../../data/seller";

const STATUS_TONES = {
  active: "success",
  pending: "warning",
  suspended: "danger",
};

function formatDate(value) {
  return new Date(value).toLocaleDateString("en-PH", { dateStyle: "medium" });
}

function StatCard({ label, value, hint }) {
  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-xs font-semibold uppercase tracking-wider text-sand-500 dark:text-sand-400">
          {label}
        </p>
        <p className="mt-2 font-display text-2xl font-semibold tabular-nums text-sand-900 dark:text-sand-100">
          {value}
        </p>
        {hint && <p className="mt-1 text-xs text-sand-500 dark:text-sand-400">{hint}</p>}
      </CardContent>
    </Card>
  );
}

export function SellerDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    sellerApi
      .fetchDashboard()
      .then((dashboard) => {
        if (!cancelled) setData(dashboard);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return <Alert tone="danger" title="Could not load your dashboard">{error}</Alert>;
  }

  if (!data) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-9 w-64" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((key) => (
            <Skeleton key={key} className="h-28 w-full" />
          ))}
        </div>
        <Skeleton className="h-56 w-full" />
      </div>
    );
  }

  const { store, sales, orders, products, inventory } = data;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
              {store.name}
            </h1>
            <Badge tone={STATUS_TONES[store.status] || "neutral"} variant="soft">
              {store.status}
            </Badge>
          </div>
          <p className="text-sm text-sand-500 dark:text-sand-400">
            {products.total} {products.total === 1 ? "product" : "products"} ·{" "}
            {orders.open} open {orders.open === 1 ? "order" : "orders"}
          </p>
        </div>
        <div className="flex gap-2">
          {store.status === "active" && (
            <Link to={`/store/${store.slug}`}>
              <Button variant="outline" size="sm">View storefront</Button>
            </Link>
          )}
          <Link to="/seller/products/new">
            <Button size="sm">Add product</Button>
          </Link>
        </div>
      </header>

      <section aria-label="Sales summary" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Gross sales"
          value={<Price amount={sales.gross} size="lg" />}
          hint={`${sales.last30Days.orders} orders in the last 30 days`}
        />
        <StatCard label="Orders" value={sales.orders} hint="Excludes cancelled and refunded" />
        <StatCard label="Units sold" value={sales.unitsSold} />
        <StatCard
          label="Average order"
          value={<Price amount={sales.averageOrderValue} size="lg" />}
        />
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Order summary</CardTitle>
            <CardDescription>Where your orders are right now (server truth).</CardDescription>
          </CardHeader>
          <CardContent>
            {orders.total === 0 ? (
              <EmptyState
                compact
                icon={InboxIcon}
                title="No orders yet"
                description="Orders from your store will appear here."
              />
            ) : (
              <ul className="flex flex-col gap-2">
                {Object.entries(orders.byStatus).map(([status, count]) => (
                  <li
                    key={status}
                    className="flex items-center justify-between gap-3 rounded-xl border border-sand-200 px-4 py-2.5 dark:border-night-800"
                  >
                    <OrderStatusBadge status={status} />
                    <span className="text-sm font-medium tabular-nums text-sand-700 dark:text-sand-300">
                      {count}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Inventory alerts</CardTitle>
            <CardDescription>
              {inventory.lowStockCount === 0
                ? "Everything is above its low-stock threshold."
                : `${inventory.lowStockCount} variants at or below their threshold.`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {inventory.lowStockItems.length === 0 ? (
              <EmptyState
                compact
                icon={PackageIcon}
                title="Stock looks healthy"
                description="Low-stock variants surface here so you can restock early."
              />
            ) : (
              <ul className="flex flex-col gap-2">
                {inventory.lowStockItems.map((item) => (
                  <li
                    key={item.variantId}
                    className="flex items-center justify-between gap-3 rounded-xl border border-sand-200 px-4 py-2.5 dark:border-night-800"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-sand-800 dark:text-sand-200">
                        {item.productTitle}
                      </p>
                      <p className="text-xs text-sand-500 dark:text-sand-400">{item.sku}</p>
                    </div>
                    <StockIndicator count={item.available} threshold={item.lowStockThreshold} />
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-4">
              <Link to="/seller/inventory">
                <Button variant="outline" size="sm">Manage inventory</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent orders</CardTitle>
          <CardDescription>Customer labels are masked until you accept an order.</CardDescription>
        </CardHeader>
        <CardContent>
          {data.recentOrders.length === 0 ? (
            <EmptyState
              compact
              icon={InboxIcon}
              title="Nothing to fulfil yet"
              description="New orders land here the moment checkout completes."
            />
          ) : (
            <ul className="flex flex-col gap-2">
              {data.recentOrders.map((order) => (
                <li
                  key={order.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sand-200 px-4 py-3 dark:border-night-800"
                >
                  <div className="flex min-w-0 flex-col">
                    <Link
                      to={`/seller/orders/${order.id}`}
                      className="font-medium text-sand-900 hover:text-moss-700 dark:text-sand-100 dark:hover:text-moss-300"
                    >
                      {order.orderNumber}
                    </Link>
                    <span className="text-xs text-sand-500 dark:text-sand-400">
                      {order.customer} · {order.itemCount}{" "}
                      {order.itemCount === 1 ? "item" : "items"} · {formatDate(order.placedAt)}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Price amount={order.total} size="sm" />
                    <OrderStatusBadge status={order.status} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent reviews</CardTitle>
          <CardDescription>Seller and product reviews arrive with Phase 14.</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            compact
            icon={StarIcon}
            title="No reviews yet"
            description="Ratings and reviews unlock when the reviews phase ships — nothing is faked in the meantime."
          />
        </CardContent>
      </Card>
    </div>
  );
}
