/**
 * Seller order detail (Phase 12.4 / 12.5) — /seller/orders/:id.
 *
 * Full seller slice view: line snapshots, parcel dispatch form (Phase 10
 * fulfillment), shipment timelines, and customer privacy ladder.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { OrderStatusBadge } from "../../components/ui/OrderStatusBadge";
import { Price } from "../../components/ui/Price";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Textarea } from "../../components/ui/Textarea";
import { Timeline } from "../../components/ui/Timeline";
import * as sellerApi from "../../data/seller";

function formatDate(value) {
  return value
    ? new Date(value).toLocaleString("en-PH", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "";
}

export function SellerOrderDetail() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [carrier, setCarrier] = useState("manual");
  const [notes, setNotes] = useState("");
  const [weight, setWeight] = useState("");

  const load = useCallback(() => {
    let cancelled = false;
    sellerApi
      .fetchSellerOrder(id)
      .then((data) => {
        if (!cancelled) setOrder(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(load, [load]);

  async function runTransition(action) {
    setBusy(true);
    setNotice(null);
    try {
      const runner =
        action === "process"
          ? sellerApi.processSellerOrder
          : sellerApi.packSellerOrder;
      const updated = await runner(order.id);
      setOrder(updated);
      setNotice({
        tone: "success",
        message: `Order marked as ${action === "process" ? "processing" : "packed"}.`,
      });
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleShip(event) {
    event.preventDefault();
    setBusy(true);
    setNotice(null);
    try {
      await sellerApi.shipSellerOrder(order.id, {
        carrier,
        notes,
        weightGrams: weight || null,
      });
      setNotice({ tone: "success", message: "Shipment parcel dispatched." });
      setNotes("");
      setWeight("");
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return <Alert tone="danger" title="Could not load this order">{error}</Alert>;
  }

  if (!order) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <Link
            to="/seller/orders"
            className="text-sm font-medium text-moss-700 hover:underline dark:text-moss-300"
          >
            ← All orders
          </Link>
          <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
            {order.orderNumber}
          </h1>
          <p className="text-xs text-sand-500 dark:text-sand-400">
            Placed {formatDate(order.placedAt)}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <OrderStatusBadge status={order.status} />
          {order.canProcess && (
            <Button
              size="sm"
              loading={busy}
              onClick={() => runTransition("process")}
            >
              Accept order
            </Button>
          )}
          {order.canPack && (
            <Button
              size="sm"
              variant="outline"
              loading={busy}
              onClick={() => runTransition("pack")}
            >
              Mark packed
            </Button>
          )}
        </div>
      </header>

      {notice && (
        <Alert tone={notice.tone} onDismiss={() => setNotice(null)}>
          {notice.message}
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Items</CardTitle>
              <CardDescription>
                Snapshotted line values written at checkout ({order.itemCount}{" "}
                items).
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="divide-y divide-sand-200 dark:divide-night-800">
                {order.items.map((item) => (
                  <li
                    key={item.id}
                    className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                  >
                    <div className="flex min-w-0 flex-col">
                      <p className="font-medium text-sand-900 dark:text-sand-100">
                        {item.title}
                      </p>
                      <p className="text-xs text-sand-500 dark:text-sand-400">
                        {item.variant ? `${item.variant} · ` : ""}
                        SKU {item.sku} · Qty {item.qty}
                      </p>
                    </div>
                    <Price amount={item.lineTotal} size="sm" />
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {order.canShip && (
            <Card>
              <CardHeader>
                <CardTitle>Dispatch shipment</CardTitle>
                <CardDescription>
                  Generates an auditable tracking number and logs the dispatch event.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleShip} className="flex flex-col gap-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Select
                      label="Carrier"
                      value={carrier}
                      onChange={(event) => setCarrier(event.target.value)}
                    >
                      <option value="manual">Standard delivery (manual)</option>
                      <option value="jtexpress">J&amp;T Express</option>
                      <option value="lbc">LBC Express</option>
                      <option value="ninjavan">Ninja Van</option>
                    </Select>
                    <Input
                      label="Package weight (grams, optional)"
                      type="number"
                      min="1"
                      step="1"
                      value={weight}
                      onChange={(event) => setWeight(event.target.value)}
                    />
                  </div>
                  <Textarea
                    label="Handling notes (optional)"
                    rows={2}
                    placeholder="Fragile, keep upright…"
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                  />
                  <div>
                    <Button type="submit" loading={busy}>
                      Create shipment parcel
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {order.shipments.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Shipments ({order.shipments.length})</CardTitle>
                <CardDescription>
                  Dispatched parcels and their append-only tracking events.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-6">
                {order.shipments.map((shipment) => (
                  <div
                    key={shipment.id}
                    className="flex flex-col gap-3 rounded-xl border border-sand-200 p-4 dark:border-night-800"
                  >
                    <div className="flex flex-col">
                      <span className="font-mono text-xs font-semibold text-sand-800 dark:text-sand-200">
                        {shipment.trackingNumber}
                      </span>
                      <span className="text-xs text-sand-500 dark:text-sand-400">
                        {shipment.carrierName || shipment.carrier || "Carrier pending"}{" "}
                        · {shipment.status}
                      </span>
                    </div>
                    {shipment.events.length > 0 && (
                      <Timeline
                        items={shipment.events.map((event) => ({
                          title: event.status,
                          description: event.description,
                          time: formatDate(event.occurredAt),
                          tone: event.status === "delivered" ? "success" : "moss",
                        }))}
                      />
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Customer context</CardTitle>
              <CardDescription>
                {order.customer.revealed
                  ? "Order accepted — delivery details unlocked."
                  : "Privacy-safe preview — full details unlock once you accept the order."}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-sand-500 dark:text-sand-400">
                  Recipient
                </p>
                <p className="font-medium text-sand-900 dark:text-sand-100">
                  {order.customer.name}
                </p>
                <p className="text-sand-600 dark:text-sand-400">
                  {order.customer.phone || "Phone hidden"}
                </p>
              </div>
              <div className="border-t border-sand-200 pt-3 dark:border-night-800">
                <p className="text-xs font-semibold uppercase tracking-wider text-sand-500 dark:text-sand-400">
                  Delivery address
                </p>
                <p className="text-sand-700 dark:text-sand-300">
                  {order.customer.address ||
                    (order.customer.city
                      ? `${order.customer.city}, ${order.customer.province}`
                      : "Unlocked when you accept the order")}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Store slice totals</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-sand-600 dark:text-sand-400">Subtotal</span>
                <Price amount={Number(order.subtotal)} size="sm" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sand-600 dark:text-sand-400">Shipping</span>
                <Price amount={Number(order.shippingFee)} size="sm" />
              </div>
              <div className="flex items-center justify-between border-t border-sand-200 pt-2 font-semibold text-sand-900 dark:border-night-800 dark:text-sand-100">
                <span>Total</span>
                <Price amount={Number(order.total)} size="sm" />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
