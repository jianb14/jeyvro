import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthCard, AuthShell } from "../components/layout/AuthShell";
import { Button } from "../components/ui/Button";
import { Checkbox } from "../components/ui/Checkbox";
import { Input } from "../components/ui/Input";
import { PasswordInput } from "../components/ui/PasswordInput";
import { Alert } from "../components/ui/Alert";
import { useToast } from "../components/ui/ToastProvider";
import {
  AlertCircleIcon,
  LeafIcon,
  ShieldCheckIcon,
  StoreIcon,
  UserPlusIcon,
} from "../components/ui/Icons";
import { useAuth } from "../features/auth/AuthContext";
import { useRequiredFields } from "../lib/formErrors";

const REQUIRED_FIELDS = ["email", "password", "confirm"];

// A policy name inside the terms checkbox label.
//
// `Checkbox` wraps its whole label in a `<label for>`, so anything clickable
// placed inside that label is a real hazard: clicking the link would also fire
// the label's activation and tick the box, which is not what someone reading
// "Privacy Policy" expects to happen. A nested `<a>`/`<button>` is invalid HTML
// inside a label anyway.
//
// So this is a `<span>` styled as a link, and the *label's* click is what does
// the work — the text is announced and reachable as part of the checkbox, and
// `onClick` on the span reports the intent via a toast instead of navigating.
// That keeps one honest affordance (the toast) without nesting interactive
// elements or silently ticking the box.
function PolicyLink({ children, onClick }) {
  return (
    <span
      role="link"
      tabIndex={0}
      onClick={(event) => {
        event.preventDefault();
        // Stop the click reaching the wrapping <label>, which would toggle the
        // checkbox as a side effect of asking to read the policy.
        event.stopPropagation();
        onClick();
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          event.stopPropagation();
          onClick();
        }
      }}
      className="cursor-pointer rounded font-medium text-moss-700 underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:text-moss-300 dark:focus-visible:outline-moss-400"
    >
      {children}
    </span>
  );
}

// A seller packing a customer's order. This panel is addressed at the half of
// the audience that came here to *sell*, so the picture has to show the work —
// boxes, a rail of stock, hands in use — rather than the finished product on a
// shelf, which is the shopper's half of the story (and the login panel's job).
//
// Landscape source, so `position` matters more here than on /login: the default
// centre crop would keep the boxes and lose her, and she is the point. The
// anchor lifts the band to hold her head, shoulders and the parcel together.
const REGISTER_PHOTO = {
  src: "https://images.pexels.com/photos/7857535/pexels-photo-7857535.jpeg?auto=compress&cs=tinysrgb&w=1200",
  width: 1200,
  height: 800,
  alt: "",
  position: "object-[50%_38%]",
};

// The promise is deliberately two-sided. A sign-up form that only sells
// "browse nice things" wastes the half of the audience that came here to sell.
const REGISTER_HIGHLIGHTS = [
  {
    icon: StoreIcon,
    title: "Open a shop, free",
    body: "List your goods and set your own prices — no listing fees.",
  },
  {
    icon: LeafIcon,
    title: "Sell what you actually make",
    body: "Handmade, local and small-batch all belong on Jeyvro.",
  },
  {
    icon: ShieldCheckIcon,
    title: "Protected payments",
    body: "Funds are only released once the order is on its way.",
  },
];

export function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const { push } = useToast();

  const [form, setForm] = useState({
    email: "",
    first_name: "",
    last_name: "",
    password: "",
    confirm: "",
  });
  // Held outside `form` on purpose: the terms box is a boolean, and
  // `requiredErrors` treats any non-blank string as filled, so routing it
  // through the same required-fields bucket would let `"false"` pass as a
  // value. It is gated explicitly below instead.
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [termsError, setTermsError] = useState(null);
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
    // Gated last, so a user who has not touched the form is told about the
    // empty fields first rather than the checkbox, and the message sits next to
    // the control that caused it (ux-patterns: feedback lives near the action).
    if (!acceptedTerms) {
      setTermsError("Please accept the Terms and Privacy Policy to continue.");
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
    <AuthShell
      photo={REGISTER_PHOTO}
      eyebrow="Join Jeyvro"
      headline="Sell your craft, or find your next favourite thing."
      blurb="One account for shoppers and independent sellers alike — no listing fees, ever."
      highlights={REGISTER_HIGHLIGHTS}
    >
      <AuthCard
        title="Create your account"
        description="It takes under a minute, and you can start selling straight away."
        footer={
          <>
            Already have an account?{" "}
            <Link
              to="/login"
              className="rounded font-medium text-moss-700 underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:text-moss-300 dark:focus-visible:outline-moss-400"
            >
              Log in
            </Link>
          </>
        }
      >
        {error && (
          <Alert tone="danger" title="Registration failed">
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
          <PasswordInput
            label="Password"
            name="password"
            autoComplete="new-password"
            required
            value={form.password}
            onChange={set("password")}
            error={fieldErrors.password?.[0]}
            hint="At least 8 characters — not too common."
          />
          <PasswordInput
            label="Confirm password"
            name="confirm"
            autoComplete="new-password"
            required
            value={form.confirm}
            onChange={set("confirm")}
            error={fieldErrors.confirm?.[0]}
          />
          {/* Both password fields get a reveal. The mock only shows one, but a
              form that lets you check the password and not the confirmation is
              strictly worse than one that does neither — and since each field
              owns its own state, revealing one never reveals the other. */}
          <div className="flex flex-col gap-1.5">
            <Checkbox
              label={
                <span className="flex flex-wrap items-center gap-x-1">
                  <span>I agree to the</span>
                  <PolicyLink onClick={() => push({
                    tone: "info",
                    title: "Terms and Conditions are not published yet",
                  })}>Terms and Conditions</PolicyLink>
                  <span>and</span>
                  <PolicyLink onClick={() => push({
                    tone: "info",
                    title: "The Privacy Policy is not published yet",
                  })}>Privacy Policy</PolicyLink>
                </span>
              }
              checked={acceptedTerms}
              onChange={(event) => {
                setAcceptedTerms(event.target.checked);
                if (event.target.checked) setTermsError(null);
              }}
              aria-describedby={termsError ? "terms-error" : undefined}
            />
            {termsError && (
              <p
                id="terms-error"
                className="flex items-center gap-1.5 text-xs font-medium text-danger-600 dark:text-danger-400"
              >
                <AlertCircleIcon size={14} className="shrink-0" />
                {termsError}
              </p>
            )}
          </div>
          <Button
            type="submit"
            size="lg"
            loading={busy}
            leadingIcon={UserPlusIcon}
            className="mt-1 w-full"
          >
            Create account
          </Button>
        </form>
      </AuthCard>
    </AuthShell>
  );
}
