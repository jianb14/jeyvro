/**
 * Order & payment operations (Phase 13.5) — /staff/orders.
 *
 * Read-only oversight console: orders, parcels, and the return/refund/
 * dispute intake queue in one surface. Every list is server-filtered
 * ({count, items}) and rows render API truth — this page never recomputes
 * money (marketplace-orders rule 1). Group access is enforced server-side
 * (§4): support/finance/operations read orders and requests, support/
 * operations read shipments; issuing refunds stays on the payments console.
 */
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Price } from "../../components/ui/Price";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Spinner } from "../../components/ui/Spinner";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { Tabs, TabPanel } from "../../components/ui/Tabs";
import {
  InboxIcon,
  PackageIcon,
  TruckIcon,
} from "../../components/ui/Icons";
import * as staffApi from "../../data/staff";
import { useAuth } from "../../features/auth/AuthContext";

const PAGE_SIZE = 10;

const ORDER_TONES = {
  placed: "info",
  awaiting_payment: "warning",
  paid: "success",
  processing: "info",
  packed: "info",
  shipped: "info",
  in_transit: "info",
  out_for_delivery: "warning",
  delivered: "success",
  completed: "success",
  cancelled: "neutral",
  refund_pending: "warning",
  refunded: "neutral",
};

const ORDER_STATUSES = [
  "placed",
  "awaiting_payment",
  "paid",
  "processing",
  "packed",
  "shipped",
  "in_transit",
  "out_for_delivery",
  "delivered",
  "completed",
  "cancelled",
  "refund_pending",
  "refunded",
];

const PAYMENT_TONES = {
  pending: "warning",
  paid: "success",
  failed: "danger",
  expired: "neutral",
  cancelled: "neutral",
  partially_refunded: "info",
  refunded: "neutral",
};

const PAYMENT_STATUSES = [
  "pending",
  "paid",
  "failed",
  "expired",
  "cancelled",
  "partially_refunded",
  "refunded",
];

const SHIPMENT_TONES = {
  pending: "neutral",
  packed: "info",
  picked_up: "info",
  in_transit: "info",
  out_for_delivery: "warning",
  delivered: "success",
  failed: "danger",
  cancelled: "neutral",
};

const SHIPMENT_STATUSES = [
  "pending",
  "packed",
  "picked_up",
  "in_transit",
  "out_for_delivery",
  "delivered",
  "failed",
  "cancelled",
];

const REQUEST_TONES = {
  pending: "warning",
  withdrawn: "neutral",
};

function label(value) {
  return String(value ?? "").replace(/_/g, " ");
}

function formatDate(value) {
  return value
    ? new Date(value).toLocaleDateString("en-PH", { dateStyle: "medium" })
    : "";
}

function formatDateTime(value) {
  return value
    ? new Date(value).toLocaleString("en-PH", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "";
}

const TABS = [
  { id: "orders", label: "Orders", icon: PackageIcon },
  { id: "shipments", label: "Shipments", icon: TruckIcon },
  { id: "requests", label: "Requests", icon: InboxIcon },
];

export function StaffOrders() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const roles = user?.staff_roles ?? [];
  // UX only — the backend refuses out-of-group reads regardless (§4):
  // finance reads orders and requests but never the parcel console.
  const canReadShipments = roles.some((role) =>
    ["support", "operations", "administrator"].includes(role)
  );
  const requestedTab = searchParams.get("tab") || "orders";
  const tab =
    requestedTab === "shipments" && !canReadShipments
      ? "orders"
      : requestedTab;
  const tabs = canReadShipments
    ? TABS
    : TABS.filter((entry) => entry.id !== "shipments");

  const setTab = (next) => {
    const params = new URLSearchParams(searchParams);
    if (next === "orders") params.delete("tab");
    else params.set("tab", next);
    setSearchParams(params);
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
          Orders & payments
        </h1>
        <p className="text-sm text-sand-500 dark:text-sand-400">
          Read-only oversight of every order, parcel, and post-purchase
          request across the marketplace. Money movement stays on the
          payments console and is finance-only (§4).
        </p>
      </header>

      <Tabs tabs={tabs} defaultTab={tab} onChange={setTab} />

      {tab === "orders" && (
        <TabPanel>
          <OrdersPanel
            searchParams={searchParams}
            setSearchParams={setSearchParams}
          />
        </TabPanel>
      )}
      {tab === "shipments" && (
        <TabPanel>
          <ShipmentsPanel
            searchParams={searchParams}
            setSearchParams={setSearchParams}
          />
        </TabPanel>
      )}
      {tab === "requests" && (
        <TabPanel>
          <RequestsPanel
            searchParams={searchParams}
            setSearchParams={setSearchParams}
          />
        </TabPanel>
      )}
    </div>
  );
}

function OrdersPanel({ searchParams, setSearchParams }) {
  const q = searchParams.get("q") || "";
  const status = searchParams.get("status") || "";
  const payment = searchParams.get("payment") || "";
  const page = Number(searchParams.get("page") || 1);

  const [search, setSearch] = useState(q);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [detailNumber, setDetailNumber] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    staffApi
      .fetchStaffOrders({ q, status, payment, page, pageSize: PAGE_SIZE })
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
  }, [q, status, payment, page]);

  useEffect(load, [load]);

  const setParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setSearchParams(next);
  };

  return (
    <div className="flex flex-col gap-6">
      {error && (
        <Alert tone="danger" title="Could not load orders">
          {error}
        </Alert>
      )}

      <form
        role="search"
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          setParam("q", search.trim());
        }}
      >
        <div className="min-w-52 flex-1">
          <Input
            label="Search orders"
            placeholder="Order number, customer email, or ship-to name…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="w-44">
          <Select
            label="Status"
            value={status}
            onChange={(event) => setParam("status", event.target.value)}
          >
            <option value="">All statuses</option>
            {ORDER_STATUSES.map((value) => (
              <option key={value} value={value}>
                {label(value)}
              </option>
            ))}
          </Select>
        </div>
        <div className="w-44">
          <Select
            label="Payment"
            value={payment}
            onChange={(event) => setParam("payment", event.target.value)}
          >
            <option value="">All payments</option>
            {PAYMENT_STATUSES.map((value) => (
              <option key={value} value={value}>
                {label(value)}
              </option>
            ))}
          </Select>
        </div>
        <Button type="submit" variant="outline">
          Search
        </Button>
      </form>

      {!data ? (
        <Skeleton className="h-64 w-full" />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={PackageIcon}
          title={q || status || payment ? "No orders match" : "No orders yet"}
          description={
            q || status || payment
              ? "Try another search or filter."
              : "Orders appear here the moment a customer checks out."
          }
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Order</TH>
              <TH>Customer</TH>
              <TH>Items</TH>
              <TH>Total</TH>
              <TH>Payment</TH>
              <TH>Status</TH>
              <TH className="text-right">Actions</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((order) => (
              <TR key={order.number}>
                <TD>
                  <p className="font-medium text-sand-900 dark:text-sand-100">
                    {order.number}
                  </p>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    {order.storeNames.join(", ")}
                  </p>
                </TD>
                <TD>
                  <span className="text-sand-800 dark:text-sand-200">
                    {order.customerEmail}
                  </span>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    {[order.shipToCity, order.shipToProvince]
                      .filter(Boolean)
                      .join(", ")}
                  </p>
                </TD>
                <TD className="tabular-nums">{order.itemCount}</TD>
                <TD>
                  <Price amount={order.grandTotal} size="sm" />
                </TD>
                <TD>
                  {order.paymentStatus ? (
                    <Badge
                      tone={PAYMENT_TONES[order.paymentStatus] || "neutral"}
                      variant="soft"
                    >
                      {label(order.paymentStatus)}
                    </Badge>
                  ) : (
                    <span className="text-xs text-sand-400">—</span>
                  )}
                  {order.paymentMethod && (
                    <p className="mt-1 text-xs text-sand-500 dark:text-sand-400">
                      {label(order.paymentMethod)}
                    </p>
                  )}
                </TD>
                <TD>
                  <Badge
                    tone={ORDER_TONES[order.status] || "neutral"}
                    variant="soft"
                  >
                    {label(order.status)}
                  </Badge>
                </TD>
                <TD>
                  <div className="flex justify-end">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setDetailNumber(order.number)}
                    >
                      View
                    </Button>
                  </div>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      {data && data.count > PAGE_SIZE && (
        <Pagination
          total={Math.ceil(data.count / PAGE_SIZE)}
          current={page}
          onChange={(next) => setParam("page", String(next))}
        />
      )}

      <StaffOrderDetailModal
        key={detailNumber}
        number={detailNumber}
        onClose={() => setDetailNumber(null)}
      />
    </div>
  );
}

function ShipmentsPanel({ searchParams, setSearchParams }) {
  const q = searchParams.get("sq") || "";
  const status = searchParams.get("sstatus") || "";
  const carrier = searchParams.get("scarrier") || "";
  const page = Number(searchParams.get("spage") || 1);

  const [search, setSearch] = useState(q);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    staffApi
      .fetchStaffShipments({ q, status, carrier, page, pageSize: PAGE_SIZE })
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
  }, [q, status, carrier, page]);

  useEffect(load, [load]);

  const setParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "spage") next.delete("spage");
    setSearchParams(next);
  };

  return (
    <div className="flex flex-col gap-6">
      {error && (
        <Alert tone="danger" title="Could not load shipments">
          {error}
        </Alert>
      )}

      <form
        role="search"
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          setParam("sq", search.trim());
        }}
      >
        <div className="min-w-52 flex-1">
          <Input
            label="Search shipments"
            placeholder="Tracking number, order number, or store…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="w-44">
          <Select
            label="Status"
            value={status}
            onChange={(event) => setParam("sstatus", event.target.value)}
          >
            <option value="">All statuses</option>
            {SHIPMENT_STATUSES.map((value) => (
              <option key={value} value={value}>
                {label(value)}
              </option>
            ))}
          </Select>
        </div>
        <div className="w-44">
          <Select
            label="Carrier"
            value={carrier}
            onChange={(event) => setParam("scarrier", event.target.value)}
          >
            <option value="">All carriers</option>
            <option value="manual">Manual</option>
            <option value="jtexpress">J&amp;T Express</option>
            <option value="lbc">LBC</option>
            <option value="ninjavan">Ninja Van</option>
          </Select>
        </div>
        <Button type="submit" variant="outline">
          Search
        </Button>
      </form>

      {!data ? (
        <Skeleton className="h-64 w-full" />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={TruckIcon}
          title={q || status || carrier ? "No parcels match" : "No parcels yet"}
          description={
            q || status || carrier
              ? "Try another search or filter."
              : "Parcels appear here as sellers dispatch shipments."
          }
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Parcel</TH>
              <TH>Store</TH>
              <TH>Carrier</TH>
              <TH>Timeline</TH>
              <TH>Shipped</TH>
              <TH>Delivered</TH>
              <TH>Status</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((shipment) => (
              <TR key={shipment.trackingNumber}>
                <TD>
                  <p className="font-medium text-sand-900 dark:text-sand-100">
                    {shipment.trackingNumber}
                  </p>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    {shipment.orderNumber}
                  </p>
                </TD>
                <TD>{shipment.storeName}</TD>
                <TD>
                  <span className="text-sand-800 dark:text-sand-200">
                    {shipment.carrierName || label(shipment.carrier)}
                  </span>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    {shipment.carrier}
                  </p>
                </TD>
                <TD className="tabular-nums">{shipment.eventCount}</TD>
                <TD>{formatDate(shipment.shippedAt)}</TD>
                <TD>{formatDate(shipment.deliveredAt)}</TD>
                <TD>
                  <Badge
                    tone={SHIPMENT_TONES[shipment.status] || "neutral"}
                    variant="soft"
                  >
                    {label(shipment.status)}
                  </Badge>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      {data && data.count > PAGE_SIZE && (
        <Pagination
          total={Math.ceil(data.count / PAGE_SIZE)}
          current={page}
          onChange={(next) => setParam("spage", String(next))}
        />
      )}
    </div>
  );
}

function RequestsPanel({ searchParams, setSearchParams }) {
  const q = searchParams.get("rq") || "";
  const kind = searchParams.get("rkind") || "";
  const status = searchParams.get("rstatus") || "";
  const page = Number(searchParams.get("rpage") || 1);

  const [search, setSearch] = useState(q);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    staffApi
      .fetchStaffRequests({ q, kind, status, page, pageSize: PAGE_SIZE })
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
  }, [q, kind, status, page]);

  useEffect(load, [load]);

  const setParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "rpage") next.delete("rpage");
    setSearchParams(next);
  };

  return (
    <div className="flex flex-col gap-6">
      {error && (
        <Alert tone="danger" title="Could not load requests">
          {error}
        </Alert>
      )}

      <form
        role="search"
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          setParam("rq", search.trim());
        }}
      >
        <div className="min-w-52 flex-1">
          <Input
            label="Search requests"
            placeholder="Order number, customer email, or reason…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="w-40">
          <Select
            label="Kind"
            value={kind}
            onChange={(event) => setParam("rkind", event.target.value)}
          >
            <option value="">All kinds</option>
            <option value="return">Return</option>
            <option value="refund">Refund</option>
            <option value="issue">Report an issue</option>
          </Select>
        </div>
        <div className="w-40">
          <Select
            label="Status"
            value={status}
            onChange={(event) => setParam("rstatus", event.target.value)}
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="withdrawn">Withdrawn</option>
          </Select>
        </div>
        <Button type="submit" variant="outline">
          Search
        </Button>
      </form>

      {!data ? (
        <Skeleton className="h-64 w-full" />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={InboxIcon}
          title={q || kind || status ? "No requests match" : "No requests yet"}
          description={
            q || kind || status
              ? "Try another search or filter."
              : "Customer returns, refund asks, and issue reports land here."
          }
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Order</TH>
              <TH>Kind</TH>
              <TH>Reason</TH>
              <TH>Store</TH>
              <TH>Filed</TH>
              <TH>Status</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((request) => (
              <TR key={request.id}>
                <TD>
                  <p className="font-medium text-sand-900 dark:text-sand-100">
                    {request.orderNumber}
                  </p>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    {request.customerEmail}
                  </p>
                </TD>
                <TD>
                  <Badge tone="info" variant="soft">
                    {request.kindLabel || label(request.kind)}
                  </Badge>
                </TD>
                <TD>
                  <span className="text-sand-800 dark:text-sand-200">
                    {request.reason}
                  </span>
                  {request.description && (
                    <p className="text-xs text-sand-500 dark:text-sand-400">
                      {request.description}
                    </p>
                  )}
                </TD>
                <TD>{request.storeName || "Whole order"}</TD>
                <TD>{formatDate(request.createdAt)}</TD>
                <TD>
                  <Badge
                    tone={REQUEST_TONES[request.status] || "neutral"}
                    variant="soft"
                  >
                    {label(request.status)}
                  </Badge>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      {data && data.count > PAGE_SIZE && (
        <Pagination
          total={Math.ceil(data.count / PAGE_SIZE)}
          current={page}
          onChange={(next) => setParam("rpage", String(next))}
        />
      )}
    </div>
  );
}

function StaffOrderDetailModal({ number, onClose }) {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState(null);

  // Fresh state for every order — the call site keys the modal by number,
  // so nothing here needs to reset state inside the effect body.
  useEffect(() => {
    if (!number) return undefined;
    let cancelled = false;
    staffApi
      .fetchStaffOrderDetail(number)
      .then((result) => {
        if (!cancelled) setDetail(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err.data?.detail || err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [number]);

  return (
    <Modal
      open={Boolean(number)}
      onClose={onClose}
      title={number ? `Order ${number}` : "Order"}
      description="Full server snapshot — read-only oversight."
    >
      {error && <Alert tone="danger">{error}</Alert>}
      {!detail && !error && (
        <div className="flex justify-center py-10">
          <Spinner />
        </div>
      )}
      {detail && (
        <div className="space-y-6 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={ORDER_TONES[detail.status] || "neutral"} variant="soft">
              {label(detail.status)}
            </Badge>
            <span className="text-sand-500 dark:text-sand-400">
              Placed {formatDateTime(detail.placedAt)}
            </span>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-sand-200 p-4 dark:border-night-800">
              <p className="font-medium text-sand-900 dark:text-sand-100">
                Customer
              </p>
              <p className="mt-1 text-sand-700 dark:text-sand-300">
                {detail.customerEmail}
              </p>
              <p className="mt-2 text-xs text-sand-500 dark:text-sand-400">
                {detail.shippingAddress.fullName} ·{" "}
                {detail.shippingAddress.phone}
              </p>
              <p className="text-xs text-sand-500 dark:text-sand-400">
                {[
                  detail.shippingAddress.line1,
                  detail.shippingAddress.line2,
                  detail.shippingAddress.city,
                  detail.shippingAddress.province,
                  detail.shippingAddress.postalCode,
                ]
                  .filter(Boolean)
                  .join(", ")}
              </p>
            </div>

            <div className="rounded-xl border border-sand-200 p-4 dark:border-night-800">
              <p className="font-medium text-sand-900 dark:text-sand-100">
                Payment
              </p>
              {detail.payment ? (
                <div className="mt-1 space-y-1 text-sand-700 dark:text-sand-300">
                  <p>{detail.payment.reference}</p>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    {detail.payment.method} · {label(detail.payment.status)}
                    {detail.payment.provider
                      ? ` · ${detail.payment.provider}`
                      : ""}
                  </p>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    Refunded: {detail.payment.refundedTotal.toLocaleString(
                      "en-PH"
                    )}
                  </p>
                </div>
              ) : (
                <p className="mt-1 text-sand-500 dark:text-sand-400">
                  No payment record.
                </p>
              )}
            </div>
          </div>

          {detail.stores.map((store) => (
            <div
              key={store.id}
              className="rounded-xl border border-sand-200 p-4 dark:border-night-800"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium text-sand-900 dark:text-sand-100">
                  {store.storeName}
                </p>
                <Badge
                  tone={ORDER_TONES[store.status] || "neutral"}
                  variant="soft"
                >
                  {label(store.status)}
                </Badge>
              </div>
              <ul className="mt-3 space-y-2">
                {store.items.map((item) => (
                  <li
                    key={item.id}
                    className="flex items-start justify-between gap-3"
                  >
                    <span className="text-sand-700 dark:text-sand-300">
                      {item.quantity} × {item.title}
                      {item.variant ? ` (${item.variant})` : ""}
                    </span>
                    <Price amount={item.lineTotal} size="sm" />
                  </li>
                ))}
              </ul>
              <div className="mt-3 flex items-center justify-between border-t border-sand-200 pt-3 dark:border-night-800">
                <span className="text-xs text-sand-500 dark:text-sand-400">
                  Subtotal {store.subtotal.toLocaleString("en-PH")} · Shipping{" "}
                  {store.shippingFee.toLocaleString("en-PH")}
                </span>
                <Price amount={store.total} size="sm" />
              </div>
            </div>
          ))}

          <div className="rounded-xl bg-sand-50 p-4 dark:bg-night-800">
            <div className="flex items-center justify-between">
              <span className="text-sand-600 dark:text-sand-300">Subtotal</span>
              <Price amount={detail.totals.subtotal} size="sm" />
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span className="text-sand-600 dark:text-sand-300">Shipping</span>
              <Price amount={detail.totals.shipping} size="sm" />
            </div>
            {detail.totals.savings > 0 && (
              <div className="mt-2 flex items-center justify-between">
                <span className="text-sand-600 dark:text-sand-300">
                  Savings
                </span>
                <Price amount={detail.totals.savings} size="sm" />
              </div>
            )}
            {detail.totals.tax > 0 && (
              <div className="mt-2 flex items-center justify-between">
                <span className="text-sand-600 dark:text-sand-300">Tax</span>
                <Price amount={detail.totals.tax} size="sm" />
              </div>
            )}
            <div className="mt-3 flex items-center justify-between border-t border-sand-200 pt-3 dark:border-night-700">
              <span className="font-medium text-sand-900 dark:text-sand-100">
                Grand total
              </span>
              <Price amount={detail.totals.grandTotal} size="md" />
            </div>
          </div>

          {detail.requests.length > 0 && (
            <div>
              <p className="font-medium text-sand-900 dark:text-sand-100">
                Post-purchase requests
              </p>
              <ul className="mt-2 space-y-2">
                {detail.requests.map((request) => (
                  <li
                    key={request.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-sand-200 px-3 py-2 dark:border-night-800"
                  >
                    <span className="text-sand-700 dark:text-sand-300">
                      {request.kindLabel} · {request.reason}
                    </span>
                    <Badge
                      tone={REQUEST_TONES[request.status] || "neutral"}
                      variant="soft"
                    >
                      {label(request.status)}
                    </Badge>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

