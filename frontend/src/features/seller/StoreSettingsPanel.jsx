/**
 * Store settings feature (Phase 4.3) — the seller edits their own store
 * profile/policies/contact. Status is API truth, displayed read-only
 * (transitions are staff-only, §6 v1.2).
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Skeleton } from "../../components/ui/Skeleton";
import { Textarea } from "../../components/ui/Textarea";
import * as storesApi from "../../data/stores";

const STATUS_TONES = {
  active: "success",
  pending: "warning",
  suspended: "danger",
};

export function StoreSettingsPanel() {
  const [store, setStore] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    storesApi
      .fetchMyStore()
      .then((data) => {
        if (!cancelled) setStore(data);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loadError) {
    return <Alert tone="danger" title="Could not load your store">{loadError}</Alert>;
  }
  if (!store) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-10 w-1/2" />
      </div>
    );
  }

  const set = (key) => (event) => {
    const { value } = event.target;
    setStore((s) => ({ ...s, [key]: value }));
    setSaved(false);
  };

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await storesApi.updateMyStore({
        name: store.name,
        description: store.description,
        logo_url: store.logo_url,
        banner_url: store.banner_url,
        contact_phone: store.contact_phone,
        return_policy: store.return_policy,
        shipping_policy: store.shipping_policy,
      });
      setStore(updated);
      setSaved(true);
    } catch (err) {
      setError(err.data?.detail || err.data?.error || err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <div className="mb-4 flex items-center gap-3">
        <Badge tone={STATUS_TONES[store.status] || "neutral"} variant="soft">
          {store.status}
        </Badge>
        {store.status === "active" && (
          <Link
            to={`/store/${store.slug}`}
            className="text-sm font-medium text-moss-700 hover:underline dark:text-moss-300"
          >
            View public storefront →
          </Link>
        )}
      </div>
      {saved && <Alert tone="success" title="Store settings saved" className="mb-4" />}
      {error && <Alert tone="danger" title="Could not save store" className="mb-4">{error}</Alert>}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input label="Store name" required maxLength={128} value={store.name} onChange={set("name")} />
        <Textarea
          label="Description"
          rows={3}
          value={store.description}
          onChange={set("description")}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Logo URL"
            type="url"
            hint="File upload arrives with the media phase."
            value={store.logo_url}
            onChange={set("logo_url")}
          />
          <Input
            label="Banner URL"
            type="url"
            hint="File upload arrives with the media phase."
            value={store.banner_url}
            onChange={set("banner_url")}
          />
        </div>
        <Input
          label="Contact phone"
          type="tel"
          value={store.contact_phone}
          onChange={set("contact_phone")}
        />
        <Textarea
          label="Return policy"
          rows={3}
          value={store.return_policy}
          onChange={set("return_policy")}
        />
        <Textarea
          label="Shipping policy"
          rows={3}
          value={store.shipping_policy}
          onChange={set("shipping_policy")}
        />
        <div>
          <Button type="submit" loading={busy}>Save store settings</Button>
        </div>
      </form>
    </div>
  );
}