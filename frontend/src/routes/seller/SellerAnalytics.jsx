/**
 * Seller analytics (Phase 19.2) — /seller/analytics.
 *
 * Every figure on this page is served by the reporting aggregates (§6 v1.16):
 * the page renders what `rebuild_reporting` derived and never re-derives a
 * number of its own (marketplace-sellers rule 5). The store is resolved from
 * the session server-side — there is no id on this page to forge — which is
 * also why this page exists beside the Phase 12 dashboard rather than inside
 * it: rule 4 keeps `/seller` untouched (documented deferral, ROADMAP §19.2).
 *
 * Two grains sit side by side. The period metrics (sales, orders, best
 * sellers, voucher and review activity) come from the rollups; the inventory
 * block is a **live snapshot** of current stock, labeled as one because stock
 * is present state, not a period figure.
 *
 * Bars are pure presentation: a day's width is the server's own number scaled
 * against the busiest day in the same series, never a figure the client
 * invented.
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
import * as sellerApi from "../../data/seller";

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

/** A compact label/value pair inside a detail card. */
function Figure({ label, value }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-sand-500 dark:text-sand-400">
        {label}
      </p>
      <p className="mt-1 font-display text-lg font-semibold tabular-nums text-sand-900 dark:text-sand-100">
        {value}
      </p>
    </div>
  );
}

export function SellerAnalytics() {
  const [range, setRange] = useState("30");
  const [analytics, setAnalytics] = useState(null);
  // `loaded`, not `loading`, and only ever flipped inside the request's own
  // callbacks: a range change keeps the last figures on screen rather than
  // blanking the page back to a skeleton (same convention as StaffAnalytics).
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    sellerApi
      .fetchSellerAnalytics({ ...windowFor(range), limit: 10 })
      .then((next) => {
        if (cancelled) return;
        setAnalytics(next);
        setError(null);
        setLoaded(true);
      })
      .catch((err) => {
        if (cancelled) return;
        setAnalytics(null);
        setError(err.data?.detail || err.message);
        setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [range]);

  useEffect(load, [load]);

  // The series arrives oldest first; a dashboard reads newest first.
  const days = useMemo(() => [...(analytics?.days ?? [])].reverse(), [analytics]);
  const busiest = useMemo(
    () => Math.max(1, ...days.map((day) => Number(day.grossSales))),
    [days]
  );

  if (!loaded) {
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

  const totals = analytics?.totals;
  const inventory = analytics?.inventory;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
            Analytics
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-sand-500 dark:text-sand-400">
            Your store's figures served from the reporting aggregates — the same
            rollups staff read, scoped to your store by the session. The
            dashboard keeps its operational view; this page is the numbers.
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

      {error ? (
        <Alert tone="danger" title="Could not load analytics">
          {error}
        </Alert>
      ) : null}

      {totals ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            label="Gross sales"
            value={formatP(totals.grossSales)}
            hint={`${totals.unitsSold} unit(s) sold in range`}
          />
          <Stat
            label="Revenue"
            value={formatP(totals.revenue)}
            hint={`${formatP(totals.capturedTotal)} collected − ${formatP(
              totals.refundedTotal
            )} refunded`}
          />
          <Stat
            label="Orders"
            value={totals.ordersCount.toLocaleString("en-PH")}
            hint={`${totals.productsSold} product(s) sold`}
          />
          <Stat
            label="Store rating"
            value={totals.reviewRatingAvg ? `${totals.reviewRatingAvg} ★` : "No rating yet"}
            hint={`${totals.reviewsCount} review(s) · ${totals.voucherRedemptions} voucher order(s)`}
          />
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Daily activity</CardTitle>
          <CardDescription>
            What was ordered and what money moved, day by day —{" "}
            {formatDay(analytics?.start)} to {formatDay(analytics?.end)}. Days
            with no activity carry no row; the rollup only records what the
            records support.
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
                    <TH className="text-right">Units</TH>
                    <TH className="text-right">Gross sales</TH>
                    <TH className="text-right">Reviews</TH>
                    <TH>Gross sales</TH>
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
                        {day.unitsSold}
                      </TD>
                      <TD className="text-right tabular-nums">
                        {formatP(day.grossSales)}
                      </TD>
                      <TD className="text-right tabular-nums">
                        {day.reviewsCount}
                      </TD>
                      <TD>
                        <span
                          className="block h-1.5 min-w-[2px] rounded-full bg-moss-500 dark:bg-moss-400"
                          style={{
                            width: `${Math.round(
                              (Number(day.grossSales) / busiest) * 100
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

      <Card>
        <CardHeader>
          <CardTitle>Best sellers</CardTitle>
          <CardDescription>
            Your products by units sold over the range — the store-scoped slice
            of the same product activity staff see, ordered units first.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {(analytics?.topProducts ?? []).length === 0 ? (
            <p className="px-6 pb-6 text-sm text-sand-500 dark:text-sand-400">
              No product sales in this range yet.
            </p>
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>Product</TH>
                  <TH className="text-right">Units</TH>
                  <TH className="text-right">Orders</TH>
                  <TH className="text-right">Merchandise</TH>
                </TR>
              </THead>
              <TBody>
                {(analytics?.topProducts ?? []).map((row) => (
                  <TR key={row.productId}>
                    <TD className="font-medium">{row.productTitle}</TD>
                    <TD className="text-right tabular-nums">{row.unitsSold}</TD>
                    <TD className="text-right tabular-nums">
                      {row.ordersCount}
                    </TD>
                    <TD className="text-right tabular-nums">
                      {formatP(row.merchandise)}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Voucher performance</CardTitle>
            <CardDescription>
              Vouchers redeemed on your products in range. The discount is the
              order-level amount apportioned to your store; your own share of
              the funding is shown beside it.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3">
            <Figure
              label="Redemptions"
              value={totals ? totals.voucherRedemptions : 0}
            />
            <Figure
              label="Discount"
              value={totals ? formatP(totals.voucherDiscount) : formatP(0)}
            />
            <Figure
              label="Your share"
              value={totals ? formatP(totals.voucherSellerShare) : formatP(0)}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Customer voice</CardTitle>
            <CardDescription>
              Published reviews of your products in range — hidden and flagged
              rows stay out of the figures exactly as they stay off the public
              list.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3">
            <Figure label="Reviews" value={totals ? totals.reviewsCount : 0} />
            <Figure
              label="Average rating"
              value={
                totals && totals.reviewRatingAvg
                  ? `${totals.reviewRatingAvg} ★`
                  : "—"
              }
            />
            <Figure
              label="Rating sum"
              value={totals ? totals.reviewsRatingSum : "0.00"}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Inventory now</CardTitle>
            <CardDescription>
              A live snapshot of your stock, not a period figure — low stock is
              a variant whose available units sit at or below its own
              threshold.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3">
            <Figure
              label="Variants"
              value={inventory ? inventory.variantsTracked : 0}
            />
            <Figure
              label="Low / out"
              value={inventory
                ? `${inventory.lowStockCount} / ${inventory.outOfStockCount}`
                : "0 / 0"}
            />
            <Figure
              label="Units on hand"
              value={inventory ? inventory.unitsOnHand : 0}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

