import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AuthCard, AuthShell } from "../components/layout/AuthShell";
import { Button } from "../components/ui/Button";
import { Checkbox } from "../components/ui/Checkbox";
import { Divider } from "../components/ui/Divider";
import { Input } from "../components/ui/Input";
import { PasswordInput } from "../components/ui/PasswordInput";
import { Alert } from "../components/ui/Alert";
import { useToast } from "../components/ui/ToastProvider";
import {
  FacebookIcon,
  GoogleIcon,
  HeartIcon,
  LogInIcon,
  MessageSquareIcon,
  TruckIcon,
} from "../components/ui/Icons";
import { useAuth } from "../features/auth/AuthContext";
import { useRequiredFields } from "../lib/formErrors";
import { postLoginRoute } from "../lib/postLoginRoute";

// A shopper mid-purchase: bags in one hand, phone in the other. The split panel
// on this route is making a promise about the *store* ("your orders, saved finds
// and seller messages are waiting"), so the picture has to show somebody
// actually shopping rather than an abstract product shot — it is the same
// argument the homepage hero makes, pointed at a different moment in the story.
//
// Same remote-and-swappable trade as the hero and the register panel: a URL the
// shop owner can change without a deploy, requested at a width that suits a
// half-screen column. `position` is the crop anchor (see ArtworkColumn) — this
// is a full-length portrait, so the band that keeps her face and the bags in
// frame is the upper-middle of the source.
const LOGIN_PHOTO = {
  src: "https://images.pexels.com/photos/6567495/pexels-photo-6567495.jpeg?auto=compress&cs=tinysrgb&w=1200",
  width: 1200,
  height: 1800,
  alt: "",
  position: "object-[50%_22%]",
};

const LOGIN_HIGHLIGHTS = [
  {
    icon: TruckIcon,
    title: "Track every order",
    body: "Follow your parcel from the seller's shelf to your door.",
  },
  {
    icon: MessageSquareIcon,
    title: "Message your sellers",
    body: "Ask about sizes, materials or shipping — all in one thread.",
  },
  {
    icon: HeartIcon,
    title: "Keep your wishlist",
    body: "Saved finds stay put, so they are still there when you come back.",
  },
];

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { push } = useToast();
  // No hardcoded fallback here — postLoginRoute() decides the landing page
  // from the account's role when nobody was bounced off a specific page.
  const from = location.state?.from;

  // Password reset and social sign-in are not built yet — there is no reset
  // endpoint and no OAuth client on the backend. Rather than render controls
  // that go nowhere (`href="#"` scrolls to top and lies about being a link) or
  // silently do nothing, each one says so. A toast is the honest affordance:
  // the control is real, focusable, and explains itself instead of appearing
  // broken. Each is `type="button"` so it can never submit the form.
  const comingSoon = (what) =>
    push({
      tone: "info",
      title: `${what} is not available yet`,
      description: "Use your email and password to sign in for now.",
    });

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  // Kept in React state only. The backend has no `remember` parameter and issues
  // a plain session cookie, so nothing is persisted client-side either — this
  // exists so the control is honest about being a real checkbox that really
  // holds a value, ready to be sent the moment the API grows the parameter.
  const [rememberMe, setRememberMe] = useState(false);
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
      // The login payload is the full user record (roles included), so the
      // landing page is chosen from real session truth rather than guessed.
      const me = await login(email, password);
      navigate(postLoginRoute(me, from), { replace: true });
    } catch (err) {
      setError(err.data?.detail || err.data?.error || err.message);
      setFieldErrors(err.data?.field_errors || {});
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      photo={LOGIN_PHOTO}
      eyebrow="Welcome back"
      headline="Pick up right where you left off."
      blurb="Your orders, saved finds and seller messages are waiting for you."
      highlights={LOGIN_HIGHLIGHTS}
    >
      <AuthCard
        title="Welcome back"
        description="Log in to pick up your orders, saved finds and messages."
        footer={
          <>
            New to Jeyvro?{" "}
            <Link
              to="/register"
              className="rounded font-medium text-moss-700 underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:text-moss-300 dark:focus-visible:outline-moss-400"
            >
              Create an account
            </Link>
          </>
        }
      >
        {error && (
          <Alert tone="danger" title="Login failed">
            {error}
          </Alert>
        )}
        <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
          {/* No envelope icon in the field. The `type="email"` already gives the
              browser its own address affordance and the mobile keypad, and a
              decorative glyph that repeats the label one line above it is
              padding, not information. Dropping it also lets the typed address
              start at the same left edge as every other field on the page. */}
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
          {/* The reveal toggle lives inside PasswordInput's trailing slot, which
              is also what reserves the `pr-10` that keeps the typed value from
              running under the eye glyph. Forgot-password rides the label row
              via `labelAction` — it is a rescue for *this* field, so it belongs
              on the field's header rather than adrift below it. */}
          <PasswordInput
            label="Password"
            name="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={changePassword}
            error={fieldErrors.password?.[0]}
            labelAction={
              <button
                type="button"
                onClick={() => comingSoon("Password reset")}
                className="rounded text-xs font-medium text-sand-500 underline-offset-4 transition-colors hover:text-moss-700 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:text-sand-400 dark:hover:text-moss-300 dark:focus-visible:outline-moss-400"
              >
                Forgot password?
              </button>
            }
          />
          <Checkbox
            label="Remember me"
            checked={rememberMe}
            onChange={(event) => setRememberMe(event.target.checked)}
            className="-mt-1"
          />
          <Button type="submit" size="lg" loading={busy} leadingIcon={LogInIcon} className="mt-1 w-full">
            Log in
          </Button>

          <div className="mt-2 flex flex-col gap-4">
            <Divider label="or log in with" />
            <div className="grid grid-cols-2 gap-3">
              <Button
                type="button"
                variant="outline"
                size="lg"
                onClick={() => comingSoon("Google sign-in")}
                leadingIcon={GoogleIcon}
              >
                Google
              </Button>
              <Button
                type="button"
                variant="outline"
                size="lg"
                onClick={() => comingSoon("Facebook sign-in")}
                leadingIcon={FacebookIcon}
              >
                Facebook
              </Button>
            </div>
          </div>
        </form>
      </AuthCard>
    </AuthShell>
  );
}
