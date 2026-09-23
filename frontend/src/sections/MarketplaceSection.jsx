import { useState } from "react";
import { Section, Demo } from "./shared";
import { ProductGrid } from "../components/ui/ProductCard";
import { Price } from "../components/ui/Price";
import { QuantityStepper } from "../components/ui/QuantityStepper";
import { VariantPicker } from "../components/ui/VariantPicker";
import { StockIndicator } from "../components/ui/StockIndicator";
import { CartItem } from "../components/ui/CartItem";
import { CartSummary } from "../components/ui/CartSummary";
import { StoreCard } from "../components/ui/StoreCard";
import { ReviewCard } from "../components/ui/ReviewCard";
import { AddressList } from "../components/ui/AddressCard";
import { PaymentMethodCard } from "../components/ui/PaymentMethodCard";
import { OrderStatusBadge } from "../components/ui/OrderStatusBadge";
import { Drawer } from "../components/ui/Drawer";
import { Chip } from "../components/ui/Chip";
import { Button } from "../components/ui/Button";
import { ToastViewport } from "../components/ui/Toast";
import { useToasts } from "../lib/useToasts";
import { FilterIcon, ShoppingCartIcon, ShoppingBagIcon } from "../components/ui/Icons";

const PRODUCTS = [
  { id: "p1", seed: 0, title: "Handwoven Bamboo Storage Basket - Large", price: 349, originalPrice: 499, discount: 30, rating: 5, sold: 1240, stock: 24, store: "Kalinga Crafts", verified: true, isNew: true },
  { id: "p2", seed: 1, title: "Organic Barako Coffee Beans 500g", price: 425, rating: 4, sold: 890, stock: 8, store: "Batangas Brew Co.", verified: true },
  { id: "p3", seed: 2, title: "Minimal Ceramic Dinner Plates (Set of 4)", price: 899, originalPrice: 1200, discount: 25, rating: 5, sold: 432, stock: 0, store: "Mugna Pottery", verified: true },
  { id: "p4", seed: 3, title: "Abaca Tote Bag - Natural Dye", price: 550, rating: 4, sold: 2100, stock: 15, store: "Bicol Weavers", verified: true, isNew: true },
  { id: "p5", seed: 4, title: "Air-dried Mango 200g Pack of 3", price: 380, originalPrice: 450, discount: 15, rating: 5, sold: 5600, stock: 42, store: "Cebu Delights" },
  { id: "p6", seed: 5, title: "Capiz Shell Wall Decor", price: 1250, rating: 4, sold: 156, stock: 5, store: "Kalinga Crafts", verified: true },
];

const STORES = [
  { name: "Kalinga Crafts", rating: 5, products: 48, location: "Baguio City", verified: true, following: false },
  { name: "Batangas Brew Co.", rating: 4, products: 23, location: "Batangas City", verified: true, following: true },
];

const REVIEWS = [
  {
    author: "Maria Santos",
    rating: 5,
    date: "2 days ago",
    verifiedPurchase: true,
    photos: 2,
    helpful: 24,
    text: "Sobrang ganda ng weave! Makapal yung basket at mukhang matibay. Highly recommended para sa authentic na gawang Pinoy.",
  },
  {
    author: "Juan Dela Cruz",
    rating: 4,
    date: "1 week ago",
    verifiedPurchase: true,
    photos: 1,
    helpful: 9,
    text: "Good quality and well-packaged. Slightly smaller than expected but works fine as a desk organizer. Delivery was fast, arrived in 2 days.",
  },
];

const ADDRESSES = [
  { id: "a1", name: "Christian Reyes", line1: "123 Sampaguita St., Barangay San Roque", city: "Quezon City", province: "Metro Manila", postal: "1100", phone: "+63 917 123 4567", isDefault: true },
  { id: "a2", name: "Office - Jeyvro HQ", line1: "25F EMY Tower, EDSA cor. Shaw Blvd.", city: "Mandaluyong", province: "Metro Manila", postal: "1550", phone: "+63 917 987 6543" },
];

const FILTERS = ["All", "Home & Living", "Food", "Fashion", "On Sale", "Free Shipping"];

export function MarketplaceSection() {
  const [cart, setCart] = useState([]);
  const [cartOpen, setCartOpen] = useState(false);
  const [activeFilter, setActiveFilter] = useState("All");
  const [qty, setQty] = useState(2);
  const [size, setSize] = useState("Medium");
  const [color, setColor] = useState("Sage");
  const [address, setAddress] = useState("a1");
  const [payment, setPayment] = useState("gcash");
  const { toasts, push, dismiss } = useToasts();

  const addToCart = (product) => {
    setCart((prev) => {
      const existing = prev.find((i) => i.id === product.id);
      if (existing) {
        return prev.map((i) => (i.id === product.id ? { ...i, qty: i.qty + 1 } : i));
      }
      return [...prev, { id: product.id, title: product.title, price: product.price, qty: 1, seed: product.seed, variant: "Default" }];
    });
    push({ tone: "success", title: "Added to cart", description: product.title });
  };

  const subtotal = cart.reduce((sum, i) => sum + i.price * i.qty, 0);

  return (
    <Section
      id="marketplace"
      title="Marketplace Components"
      description="Kumpletong commerce pack: product cards, cart, checkout pieces — may ₱ pricing, GCash/COD payments, at PH-context details."
    >
      <Demo label="Product Grid — 6 sample products (functional add to cart)" className="w-full">
        <div className="mb-4 flex w-full flex-wrap items-center gap-2">
          <span className="mr-1 flex items-center gap-1.5 text-xs font-medium text-sand-500 dark:text-sand-400">
            <FilterIcon size={14} /> Filters:
          </span>
          {FILTERS.map((f) => (
            <Chip key={f} label={f} selected={activeFilter === f} onClick={() => setActiveFilter(f)} />
          ))}
        </div>
        <ProductGrid products={PRODUCTS} onAddToCart={addToCart} columns={3} className="w-full" />
      </Demo>

      <Demo label="Cart — click to open the live cart drawer">
        <Button size="lg" leadingIcon={ShoppingCartIcon} onClick={() => setCartOpen(true)}>
          View cart ({cart.reduce((s, i) => s + i.qty, 0)})
        </Button>
        <Button variant="outline" size="lg" leadingIcon={ShoppingBagIcon} onClick={() => setCartOpen(true)}>
          Checkout flow
        </Button>

        <Drawer
          open={cartOpen}
          onClose={() => setCartOpen(false)}
          side="right"
          size="md"
          title="Your Cart"
          description={`${cart.reduce((s, i) => s + i.qty, 0)} item(s)`}
        >
          {cart.length === 0 ? (
            <p className="py-10 text-center text-sm text-sand-400">Empty pa ang cart — add products from the grid!</p>
          ) : (
            <div className="flex flex-col gap-6">
              <ul className="flex flex-col gap-3">
                {cart.map((item) => (
                  <CartItem
                    key={item.id}
                    item={item}
                    onQtyChange={(id, q) =>
                      setCart((prev) => prev.map((i) => (i.id === id ? { ...i, qty: q } : i)))
                    }
                    onRemove={(id) => setCart((prev) => prev.filter((i) => i.id !== id))}
                  />
                ))}
              </ul>
              <CartSummary
                subtotal={subtotal}
                shipping={subtotal > 1000 ? 0 : 60}
                discount={0}
                onCheckout={() => {
                  setCartOpen(false);
                  push({ tone: "success", title: "Checkout successful!", description: "Salamat sa pag-shop sa Jeyvro." });
                  setCart([]);
                }}
              />
            </div>
          )}
        </Drawer>
        <ToastViewport toasts={toasts} onDismiss={dismiss} />
      </Demo>



      <Demo label="Price & Stock">
        <div className="flex flex-col gap-4">
          <Price amount={349} originalAmount={499} discount={30} size="lg" />
          <Price amount={1250} size="md" />
          <Price amount={299} installment="₱299/mo · 12 months, 0% interest" size="md" />
          <div className="flex flex-wrap gap-6">
            <StockIndicator count={24} />
            <StockIndicator count={7} />
            <StockIndicator count={0} />
          </div>
        </div>
      </Demo>


      <Demo label="Quantity & Variants">
        <div className="flex flex-col gap-5">
          <div className="flex flex-wrap items-center gap-6">
            <div>
              <p className="mb-2 text-xs text-sand-400">Boxed variant</p>
              <QuantityStepper value={qty} onChange={setQty} />
            </div>
            <div>
              <p className="mb-2 text-xs text-sand-400">Inline / small</p>
              <QuantityStepper value={3} size="sm" variant="inline" />
            </div>
            <div>
              <p className="mb-2 text-xs text-sand-400">Max reached (5)</p>
              <QuantityStepper value={5} max={5} />
            </div>
          </div>
          <VariantPicker
            label="Size"
            type="pill"
            value={size}
            onChange={setSize}
            options={[
              { label: "Small" },
              { label: "Medium" },
              { label: "Large" },
              { label: "XL", disabled: true },
            ]}
          />
          <VariantPicker
            label="Color"
            type="swatch"
            value={color}
            onChange={setColor}
            options={[
              { label: "Sage", color: "#84a471" },
              { label: "Moss", color: "#4f6d3f" },
              { label: "Sand", color: "#d3ccbb" },
              { label: "Terracotta", color: "#d08880" },
              { label: "Midnight", color: "#2d3b27", disabled: true },
            ]}
          />
        </div>
      </Demo>

      <Demo label="Store Cards">
        <div className="grid w-full gap-4 md:grid-cols-2">
          {STORES.map((s) => (
            <StoreCard key={s.name} store={s} />
          ))}
        </div>
      </Demo>

      <Demo label="Reviews" className="w-full">
        <div className="grid w-full gap-4 md:grid-cols-2">
          {REVIEWS.map((r) => (
            <ReviewCard key={r.author} review={r} />
          ))}
        </div>
      </Demo>

      <Demo label="Checkout — Addresses" className="w-full">
        <AddressList addresses={ADDRESSES} selectedId={address} onSelect={setAddress} />
      </Demo>

      <Demo label="Checkout — Payment Methods" className="w-full">
        <div className="grid w-full gap-3 md:grid-cols-2">
          <PaymentMethodCard method="gcash" label="GCash" description="Instant e-wallet payment" selected={payment === "gcash"} onSelect={setPayment} />
          <PaymentMethodCard method="maya" label="Maya" description="Pay with Maya balance" selected={payment === "maya"} onSelect={setPayment} />
          <PaymentMethodCard method="card" label="Credit / Debit Card" description="Visa, Mastercard, JCB" selected={payment === "card"} onSelect={setPayment} />
          <PaymentMethodCard method="cod" label="Cash on Delivery" description="Bayad pagdating ng delivery" selected={payment === "cod"} onSelect={setPayment} />
        </div>
      </Demo>

      <Demo label="Order Status Badges">
        <div className="flex flex-wrap gap-2">
          {["to-pay", "to-ship", "to-receive", "completed", "cancelled", "refunded"].map((s) => (
            <OrderStatusBadge key={s} status={s} />
          ))}
        </div>
      </Demo>
    </Section>
  );
}
