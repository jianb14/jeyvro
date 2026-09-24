/**
 * Wishlist feature module — saved-product state for the whole app (7.2).
 * Private per customer (marketplace-community rule 5): the API scopes rows
 * to the signed-in user, and mutations only apply the server's confirmed
 * result — never an optimistic guess.
 */
/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import * as wishlistApi from "../../data/wishlist";

const WishlistContext = createContext(null);

export function WishlistProvider({ children }) {
  const { user, loading: authLoading } = useAuth();
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);

  // Saved ids belong to the signed-in user only; logged-out visitors see
  // an empty set (entries stay stale but unreachable until the next fetch).
  useEffect(() => {
    if (authLoading || !user) return undefined;
    let cancelled = false;
    wishlistApi
      .fetchWishlist({ pageSize: 100 })
      .then((data) => {
        if (!cancelled) setEntries(data.items);
      })
      .catch(() => {
        if (!cancelled) setEntries([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, user]);

  const savedIds = useMemo(
    () => new Set(user ? entries.map((entry) => entry.productId) : []),
    [entries, user]
  );

  const isSaved = useCallback((productId) => savedIds.has(productId), [savedIds]);

  const add = useCallback(async (productId) => {
    const entry = await wishlistApi.addToWishlist(productId);
    setEntries((prev) => [
      entry,
      ...prev.filter((item) => item.productId !== productId),
    ]);
    return entry;
  }, []);

  const remove = useCallback(async (productId) => {
    await wishlistApi.removeFromWishlist(productId);
    setEntries((prev) => prev.filter((item) => item.productId !== productId));
  }, []);

  const toggle = useCallback(
    async (productId) => {
      if (savedIds.has(productId)) {
        await remove(productId);
        return false;
      }
      await add(productId);
      return true;
    },
    [savedIds, add, remove]
  );

  const value = useMemo(
    () => ({ entries, savedIds, isSaved, add, remove, toggle, loading }),
    [entries, savedIds, isSaved, add, remove, toggle, loading]
  );

  return (
    <WishlistContext.Provider value={value}>{children}</WishlistContext.Provider>
  );
}

export function useWishlist() {
  const context = useContext(WishlistContext);
  if (!context) {
    throw new Error("useWishlist must be used inside <WishlistProvider>");
  }
  return context;
}
