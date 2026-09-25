import { Routes, Route } from "react-router-dom";
import { AuthProvider, ProtectedRoute } from "./features/auth/AuthContext";
import { CartProvider } from "./features/cart/CartContext";
import { WishlistProvider } from "./features/wishlist/WishlistContext";
import { ToastProvider } from "./components/ui/ToastProvider";
import { Home } from "./routes/Home";
import { Browse } from "./routes/Browse";
import { ProductDetail } from "./routes/ProductDetail";
import { Cart } from "./routes/Cart";
import { Checkout } from "./routes/Checkout";
import { OrderDetail } from "./routes/OrderDetail";
import { Wishlist } from "./routes/Wishlist";
import { Login } from "./routes/Login";
import { Register } from "./routes/Register";
import { Account } from "./routes/Account";
import { BecomeSeller } from "./routes/BecomeSeller";
import { Storefront } from "./routes/Storefront";

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <CartProvider>
          <WishlistProvider>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/products" element={<Browse />} />
              <Route path="/category/:slug" element={<Browse />} />
              <Route path="/product/:slug" element={<ProductDetail />} />
              <Route path="/cart" element={<Cart />} />
              <Route
                path="/checkout"
                element={
                  <ProtectedRoute>
                    <Checkout />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/orders/:number"
                element={
                  <ProtectedRoute>
                    <OrderDetail />
                  </ProtectedRoute>
                }
              />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/store/:slug" element={<Storefront />} />
              <Route
                path="/wishlist"
                element={
                  <ProtectedRoute>
                    <Wishlist />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/account"
                element={
                  <ProtectedRoute>
                    <Account />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/sell"
                element={
                  <ProtectedRoute>
                    <BecomeSeller />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Home />} />
            </Routes>
          </WishlistProvider>
        </CartProvider>
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;