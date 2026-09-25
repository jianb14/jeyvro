import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Navbar } from "../components/layout/Navbar";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Alert } from "../components/ui/Alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/Card";
import { useAuth } from "../features/auth/AuthContext";
import { useRequiredFields } from "../lib/formErrors";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from || "/account";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const { fieldErrors, validate, clearField, setFieldErrors } = useRequiredFields(
    { email, password },
    ["email", "password"]
  );

  const changeEmail = (event) => {
    setEmail(event.target.value);
    clearField("email");
  };

  const changePassword = (event) => {
    setPassword(event.target.value);
    clearField("password");
  };

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    // The form is noValidate: missing fields show our red inline messages
    // instead of the browser's native bubble (server stays the gate, §10.1).
    if (!validate()) return;
    setBusy(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.data?.detail || err.data?.error || err.message);
      setFieldErrors(err.data?.field_errors || {});
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-sand-50 dark:bg-night-950">
      <Navbar />
      <main className="mx-auto flex max-w-md flex-col gap-6 px-4 py-16">
        <Card>
          <CardHeader>
            <CardTitle>Welcome back</CardTitle>
            <CardDescription>Log in to your Jeyvro account.</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <Alert tone="danger" title="Login failed" className="mb-4">
                {error}
              </Alert>
            )}
            <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
              <Input
                label="Email"
                type="email"
                name="email"
                autoComplete="email"
                required
                value={email}
                onChange={changeEmail}
                error={fieldErrors.email?.[0]}
              />
              <Input
                label="Password"
                type="password"
                name="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={changePassword}
                error={fieldErrors.password?.[0]}
              />
              <Button type="submit" loading={busy} className="w-full">
                Log in
              </Button>
            </form>
          </CardContent>
        </Card>
        <p className="text-center text-sm text-sand-500 dark:text-sand-400">
          New to Jeyvro?{" "}
          <Link to="/register" className="font-medium text-moss-700 hover:underline dark:text-moss-300">
            Create an account
          </Link>
        </p>
      </main>
    </div>
  );
}
