/**
 * Checkout (Phase 8, payments in Phase 9) — signed-in, server-priced.
 *
 * Steps live in the URL (?step=address|shipping|payment|review) so refresh
 * and the back button work; every amount comes from the checkout API (§6):
 * the preview adds per-store shipping to the live cart lines, the payment
 * options arrive with server-reported availability, and placing the order
 * sends only the address id + chosen method — the client never computes or
 * sends money (marketplace-orders rule 1).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Navbar } from "../components/layout/Navbar";
import { Alert } from "../components/ui/Alert";
import { AddressList } from "../components/ui/AddressCard";
import { Breadcrumb } from "../components/ui/Breadcrumb";
import { Button } from "../components/ui/Button";
import { Checkbox } from "../components/ui/Checkbox";
import { EmptyState } from "../components/ui/EmptyState";
import { ShoppingCartIcon, TagIcon, TruckIcon } from "../components/ui/Icons";
import { Input } from "../components/ui/Input";
import { PaymentMethodCard } from "../components/ui/PaymentMethodCard";
import { Price } from "../components/ui/Price";
import { Skeleton } from "../components/ui/Skeleton";
import { Stepper } from "../components/ui/Stepper";
import { useToast } from "../components/ui/ToastProvider";
import * as authApi from "../data/auth";
import { fetchCheckout, placeOrder } from "../data/orders";
import { useCart } from "../features/cart/CartContext";
import { useRequiredFields } from "../lib/formErrors";

const STEPS = [
  { id: "address", label: "Address" },
  { id: "shipping", label: "Shipping" },
  { id: "payment", label: "Payment" },
  { id: "review", label: "Review" },
];

const ADDRESS_FIELDS = [
  "full_name", "phone", "line1", "city", "province", "postal_code",
];

const EMPTY_DRAFT = {
  label: "",
  full_name: "",
  phone: "",
  line1: "",
  line2: "",
  city: "",
  province: "",
  postal_code: "",
  is_default: false,
};

/** API address → the AddressCard display contract. */
function toCard(address) {
  return {
    id: address.id,
    name: address.full_name,
    line1: [address.line1, address.line2].filter(Boolean).join(", "),
    city: address.city,
    province: address.province,
    postal: address.postal_code,
    phone: address.phone,
    isDefault: Boolean(address.is_default),
  };
}

export function Checkout() {
  const { refresh: refreshCart } = useCart();
  const { push } = useToast();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(true);
  const [previewError, setPreviewError] = useState(null);
  const [addresses, setAddresses] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [addingAddress, setAddingAddress] = useState(false);
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [savingAddress, setSavingAddress] = useState(false);
  const [addressError, setAddressError] = useState(null);
  const [placing, setPlacing] = useState(false);
  const [placeError, setPlaceError] = useState(null);
  const [paymentMethod, setPaymentMethod] = useState("cod");

  const { fieldErrors, validate, clearField, setFieldErrors } = useRequiredFields(
    draft,
    ADDRESS_FIELDS
  );

  const stepParam = searchParams.get("step");
  const step = STEPS.some((s) => s.id === stepParam) ? stepParam : STEPS[0].id;
  const currentIndex = STEPS.findIndex((s) => s.id === step);

  const goTo = useCallback(
    (id) => setSearchParams(id === STEPS[0].id ? {} : { step: id }),
    [setSearchParams]
  );

  const refreshPreview = useCallback(async () => {
    try {
      const data = await fetchCheckout();
      setPreview(data);
      setPreviewError(null);
      return data;
    } catch (err) {
      setPreviewError(err.data?.detail || err.message);
      return null;
    } finally {
      setPreviewLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchCheckout()
      .then((data) => {
        if (!cancelled) {
          setPreview(data);
          setPreviewError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setPreviewError(err.data?.detail || err.message);
      })
      .finally(() => {
        if (!cancelled) setPreviewLoading(false);
      });
    authApi
      .fetchAddresses()
      .then((data) => {
        if (cancelled) return;
        const items = data.items ?? [];
        setAddresses(items);
        const preferred = items.find((a) => a.is_default) ?? items[0];
        setSelectedId((current) => current ?? preferred?.id ?? null);
        setAddingAddress(items.length === 0);
      })
      .catch((err) => {
        if (!cancelled) setAddressError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Entering Review re-prices against live truth — the whole point of the
  // server-side checkout (§6): never trust numbers fetched earlier.
  useEffect(() => {
    if (step !== "review") return;
    let cancelled = false;
    fetchCheckout()
      .then((data) => {
        if (!cancelled) {
          setPreview(data);
          setPreviewError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setPreviewError(err.data?.detail || err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [step]);

  // Payment options are server truth (§6 v1.8): the active method is the
  // user's selection when offered by the server, otherwise the first
  // available method (resolved during render, never through cascading state).
  const paymentMethods = useMemo(
    () => preview?.paymentMethods ?? [],
    [preview?.paymentMethods]
  );
  const activePaymentMethod = useMemo(() => {
    const available = paymentMethods.filter((m) => m.available);
    if (available.length === 0) return paymentMethod;
    return available.some((m) => m.id === paymentMethod)
      ? paymentMethod
      : available[0].id;
  }, [paymentMethods, paymentMethod]);
  const selectedPaymentMethod =
    paymentMethods.find((method) => method.id === activePaymentMethod) ?? null;

  const setField = (key) => (event) => {
    const { value, type, checked } = event.target;
    setDraft((d) => ({ ...d, [key]: type === "checkbox" ? checked : value }));
    clearField(key);
  };

  async function saveAddress() {
    if (!validate()) return;
    setSavingAddress(true);
    setAddressError(null);
    try {
      const created = await authApi.createAddress({ ...draft });
      const items = await authApi.fetchAddresses();
      setAddresses(items.items ?? []);
      setSelectedId(created.id);
      setDraft(EMPTY_DRAFT);
      setAddingAddress(false);
      push({ tone: "success", title: "Address saved" });
    } catch (err) {
      setAddressError(err.data?.detail || err.data?.error || err.message);
      setFieldErrors(err.data?.field_errors || {});
    } finally {
      setSavingAddress(false);
    }
  }

  async function submitOrder() {
    if (!selectedId) return;
    setPlacing(true);
    setPlaceError(null);
    try {
      const order = await placeOrder(selectedId, activePaymentMethod);
      refreshCart();
      push({ tone: "success", title: `Order ${order.number} placed` });
      navigate(`/orders/${order.number}`, { state: { justPlaced: true } });
    } catch (err) {
      setPlaceError(err.data?.detail || err.message);
      await refreshPreview(); // revalidate: the failure may be a stale line
    } finally {
      setPlacing(false);
    }
  }

  const issues = preview?.issues ?? [];
  const totals = preview?.totals ?? {
    itemCount: 0, subtotal: 0, savings: 0, shipping: 0, tax: 0, grandTotal: 0,
  };
  const cards = useMemo(() => (addresses ?? []).map(toCard), [addresses]);
  const selectedAddress = useMemo(
    () => (addresses ?? []).find((a) => a.id === selectedId) ?? null,
    [addresses, selectedId]
  );
  const emptyCart = !previewLoading && (preview?.items?.length ?? 0) === 0;
  const canReview = Boolean(preview?.ready) && Boolean(selectedId);

  return (
    <div className="min-h-dvh bg-sand-50 dark:bg-night-950">
      <Navbar />

      <main className="mx-auto max-w-6xl px-4 pb-24 pt-6 sm:px-6 lg:px-8">
        <Breadcrumb
          className="mb-6"
          items={[
            { label: "Home", to: "/" },
            { label: "Cart", to: "/cart" },
            { label: "Checkout" },
          ]}
        />

        <div className="mb-8">
          <Stepper steps={STEPS} current={currentIndex} className="mx-auto max-w-md" />
        </div>

        {previewError && (
          <Alert tone="danger" title="Could not load checkout" className="mb-6">
            {previewError}
          </Alert>
        )}

        {emptyCart ? (
          <EmptyState
            icon={ShoppingCartIcon}
            title="Your cart is empty"
            description="Add items from any store before checking out."
            action={<Button onClick={() => navigate("/products")}>Browse products</Button>}
          />
        ) : (
          <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_340px]">
            <section className="flex flex-col gap-6">
              {issues.length > 0 && (
                <Alert tone="warning" title="Some items need attention">
                  {issues
                    .map((issue) => `${issue.title}: ${issue.reason}`)
                    .join(" ")}
                </Alert>
              )}

              {step === "address" && (
                <div className="flex flex-col gap-4">
                  <h1 className="font-display text-xl font-semibold text-sand-900 dark:text-sand-100">
                    Where should this order go?
                  </h1>
                  {addressError && (
                    <Alert tone="danger" title="Address error">{addressError}</Alert>
                  )}
                  {addresses === null ? (
                    <Skeleton className="h-44 w-full" />
                  ) : (
                    <>
                      {cards.length > 0 && (
                        <AddressList
                          addresses={cards}
                          selectedId={selectedId}
                          onSelect={setSelectedId}
                        />
                      )}
                      {addingAddress ? (
                        <form
                          noValidate
                          onSubmit={(event) => {
                            event.preventDefault();
                            saveAddress();
                          }}
                          className="flex flex-col gap-4 rounded-2xl border border-sand-200 bg-white p-5 dark:border-night-800 dark:bg-night-900"
                        >
                          <Input
                            label="Full name"
                            name="full_name"
                            required
                            value={draft.full_name}
                            onChange={setField("full_name")}
                            error={fieldErrors.full_name?.[0]}
                          />
                          <div className="grid gap-4 sm:grid-cols-2">
                            <Input
                              label="Phone"
                              name="phone"
                              type="tel"
                              required
                              value={draft.phone}
                              onChange={setField("phone")}
                              error={fieldErrors.phone?.[0]}
                            />
                            <Input
                              label="Label (optional)"
                              name="label"
                              hint="e.g. Home or Office"
                              value={draft.label}
                              onChange={setField("label")}
                            />
                          </div>
                          <Input
                            label="Street address"
                            name="line1"
                            required
                            value={draft.line1}
                            onChange={setField("line1")}
                            error={fieldErrors.line1?.[0]}
                          />
                          <Input
                            label="Unit / building (optional)"
                            name="line2"
                            value={draft.line2}
                            onChange={setField("line2")}
                          />
                          <div className="grid gap-4 sm:grid-cols-3">
                            <Input
                              label="City"
                              name="city"
                              required
                              value={draft.city}
                              onChange={setField("city")}
                              error={fieldErrors.city?.[0]}
                            />
                            <Input
                              label="Province"
                              name="province"
                              required
                              value={draft.province}
                              onChange={setField("province")}
                              error={fieldErrors.province?.[0]}
                            />
                            <Input
                              label="Postal code"
                              name="postal_code"
                              required
                              value={draft.postal_code}
                              onChange={setField("postal_code")}
                              error={fieldErrors.postal_code?.[0]}
                            />
                          </div>
                          <Checkbox
                            label="Set as my default address"
                            checked={draft.is_default}
                            onChange={setField("is_default")}
                          />
                          <div className="flex flex-wrap gap-3">
                            <Button type="submit" loading={savingAddress}>
                              Save address
                            </Button>
                            {cards.length > 0 && (
                              <Button
                                type="button"
                                variant="outline"
                                onClick={() => setAddingAddress(false)}
                              >
                                Cancel
                              </Button>
                            )}
                          </div>
                        </form>
                      ) : (
                        <div>
                          <Button
                            variant="outline"
                            onClick={() => setAddingAddress(true)}
                          >
                            Add a new address
                          </Button>
                        </div>
                      )}
                    </>
                  )}
                  <div className="flex justify-end">
                    <Button
                      size="lg"
                      disabled={!selectedId || savingAddress}
                      onClick={() => goTo("shipping")}
                    >
                      Continue to shipping
                    </Button>
                  </div>
                </div>
              )}

              {step === "shipping" && (
                <div className="flex flex-col gap-4">
                  <h1 className="font-display text-xl font-semibold text-sand-900 dark:text-sand-100">
                    Shipping is charged per store
                  </h1>
                  <p className="text-sm text-sand-500 dark:text-sand-400">
                    Each seller ships their own parcel, so every store has its
                    own fee.
                  </p>
                  <ul className="flex flex-col gap-3">
                    {(preview?.groups ?? []).map((group) => (
                      <li
                        key={group.storeSlug}
                        className="rounded-2xl border border-sand-200 bg-white p-4 dark:border-night-800 dark:bg-night-900"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <span className="text-sm font-semibold text-sand-900 dark:text-sand-100">
                            {group.storeName}
                          </span>
                          <span className="text-xs text-sand-500 dark:text-sand-400">
                            {group.itemCount}{" "}
                            {group.itemCount === 1 ? "item" : "items"}
                          </span>
                        </div>
                        <div className="mt-3 flex flex-col gap-1.5 text-sm">
                          <div className="flex items-center justify-between text-sand-600 dark:text-sand-300">
                            <span>Store subtotal</span>
                            <Price amount={group.subtotal} size="sm" />
                          </div>
                          <div className="flex items-center justify-between text-sand-600 dark:text-sand-300">
                            <span className="flex items-center gap-1.5">
                              <TruckIcon size={14} /> Shipping
                            </span>
                            {group.freeShipping ? (
                              <span className="text-sm font-medium text-success-700 dark:text-success-400">
                                Free
                              </span>
                            ) : (
                              <Price amount={group.shippingFee} size="sm" />
                            )}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                  <div className="flex justify-between">
                    <Button variant="outline" onClick={() => goTo("address")}>
                      Back
                    </Button>
                    <Button
                      size="lg"
                      disabled={!selectedId}
                      onClick={() => goTo("payment")}
                    >
                      Continue to payment
                    </Button>
                  </div>
                </div>
              )}

              {step === "payment" && (
                <div className="flex flex-col gap-4">
                  <h1 className="font-display text-xl font-semibold text-sand-900 dark:text-sand-100">
                    How would you like to pay?
                  </h1>
                  {paymentMethods.length === 0 ? (
                    <Skeleton className="h-24 w-full" />
                  ) : (
                    <div className="flex flex-col gap-3">
                      {paymentMethods.map((method) => (
                        <PaymentMethodCard
                          key={method.id}
                          method={method.id}
                          label={method.label}
                          description={method.description}
                          selected={method.id === activePaymentMethod}
                          onSelect={setPaymentMethod}
                          disabled={!method.available}
                        />
                      ))}
                    </div>
                  )}
                  <p className="text-xs leading-relaxed text-sand-500 dark:text-sand-400">
                    Cash on Delivery is collected when your order arrives.
                    Online methods appear here as soon as their gateway is
                    connected.
                  </p>
                  <div className="flex justify-between">
                    <Button variant="outline" onClick={() => goTo("shipping")}>
                      Back
                    </Button>
                    <Button
                      size="lg"
                      disabled={!selectedPaymentMethod}
                      onClick={() => goTo("review")}
                    >
                      Continue to review
                    </Button>
                  </div>
                </div>
              )}

              {step === "review" && (
                <div className="flex flex-col gap-4">
                  <h1 className="font-display text-xl font-semibold text-sand-900 dark:text-sand-100">
                    Review your order
                  </h1>
                  {placeError && (
                    <Alert tone="danger" title="Could not place the order">
                      {placeError}
                    </Alert>
                  )}
                  {selectedPaymentMethod && (
                    <div className="rounded-2xl border border-sand-200 bg-white p-4 dark:border-night-800 dark:bg-night-900">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-sand-900 dark:text-sand-100">
                          Payment
                        </p>
                        <button
                          type="button"
                          onClick={() => goTo("payment")}
                          className="text-xs font-medium text-moss-700 underline-offset-2 hover:underline dark:text-moss-300"
                        >
                          Change
                        </button>
                      </div>
                      <p className="mt-1.5 text-sm text-sand-700 dark:text-sand-300">
                        {selectedPaymentMethod.label}
                      </p>
                      <p className="text-sm text-sand-500 dark:text-sand-400">
                        {selectedPaymentMethod.id === "cod" ? (
                          <>
                            Pay <Price amount={totals.grandTotal} size="sm" /> in
                            cash when your order arrives.
                          </>
                        ) : (
                          "You will complete this payment online after placing the order."
                        )}
                      </p>
                    </div>
                  )}

                  {previewLoading && !preview ? (
                    <Skeleton className="h-40 w-full" />
                  ) : (
                    <ul className="flex flex-col gap-4">
                      {(preview?.groups ?? []).map((group) => (
                        <li
                          key={group.storeSlug}
                          className="rounded-2xl border border-sand-200 bg-white p-4 dark:border-night-800 dark:bg-night-900"
                        >
                          <p className="text-sm font-semibold text-sand-900 dark:text-sand-100">
                            {group.storeName}
                          </p>
                          <ul className="mt-3 flex flex-col gap-3">
                            {group.items.map((item) => (
                              <li
                                key={item.id}
                                className="flex items-start justify-between gap-4"
                              >
                                <div className="flex min-w-0 flex-col">
                                  <span className="truncate text-sm text-sand-800 dark:text-sand-200">
                                    {item.title}
                                  </span>
                                  <span className="text-xs text-sand-500 dark:text-sand-400">
                                    {item.variant || item.sku} · ×{item.qty}
                                  </span>
                                </div>
                                <Price amount={item.lineTotal} size="sm" />
                              </li>
                            ))}
                          </ul>
                        </li>
                      ))}
                    </ul>
                  )}

                  {selectedAddress && (
                    <div className="rounded-2xl border border-sand-200 bg-white p-4 dark:border-night-800 dark:bg-night-900">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-sand-900 dark:text-sand-100">
                          Ship to
                        </p>
                        <button
                          type="button"
                          onClick={() => goTo("address")}
                          className="text-xs font-medium text-moss-700 underline-offset-2 hover:underline dark:text-moss-300"
                        >
                          Change
                        </button>
                      </div>
                      <p className="mt-1.5 text-sm text-sand-700 dark:text-sand-300">
                        {selectedAddress.full_name} · {selectedAddress.phone}
                      </p>
                      <p className="text-sm text-sand-500 dark:text-sand-400">
                        {[selectedAddress.line1, selectedAddress.line2]
                          .filter(Boolean)
                          .join(", ")}
                        , {selectedAddress.city}, {selectedAddress.province}{" "}
                        {selectedAddress.postal_code}
                      </p>
                    </div>
                  )}

                  <div className="flex justify-between">
                    <Button variant="outline" onClick={() => goTo("payment")}>
                      Back
                    </Button>
                    <Button
                      size="lg"
                      loading={placing}
                      disabled={!canReview}
                      onClick={submitOrder}
                    >
                      Place order
                    </Button>
                  </div>
                </div>
              )}
            </section>

            <aside className="lg:sticky lg:top-24 lg:self-start">
              <div className="flex flex-col gap-4 rounded-2xl border border-sand-200 bg-white p-5 shadow-soft dark:border-night-800 dark:bg-night-900">
                <p className="font-display text-lg font-semibold text-sand-900 dark:text-sand-100">
                  Order Summary
                </p>
                {previewLoading && !preview ? (
                  <Skeleton className="h-32 w-full" />
                ) : (
                  <div className="flex flex-col gap-2.5 text-sm">
                    <div className="flex items-center justify-between text-sand-600 dark:text-sand-300">
                      <span>
                        Subtotal ({totals.itemCount}{" "}
                        {totals.itemCount === 1 ? "item" : "items"})
                      </span>
                      <Price amount={totals.subtotal} size="sm" />
                    </div>
                    {totals.savings > 0 && (
                      <div className="flex items-center justify-between font-medium text-success-700 dark:text-success-400">
                        <span className="flex items-center gap-1.5">
                          <TagIcon size={14} /> You save
                        </span>
                        <Price amount={totals.savings} size="sm" />
                      </div>
                    )}
                    <div className="flex items-center justify-between text-sand-600 dark:text-sand-300">
                      <span className="flex items-center gap-1.5">
                        <TruckIcon size={14} /> Shipping
                        {(preview?.groups?.length ?? 0) > 1
                          ? ` (${preview.groups.length} stores)`
                          : ""}
                      </span>
                      <Price amount={totals.shipping} size="sm" />
                    </div>
                  </div>
                )}
                <div className="flex items-baseline justify-between border-t border-sand-200 pt-4 dark:border-night-800">
                  <span className="text-sm font-medium text-sand-600 dark:text-sand-300">
                    Total
                  </span>
                  <Price amount={totals.grandTotal} size="lg" />
                </div>
                <p className="text-xs leading-relaxed text-sand-500 dark:text-sand-400">
                  Every amount is computed by Jeyvro from live prices and
                  per-store shipping fees.
                </p>
              </div>
            </aside>
          </div>
        )}
      </main>
    </div>
  );
}


