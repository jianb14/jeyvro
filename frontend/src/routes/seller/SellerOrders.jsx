/**
 * Seller orders (Phase 12.4) — /seller/orders.
 *
 * Incoming store slices ({count, items}); URL-driven search and status
 * filter. Transitions (process / pack / ship) round-trip through the
 * fulfillment endpoints (§10), and customer privacy is preserved by the
 * API ladder (§12.5).
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { OrderStatusBadge } from "../../components/ui/OrderStatusBadge";
import { Pagination } from "../../components/ui/Pagination";
import { Price } from "../../components/ui/Price";
import { SearchInput } from "../../components/ui/SearchInput";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { InboxIcon } from "../../components/ui/Icons";
import * as sellerApi from "../../data/seller";

const PAGE_SIZE = 10;

function formatDate(value) {
  return value
    ? new Date(value).toLocaleDateString("en-PH", { dateStyle: "medium" })
    : "";
}

export function SellerOrders() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("q") || "");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const q = searchParams.get("q") || "";
  const status = searchParams.get("status") || "";
  const page = Number(searchParams.get("page") || 1);

  const load = useCallback(() => {
    let cancelled = false;
    sellerApi
      .fetchSellerOrders({ q, status, page, pageSize: PAGE_SIZE })
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
  }, [q, status, page]);

  useEffect(load, [load]);

  const setParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setSearchParams(next);
  };

  async function runTransition(order, action) {
    setBusyId(order.id);
    setNotice(null);
    try {
      const runner =
        action === "process"
          ? sellerApi.processSellerOrder
          : sellerApi.packSellerOrder;
      await runner(order.id);
      setNotice({
        tone: "success",
        message: `${order.orderNumber}: marked as ${action === "process" ? "processing" : "packed"}.`,
      });
      load();
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
          Incoming orders
        </h1>
        <p className="text-sm text-sand-500 dark:text-sand-400">
          Accept, pack, and dispatch your store slices. Full delivery details
          unlock once you accept an order.
        </p>
      </header>

      {notice && (
        <Alert tone={notice.tone} onDismiss={() => setNotice(null)}>
          {notice.message}
        </Alert>
      )}
      {error && <Alert tone="danger" title="Could not load orders">{error}</Alert>}

      <form
        role="search"
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          setParam("q", search.trim());
        }}
      >
        <div className="min-w-52 flex-1">
          <SearchInput
            label="Search orders"
            placeholder="Order number or customer name…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onClear={() => {
              setSearch("");
              setParam("q", "");
            }}
          />
        </div>
        <div className="w-48">
          <Select
            label="Status"
            value={status}
            onChange={(event) => setParam("status", event.target.value)}
          >
            <option value="">All statuses</option>
            <option value="awaiting_payment">Awaiting payment</option>
            <option value="paid">Paid</option>
            <option value="processing">Processing</option>
            <option value="packed">Packed</option>
            <option value="shipped">Shipped</option>
            <option value="delivered">Delivered</option>
            <option value="cancelled">Cancelled</option>
          </Select>
        </div>
        <Button type="submit" variant="outline">Search</Button>
      </form>

      {!data ? (
        <Skeleton className="h-72 w-full" />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={InboxIcon}
          title={q || status ? "No orders match" : "No orders yet"}
          description={
            q || status
              ? "Try another search or status filter."
              : "When customers order from your store, the orders land here."
          }
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Order</TH>
              <TH>Placed</TH>
              <TH>Customer</TH>
              <TH>Items</TH>
              <TH>Total</TH>
              <TH>Status</TH>
              <TH className="text-right">Actions</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((order) => (
              <TR key={order.id}>
                <TD>
                  <Link
                    to={`/seller/orders/${order.id}`}
                    className="font-medium text-sand-900 hover:text-moss-700 dark:text-sand-100 dark:hover:text-moss-300"
                  >
                    {order.orderNumber}
                  </Link>
                  {order.payment && (
                    <p className="text-xs text-sand-500 dark:text-sand-400">
                      {order.payment.methodLabel} · {order.payment.status}
                    </p>
                  )}
                </TD>
                <TD>{formatDate(order.placedAt)}</TD>
                <TD>
                  <span className="text-sand-800 dark:text-sand-200">
                    {order.customer.name}
                  </span>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    {order.customer.city
                      ? `${order.customer.city}, ${order.customer.province}`
                      : "—"}
                  </p>
                </TD>
                <TD className="tabular-nums">{order.itemCount}</TD>
                <TD>
                  <Price amount={order.total} size="sm" />
                </TD>
                <TD>
                  <OrderStatusBadge status={order.status} />
                </TD>
                <TD>
                  <div className="flex justify-end gap-2">
                    {order.canProcess && (
                      <Button
                        size="sm"
                        variant="outline"
                        loading={busyId === order.id}
                        onClick={() => runTransition(order, "process")}
                      >
                        Accept
                      </Button>
                    )}
                    {order.canPack && (
                      <Button
                        size="sm"
                        variant="outline"
                        loading={busyId === order.id}
                        onClick={() => runTransition(order, "pack")}
                      >
                        Pack
                      </Button>
                    )}
                    <Link to={`/seller/orders/${order.id}`}>
                      <Button size="sm" variant={order.canShip ? "primary" : "ghost"}>
                        {order.canShip ? "Ship" : "View"}
                      </Button>
                    </Link>
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
    </div>
  );
}
