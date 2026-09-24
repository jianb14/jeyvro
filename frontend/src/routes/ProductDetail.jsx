/**
 * Product detail (Phase 6.3) — gallery, variant picker over server truth
 * (per-variant price and stock), quantity, store info, and related
 * products. Add to cart / Buy now / wishlist are visible foundations —
 * they turn functional with Phase 7 (cart & wishlist).
 */
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { cx } from "../lib/cx";
import { Navbar } from "../components/layout/Navbar";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Breadcrumb } from "../components/ui/Breadcrumb";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { Price } from "../components/ui/Price";
import { ProductShelf } from "../components/ui/ProductShelf";
import { ProductArt } from "../components/ui/ProductArt";
import { QuantityStepper } from "../components/ui/QuantityStepper";
import { Rating } from "../components/ui/Rating";
import { Skeleton } from "../components/ui/Skeleton";
import { StockIndicator } from "../components/ui/StockIndicator";
import { VariantPicker } from "../components/ui/VariantPicker";
import { useToast } from "../components/ui/ToastProvider";
import {
  CheckCircleIcon,
  HeartIcon,
  HeartSolidIcon,
  InboxIcon,
  ShieldCheckIcon,
  ShoppingCartIcon,
  StoreIcon,
  TruckIcon,
} from "../components/ui/Icons";
import { useAuth } from "../features/auth/AuthContext";
import { useCart } from "../features/cart/CartContext";
import { useQuickAdd } from "../features/cart/useQuickAdd";
import { useWishlist } from "../features/wishlist/WishlistContext";
import { getProductById, getProducts } from "../data/products";
import { recordRecentlyViewed } from "../lib/recentlyViewed";

export function ProductDetail() {
  const { slug } = useParams();
  const { push } = useToast();
  const { user } = useAuth();
  const { addItem } = useCart();
  const { isSaved, toggle } = useWishlist();
  const quickAdd = useQuickAdd();
  const navigate = useNavigate();
  const location = useLocation();
  const [state, setState] = useState({ slug, status: "loading", product: null, error: null });
  const [related, setRelated] = useState({ slug: null, items: [] });
  const [selectedId, setSelectedId] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [activeImage, setActiveImage] = useState(0);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getProductById(slug)
      .then((product) => {
        if (cancelled) return null;
        if (!product) {
          setState({ slug, status: "not-found", product: null, error: null });
          return null;
        }
        setState({ slug, status: "ready", product, error: null });
        const initial =
          product.variants.find((variant) => variant.isDefault) ??
          product.variants.find((variant) => variant.active) ??
          product.variants[0] ??
          null;
        setSelectedId(initial?.id ?? null);
        setQuantity(1);
        setActiveImage(0);
        recordRecentlyViewed(product);
        return getProducts({ category: product.categorySlug, pageSize: 6 }).catch(() => null);
      })
      .then((result) => {
        if (cancelled || !result) return;
        setRelated({
          slug,
          items: result.items.filter((item) => item.id !== slug).slice(0, 4),
        });
      })
      .catch((err) => {
        if (!cancelled) {
          setState({
            slug,
            status: "error",
            product: null,
            error: err.data?.detail || err.message,
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const view = state.slug === slug ? state : { status: "loading", product: null, error: null };
  const product = view.product;
  const variants = product?.variants ?? [];
  const selected = variants.find((variant) => variant.id === selectedId) ?? variants[0] ?? null;
  const stock = selected?.stock ?? product?.stock ?? 0;
  const soldOut = stock === 0;
  const gallery = product
    ? product.images.length > 0
      ? product.images
      : product.image
        ? [product.image]
        : []
    : [];
  const mainImage = gallery[activeImage] ?? gallery[0] ?? null;
  const showDiscount = Boolean(product && selected && selected.price === product.price);
  const fav = product ? isSaved(product.id) : false;

  const addSelected = async () => {
    if (!selected) return;
    setAdding(true);
    try {
      await addItem(selected.id, quantity);
      push({
        tone: "success",
        title: "Added to cart",
        description: `${product.title} · ${selected.name} × ${quantity}`,
      });
    } catch (err) {
      push({
        tone: "danger",
        title: "Could not add to cart",
        description: err.data?.detail || err.message,
      });
    } finally {
      setAdding(false);
    }
  };

  // Buy now = add the selection, then land on the cart (checkout is Phase 8).
  const buyNow = async () => {
    if (!selected) return;
    setAdding(true);
    try {
      await addItem(selected.id, quantity);
      navigate("/cart");
    } catch (err) {
      push({
        tone: "danger",
        title: "Could not add to cart",
        description: err.data?.detail || err.message,
      });
    } finally {
      setAdding(false);
    }
  };

  const toggleFav = async () => {
    if (!user) {
      push({
        tone: "info",
        title: "Sign in to save items",
        description: "Your wishlist follows your account.",
      });
      navigate("/login", { state: { from: location.pathname } });
      return;
    }
    try {
      const saved = await toggle(product.id);
      push({
        tone: "success",
        title: saved ? "Saved for later" : "Removed from wishlist",
        description: product.title,
      });
    } catch (err) {
      push({
        tone: "danger",
        title: "Wishlist update failed",
        description: err.data?.detail || err.message,
      });
    }
  };

  return (
    <div className="min-h-dvh bg-sand-50 dark:bg-night-950">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 pb-24 pt-6 sm:px-6 lg:px-8">
        <Breadcrumb
          className="mb-6"
          items={
            product
              ? [
                  { label: "Home", to: "/" },
                  product.category && {
                    label: product.category,
                    to: `/category/${product.categorySlug}`,
                  },
                  { label: product.title },
                ].filter(Boolean)
              : [{ label: "Home", to: "/" }, { label: "Product" }]
          }
        />

        {view.status === "loading" && (
          <div className="grid gap-8 lg:grid-cols-2">
            <Skeleton className="aspect-square w-full rounded-2xl" />
            <div className="flex flex-col gap-4">
              <Skeleton className="h-9 w-3/4" />
              <Skeleton className="h-5 w-1/3" />
              <Skeleton className="h-10 w-1/2" />
              <Skeleton className="h-11 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          </div>
        )}

        {view.status === "error" && (
          <Alert tone="danger" title="Could not load this product">
            {view.error}
          </Alert>
        )}

        {view.status === "not-found" && (
          <EmptyState
            icon={InboxIcon}
            title="Product not found"
            description="This product does not exist or is not available right now."
            action={
              <Link to="/products">
                <Button>Browse products</Button>
              </Link>
            }
          />
        )}

        {view.status === "ready" && product && (
          <article className="flex flex-col gap-12">
            <div className="grid gap-8 lg:grid-cols-2">
              <div className="flex flex-col gap-3">
                <div className="overflow-hidden rounded-2xl border border-sand-200 bg-white dark:border-night-800 dark:bg-night-900">
                  {mainImage ? (
                    <img
                      src={mainImage}
                      alt={product.title}
                      className="aspect-square w-full object-cover"
                    />
                  ) : (
                    <ProductArt seed={product.seed} className="aspect-square w-full" />
                  )}
                </div>
                {gallery.length > 1 && (
                  <div className="flex gap-2 overflow-x-auto pb-1">
                    {gallery.map((src, index) => (
                      <button
                        key={src}
                        type="button"
                        onClick={() => setActiveImage(index)}
                        aria-label={`View image ${index + 1}`}
                        aria-pressed={index === activeImage}
                        className={cx(
                          "size-16 shrink-0 overflow-hidden rounded-xl border-2 transition-colors",
                          index === activeImage
                            ? "border-moss-600 dark:border-moss-400"
                            : "border-transparent ring-1 ring-sand-200 dark:ring-night-700"
                        )}
                      >
                        <img src={src} alt="" className="size-full object-cover" />
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex flex-col gap-4">
                <div className="flex flex-wrap items-center gap-2">
                  {product.isNew && (
                    <Badge tone="moss" variant="soft">NEW</Badge>
                  )}
                  {soldOut && (
                    <Badge tone="neutral" variant="soft">SOLD OUT</Badge>
                  )}
                </div>
                <h1 className="font-display text-2xl font-semibold tracking-tight text-sand-900 dark:text-sand-100 sm:text-3xl">
                  {product.title}
                </h1>
                <div className="flex flex-wrap items-center gap-2 text-sm text-sand-500 dark:text-sand-400">
                  <Rating value={product.rating} readonly size="sm" />
                  <span className="tabular-nums">({product.rating})</span>
                  <span aria-hidden="true">·</span>
                  <span className="tabular-nums">{product.sold} sold</span>
                  {product.category && (
                    <>
                      <span aria-hidden="true">·</span>
                      <Link
                        to={`/category/${product.categorySlug}`}
                        className="transition-colors hover:text-moss-700 dark:hover:text-moss-300"
                      >
                        {product.category}
                      </Link>
                    </>
                  )}
                </div>

                <Price
                  amount={selected ? selected.price : product.price}
                  originalAmount={showDiscount ? product.originalPrice : undefined}
                  discount={showDiscount ? product.discount : undefined}
                  size="xl"
                />
                <StockIndicator count={stock} threshold={selected?.lowStockThreshold ?? 10} />

                {variants.length > 1 && (
                  <VariantPicker
                    label="Variant"
                    options={variants.map((variant) => ({
                      label: variant.name,
                      disabled: variant.stock === 0 && variant.id !== selected?.id,
                    }))}
                    value={selected?.name}
                    onChange={(name) => {
                      const next = variants.find((variant) => variant.name === name);
                      if (next) {
                        setSelectedId(next.id);
                        setQuantity(1);
                      }
                    }}
                  />
                )}

                <div className="flex flex-wrap items-center gap-3">
                  <QuantityStepper
                    value={quantity}
                    min={1}
                    max={Math.max(1, stock)}
                    onChange={setQuantity}
                    disabled={soldOut}
                  />
                  <span className="text-sm text-sand-500 dark:text-sand-400">
                    {soldOut ? "Restocking soon" : "Prices and stock are server-verified"}
                  </span>
                </div>

                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button
                    size="lg"
                    className="flex-1"
                    leadingIcon={ShoppingCartIcon}
                    disabled={soldOut}
                    loading={adding}
                    onClick={addSelected}
                  >
                    {soldOut ? "Sold out" : "Add to cart"}
                  </Button>
                  <Button
                    size="lg"
                    variant="secondary"
                    className="flex-1"
                    disabled={soldOut}
                    onClick={buyNow}
                  >
                    Buy now
                  </Button>
                  <Button
                    size="lg"
                    variant="outline"
                    onClick={toggleFav}
                    leadingIcon={fav ? HeartSolidIcon : HeartIcon}
                    aria-pressed={fav}
                  >
                    {fav ? "Saved" : "Wishlist"}
                  </Button>
                </div>

                <Card className="p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-moss-100 text-moss-700 dark:bg-moss-900 dark:text-moss-300">
                        <StoreIcon size={18} />
                      </span>
                      <div className="min-w-0">
                        <p className="flex items-center gap-1.5 font-medium text-sand-900 dark:text-sand-100">
                          <span className="truncate">{product.store}</span>
                          {product.verified && (
                            <span title="Verified seller" className="shrink-0 text-moss-600 dark:text-moss-400">
                              <ShieldCheckIcon size={14} />
                            </span>
                          )}
                        </p>
                        <p className="text-xs text-sand-500 dark:text-sand-400">
                          Sold and shipped by this store
                        </p>
                      </div>
                    </div>
                    <Link to={`/store/${product.storeSlug}`}>
                      <Button variant="outline" size="sm">Visit store</Button>
                    </Link>
                  </div>
                </Card>

                <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-sand-500 dark:text-sand-400">
                  <span className="inline-flex items-center gap-1.5">
                    <ShieldCheckIcon size={14} /> Server-verified stock
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <TruckIcon size={14} /> Shipping computed at checkout
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <CheckCircleIcon size={14} /> Checkout arrives in Phase 8
                  </span>
                </div>
              </div>
            </div>

            {product.description && (
              <section className="flex flex-col gap-2">
                <h2 className="font-display text-lg font-semibold text-sand-900 dark:text-sand-100">
                  About this product
                </h2>
                <p className="whitespace-pre-line text-sm leading-relaxed text-sand-600 dark:text-sand-300">
                  {product.description}
                </p>
              </section>
            )}

            {related.slug === slug && related.items.length > 0 && (
              <ProductShelf
                title="You might also like"
                subtitle={
                  product.category
                    ? `More from ${product.category}`
                    : "More from the catalog"
                }
                products={related.items}
                columns={4}
                onAddToCart={quickAdd}
              />
            )}
          </article>
        )}
      </main>
    </div>
  );
}


