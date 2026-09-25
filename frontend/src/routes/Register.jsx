import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Navbar } from "../components/layout/Navbar";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Alert } from "../components/ui/Alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/Card";
import { useAuth } from "../features/auth/AuthContext";
import { useRequiredFields } from "../lib/formErrors";

const REQUIRED_FIELDS = ["email", "password", "confirm"];

export function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: "",
    first_name: "",
    last_name: "",
    password: "",
    confirm: "",
  });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const { fieldErrors, validate, clearField, setFieldErrors } = useRequiredFields(form, REQUIRED_FIELDS);

  const set = (key) => (event) => {
    setForm((f) => ({ ...f, [key]: event.target.value }));
    clearField(key);
  };

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    // noValidate: required fields render our red inline messages, never the
    // browser's native bubble (server stays the gate, §10.1).
    if (!validate()) return;
    if (form.password !== form.confirm) {
      setFieldErrors({ confirm: ["Passwords do not match."] });
      return;
    }
    setBusy(true);
    try {
      const payload = {
        email: form.email,
        first_name: form.first_name,
        last_name: form.last_name,
        password: form.password,
      };
      await register(payload);
      navigate("/login", {
        replace: true,
        state: { registered: form.email },
      });
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
            <CardTitle>Create your account</CardTitle>
            <CardDescription>Join Jeyvro — handpicked local goods from independent sellers.</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <Alert tone="danger" title="Registration failed" className="mb-4">
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
                value={form.email}
                onChange={set("email")}
                error={fieldErrors.email?.[0]}
              />
              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="First name"
                  name="first_name"
                  autoComplete="given-name"
                  value={form.first_name}
                  onChange={set("first_name")}
                  error={fieldErrors.first_name?.[0]}
                />
                <Input
                  label="Last name"
                  name="last_name"
                  autoComplete="family-name"
                  value={form.last_name}
                  onChange={set("last_name")}
                  error={fieldErrors.last_name?.[0]}
                />
              </div>
              <Input
                label="Password"
                type="password"
                name="password"
                autoComplete="new-password"
                required
                value={form.password}
                onChange={set("password")}
                error={fieldErrors.password?.[0]}
                hint="At least 8 characters — not too common."
              />
              <Input
                label="Confirm password"
                type="password"
                name="confirm"
                autoComplete="new-password"
                required
                value={form.confirm}
                onChange={set("confirm")}
                error={fieldErrors.confirm?.[0]}
              />
              <Button type="submit" loading={busy} className="w-full">
                Create account
              </Button>
            </form>
          </CardContent>
        </Card>
        <p className="text-center text-sm text-sand-500 dark:text-sand-400">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-moss-700 hover:underline dark:text-moss-300">
            Log in
          </Link>
        </p>
      </main>
    </div>
  );
}
