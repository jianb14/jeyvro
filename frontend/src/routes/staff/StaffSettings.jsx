/**
 * Platform settings console (Phase 13.6) — the marketplace's operating
 * configuration in five auditable sections: marketplace identity,
 * commission, shipping defaults, feature switches, and the notification
 * defaults new accounts start with. Reads are §4-gated server-side to
 * administrator/finance/operations; edits are administrator-only except
 * commission (finance too). This page mirrors those groups so out-of-role
 * staff see read-only cards — the backend refuses regardless (UX, not
 * security). Money values stay server strings; nothing is recomputed here.
 */
import { useEffect, useState } from "react";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { Skeleton } from "../../components/ui/Skeleton";
import { Switch } from "../../components/ui/Switch";
import * as staffApi from "../../data/staff";
import { useAuth } from "../../features/auth/AuthContext";
import { requiredErrors } from "../../lib/formErrors";

// Server field_errors arrive snake_case; local state and Input error props
// use camelCase, so the bucket is translated once on the way in.
function camelErrors(fieldErrors = {}) {
  return Object.fromEntries(
    Object.entries(fieldErrors).map(([key, value]) => [
      key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase()),
      value,
    ])
  );
}

function Section({ title, description, notice, footer, children }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {notice}
        {children}
      </CardContent>
      <CardFooter>{footer}</CardFooter>
    </Card>
  );
}

export function StaffSettings() {
  const { user } = useAuth();
  const [settings, setSettings] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [busyCard, setBusyCard] = useState(null);
  const [notice, setNotice] = useState({});
  const [fieldErrors, setFieldErrors] = useState({});

  // The §4 matrix mirrored as UX: finance edits commission only, every
  // other write belongs to administrator. The server enforces both.
  const roles = user?.staff_roles ?? [];
  const canEditGeneral = roles.includes("administrator");
  const canEditCommission = canEditGeneral || roles.includes("finance");
  const readOnlyNote = "View only — your role cannot edit this section.";

  useEffect(() => {
    let alive = true;
    staffApi
      .fetchStaffSettings()
      .then((data) => {
        if (alive) setSettings(data);
      })
      .catch((err) => {
        if (alive) setLoadError(err.message);
      });
    return () => {
      alive = false;
    };
  }, []);

  if (loadError) {
    return (
      <Alert tone="danger" title="Could not load platform settings">
        {loadError}
      </Alert>
    );
  }
  if (!settings) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-9 w-56" />
        <Skeleton className="h-44 w-full" />
        <Skeleton className="h-44 w-full" />
        <Skeleton className="h-44 w-full" />
      </div>
    );
  }

  const set = (key) => (event) => {
    setSettings((current) => ({ ...current, [key]: event.target.value }));
    setFieldErrors((errors) => ({ ...errors, [key]: undefined }));
    setNotice({});
  };

  const setToggle = (key) => (value) => {
    setSettings((current) => ({ ...current, [key]: value }));
    setNotice({});
  };

  async function saveCard(card, required, save) {
    setNotice({});
    setFieldErrors({});
    // Client checks are UX only — the server validates every field again
    // (§10.1), and its field_errors land in the same bucket below.
    const missing = requiredErrors(settings, required);
    if (Object.keys(missing).length > 0) {
      setFieldErrors(missing);
      return;
    }
    setBusyCard(card);
    try {
      const updated = await save();
      setSettings(updated);
      setNotice({
        [card]: {
          tone: "success",
          title: "Saved",
          message: "The platform row is updated and the change is audit-logged.",
        },
      });
    } catch (err) {
      setNotice({
        [card]: {
          tone: "danger",
          title: "Could not save",
          message: err.data?.detail || err.data?.error || err.message,
        },
      });
      setFieldErrors(camelErrors(err.data?.field_errors));
    } finally {
      setBusyCard(null);
    }
  }

  const saveMarketplace = () =>
    saveCard("marketplace", ["platformName", "supportEmail"], () =>
      staffApi.updateStaffSettings({
        platform_name: settings.platformName,
        support_email: settings.supportEmail,
      })
    );

  const saveCommission = () =>
    saveCard("commission", ["commissionRatePercent"], () =>
      staffApi.updateStaffCommission({
        commission_rate_percent: settings.commissionRatePercent,
      })
    );

  const saveShipping = () =>
    saveCard("shipping", ["defaultShippingFlatFee"], () =>
      staffApi.updateStaffSettings({
        default_shipping_flat_fee: settings.defaultShippingFlatFee,
        default_free_shipping_threshold:
          settings.defaultFreeShippingThreshold === "" ||
          settings.defaultFreeShippingThreshold == null
            ? null
            : settings.defaultFreeShippingThreshold,
      })
    );

  const saveFeature = () =>
    saveCard("feature", ["paymentExpiryHours"], () =>
      staffApi.updateStaffSettings({
        cod_enabled: settings.codEnabled,
        payment_expiry_hours: Number(settings.paymentExpiryHours),
      })
    );

  const saveNotifications = () =>
    saveCard("notification", [], () =>
      staffApi.updateStaffSettings({
        default_order_updates_email: settings.defaultOrderUpdatesEmail,
        default_promotions_email: settings.defaultPromotionsEmail,
        default_messaging_email: settings.defaultMessagingEmail,
      })
    );

  const cardNotice = (card) =>
    notice[card] ? (
      <Alert tone={notice[card].tone} title={notice[card].title}>
        {notice[card].message}
      </Alert>
    ) : null;

  const saveButton = (card, handler, canEdit) =>
    canEdit ? (
      <Button onClick={handler} disabled={busyCard !== null}>
        {busyCard === card ? "Saving…" : "Save changes"}
      </Button>
    ) : (
      <span className="text-xs text-sand-500 dark:text-sand-400">
        {readOnlyNote}
      </span>
    );

  return (
    <div className="flex max-w-3xl flex-col gap-4">
      <div>
        <h2 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
          Platform settings
        </h2>
        <p className="mt-1 text-sm text-sand-500 dark:text-sand-400">
          Marketplace-wide configuration — one server row, every edit
          audited.
          {settings.updatedAt
            ? ` Last updated ${new Date(settings.updatedAt).toLocaleString()}${
                settings.updatedByEmail
                  ? ` by ${settings.updatedByEmail}`
                  : ""
              }.`
            : ""}
        </p>
      </div>

      <Section
        title="Marketplace"
        description="The storefront's public identity: the name shown in the footer and the support contact customers reach."
        notice={cardNotice("marketplace")}
        footer={saveButton("marketplace", saveMarketplace, canEditGeneral)}
      >
        <Input
          label="Platform name"
          name="platform_name"
          required
          maxLength={60}
          value={settings.platformName}
          onChange={set("platformName")}
          error={fieldErrors.platformName?.[0]}
          disabled={!canEditGeneral}
        />
        <Input
          label="Support email"
          name="support_email"
          type="email"
          value={settings.supportEmail}
          onChange={set("supportEmail")}
          error={fieldErrors.supportEmail?.[0]}
          disabled={!canEditGeneral}
          hint="Shown in the storefront footer as the contact for customer help."
        />
      </Section>

      <Section
        title="Commission"
        description="The platform's take per sale. Finance and administrators may adjust it; the rate is stored now and applied once the commission engine lands."
        notice={cardNotice("commission")}
        footer={saveButton("commission", saveCommission, canEditCommission)}
      >
        <Input
          label="Commission rate (%)"
          name="commission_rate_percent"
          type="number"
          min="0"
          max="100"
          step="0.01"
          required
          value={settings.commissionRatePercent}
          onChange={set("commissionRatePercent")}
          error={fieldErrors.commissionRatePercent?.[0]}
          disabled={!canEditCommission}
          hint="Between 0 and 100. Payouts and commission reporting consume this later."
        />
      </Section>

      <Section
        title="Shipping defaults"
        description="What a brand-new store starts with — sellers keep full control of their own store's values afterwards."
        notice={cardNotice("shipping")}
        footer={saveButton("shipping", saveShipping, canEditGeneral)}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Default flat fee (₱)"
            name="default_shipping_flat_fee"
            type="number"
            min="0"
            step="0.01"
            required
            value={settings.defaultShippingFlatFee}
            onChange={set("defaultShippingFlatFee")}
            error={fieldErrors.defaultShippingFlatFee?.[0]}
            disabled={!canEditGeneral}
          />
          <Input
            label="Default free-shipping threshold (₱)"
            name="default_free_shipping_threshold"
            type="number"
            min="0"
            step="0.01"
            value={settings.defaultFreeShippingThreshold ?? ""}
            onChange={set("defaultFreeShippingThreshold")}
            error={fieldErrors.defaultFreeShippingThreshold?.[0]}
            disabled={!canEditGeneral}
            hint="Leave empty for no threshold."
          />
        </div>
      </Section>

      <Section
        title="Feature switches"
        description="Live operational switches — they take effect on the very next request."
        notice={cardNotice("feature")}
        footer={saveButton("feature", saveFeature, canEditGeneral)}
      >
        <Switch
          checked={settings.codEnabled}
          onChange={setToggle("codEnabled")}
          disabled={!canEditGeneral}
          label="Cash on delivery"
          description="When off, checkout refuses COD: the option greys out and orders cannot be placed with it."
        />
        <Input
          label="Online payment window (hours)"
          name="payment_expiry_hours"
          type="number"
          min="1"
          max="168"
          step="1"
          required
          value={settings.paymentExpiryHours}
          onChange={set("paymentExpiryHours")}
          error={fieldErrors.paymentExpiryHours?.[0]}
          disabled={!canEditGeneral}
          hint="1–168 hours before an unpaid online payment expires and releases its stock."
        />
      </Section>

      <Section
        title="Notification defaults"
        description="The starting preferences for every new account. Existing customers keep their own choices — the platform never overwrites them."
        notice={cardNotice("notification")}
        footer={saveButton("notification", saveNotifications, canEditGeneral)}
      >
        <Switch
          checked={settings.defaultOrderUpdatesEmail}
          onChange={setToggle("defaultOrderUpdatesEmail")}
          disabled={!canEditGeneral}
          label="Order updates by default"
          description="Shipping and delivery emails new accounts start subscribed to."
        />
        <Switch
          checked={settings.defaultPromotionsEmail}
          onChange={setToggle("defaultPromotionsEmail")}
          disabled={!canEditGeneral}
          label="Promotions by default"
          description="Marketing emails new accounts start subscribed to."
        />
        <Switch
          checked={settings.defaultMessagingEmail}
          onChange={setToggle("defaultMessagingEmail")}
          disabled={!canEditGeneral}
          label="Messaging by default"
          description="Buyer–seller message emails new accounts start subscribed to."
        />
      </Section>
    </div>
  );
}



