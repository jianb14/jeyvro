/**
 * Platform analytics (Phase 19.1) — /staff/analytics.
 *
 * Every figure on this page is served by the reporting aggregates (§6 v1.16):
 * the console never queries a transactional table, and it never re-derives a
 * number the server already computed (marketplace-admin rule 5). The date
 * range is the only input, and the server validates it.
 *
 * Two audiences share the page, mirroring the API's §4 gates exactly: the
 * financial figures (GMV, revenue, commission, refunds) and the store
 * leaderboard belong to finance/administrator, while product activity is open
 * to the read-only oversight groups as well. A role that may not read the
 * money does not ask for it — the load is shaped by the caller's own roles
 * instead of firing a request that would 403, so a support operator gets a
 * working page rather than a broken one, and never a half-drawn dashboard of
 * zeroes standing in for figures they were refused.
 *
 * §19.3's operational section (order status, fulfillment, returns, refunds,
 * support workload, seller performance) follows the same discipline against its
 * own gate: the oversight groups get it, the moderator's page never requests
 * it. Every figure is the server's count — the page divides nothing itself, so
 * a rate can never be "roughly right" (marketplace-admin rule 5).
 *
 * §19.4's CSV exports follow the page's range and the same gate: a download is
 * a plain navigation (the session cookie travels with it) to the report the
 * caller's role may read, and the links shown are exactly the reports that
 * route would serve.
 *
 * Bars are the one thing drawn here, and they are pure presentation: the width
 * is the server's number scaled against the busiest day in the same series,
 * never a figure the client invented.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert } from "../../components/ui/Alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { DownloadIcon } from "../../components/ui/Icons";
import { useAuth } from "../../features/auth/AuthContext";
import * as staffApi from "../../data/staff";

const MONEY_GROUPS = ["finance", "administrator", "super_administrator"];

// §19.3: operational counts are what support and operations oversee, so they
// ride the same gate the API enforces (support / operations / finance /
// administrator) — the page asks for exactly what its caller's roles allow.
const OPERATIONAL_GROUPS = [
  "support",
  "operations",
  "finance",
  "administrator",
  "super_administrator",
];

const RANGES = [
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
];

function formatP(n) {
  return (
    "₱" +
    Number(n).toLocaleString("en-PH", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

function formatDay(value) {
  return value
    ? new Date(`${value}T00:00:00`).toLocaleDateString("en-PH", {
        dateStyle: "medium",
      })
    : "—";
}

/** The preset window, as ISO days the server can parse. */
function windowFor(days) {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - (Number(days) - 1));
  const iso = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
      d.getDate()
    ).padStart(2, "0")}`;
  return { from: iso(from), to: iso(to) };
}

/** One headline figure — the server's total, formatted for reading. */
function Stat({ label, value, hint }) {
  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-xs font-medium uppercase tracking-wide text-sand-500 dark:text-sand-400">
          {label}
        </p>
        <p className="mt-1 font-display text-2xl font-semibold tabular-nums text-sand-900 dark:text-sand-100">
          {value}
        </p>
        <p className="mt-1 text-xs text-sand-500 dark:text-sand-400">{hint}</p>
      </CardContent>
    </Card>
  );
}

export function StaffAnalytics() {
  const { user } = useAuth();
  const roles = user?.staff_roles ?? [];
  const canSeeMoney = roles.some((role) => MONEY_GROUPS.includes(role));
  const canSeeOperations = roles.some((role) => OPERATIONAL_GROUPS.includes(role));

  const [range, setRange] = useState("30");
  const [summary, setSummary] = useState(null);
  const [stores, setStores] = useState([]);
  const [products, setProducts] = useState([]);
  // §19.3 — the operational day and the store's operational totals, loaded
  // only for the groups the API would serve.
  const [operations, setOperations] = useState(null);
  const [performance, setPerformance] = useState([]);
  // `loaded`, not `loading`, and only ever flipped inside the request's own
  // callbacks: a setState called synchronously in an effect body is a cascading
  // render, and a range change should keep the last figures on screen rather
  // than blanking the page back to a skeleton.
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    const params = windowFor(range);
    // Each list is fetched only by the roles the backend would serve: asking
    // for what you cannot read is a guaranteed 403, not a feature.
    const summaryJob = canSeeMoney
      ? staffApi.fetchStaffAnalyticsSummary(params)
      : Promise.resolve(null);
    const storesJob = canSeeMoney
      ? staffApi.fetchStaffAnalyticsStores({ ...params, limit: 10 })
      : Promise.resolve([]);
    const productsJob = canSeeOperations
      ? staffApi.fetchStaffAnalyticsProducts({
          ...params,
          limit: 10,
        })
      : Promise.resolve([]);
    // §19.3 — same discipline for the operational reads: a moderator's page
    // never fires the request that would 403.
    const operationsJob = canSeeOperations
      ? staffApi.fetchStaffAnalyticsOperations(params)
      : Promise.resolve(null);
    const performanceJob = canSeeOperations
      ? staffApi.fetchStaffAnalyticsPerformance({ ...params, limit: 10 })
      : Promise.resolve([]);

    Promise.all([summaryJob, storesJob, productsJob, operationsJob, performanceJob])
      .then(([nextSummary, nextStores, nextProducts, nextOperations, nextPerformance]) => {
        if (cancelled) return;
        setSummary(nextSummary);
        setStores(nextStores);
        setProducts(nextProducts);
        setOperations(nextOperations);
        setPerformance(nextPerformance);
        setError(null);
        setLoaded(true);
      })
      .catch((err) => {
        if (cancelled) return;
        setSummary(null);
        setStores([]);
        setProducts([]);
        setOperations(null);
        setPerformance([]);
        setError(err.data?.detail || err.message);
        setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [range, canSeeMoney, canSeeOperations]);

  useEffect(load, [load]);

  const loading = !loaded;

  // The series arrives oldest first; a dashboard reads newest first.
  const days = useMemo(() => [...(summary?.days ?? [])].reverse(), [summary]);
  // §19.3 operations read the newest day the same way.
  const operationDays = useMemo(
    () => [...(operations?.days ?? [])].reverse(),
    [operations]
  );
  // §19.4 — the export links carry the same range the page is showing.
  const exportRange = useMemo(() => windowFor(range), [range]);
  const busiest = useMemo(
    () => Math.max(1, ...days.map((day) => Number(day.gmv))),
    [days]
  );

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-9 w-64" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((key) => (
            <Skeleton key={key} className="h-24 w-full" />
          ))}
        </div>
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
            Analytics
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-sand-500 dark:text-sand-400">
            Marketplace figures served from the reporting aggregates — derived
            from the records, rebuildable on demand, never hand-edited.
          </p>
        </div>
        <div className="w-44">
          <Select
            label="Range"
            value={range}
            onChange={(event) => setRange(event.target.value)}
          >
            {RANGES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {canSeeMoney || canSeeOperations ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium uppercase tracking-wide text-sand-500 dark:text-sand-400">
            Export CSV
          </span>
          {staffApi.STAFF_ANALYTICS_REPORTS.filter((report) =>
            report.money ? canSeeMoney : canSeeOperations
          ).map((report) => (
            <a
              key={report.slug}
              href={staffApi.staffAnalyticsCsvUrl(report.slug, exportRange)}
              download
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-sand-300 px-3 text-xs font-medium text-sand-800 transition-colors hover:border-moss-400 hover:bg-moss-50 dark:border-night-700 dark:text-sand-200 dark:hover:border-moss-600 dark:hover:bg-night-800"
            >
              <DownloadIcon size={14} className="shrink-0 opacity-90" />
              {report.label}
            </a>
          ))}
        </div>
      ) : null}

      {error ? (
        <Alert tone="danger" title="Could not load analytics">
          {error}
        </Alert>
      ) : null}

      {canSeeMoney && summary ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            label="GMV"
            value={formatP(summary.totals.gmv)}
            hint={`${summary.totals.ordersCount} order(s) placed`}
          />
          <Stat
            label="Revenue"
            value={formatP(summary.totals.revenue)}
            hint={`${formatP(summary.totals.capturedTotal)} collected − ${formatP(
              summary.totals.refundedTotal
            )} refunded`}
          />
          <Stat
            label="Commission"
            value={formatP(summary.totals.commission)}
            hint={`on ${formatP(summary.totals.commissionBase)} net merchandise`}
          />
          <Stat
            label="Active customers"
            value={summary.totals.customerDays.toLocaleString("en-PH")}
            hint={`customer days · ${summary.totals.unitsSold} unit(s) sold`}
          />
        </div>
      ) : null}

      {canSeeMoney && summary ? (
        <Card>
          <CardHeader>
            <CardTitle>Daily activity</CardTitle>
            <CardDescription>
              What was ordered and what money moved, day by day —{" "}
              {formatDay(summary.start)} to {formatDay(summary.end)}. Commission
              is earned on capture, so it follows the cash rather than the day
              an order was placed.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {days.length === 0 ? (
              <p className="px-6 pb-6 text-sm text-sand-500 dark:text-sand-400">
                No days in this range yet. Run{" "}
                <code className="rounded bg-sand-100 px-1.5 py-0.5 text-xs dark:bg-night-800">
                  python manage.py rebuild_reporting
                </code>{" "}
                to derive the aggregates from the records.
              </p>
            ) : (
              <div className="max-h-96 overflow-y-auto">
                <Table>
                  <THead>
                    <TR>
                      <TH>Day</TH>
                      <TH className="text-right">Orders</TH>
                      <TH className="text-right">GMV</TH>
                      <TH className="text-right">Collected</TH>
                      <TH className="text-right">Refunded</TH>
                      <TH className="text-right">Commission</TH>
                      <TH>GMV</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {days.map((day) => (
                      <TR key={day.day}>
                        <TD>{formatDay(day.day)}</TD>
                        <TD className="text-right tabular-nums">
                          {day.ordersCount}
                        </TD>
                        <TD className="text-right tabular-nums">
                          {formatP(day.gmv)}
                        </TD>
                        <TD className="text-right tabular-nums">
                          {formatP(day.capturedTotal)}
                        </TD>
                        <TD className="text-right tabular-nums">
                          {formatP(day.refundedTotal)}
                        </TD>
                        <TD className="text-right tabular-nums">
                          {formatP(day.commission)}
                        </TD>
                        <TD>
                          <span
                            className="block h-1.5 min-w-[2px] rounded-full bg-moss-500 dark:bg-moss-400"
                            style={{
                              width: `${Math.round(
                                (Number(day.gmv) / busiest) * 100
                              )}%`,
                            }}
                          />
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}

      {!canSeeMoney ? (
        <Alert tone="info" title="Money figures are finance's to read">
          The revenue, commission and refund totals are gated to the finance and
          administrator groups (§4). What follows is the product activity your
          group already oversees.
        </Alert>
      ) : null}

      {canSeeMoney ? (
        <Card>
          <CardHeader>
            <CardTitle>Store leaderboard</CardTitle>
            <CardDescription>
              Range totals per store, biggest seller first. Commission is taken
              on the store's own net merchandise — its sales less the discounts
              that store funded — never on shipping.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {stores.length === 0 ? (
              <p className="px-6 pb-6 text-sm text-sand-500 dark:text-sand-400">
                No store activity in this range.
              </p>
            ) : (
              <Table>
                <THead>
                  <TR>
                    <TH>Store</TH>
                    <TH className="text-right">Orders</TH>
                    <TH className="text-right">Units</TH>
                    <TH className="text-right">Gross sales</TH>
                    <TH className="text-right">Store-funded</TH>
                    <TH className="text-right">Refunded</TH>
                    <TH className="text-right">Revenue</TH>
                    <TH className="text-right">Commission</TH>
                  </TR>
                </THead>
                <TBody>
                  {stores.map((store) => (
                    <TR key={store.storeId}>
                      <TD className="font-medium text-sand-900 dark:text-sand-100">
                        {store.storeName}
                      </TD>
                      <TD className="text-right tabular-nums">
                        {store.ordersCount}
                      </TD>
                      <TD className="text-right tabular-nums">
                        {store.unitsSold}
                      </TD>
                      <TD className="text-right tabular-nums">
                        {formatP(store.grossSales)}
                      </TD>
                      <TD className="text-right tabular-nums">
                        {formatP(store.sellerFundedDiscount)}
                      </TD>
                      <TD className="text-right tabular-nums">
                        {formatP(store.refundedTotal)}
                      </TD>
                      <TD className="text-right tabular-nums">
                        {formatP(store.revenue)}
                      </TD>
                      <TD className="text-right tabular-nums">
                        {formatP(store.commission)}
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            )}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Product activity</CardTitle>
          <CardDescription>
            Best-selling products by units in this range. Merchandise is the
            gross line value the order snapshots recorded.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {products.length === 0 ? (
            <p className="px-6 pb-6 text-sm text-sand-500 dark:text-sand-400">
              Nothing sold in this range.
            </p>
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>Product</TH>
                  <TH>Store</TH>
                  <TH className="text-right">Units</TH>
                  <TH className="text-right">Orders</TH>
                  <TH className="text-right">Merchandise</TH>
                </TR>
              </THead>
              <TBody>
                {products.map((product) => (
                  <TR key={`${product.storeId}-${product.productId}`}>
                    <TD className="font-medium text-sand-900 dark:text-sand-100">
                      {product.productTitle}
                    </TD>
                    <TD>{product.storeName}</TD>
                    <TD className="text-right tabular-nums">
                      {product.unitsSold}
                    </TD>
                    <TD className="text-right tabular-nums">
                      {product.ordersCount}
                    </TD>
                    <TD className="text-right tabular-nums">
                      {formatP(product.merchandise)}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </CardContent>
      </Card>
      {canSeeOperations && operations ? (
        <Card>
          <CardHeader>
            <CardTitle>Operations</CardTitle>
            <CardDescription>
              What the records show happened, day by day —{" "}
              {formatDay(operations.start)} to {formatDay(operations.end)}.
              Orders are bucketed by where they stand as of the last rebuild,
              and a settled refund is counted from the ledger debit that moved
              the money, not from when it was requested.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 p-6">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Stat
                label="Orders open"
                value={operations.totals.ordersOpen.toLocaleString("en-PH")}
                hint={`${operations.totals.ordersCancelled} cancelled · ${operations.totals.ordersRefunded} refunded`}
              />
              <Stat
                label="Orders completed"
                value={operations.totals.ordersCompleted.toLocaleString("en-PH")}
                hint="delivered or completed in range"
              />
              <Stat
                label="Parcels delivered"
                value={operations.totals.shipmentsDelivered.toLocaleString("en-PH")}
                hint={`${operations.totals.shipmentsCreated} parcel(s) sent`}
              />
              <Stat
                label="Returns filed"
                value={operations.totals.returnsFiled.toLocaleString("en-PH")}
                hint={`${operations.totals.returnsApproved} approved · ${operations.totals.returnsRejected} rejected`}
              />
              <Stat
                label="Refunds settled"
                value={operations.totals.refundsSettled.toLocaleString("en-PH")}
                hint={`${operations.totals.refundsIssued} refund(s) issued`}
              />
              <Stat
                label="Support volume"
                value={operations.totals.messagesSent.toLocaleString("en-PH")}
                hint={`${operations.totals.requestsFiled} request(s) · ${operations.totals.disputesOpened} dispute(s)`}
              />
            </div>

            {operationDays.length === 0 ? (
              <p className="text-sm text-sand-500 dark:text-sand-400">
                No operational rows in this range yet. Run{" "}
                <code className="rounded bg-sand-100 px-1.5 py-0.5 text-xs dark:bg-night-800">
                  python manage.py rebuild_reporting
                </code>{" "}
                to derive them from the records.
              </p>
            ) : (
              <div className="max-h-96 overflow-y-auto">
                <Table>
                  <THead>
                    <TR>
                      <TH>Day</TH>
                      <TH className="text-right">Completed</TH>
                      <TH className="text-right">Delivered</TH>
                      <TH className="text-right">Returns</TH>
                      <TH className="text-right">Refunds</TH>
                      <TH className="text-right">Messages</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {operationDays.map((day) => (
                      <TR key={`ops-${day.day}`}>
                        <TD>{formatDay(day.day)}</TD>
                        <TD className="text-right tabular-nums">
                          {day.ordersCompleted}
                        </TD>
                        <TD className="text-right tabular-nums">
                          {day.shipmentsDelivered}
                        </TD>
                        <TD className="text-right tabular-nums">
                          {day.returnsFiled}
                        </TD>
                        <TD className="text-right tabular-nums">
                          {day.refundsSettled}
                        </TD>
                        <TD className="text-right tabular-nums">
                          {day.messagesSent}
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}
      {canSeeOperations && performance.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Seller performance</CardTitle>
            <CardDescription>
              Per-store operational totals for the range, busiest deliverer
              first. Only records that name a store slice are attributed to a
              store — a whole-order record belongs to the marketplace, not to
              one seller, and is never split to look busier than it was.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <THead>
                <TR>
                  <TH>Store</TH>
                  <TH className="text-right">Sent</TH>
                  <TH className="text-right">Delivered</TH>
                  <TH className="text-right">Returns filed</TH>
                  <TH className="text-right">Returns received</TH>
                  <TH className="text-right">Disputes</TH>
                  <TH className="text-right">Messages</TH>
                </TR>
              </THead>
              <TBody>
                {performance.map((row) => (
                  <TR key={`perf-${row.storeId}`}>
                    <TD className="font-medium text-sand-900 dark:text-sand-100">
                      {row.storeName}
                    </TD>
                    <TD className="text-right tabular-nums">
                      {row.shipmentsCreated}
                    </TD>
                    <TD className="text-right tabular-nums">
                      {row.shipmentsDelivered}
                    </TD>
                    <TD className="text-right tabular-nums">
                      {row.returnsFiled}
                    </TD>
                    <TD className="text-right tabular-nums">
                      {row.returnsReceived}
                    </TD>
                    <TD className="text-right tabular-nums">
                      {row.disputesOpened}
                    </TD>
                    <TD className="text-right tabular-nums">
                      {row.messagesSent}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
