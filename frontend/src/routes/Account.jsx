import { useEffect, useState } from "react";
import { Navbar } from "../components/layout/Navbar";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Alert } from "../components/ui/Alert";
import { Tabs, TabPanel } from "../components/ui/Tabs";
import { Badge } from "../components/ui/Badge";
import { useAuth } from "../features/auth/AuthContext";
import * as authApi from "../data/auth";

function ProfilePanel() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({
    first_name: user.first_name || "",
    last_name: user.last_name || "",
    phone: user.phone || "",
  });
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await authApi.updateMe(form);
      setUser(updated);
      setSaved(true);
    } catch (err) {
      setError(err.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-md">
      {saved && <Alert tone="success" title="Profile saved" className="mb-4" />}
      {error && <Alert tone="danger" title="Could not save profile" className="mb-4">{error}</Alert>}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input label="Email" value={user.email} disabled hint="Email is your login identity." />
        <Input label="First name" value={form.first_name} onChange={set("first_name")} />
        <Input label="Last name" value={form.last_name} onChange={set("last_name")} />
        <Input label="Phone" value={form.phone} onChange={set("phone")} />
        <div>
          <Button type="submit" loading={busy}>Save profile</Button>
        </div>
      </form>
    </div>
  );
}

function SecurityPanel() {
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [busy, setBusy] = useState(false);

  const set = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    setFieldErrors({});
    try {
      if (form.next !== form.confirm) throw { data: { detail: "New passwords do not match." } };
      await authApi.changePassword(form.current, form.next);
      setSaved(true);
      setForm({ current: "", next: "", confirm: "" });
    } catch (err) {
      setError(err.data?.detail || err.data?.error || err.message);
      setFieldErrors(err.data?.field_errors || {});
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-md">
      {saved && <Alert tone="success" title="Password changed" className="mb-4" />}
      {error && <Alert tone="danger" title="Could not change password" className="mb-4">{error}</Alert>}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input label="Current password" type="password" autoComplete="current-password" required value={form.current} onChange={set("current")} error={fieldErrors.current_password?.[0]} />
        <Input label="New password" type="password" autoComplete="new-password" required value={form.next} onChange={set("next")} error={fieldErrors.new_password?.[0]} />
        <Input label="Confirm new password" type="password" autoComplete="new-password" required value={form.confirm} onChange={set("confirm")} />
        <div>
          <Button type="submit" loading={busy}>Change password</Button>
        </div>
      </form>
    </div>
  );
}

function AddressesPanel() {
  const [addresses, setAddresses] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ full_name: "", phone: "", line1: "", city: "", province: "", postal_code: "" });

  const set = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  async function load() {
    try {
      const data = await authApi.fetchAddresses();
      setAddresses(data.items);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    let cancelled = false;
    authApi
      .fetchAddresses()
      .then((data) => {
        if (!cancelled) setAddresses(data.items);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleAdd(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await authApi.createAddress(form);
      setForm({ full_name: "", phone: "", line1: "", city: "", province: "", postal_code: "" });
      await load();
    } catch (err) {
      setError(err.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id) {
    setError(null);
    try {
      await authApi.deleteAddress(id);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="max-w-xl">
      {error && <Alert tone="danger" title="Address error" className="mb-4">{error}</Alert>}
      {addresses === null ? (
        <p className="text-sand-500">Loading addresses…</p>
      ) : addresses.length === 0 ? (
        <p className="text-sand-500">No addresses yet — add one below.</p>
      ) : (
        <ul className="mb-6 flex flex-col gap-3">
          {addresses.map((a) => (
            <li key={a.id} className="flex items-start justify-between gap-4 rounded-xl border border-sand-200 p-4 dark:border-night-800">
              <div className="text-sm">
                <p className="font-medium text-sand-900 dark:text-sand-100">
                  {a.full_name}{" "}
                  {a.is_default && (
                    <Badge tone="success" variant="soft" size="sm">Default</Badge>
                  )}
                </p>
                <p className="text-sand-500 dark:text-sand-400">{a.line1}, {a.city}, {a.province} {a.postal_code}</p>
                <p className="text-sand-500 dark:text-sand-400">{a.phone}</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => handleDelete(a.id)}>Delete</Button>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={handleAdd} className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3">
          <Input label="Full name" required value={form.full_name} onChange={set("full_name")} />
          <Input label="Phone" required value={form.phone} onChange={set("phone")} />
        </div>
        <Input label="Street address" required value={form.line1} onChange={set("line1")} />
        <div className="grid grid-cols-3 gap-3">
          <Input label="City" required value={form.city} onChange={set("city")} />
          <Input label="Province" required value={form.province} onChange={set("province")} />
          <Input label="Postal code" required value={form.postal_code} onChange={set("postal_code")} />
        </div>
        <div>
          <Button type="submit" variant="secondary" loading={busy}>Add address</Button>
        </div>
      </form>
    </div>
  );
}


function PreferencesPanel() {
  const [prefs, setPrefs] = useState(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    authApi
      .fetchNotificationPreferences()
      .then(setPrefs)
      .catch((err) => setError(err.message));
  }, []);

  const toggle = (key) => async () => {
    const next = { ...prefs, [key]: !prefs[key] };
    setPrefs(next);
    try {
      const savedPrefs = await authApi.updateNotificationPreferences(next);
      setPrefs(savedPrefs);
      setSaved(true);
    } catch (err) {
      setError(err.message);
    }
  };

  if (error) return <Alert tone="danger" title="Error" className="max-w-md">{error}</Alert>;
  if (!prefs) return <p className="text-sand-500">Loading preferences…</p>;

  const ROWS = [
    ["order_updates_email", "Order updates", "Shipping and delivery status by email."],
    ["promotions_email", "Promotions", "Sales, vouchers, and campaigns."],
    ["messaging_email", "Messages", "Seller replies and customer questions."],
  ];

  return (
    <div className="max-w-md">
      {saved && <Alert tone="success" title="Preferences saved" className="mb-4" />}
      <div className="flex flex-col divide-y divide-sand-200 dark:divide-night-800">
        {ROWS.map(([key, label, description]) => (
          <div key={key} className="flex items-center justify-between gap-4 py-4">
            <div>
              <p className="font-medium text-sand-900 dark:text-sand-100">{label}</p>
              <p className="text-sm text-sand-500 dark:text-sand-400">{description}</p>
            </div>
            <Button variant="outline" size="sm" onClick={toggle(key)}>
              {prefs[key] ? "On" : "Off"}
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}

const TABS = [
  { id: "profile", label: "Profile" },
  { id: "security", label: "Security" },
  { id: "addresses", label: "Addresses" },
  { id: "preferences", label: "Preferences" },
];

export function Account() {
  const { user } = useAuth();
  const [tab, setTab] = useState("profile");

  return (
    <div className="min-h-screen bg-sand-50 dark:bg-night-950">
      <Navbar />
      <main className="mx-auto max-w-4xl px-4 py-12">
        <div className="mb-8 flex items-center gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
              {user.first_name ? `Hello, ${user.first_name}` : "Your account"}
            </h1>
            <p className="text-sm text-sand-500 dark:text-sand-400">{user.email}</p>
          </div>
          <Badge tone={user.email_verified ? "success" : "warning"} variant="soft">
            {user.email_verified ? "Verified" : "Unverified"}
          </Badge>
        </div>
        <Tabs tabs={TABS} defaultTab="profile" onChange={setTab} />
        {tab === "profile" && <TabPanel><ProfilePanel /></TabPanel>}
        {tab === "security" && <TabPanel><SecurityPanel /></TabPanel>}
        {tab === "addresses" && <TabPanel><AddressesPanel /></TabPanel>}
        {tab === "preferences" && <TabPanel><PreferencesPanel /></TabPanel>}
      </main>
    </div>
  );
}

