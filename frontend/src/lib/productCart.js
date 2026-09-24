/**
 * Cart helpers for product payloads (Phase 7) — decides which variant an
 * "Add to cart" button on a product card adds, and why it can't when it
 * can't. One implementation shared by Home, Browse, Storefront, and the
 * wishlist page (frontend-feature reuse-first).
 */

export function resolveQuickAddVariant(product) {
  const inStock = (product?.variants ?? []).filter(
    (variant) => variant.active && variant.stock > 0
  );
  if (inStock.length === 0) return { variant: null, reason: "out_of_stock" };
  if (inStock.length === 1) return { variant: inStock[0], reason: null };
  const preferred = inStock.find((variant) => variant.isDefault);
  if (preferred) return { variant: preferred, reason: null };
  // Several options and no default in stock — the shopper must choose on
  // the detail page rather than have a variant picked for them.
  return { variant: null, reason: "needs_choice" };
}
