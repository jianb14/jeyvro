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
import { Orders } from "./routes/Orders";
import { Receipt } from "./routes/Receipt";
import { Wishlist } from "./routes/Wishlist";
import { Login } from "./routes/Login";
import { Register } from "./routes/Register";
import { Account } from "./routes/Account";
import { BecomeSeller } from "./routes/BecomeSeller";
import { Storefront } from "./routes/Storefront";
import { SellerLayout } from "./routes/seller/SellerLayout";
import { SellerDashboard } from "./routes/seller/SellerDashboard";
import { SellerProducts } from "./routes/seller/SellerProducts";
import { SellerProductEdit } from "./routes/seller/SellerProductEdit";
import { SellerInventory } from "./routes/seller/SellerInventory";
import { SellerOrders } from "./routes/seller/SellerOrders";
import { SellerOrderDetail } from "./routes/seller/SellerOrderDetail";
import { SellerStoreSettings } from "./routes/seller/SellerStoreSettings";
import { StaffLayout } from "./routes/staff/StaffLayout";
import { StaffSellerApplications } from "./routes/staff/StaffSellerApplications";
import { StaffStores } from "./routes/staff/StaffStores";
import { StaffUsers } from "./routes/staff/StaffUsers";
import { StaffTeam } from "./routes/staff/StaffTeam";
import { StaffAuditLog } from "./routes/staff/StaffAuditLog";
import { StaffCatalog } from "./routes/staff/StaffCatalog";
import { StaffTaxonomy } from "./routes/staff/StaffTaxonomy";
import { StaffOrders } from "./routes/staff/StaffOrders";
import { StaffPayments } from "./routes/staff/StaffPayments";

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
                path="/orders"
                element={
                  <ProtectedRoute>
                    <Orders />
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
              <Route
                path="/orders/:number/receipt"
                element={
                  <ProtectedRoute>
                    <Receipt />
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
              <Route
                path="/seller"
                element={
                  <ProtectedRoute>
                    <SellerLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<SellerDashboard />} />
                <Route path="products" element={<SellerProducts />} />
                <Route path="products/new" element={<SellerProductEdit />} />
                <Route path="products/:id" element={<SellerProductEdit />} />
                <Route path="inventory" element={<SellerInventory />} />
                <Route path="orders" element={<SellerOrders />} />
                <Route path="orders/:id" element={<SellerOrderDetail />} />
                <Route path="settings" element={<SellerStoreSettings />} />
              </Route>
              <Route
                path="/staff"
                element={
                  <ProtectedRoute>
                    <StaffLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<StaffSellerApplications />} />
                <Route path="stores" element={<StaffStores />} />
                <Route path="catalog" element={<StaffCatalog />} />
                <Route path="taxonomy" element={<StaffTaxonomy />} />
                <Route path="orders" element={<StaffOrders />} />
                <Route path="payments" element={<StaffPayments />} />
                <Route path="users" element={<StaffUsers />} />
                <Route path="team" element={<StaffTeam />} />
                <Route path="audit" element={<StaffAuditLog />} />
              </Route>
              <Route path="*" element={<Home />} />
            </Routes>
          </WishlistProvider>
        </CartProvider>
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;