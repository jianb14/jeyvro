/**
 * Voucher Center (Phase 16.4) — /vouchers.
 *
 * The browse-side home for every active code on the marketplace, platform and
 * store alike. It is a *browse* surface, not a redemption surface: the page
 * copies a code and nothing more. Eligibility, the spend floor, the discount
 * math, and the "you already used this" refusals all stay server-side
 * (§16.1 — the client never decides whether a voucher applies), so nothing here
 * calculates a discount; the card renders the rule the server published and
 * checkout re-decides it against the live cart.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Navbar } from "../components/layout/Navbar";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Breadcrumb } from "../components/ui/Breadcrumb";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { Skeleton } from "../components/ui/Skeleton";
import { Tabs } from "../components/ui/Tabs";
import { useToast } from "../components/ui/ToastProvider";
import { CopyIcon, TagIcon } from "../components/ui/Icons";
import * as promotionsApi from "../data/promotions";

const SCOPES = [
  { id: "all", label: "All vouchers" },
  { id: "platform", label: "Platform" },
  { id: "seller", label: "Store" },
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
  return new Date(value).toLocaleDateString("en-PH", { dateStyle: "medium" });
}

/**
 * The headline saving, spelled from the server's own two numbers. A percentage
 * code renders its percentage; a fixed code renders its peso amount. This is
 * formatting of server truth, not a discount calculation.
 */
function describeValue(voucher) {
  return voucher.discountType === "percentage"
    ? `${voucher.value}% OFF`
    : `${formatP(voucher.value)} OFF`;
}

/** The qualifiers that decide whether this code is usable at all. */
function describeConditions(voucher) {
  const conditions = [];
  if (voucher.minSpend > 0) conditions.push(`Min. spend ${formatP(voucher.minSpend)}`);
  if (voucher.maxDiscount !== null) conditions.push(`Up to ${formatP(voucher.maxDiscount)} off`);
  if (voucher.firstOrderOnly) conditions.push("First order only");
  return conditions;
}

/** The stored window as the server has it — no countdown math on the client. */
function describeWindow(voucher) {
  if (voucher.startsAt && voucher.endsAt) {
    return `${formatDay(voucher.startsAt)} → ${formatDay(voucher.endsAt)}`;
  }
  if (voucher.endsAt) return `Ends ${formatDay(voucher.endsAt)}`;
  if (voucher.startsAt) return `Starts ${formatDay(voucher.startsAt)}`;
  return "Always on";
}

/** One code: the rule the server published, plus the code to copy. */
function VoucherCard({ voucher, onCopy, copied }) {
  const conditions = describeConditions(voucher);
  return (
    <li className="flex flex-col gap-4 rounded-2xl border border-sand-200 bg-white p-5 dark:border-night-800 dark:bg-night-900">
      <div className="flex items-start justify-between gap-3">
        <p className="font-display text-2xl font-semibold text-moss-700 dark:text-moss-300">
          {describeValue(voucher)}
        </p>
        <Badge tone={voucher.scope === "platform" ? "moss" : "info"} size="sm">
          {voucher.scope === "platform" ? "Platform" : "Store"}
        </Badge>
      </div>

      <div className="min-w-0">
        <p className="truncate font-medium text-sand-900 dark:text-sand-100">{voucher.title}</p>
        {voucher.description && (
          <p className="mt-0.5 line-clamp-2 text-sm text-sand-500 dark:text-sand-400">
            {voucher.description}
          </p>
        )}
      </div>

      {voucher.storeSlug && (
        <Link
          to={`/store/${voucher.storeSlug}`}
          className="truncate text-sm font-medium text-moss-700 hover:underline dark:text-moss-300"
        >
          {voucher.storeName}
        </Link>
      )}

      {conditions.length > 0 && (
        <ul className="flex flex-col gap-1">
          {conditions.map((condition) => (
            <li key={condition} className="text-xs text-sand-500 dark:text-sand-400">
              {condition}
            </li>
          ))}
        </ul>
      )}

      <p className="text-xs text-sand-400 dark:text-sand-500">{describeWindow(voucher)}</p>

      <div className="mt-auto flex items-center gap-2 pt-2">
        <code className="min-w-0 flex-1 truncate rounded-lg border border-dashed border-sand-300 bg-sand-50 px-3 py-2 font-mono text-sm uppercase tracking-wider text-sand-800 dark:border-night-700 dark:bg-night-950 dark:text-sand-100">
          {voucher.code}
        </code>
        <Button
          variant="outline"
          size="sm"
          leadingIcon={CopyIcon}
          loading={copied}
          onClick={() => onCopy(voucher)}
        >
          Copy
        </Button>
      </div>
    </li>
  );
}


export function Vouchers() {
  const { push } = useToast();
  const [vouchers, setVouchers] = useState(null);
  const [error, setError] = useState(null);
  const [scope, setScope] = useState("all");
  const [copiedId, setCopiedId] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    promotionsApi
      .fetchPublicVouchers()
      .then((items) => {
        if (!cancelled) {
          setVouchers(items);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setVouchers([]);
          setError(err.data?.detail || err.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(load, [load]);

  // The whole list is fetched once and filtered here; the scope is a browser
  // convenience, not a query, so switching tabs never re-requests.
  const visible = useMemo(() => {
    if (!vouchers) return [];
    if (scope === "all") return vouchers;
    return vouchers.filter((voucher) => voucher.scope === scope);
  }, [vouchers, scope]);

  const copy = async (voucher) => {
    try {
      await navigator.clipboard.writeText(voucher.code);
      setCopiedId(voucher.id);
      push({
        tone: "success",
        title: "Voucher code copied",
        description: `${voucher.code} is ready to paste at checkout.`,
      });
    } catch {
      push({
        tone: "danger",
        title: "Could not copy the code",
        description: `Copy it by hand: ${voucher.code}`,
      });
    }
  };

  return (
    <div className="min-h-dvh bg-sand-50 dark:bg-night-950">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 pb-24 pt-6 sm:px-6 lg:px-8">
        <Breadcrumb className="mb-6" items={[{ label: "Home", to: "/" }, { label: "Vouchers" }]} />

        <div className="mb-6">
          <h1 className="font-display text-2xl font-semibold tracking-tight text-sand-900 dark:text-sand-100 sm:text-3xl">
            Voucher center
          </h1>
          <p className="mt-1 text-sm text-sand-500 dark:text-sand-400">
            Every active code on the marketplace. Copy one and paste it at checkout — we
            check it against your cart.
          </p>
        </div>

        {error && (
          <Alert tone="danger" title="Could not load vouchers" className="mb-6">
            {error}{" "}
            <button type="button" onClick={load} className="font-medium underline">
              Try again
            </button>
          </Alert>
        )}

        {vouchers === null && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-44 rounded-2xl" />
            ))}
          </div>
        )}

        {vouchers !== null && (
          <>
            <Tabs tabs={SCOPES} defaultTab="all" onChange={setScope} className="mb-6" />

            {visible.length === 0 ? (
              <EmptyState
                icon={TagIcon}
                title={vouchers.length === 0 ? "No vouchers on offer yet" : "Nothing in this tab"}
                description={
                  vouchers.length === 0
                    ? "When the marketplace or a store issues a code, it shows up here."
                    : "Try another tab — there are codes in the others."
                }
                action={
                  <Link to="/products">
                    <Button variant="outline">Browse products</Button>
                  </Link>
                }
              />
            ) : (
              <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {visible.map((voucher) => (
                  <VoucherCard
                    key={voucher.id}
                    voucher={voucher}
                    onCopy={copy}
                    copied={copiedId === voucher.id}
                  />
                ))}
              </ul>
            )}
          </>
        )}
      </main>
    </div>
  );
}

