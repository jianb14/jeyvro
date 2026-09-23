import { Routes, Route } from "react-router-dom";
import { AuthProvider, ProtectedRoute } from "./features/auth/AuthContext";
import { Home } from "./routes/Home";
import { DesignSystem } from "./routes/DesignSystem";
import { Login } from "./routes/Login";
import { Register } from "./routes/Register";
import { Account } from "./routes/Account";

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/design-system" element={<DesignSystem />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/account"
          element={
            <ProtectedRoute>
              <Account />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Home />} />
      </Routes>
    </AuthProvider>
  );
}

export default App;

