/**
 * Product editor (Phase 12.2) — /seller/products/new and
 * /seller/products/:id.
 *
 * Create lands as a draft; every later change goes through the API:
 * details PATCH, variant PATCH/DELETE (delete deactivates when order
 * history exists), validated image upload (§8 media), and lifecycle
 * actions (submit / unpublish / archive / delete) whose rules live
 * server-side. Stock never moves here — the inventory page owns that.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card";
import { FileUpload } from "../../components/ui/FileUpload";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Switch } from "../../components/ui/Switch";
import { Textarea } from "../../components/ui/Textarea";
import { TrashIcon } from "../../components/ui/Icons";
import { getCategories } from "../../data/products";
import * as sellerApi from "../../data/seller";

const STATUS_TONES = {
  draft: "neutral",
  pending_review: "warning",
  published: "success",
  unpublished: "neutral",
  rejected: "danger",
  archived: "neutral",
};

function notify(setter, tone, message) {
  setter({ tone, message });
}

function VariantRow({ product, variant, onReload, onNotice }) {
  const [name, setName] = useState(variant.name);
  const [price, setPrice] = useState(String(variant.price));
  const [busy, setBusy] = useState(false);

  async function save(payload) {
    setBusy(true);
    try {
      await sellerApi.updateVariant(product.id, variant.id, payload);
      notify(onNotice, "success", `Variant ${variant.sku} updated.`);
      onReload();
    } catch (err) {
      notify(onNotice, "danger", err.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      const result = await sellerApi.removeVariant(product.id, variant.id);
      notify(onNotice, "success", result.detail);
      onReload();
    } catch (err) {
      notify(onNotice, "danger", err.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="flex flex-wrap items-end gap-3 rounded-xl border border-sand-200 p-4 dark:border-night-800">
      <div className="w-40">
        <Input
          label="Name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          disabled={product.status === "archived"}
        />
      </div>
      <div className="w-32">
        <Input
          label="Price (₱)"
          type="number"
          min="0"
          step="0.01"
          value={price}
          onChange={(event) => setPrice(event.target.value)}
          disabled={product.status === "archived"}
        />
      </div>
      <div className="flex flex-col gap-1.5 pb-1">
        <span className="text-xs font-medium text-sand-600 dark:text-sand-400">SKU</span>
        <span className="text-sm text-sand-700 dark:text-sand-300">{variant.sku}</span>
      </div>
      <div className="flex flex-col gap-1.5 pb-1">
        <span className="text-xs font-medium text-sand-600 dark:text-sand-400">Available</span>
        <span className="text-sm tabular-nums text-sand-700 dark:text-sand-300">
          {variant.inventory?.available ?? 0}
        </span>
      </div>
      <Switch
        label="Active"
        checked={variant.isActive}
        disabled={busy || product.status === "archived"}
        onChange={(checked) => save({ is_active: checked })}
      />
      {product.status !== "archived" && (
        <>
          <Button
            size="sm"
            variant="outline"
            loading={busy}
            onClick={() => save({ name, price })}
          >
            Save variant
          </Button>
          <Button size="sm" variant="ghost" disabled={busy} onClick={remove}>
            Remove
          </Button>
        </>
      )}
    </li>
  );
}

function VariantSection({ product, onReload, onNotice }) {
  const [form, setForm] = useState({ name: "", price: "", initial_stock: "" });
  const [busy, setBusy] = useState(false);

  async function addVariant(event) {
    event.preventDefault();
    setBusy(true);
    try {
      await sellerApi.addVariant(product.id, {
        name: form.name,
        price: form.price,
        ...(form.initial_stock !== ""
          ? { initial_stock: Number(form.initial_stock) }
          : {}),
      });
      setForm({ name: "", price: "", initial_stock: "" });
      notify(onNotice, "success", "Variant added.");
      onReload();
    } catch (err) {
      notify(onNotice, "danger", err.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Variants</CardTitle>
        <CardDescription>
          Every purchaseable option carries its own price and stock. Stock
          changes happen on the inventory page so the history stays intact.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {product.variants.length === 0 ? (
          <p className="text-sm text-sand-500 dark:text-sand-400">
            Add at least one variant before submitting for review.
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {product.variants.map((variant) => (
              <VariantRow
                key={variant.id}
                product={product}
                variant={variant}
                onReload={onReload}
                onNotice={onNotice}
              />
            ))}
          </ul>
        )}

        {product.status !== "archived" && (
          <form onSubmit={addVariant} className="flex flex-wrap items-end gap-3">
            <div className="w-40">
              <Input
                label="New variant name"
                placeholder="Large, Red…"
                value={form.name}
                onChange={(event) =>
                  setForm((f) => ({ ...f, name: event.target.value }))
                }
              />
            </div>
            <div className="w-32">
              <Input
                label="Price (₱)"
                type="number"
                min="0"
                step="0.01"
                required
                value={form.price}
                onChange={(event) =>
                  setForm((f) => ({ ...f, price: event.target.value }))
                }
              />
            </div>
            <div className="w-32">
              <Input
                label="Opening stock"
                type="number"
                min="0"
                step="1"
                value={form.initial_stock}
                onChange={(event) =>
                  setForm((f) => ({ ...f, initial_stock: event.target.value }))
                }
              />
            </div>
            <Button type="submit" variant="outline" loading={busy}>
              Add variant
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}

function ImageSection({ product, onReload, onNotice }) {
  const [busy, setBusy] = useState(false);

  async function upload(files) {
    const file = files[0];
    if (!file) return;
    setBusy(true);
    try {
      await sellerApi.uploadProductImage(product.id, file, {
        altText: product.title,
        position: product.images.length,
      });
      notify(onNotice, "success", "Image uploaded.");
      onReload();
    } catch (err) {
      notify(onNotice, "danger", err.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  }

  async function removeImage(image) {
    setBusy(true);
    try {
      await sellerApi.removeProductImage(product.id, image.id);
      notify(onNotice, "success", "Image removed.");
      onReload();
    } catch (err) {
      notify(onNotice, "danger", err.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Images</CardTitle>
        <CardDescription>
          JPG, PNG, or WebP up to 5 MB — the server validates type and size
          (§8 media).
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {product.images.length > 0 && (
          <ul className="flex flex-wrap gap-3">
            {product.images.map((image) => (
              <li
                key={image.id}
                className="flex flex-col items-start gap-2 rounded-xl border border-sand-200 p-2 dark:border-night-800"
              >
                <img
                  src={image.url}
                  alt={image.altText || product.title}
                  className="size-28 rounded-lg object-cover"
                />
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy || product.status === "archived"}
                  leadingIcon={TrashIcon}
                  onClick={() => removeImage(image)}
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        )}
        {product.status !== "archived" && (
          <FileUpload
            accept="image/jpeg,image/png,image/webp"
            multiple={false}
            disabled={busy}
            onFiles={upload}
          />
        )}
      </CardContent>
    </Card>
  );
}


function LifecycleCard({ product, onReload, onNotice }) {
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const navigate = useNavigate();

  async function run(action) {
    setBusy(true);
    try {
      const runner = {
        submit: sellerApi.submitProduct,
        unpublish: sellerApi.unpublishProduct,
        archive: sellerApi.archiveProduct,
      }[action];
      const updated = await runner(product.id);
      notify(onNotice, "success", `${updated.title}: ${action} succeeded.`);
      onReload();
    } catch (err) {
      notify(onNotice, "danger", err.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await sellerApi.deleteProduct(product.id);
      navigate("/seller/products", { replace: true });
    } catch (err) {
      notify(onNotice, "danger", err.data?.detail || err.message);
      setBusy(false);
    }
  }

  const archivable = ["draft", "rejected", "unpublished"].includes(product.status);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Review status</CardTitle>
        <CardDescription>
          Status moves run through the marketplace review flow — staff publish
          pending products; you can unpublish or archive your own.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap items-center gap-3">
        <Badge tone={STATUS_TONES[product.status] || "neutral"} variant="soft">
          {product.status.replace("_", " ")}
        </Badge>
        {product.status === "rejected" && product.rejectionReason && (
          <p className="w-full text-sm text-danger-600 dark:text-danger-400">
            {product.rejectionReason}
          </p>
        )}
        {archivable && (
          <Button size="sm" loading={busy} onClick={() => run("submit")}>
            Submit for review
          </Button>
        )}
        {product.status === "published" && (
          <Button size="sm" variant="outline" loading={busy} onClick={() => run("unpublish")}>
            Unpublish
          </Button>
        )}
        {archivable && (
          <Button size="sm" variant="outline" loading={busy} onClick={() => run("archive")}>
            Archive
          </Button>
        )}
        {product.status !== "archived" && (
          <Button
            size="sm"
            variant="destructive"
            disabled={busy}
            onClick={() => setConfirmDelete(true)}
          >
            Delete
          </Button>
        )}
        <Modal
          open={confirmDelete}
          onClose={() => setConfirmDelete(false)}
          title="Delete this product?"
          description="Products that have already been ordered are archived instead — past orders always keep their history."
          footer={
            <>
              <Button variant="ghost" onClick={() => setConfirmDelete(false)}>
                Cancel
              </Button>
              <Button variant="destructive" loading={busy} onClick={remove}>
                Delete product
              </Button>
            </>
          }
        >
          {product.title}
        </Modal>
      </CardContent>
    </Card>
  );
}

export function SellerProductEdit() {
  const { id } = useParams();
  const isCreate = !id;
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState({
    title: "",
    description: "",
    base_price: "",
    compare_at_price: "",
    category: "",
  });
  const [loadError, setLoadError] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    if (isCreate) return undefined;
    let cancelled = false;
    sellerApi
      .fetchMyProduct(id)
      .then((data) => {
        if (cancelled) return;
        setProduct(data);
        setForm({
          title: data.title,
          description: data.description,
          base_price: String(data.basePrice),
          compare_at_price:
            data.compareAtPrice != null ? String(data.compareAtPrice) : "",
          category: data.category != null ? String(data.category) : "",
        });
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [id, isCreate]);

  useEffect(load, [load]);

  useEffect(() => {
    let cancelled = false;
    getCategories()
      .then((items) => {
        if (!cancelled) setCategories(items);
      })
      .catch(() => {
        if (!cancelled) setCategories([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    const payload = {
      title: form.title,
      description: form.description,
      base_price: form.base_price,
      compare_at_price:
        form.compare_at_price === "" ? null : form.compare_at_price,
      category: form.category === "" ? null : Number(form.category),
    };
    try {
      if (isCreate) {
        const created = await sellerApi.createProduct(payload);
        navigate(`/seller/products/${created.id}`, { replace: true });
      } else {
        const updated = await sellerApi.updateProduct(product.id, payload);
        setProduct(updated);
        notify(setNotice, "success", "Product saved.");
      }
    } catch (err) {
      setError(err.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    return <Alert tone="danger" title="Could not load this product">{loadError}</Alert>;
  }
  if (!isCreate && !product) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-9 w-72" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const readOnly = product?.status === "archived";
  const set = (key) => (event) =>
    setForm((f) => ({ ...f, [key]: event.target.value }));

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <Link
            to="/seller/products"
            className="text-sm font-medium text-moss-700 hover:underline dark:text-moss-300"
          >
            ← All products
          </Link>
          <h1 className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">
            {isCreate ? "New product" : product.title}
          </h1>
        </div>
        {!isCreate && (
          <Badge tone={STATUS_TONES[product.status] || "neutral"} variant="soft">
            {product.status.replace("_", " ")}
          </Badge>
        )}
      </header>

      {notice && (
        <Alert tone={notice.tone} onDismiss={() => setNotice(null)}>
          {notice.message}
        </Alert>
      )}
      {error && <Alert tone="danger" title="Could not save product">{error}</Alert>}
      {readOnly && (
        <Alert tone="info" title="Archived products are read-only">
          Archived products can no longer be edited or sold. Create a new
          product when you are ready to sell again.
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
          <CardDescription>
            The base price shows when a product has no active variants; variant
            prices win for display and checkout.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} noValidate className="flex flex-col gap-4">
            <Input
              label="Title"
              required
              maxLength={180}
              value={form.title}
              onChange={set("title")}
              disabled={readOnly}
            />
            <Textarea
              label="Description"
              rows={4}
              value={form.description}
              onChange={set("description")}
              disabled={readOnly}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Base price (₱)"
                type="number"
                min="0"
                step="0.01"
                required
                value={form.base_price}
                onChange={set("base_price")}
                disabled={readOnly}
              />
              <Input
                label="Compare-at price (₱)"
                type="number"
                min="0"
                step="0.01"
                hint="Optional reference price — the discount is computed server-side."
                value={form.compare_at_price}
                onChange={set("compare_at_price")}
                disabled={readOnly}
              />
            </div>
            <Select
              label="Category"
              value={form.category}
              onChange={set("category")}
              disabled={readOnly}
            >
              <option value="">No category</option>
              {categories.map((category) => (
                <option key={category.id} value={String(category.id)}>
                  {category.name}
                </option>
              ))}
            </Select>
            {!readOnly && (
              <div>
                <Button type="submit" loading={busy}>
                  {isCreate ? "Create draft" : "Save changes"}
                </Button>
              </div>
            )}
          </form>
        </CardContent>
      </Card>

      {!isCreate && product && (
        <>
          <LifecycleCard product={product} onReload={load} onNotice={setNotice} />
          <VariantSection product={product} onReload={load} onNotice={setNotice} />
          <ImageSection product={product} onReload={load} onNotice={setNotice} />
        </>
      )}
    </div>
  );
}

