/**
 * Become-a-seller feature (Phase 4.1) — application form + already-a-seller
 * state. Server truth only: pending review message comes from the API
 * result, never a client-side guess (marketplace-sellers rule 5).
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { StoreIcon } from "../../components/ui/Icons";
import { Textarea } from "../../components/ui/Textarea";
import * as storesApi from "../../data/stores";
import { useRequiredFields } from "../../lib/formErrors";

export function BecomeSellerForm() {
  const [existingStore, setExistingStore] = useState(undefined); // undefined = checking
  const [form, setForm] = useState({
    store_name: "",
    store_description: "",
    contact_phone: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const { fieldErrors, validate, clearField, setFieldErrors } = useRequiredFields(
    { store_name: form.store_name },
    ["store_name"]
  );

  useEffect(() => {
    let cancelled = false;
    storesApi
      .fetchMyStore()
      .then((store) => {
        if (!cancelled) setExistingStore(store);
      })
      .catch(() => {
        if (!cancelled) setExistingStore(null); // no store yet — show the form
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const set = (key) => (event) => {
    setForm((f) => ({ ...f, [key]: event.target.value }));
    clearField(key);
  };

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    // noValidate: required fields render our red inline messages, never the
    // browser's native bubble (server stays the gate, §10.1).
    if (!validate()) return;
    setBusy(true);
    try {
      await storesApi.applyAsSeller(form);
      setSubmitted(true);
    } catch (err) {
      setError(err.data?.detail || err.data?.error || err.message);
      setFieldErrors(err.data?.field_errors || {});
    } finally {
      setBusy(false);
    }
  }

  if (existingStore === undefined) {
    return (
      <div className="flex min-h-[30vh] items-center justify-center">
        <div className="size-8 animate-spin rounded-full border-2 border-moss-600 border-t-transparent" />
      </div>
    );
  }

  if (existingStore) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>You already run a store</CardTitle>
          <CardDescription>
            {existingStore.name} — status: {existingStore.status}.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          {existingStore.status === "active" && (
            <Link to={`/store/${existingStore.slug}`}>
              <Button variant="outline">View public storefront</Button>
            </Link>
          )}
          <Link to="/account">
            <Button variant="secondary">Manage store settings</Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  if (submitted) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Application submitted</CardTitle>
          <CardDescription>
            Your store is pending review. Our team checks every application —
            you will see the store go live in your account once approved.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Link to="/account">
            <Button variant="outline">Back to account</Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <StoreIcon size={20} /> Sell on Jeyvro
        </CardTitle>
        <CardDescription>
          Tell us about your store. A moderator reviews every application
          before your storefront goes live.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {error && (
          <Alert tone="danger" title="Could not submit application" className="mb-4">
            {error}
          </Alert>
        )}
        <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
          <Input
            label="Store name"
            name="store_name"
            required
            maxLength={128}
            value={form.store_name}
            onChange={set("store_name")}
            error={fieldErrors.store_name?.[0]}
          />
          <Textarea
            label="Store description"
            name="store_description"
            hint="What do you sell? What makes your shop special?"
            rows={4}
            value={form.store_description}
            onChange={set("store_description")}
            error={fieldErrors.store_description?.[0]}
          />
          <Input
            label="Contact phone"
            name="contact_phone"
            type="tel"
            autoComplete="tel"
            placeholder="+63 9xx xxx xxxx"
            value={form.contact_phone}
            onChange={set("contact_phone")}
            error={fieldErrors.contact_phone?.[0]}
          />
          <div>
            <Button type="submit" loading={busy} className="w-full">
              Submit application
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}