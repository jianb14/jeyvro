/**
 * Payment & refund oversight (Phase 13.5) — /staff/payments.
 *
 * The finance console (marketplace-orders rule 1 — the API is the only
 * writer): the settlement queue and the refund trail, both server-filtered
 * ({count, items}) and read-only. Support and finance read payments;
 * refunds list for support/finance while issuing one stays finance-only
 * (§4) on the order payment endpoint — this page never moves money.
 */
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Pagination } from "../../components/ui/Pagination";
import { Price } from "../../components/ui/Price";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { Tabs, TabPanel } from "../../components/ui/Tabs";
import { CreditCardIcon, WalletIcon } from "../../components/ui/Icons";
import * as staffApi from "../../data/staff";

const PAGE_SIZE = 10;

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

const REFUND_TONES = {
  pending: "warning",
  succeeded: "success",
  failed: "danger",
};

function label(value) {
  return String(value ?? "").replace(/_/g, " ");
}

function formatDate(value) {
  return value
    ? new Date(value).toLocaleDateString("en-PH", { dateStyle: "medium" })
    : "";
}

const TABS = [
  { id: "payments", label: "Payments", icon: CreditCardIcon },
  { id: "refunds", label: "Refunds", icon: WalletIcon },
];

export function StaffPayments() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") || "payments";

  const setTab = (next) => {
    const params = new URLSearchParams(searchParams);
    if (next === "payments") params.delete("tab");
    else params.set("tab", next);
    setSearchParams(params);
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
          Payments & refunds
        </h1>
        <p className="text-sm text-sand-500 dark:text-sand-400">
          Read-only money oversight: the settlement queue, every captured
          payment, and the refund trail with the staff member who issued it.
          Refunds are issued by finance only (§4).
        </p>
      </header>

      <Tabs tabs={TABS} defaultTab={tab} onChange={setTab} />

      {tab === "payments" && (
        <TabPanel>
          <PaymentsPanel
            searchParams={searchParams}
            setSearchParams={setSearchParams}
          />
        </TabPanel>
      )}
      {tab === "refunds" && (
        <TabPanel>
          <RefundsPanel
            searchParams={searchParams}
            setSearchParams={setSearchParams}
          />
        </TabPanel>
      )}
    </div>
  );
}

function PaymentsPanel({ searchParams, setSearchParams }) {
  const q = searchParams.get("q") || "";
  const status = searchParams.get("status") || "";
  const method = searchParams.get("method") || "";
  const page = Number(searchParams.get("page") || 1);

  const [search, setSearch] = useState(q);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    staffApi
      .fetchStaffPayments({ q, status, method, page, pageSize: PAGE_SIZE })
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
  }, [q, status, method, page]);

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
        <Alert tone="danger" title="Could not load payments">
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
            label="Search payments"
            placeholder="Payment reference, order number, or customer email…"
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
            {PAYMENT_STATUSES.map((value) => (
              <option key={value} value={value}>
                {label(value)}
              </option>
            ))}
          </Select>
        </div>
        <div className="w-40">
          <Select
            label="Method"
            value={method}
            onChange={(event) => setParam("method", event.target.value)}
          >
            <option value="">All methods</option>
            <option value="cod">Cash on Delivery</option>
            <option value="card">Card</option>
            <option value="gcash">GCash</option>
            <option value="maya">Maya</option>
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
          icon={CreditCardIcon}
          title={q || status || method ? "No payments match" : "No payments yet"}
          description={
            q || status || method
              ? "Try another search or filter."
              : "Payments appear here at checkout — COD included."
          }
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Payment</TH>
              <TH>Order</TH>
              <TH>Method</TH>
              <TH>Amount</TH>
              <TH>Refunded</TH>
              <TH>Status</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((payment) => (
              <TR key={payment.reference}>
                <TD>
                  <p className="font-medium text-sand-900 dark:text-sand-100">
                    {payment.reference}
                  </p>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    {payment.customerEmail}
                  </p>
                </TD>
                <TD>{payment.orderNumber}</TD>
                <TD>
                  <span className="text-sand-800 dark:text-sand-200">
                    {label(payment.method)}
                  </span>
                  {payment.provider && (
                    <p className="text-xs text-sand-500 dark:text-sand-400">
                      {payment.provider}
                    </p>
                  )}
                </TD>
                <TD>
                  <Price amount={payment.amount} size="sm" />
                </TD>
                <TD className="tabular-nums">
                  {payment.refundedTotal.toLocaleString("en-PH")}
                </TD>
                <TD>
                  <Badge
                    tone={PAYMENT_TONES[payment.status] || "neutral"}
                    variant="soft"
                  >
                    {label(payment.status)}
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
          onChange={(next) => setParam("page", String(next))}
        />
      )}
    </div>
  );
}

function RefundsPanel({ searchParams, setSearchParams }) {
  const q = searchParams.get("rq") || "";
  const status = searchParams.get("rstatus") || "";
  const page = Number(searchParams.get("rpage") || 1);

  const [search, setSearch] = useState(q);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    staffApi
      .fetchStaffRefunds({ q, status, page, pageSize: PAGE_SIZE })
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
    if (key !== "rpage") next.delete("rpage");
    setSearchParams(next);
  };

  return (
    <div className="flex flex-col gap-6">
      {error && (
        <Alert tone="danger" title="Could not load refunds">
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
            label="Search refunds"
            placeholder="Refund reference, payment reference, or order number…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="w-44">
          <Select
            label="Status"
            value={status}
            onChange={(event) => setParam("rstatus", event.target.value)}
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="succeeded">Succeeded</option>
            <option value="failed">Failed</option>
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
          icon={WalletIcon}
          title={q || status ? "No refunds match" : "No refunds yet"}
          description={
            q || status
              ? "Try another search or status filter."
              : "Refunds issued by finance appear here with the issuing staff member."
          }
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Refund</TH>
              <TH>Order</TH>
              <TH>Amount</TH>
              <TH>Reason</TH>
              <TH>Issued by</TH>
              <TH>Filed</TH>
              <TH>Status</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((refund) => (
              <TR key={refund.reference}>
                <TD>
                  <p className="font-medium text-sand-900 dark:text-sand-100">
                    {refund.reference}
                  </p>
                  <p className="text-xs text-sand-500 dark:text-sand-400">
                    {refund.paymentReference}
                  </p>
                </TD>
                <TD>{refund.orderNumber}</TD>
                <TD>
                  <Price amount={refund.amount} size="sm" />
                </TD>
                <TD>
                  <span className="text-sand-700 dark:text-sand-300">
                    {refund.reason || "—"}
                  </span>
                </TD>
                <TD>
                  <span className="text-sand-800 dark:text-sand-200">
                    {refund.issuedBy || "system"}
                  </span>
                </TD>
                <TD>{formatDate(refund.createdAt)}</TD>
                <TD>
                  <Badge
                    tone={REFUND_TONES[refund.status] || "neutral"}
                    variant="soft"
                  >
                    {label(refund.status)}
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
