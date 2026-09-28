/**
 * Seller promotions desk (Phase 16.4) — /seller/promotions.
 *
 * Sellers describe the promotions the checkout engine applies on its own
 * (§16.2): this page writes the rule and the platform decides eligibility on
 * every cart — no discount is ever computed here. Deactivating is a switch,
 * never a delete, because orders keep pointing at the promotion that priced
 * them, and every change lands in the audit trail.
 */
import { useCallback, useEffect, useState } from "react";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Checkbox } from "../../components/ui/Checkbox";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Switch } from "../../components/ui/Switch";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { PercentIcon } from "../../components/ui/Icons";
import * as promotionsApi from "../../data/promotions";

const KINDS = [
  { value: "flash_sale", label: "Flash sale" },
  { value: "product_discount", label: "Product discount" },
  { value: "bundle", label: "Bundle" },
  { value: "free_shipping", label: "Free shipping" },
  { value: "buy_x_get_y", label: "Buy X get Y" },
];

const KIND_LABELS = Object.fromEntries(KINDS.map(({ value, label }) => [value, label]));

const EMPTY_FORM = {
  name: "",
  kind: "flash_sale",
  discountType: "percentage",
  value: "",
  minSpend: "",
  minQty: "1",
  isActive: true,
};

function formatP(n) {
  return "₱" + Number(n).toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDay(value) {
  return new Date(value).toLocaleDateString("en-PH", { dateStyle: "medium" });
}

/** The stored window, as the server has it (no client-side clock logic). */
function describeWindow(promo) {
  if (promo.startsAt && promo.endsAt) {
    return `${formatDay(promo.startsAt)} → ${formatDay(promo.endsAt)}`;
  }
  if (promo.startsAt) return `From ${formatDay(promo.startsAt)}`;
  if (promo.endsAt) return `Until ${formatDay(promo.endsAt)}`;
  return "Always on";
}

/** One line per rule: the server's own value plus its qualifiers. */
function describePromotion(promo) {
  const base =
    promo.discountType === "percentage"
      ? `${promo.value}% off`
      : `${formatP(promo.value)} off`;
  const conditions = [];
  if (promo.minSpend > 0) conditions.push(`min. spend ${formatP(promo.minSpend)}`);
  if (promo.minQty > 1) conditions.push(`${promo.minQty}+ items`);
  return conditions.length ? `${base} · ${conditions.join(" · ")}` : base;
}

export function SellerPromotions() {
  const [promotions, setPromotions] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [confirming, setConfirming] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    promotionsApi
      .fetchSellerPromotions()
      .then((items) => {
        if (!cancelled) {
          setPromotions(items);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.data?.detail || err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(load, [load]);

  const setField = (key) => (event) =>
    setForm((current) => ({ ...current, [key]: event.target.value }));

  function openCreate() {
    setForm(EMPTY_FORM);
    setNotice(null);
    setCreating(true);
  }

  const replacePromotion = (updated) =>
    setPromotions((current) =>
      (current ?? []).map((promo) => (promo.id === updated.id ? updated : promo))
    );

  async function submitCreate(event) {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    try {
      const created = await promotionsApi.createSellerPromotion({
        name: form.name.trim(),
        kind: form.kind,
        discountType: form.discountType,
        value: Number(form.value) || 0,
        minSpend: Number(form.minSpend) || 0,
        minQty: Number(form.minQty) || 1,
        isActive: form.isActive,
      });
      setPromotions((current) => [created, ...(current ?? [])]);
      setCreating(false);
      setNotice({
        tone: "success",
        message: `“${created.label || created.name}” is live — qualifying carts get the discount automatically.`,
      });
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(promo, isActive) {
    setBusyId(promo.id);
    setNotice(null);
    try {
      replacePromotion(await promotionsApi.setSellerPromotionActive(promo.id, isActive));
      setNotice({
        tone: "success",
        message: isActive
          ? `“${promo.label || promo.name}” is applying again.`
          : `“${promo.label || promo.name}” paused.`,
      });
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusyId(null);
    }
  }

  async function deactivate() {
    if (!confirming) return;
    const promo = confirming;
    setBusyId(promo.id);
    setNotice(null);
    try {
      await promotionsApi.deactivateSellerPromotion(promo.id);
      replacePromotion({ ...promo, isActive: false });
      setConfirming(null);
      setNotice({
        tone: "success",
        message: `“${promo.label || promo.name}” deactivated — it no longer prices any cart.`,
      });
    } catch (err) {
      setNotice({ tone: "danger", message: err.data?.detail || err.message });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
            Promotions
          </h1>
          <p className="text-sm text-sand-500 dark:text-sand-400">
            Deals Jeyvro applies to qualifying carts on its own. You name the
            rule; the platform judges every cart and prices the discount.
          </p>
        </div>
        <Button onClick={openCreate}>New promotion</Button>
      </header>

      {notice && (
        <Alert tone={notice.tone} onDismiss={() => setNotice(null)}>
          {notice.message}
        </Alert>
      )}
      {error && (
        <Alert tone="danger" title="Could not load promotions">
          {error}
        </Alert>
      )}

      {!promotions ? (
        <Skeleton className="h-72 w-full" />
      ) : promotions.length === 0 ? (
        <EmptyState
          icon={PercentIcon}
          title="No promotions yet"
          description="Create a store-wide deal — a percentage or an amount off — and Jeyvro starts applying it to qualifying carts."
          action={<Button onClick={openCreate}>Create your first promotion</Button>}
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Promotion</TH>
              <TH>Kind</TH>
              <TH>Rule</TH>
              <TH>Window</TH>
              <TH>Active</TH>
              <TH className="text-right">Actions</TH>
            </TR>
          </THead>
          <TBody>
            {promotions.map((promo) => (
              <TR key={promo.id}>
                <TD>
                  <span className="font-medium text-sand-900 dark:text-sand-100">
                    {promo.label || promo.name}
                  </span>
                  {promo.campaignName && promo.campaignName !== promo.label && (
                    <p className="text-xs text-sand-500 dark:text-sand-400">
                      {promo.campaignName}
                    </p>
                  )}
                </TD>
                <TD>
                  <Badge tone="moss" size="sm">
                    {KIND_LABELS[promo.kind] || promo.kind}
                  </Badge>
                </TD>
                <TD className="tabular-nums">{describePromotion(promo)}</TD>
                <TD className="text-xs">{describeWindow(promo)}</TD>
                <TD>
                  <Switch
                    size="sm"
                    checked={promo.isActive}
                    disabled={busyId === promo.id}
                    onChange={(next) => toggleActive(promo, next)}
                  />
                </TD>
                <TD>
                  <div className="flex justify-end">
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={!promo.isActive || busyId === promo.id}
                      onClick={() => setConfirming(promo)}
                    >
                      Deactivate
                    </Button>
                  </div>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      <p className="text-xs leading-relaxed text-sand-500 dark:text-sand-400">
        Voucher codes are issued by Jeyvro staff, not by stores — the rules
        above apply on their own, and every change is written to the audit
        trail.
      </p>

      <Modal
        open={creating}
        onClose={() => setCreating(false)}
        title="New promotion"
        description="Applies store-wide. Jeyvro recomputes the discount on every cart — never from this form."
        footer={
          <>
            <Button variant="ghost" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button type="submit" form="promotion-form" loading={saving}>
              Create promotion
            </Button>
          </>
        }
      >
        <form id="promotion-form" className="flex flex-col gap-4" onSubmit={submitCreate}>
          <Input
            label="Name"
            required
            maxLength={120}
            value={form.name}
            onChange={setField("name")}
            placeholder="Weekend flash sale"
            hint="Becomes the offer's public label on the storefront."
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Select label="Kind" value={form.kind} onChange={setField("kind")}>
              {KINDS.map((kind) => (
                <option key={kind.value} value={kind.value}>
                  {kind.label}
                </option>
              ))}
            </Select>
            <Select
              label="Discount type"
              value={form.discountType}
              onChange={setField("discountType")}
            >
              <option value="percentage">Percentage off</option>
              <option value="fixed">Amount off</option>
            </Select>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <Input
              label={form.discountType === "percentage" ? "Percent off" : "Amount off (₱)"}
              type="number"
              min="0"
              step={form.discountType === "percentage" ? "1" : "0.01"}
              max={form.discountType === "percentage" ? "100" : undefined}
              required
              value={form.value}
              onChange={setField("value")}
            />
            <Input
              label="Min. spend (₱)"
              type="number"
              min="0"
              step="0.01"
              value={form.minSpend}
              onChange={setField("minSpend")}
            />
            <Input
              label="Min. items"
              type="number"
              min="1"
              step="1"
              value={form.minQty}
              onChange={setField("minQty")}
            />
          </div>
          <Checkbox
            label="Start applying immediately"
            description="Leave it off to save the rule now and switch it on later."
            checked={form.isActive}
            onChange={(event) =>
              setForm((current) => ({ ...current, isActive: event.target.checked }))
            }
          />
        </form>
      </Modal>

      <Modal
        open={Boolean(confirming)}
        onClose={() => setConfirming(null)}
        title="Deactivate this promotion?"
        description="It stops pricing carts straight away; orders already placed keep the discount they were given."
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirming(null)}>
              Keep it active
            </Button>
            <Button
              variant="destructive"
              loading={busyId === confirming?.id}
              onClick={deactivate}
            >
              Deactivate
            </Button>
          </>
        }
      >
        <p className="text-sm text-sand-600 dark:text-sand-300">
          {confirming ? describePromotion(confirming) : ""}
        </p>
      </Modal>
    </div>
  );
}
