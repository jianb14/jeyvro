/**
 * Staff campaign & promotion console (Phase 16.4) — /staff/campaigns.
 *
 * Two oversight views over the platform-wide promotion engine (§16.2):
 *
 * 1. Campaigns — the container (scope + window). Operations and administrators
 *    can open a marketplace-wide campaign here; the server fixes its scope to
 *    `platform` and writes the `campaign.created` audit row, so a caller can
 *    never attach a store or skip the trail.
 * 2. Promotions — every rule across every store, active or not. This is
 *    oversight, not the public feed: a switched-off rule stays listed so
 *    operations can see what is off (the storefront never shows it).
 *
 * The console writes and reads only; it never computes a discount — every
 * number rendered here is the server's own (marketplace rule 1).
 */
import { useCallback, useEffect, useState } from "react";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Checkbox } from "../../components/ui/Checkbox";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Skeleton } from "../../components/ui/Skeleton";
import { Tabs, TabPanel } from "../../components/ui/Tabs";
import { Table, TBody, TD, TH, THead, TR } from "../../components/ui/Table";
import { useToast } from "../../components/ui/ToastProvider";
import { MegaphoneIcon, PercentIcon, PlusIcon } from "../../components/ui/Icons";
import { useAuth } from "../../features/auth/AuthContext";
import * as promotionsApi from "../../data/promotions";

const KIND_LABELS = {
  flash_sale: "Flash sale",
  product_discount: "Product discount",
  bundle: "Bundle",
  free_shipping: "Free shipping",
  buy_x_get_y: "Buy X get Y",
};

const EMPTY_FORM = { name: "", description: "", startsAt: "", endsAt: "", isActive: true };

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
  return value ? new Date(value).toLocaleDateString("en-PH", { dateStyle: "medium" }) : "—";
}

/** The stored window, as the server has it (no client-side clock logic). */
function describeWindow(row) {
  if (row.startsAt && row.endsAt) return `${formatDay(row.startsAt)} → ${formatDay(row.endsAt)}`;
  if (row.endsAt) return `Until ${formatDay(row.endsAt)}`;
  if (row.startsAt) return `From ${formatDay(row.startsAt)}`;
  return "Always on";
}

/** One rule line: the server's value plus its qualifiers. */
function describeRule(promo) {
  const base =
    promo.discountType === "percentage" ? `${promo.value}% off` : `${formatP(promo.value)} off`;
  const conditions = [];
  if (promo.minSpend > 0) conditions.push(`min. spend ${formatP(promo.minSpend)}`);
  if (promo.kind === "buy_x_get_y" && promo.buyQty && promo.getQty) {
    conditions.push(`buy ${promo.buyQty} get ${promo.getQty}`);
  }
  return conditions.length ? `${base} · ${conditions.join(" · ")}` : base;
}

export function StaffCampaigns() {
  const { push } = useToast();
  const { user } = useAuth();
  // Campaign *management* is operations/administrator; promotion *oversight*
  // is wider (finance included). A role that may only oversee lands on the
  // promotions tab and never sees a control it would be refused for (§4).
  const roles = user?.staff_roles ?? [];
  const canManageCampaigns = roles.some((role) =>
    ["operations", "administrator", "super_administrator"].includes(role)
  );
  const [tab, setTab] = useState(canManageCampaigns ? "campaigns" : "promotions");
  const [campaigns, setCampaigns] = useState(null);
  const [promotions, setPromotions] = useState(null);
  const [error, setError] = useState(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    // The two consoles have different §4 gates: promotions oversight is open to
    // finance too, campaign management is not. Loading both unconditionally
    // would hand a finance operator a 403 on a page they may legitimately
    // enter, so each list is fetched only when the role may read it.
    const mayManage = canManageCampaigns;
    const jobs = [promotionsApi.fetchStaffPromotions()];
    if (mayManage) jobs.push(promotionsApi.fetchStaffCampaigns());
    Promise.all(jobs)
      .then((results) => {
        if (cancelled) return;
        setPromotions(results[0]);
        setCampaigns(mayManage ? results[1] : []);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setCampaigns([]);
        setPromotions([]);
        setError(err.data?.detail || err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [canManageCampaigns]);

  useEffect(load, [load]);

  const setField = (field) => (event) =>
    setForm((current) => ({ ...current, [field]: event.target.value }));

  const submitCreate = async (event) => {
    event.preventDefault();
    setSaving(true);
    setFormError(null);
    try {
      const created = await promotionsApi.createStaffCampaign({
        name: form.name.trim(),
        description: form.description.trim(),
        // Blank dates are omitted, not sent empty, so the server keeps the
        // campaign always-on rather than failing on an empty string.
        startsAt: form.startsAt || undefined,
        endsAt: form.endsAt || undefined,
        isActive: form.isActive,
      });
      setCreating(false);
      setForm(EMPTY_FORM);
      push({
        tone: "success",
        title: "Campaign created",
        description: `${created.name} is ${created.isActive ? "live" : "saved inactive"}.`,
      });
      // Re-read rather than splice: the server owns ids, counts, and the audit
      // trail, so a fresh read is the honest state after a write.
      load();
    } catch (err) {
      setFormError(err.data?.detail || err.message);
    } finally {
      setSaving(false);
    }
  };

  const loading = campaigns === null || promotions === null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-sand-900 dark:text-sand-100">
            Campaigns &amp; promotions
          </h1>
          <p className="mt-1 text-sm text-sand-500 dark:text-sand-400">
            Platform-wide campaigns and the rules inside them, across every store.
          </p>
        </div>
        {tab === "campaigns" && canManageCampaigns && (
          <Button leadingIcon={PlusIcon} onClick={() => setCreating(true)}>
            New campaign
          </Button>
        )}
      </div>

      {error && (
        <Alert tone="danger" title="Could not load the promotion console">
          {error}{" "}
          <button type="button" onClick={load} className="font-medium underline">
            Try again
          </button>
        </Alert>
      )}

      {loading ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : (
        <Tabs
          tabs={[
            ...(canManageCampaigns
              ? [
                  {
                    id: "campaigns",
                    label: `Campaigns (${campaigns.length})`,
                    icon: MegaphoneIcon,
                  },
                ]
              : []),
            { id: "promotions", label: `Promotions (${promotions.length})`, icon: PercentIcon },
          ]}
          defaultTab={canManageCampaigns ? "campaigns" : "promotions"}
          onChange={setTab}
        />
      )}


      {loading ? null : tab === "campaigns" ? (
        <TabPanel className="pt-0">
          {campaigns.length === 0 ? (
            <EmptyState
              icon={MegaphoneIcon}
              title="No campaigns yet"
              description="Open a marketplace-wide campaign to group promotions under one window."
              action={<Button onClick={() => setCreating(true)}>New campaign</Button>}
            />
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>Campaign</TH>
                  <TH>Scope</TH>
                  <TH>Rules</TH>
                  <TH>Window</TH>
                  <TH>Status</TH>
                </TR>
              </THead>
              <TBody>
                {campaigns.map((campaign) => (
                  <TR key={campaign.id}>
                    <TD>
                      <span className="font-medium text-sand-900 dark:text-sand-100">
                        {campaign.name}
                      </span>
                      {campaign.description && (
                        <span className="mt-0.5 block text-xs text-sand-500 dark:text-sand-400">
                          {campaign.description}
                        </span>
                      )}
                    </TD>
                    <TD>
                      <Badge tone={campaign.scope === "platform" ? "moss" : "info"} size="sm">
                        {campaign.scope === "platform" ? "Platform" : campaign.storeName || "Store"}
                      </Badge>
                    </TD>
                    <TD className="tabular-nums">{campaign.promotionCount}</TD>
                    <TD className="whitespace-nowrap text-sand-500 dark:text-sand-400">
                      {describeWindow(campaign)}
                    </TD>
                    <TD>
                      <Badge tone={campaign.isActive ? "moss" : "neutral"} size="sm">
                        {campaign.isActive ? "Active" : "Inactive"}
                      </Badge>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </TabPanel>
      ) : (
        <TabPanel className="pt-0">
          {promotions.length === 0 ? (
            <EmptyState
              icon={PercentIcon}
              title="No promotions yet"
              description="Stores create their own rules from the seller desk; they all surface here for oversight."
            />
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>Rule</TH>
                  <TH>Store</TH>
                  <TH>Campaign</TH>
                  <TH>Offer</TH>
                  <TH>Status</TH>
                </TR>
              </THead>
              <TBody>
                {promotions.map((promo) => (
                  <TR key={promo.id}>
                    <TD>
                      <span className="font-medium text-sand-900 dark:text-sand-100">
                        {promo.label || promo.name}
                      </span>
                      <span className="mt-0.5 block text-xs text-sand-500 dark:text-sand-400">
                        {KIND_LABELS[promo.kind] || promo.kind}
                      </span>
                    </TD>
                    <TD className="text-sand-500 dark:text-sand-400">{promo.storeName || "Platform"}</TD>
                    <TD className="text-sand-500 dark:text-sand-400">{promo.campaignName || "—"}</TD>
                    <TD className="whitespace-nowrap text-sand-500 dark:text-sand-400">
                      {describeRule(promo)}
                    </TD>
                    <TD>
                      <Badge tone={promo.isActive ? "moss" : "neutral"} size="sm">
                        {promo.isActive ? "Active" : "Inactive"}
                      </Badge>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </TabPanel>
      )}


      <Modal
        open={creating}
        onClose={() => setCreating(false)}
        title="New platform campaign"
        description="Marketplace-wide by default — it is never attached to a single store."
        footer={
          <>
            <Button variant="ghost" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button type="submit" form="campaign-form" loading={saving}>
              Create campaign
            </Button>
          </>
        }
      >
        {formError && (
          <Alert tone="danger" title="Could not create the campaign" className="mb-4">
            {formError}
          </Alert>
        )}
        <form id="campaign-form" className="flex flex-col gap-4" onSubmit={submitCreate}>
          <Input
            label="Name"
            required
            maxLength={120}
            value={form.name}
            onChange={setField("name")}
            placeholder="Harvest sale"
            hint="How the campaign reads across the marketplace."
          />
          <Input
            label="Description"
            value={form.description}
            onChange={setField("description")}
            placeholder="September marketplace-wide promo."
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Starts at"
              type="datetime-local"
              value={form.startsAt}
              onChange={setField("startsAt")}
            />
            <Input
              label="Ends at"
              type="datetime-local"
              value={form.endsAt}
              onChange={setField("endsAt")}
            />
          </div>
          <Checkbox
            label="Start it now"
            description="Leave it off to save the campaign and switch it on later."
            checked={form.isActive}
            onChange={(event) =>
              setForm((current) => ({ ...current, isActive: event.target.checked }))
            }
          />
        </form>
      </Modal>
    </div>
  );
}

