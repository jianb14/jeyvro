/**
 * useQuickAdd — the shared "Add to cart" behavior for product cards
 * (Phase 7). Adds the card's variant through the server, or routes the
 * shopper to the product page when a real choice is required. Feedback
 * follows ux-patterns: Toast for the outcome, navigation for the rest.
 */
import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useToast } from "../../components/ui/ToastProvider";
import { resolveQuickAddVariant } from "../../lib/productCart";
import { useCart } from "./CartContext";

export function useQuickAdd() {
  const { addItem } = useCart();
  const { push } = useToast();
  const navigate = useNavigate();

  return useCallback(
    async (product) => {
      const { variant, reason } = resolveQuickAddVariant(product);
      if (!variant) {
        push({
          tone: reason === "needs_choice" ? "info" : "warning",
          title: reason === "needs_choice" ? "Choose an option" : "Out of stock",
          description:
            reason === "needs_choice"
              ? `${product.title} has multiple options — pick one to add it.`
              : `${product.title} is not available right now.`,
        });
        navigate(`/product/${product.id}`);
        return;
      }
      try {
        await addItem(variant.id, 1);
        push({
          tone: "success",
          title: "Added to cart",
          description: `${product.title} — ${variant.name}`,
        });
      } catch (err) {
        push({
          tone: "danger",
          title: "Could not add to cart",
          description: err.data?.detail || err.message,
        });
      }
    },
    [addItem, push, navigate]
  );
}
