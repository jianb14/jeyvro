/**
 * Cart feature module — server cart state for the whole app (Phase 7).
 * The server is the source of truth (§6): every mutation returns the
 * recomputed cart, and the provider stores exactly that response — the
 * client never patches quantities, prices, or totals by hand.
 */
/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import * as cartApi from "../../data/cart";

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const { user, loading: authLoading } = useAuth();
  const [cart, setCart] = useState(null);
  const [loading, setLoading] = useState(true);

  // Refetch on every auth transition: login merges the guest cart into the
  // account cart server-side; logout returns to the (empty) guest session.
  // The previous cart stays visible while refetching — no flicker, and no
  // synchronous setState inside the effect body (frontend-state rule 7).
  useEffect(() => {
    if (authLoading) return undefined;
    let cancelled = false;
    cartApi
      .fetchCart()
      .then((data) => {
        if (!cancelled) setCart(data);
      })
      .catch(() => {
        if (!cancelled) setCart(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, user]);

  const addItem = useCallback(async (variantId, quantity = 1) => {
    const data = await cartApi.addCartItem(variantId, quantity);
    setCart(data);
    return data;
  }, []);

  const updateItem = useCallback(async (itemId, quantity) => {
    const data = await cartApi.updateCartItem(itemId, quantity);
    setCart(data);
    return data;
  }, []);

  const removeItem = useCallback(async (itemId) => {
    const data = await cartApi.removeCartItem(itemId);
    setCart(data);
    return data;
  }, []);

  const clear = useCallback(async () => {
    const data = await cartApi.clearCart();
    setCart(data);
    return data;
  }, []);

  const refresh = useCallback(async () => {
    const data = await cartApi.fetchCart();
    setCart(data);
    return data;
  }, []);

  const value = useMemo(
    () => ({
      cart,
      loading,
      itemCount: cart?.totals.itemCount ?? 0,
      lineCount: cart?.totals.lineCount ?? 0,
      addItem,
      updateItem,
      removeItem,
      clear,
      refresh,
    }),
    [cart, loading, addItem, updateItem, removeItem, clear, refresh]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error("useCart must be used inside <CartProvider>");
  return context;
}
