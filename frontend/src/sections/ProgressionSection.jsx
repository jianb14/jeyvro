import { useState } from "react";
import { Section, Demo } from "./shared";
import { Stepper } from "../components/ui/Stepper";
import { Timeline } from "../components/ui/Timeline";
import { Button } from "../components/ui/Button";
import {
  CheckCircleIcon,
  SendIcon,
  UserIcon,
  CreditCardIcon,
  PackageIcon,
  ClockIcon,
  XCircleIcon,
  BellIcon,
} from "../components/ui/Icons";

const STEPS = [
  { label: "Account", description: "Create your login" },
  { label: "Profile", description: "Tell us about you" },
  { label: "Team", description: "Invite teammates" },
  { label: "Billing", description: "Choose a plan" },
];

const TIMELINE = [
  {
    title: "Order placed",
    time: "9:00 AM",
    description: "Your order has been received.",
    tone: "moss",
    icon: CheckCircleIcon,
  },
  {
    title: "Payment confirmed",
    time: "9:02 AM",
    description: "GCash payment of ₱1,299.00 verified.",
    tone: "success",
    icon: CreditCardIcon,
  },
  {
    title: "Item shipped",
    time: "1:45 PM",
    description: "Package left the Pasig warehouse via JEX.",
    tone: "info",
    icon: SendIcon,
  },
  {
    title: "Out for delivery",
    time: "Tomorrow, 8:00 AM",
    description: "Courier Juan D. is on the way.",
    tone: "warning",
    icon: PackageIcon,
  },
];

const ACTIVITY = [
  {
    title: "Maria approved the design review",
    time: "2 hours ago",
    description: "Marked all 12 screens as approved.",
    tone: "success",
    icon: CheckCircleIcon,
  },
  {
    title: "Deploy failed on production",
    time: "5 hours ago",
    description: "Build error in checkout module - rollback completed.",
    tone: "danger",
    icon: XCircleIcon,
  },
  {
    title: "Juan joined the workspace",
    time: "Yesterday",
    description: "Invited by Christian as Frontend Developer.",
    tone: "info",
    icon: UserIcon,
  },
  {
    title: "Billing reminder",
    time: "2 days ago",
    description: "Your Pro plan renews in 7 days.",
    tone: "neutral",
    icon: BellIcon,
  },
];

export function ProgressionSection() {
  const [step, setStep] = useState(1);

  return (
    <Section
      id="progression"
      title="Steppers & Timeline"
      description="Multi-step progress at activity feeds — may completed, current, at upcoming states."
    >
      <Demo label="Stepper — horizontal (interactive)" className="w-full">
        <div className="w-full">
          <Stepper steps={STEPS} current={step} />
          <div className="mt-6 flex justify-center gap-3">
            <Button variant="outline" size="sm" disabled={step === 0} onClick={() => setStep((s) => Math.max(0, s - 1))}>
              Back
            </Button>
            <Button
              size="sm"
              disabled={step === STEPS.length - 1}
              onClick={() => setStep((s) => Math.min(STEPS.length - 1, s + 1))}
            >
              Next step
            </Button>
          </div>
        </div>
      </Demo>

      <Demo label="Stepper — vertical">
        <Stepper orientation="vertical" steps={STEPS} current={2} className="w-full max-w-sm" />
      </Demo>

      <Demo label="Timeline — order tracking">
        <div className="grid w-full gap-8 md:grid-cols-2">
          <Timeline items={TIMELINE} />
          <Timeline items={ACTIVITY} />
        </div>
      </Demo>

      <Demo label="Timeline — compact (no icons)">
        <Timeline
          className="w-full max-w-sm"
          items={[
            { title: "Draft created", time: "Mon", tone: "neutral" },
            { title: "Sent for review", time: "Tue", tone: "info" },
            { title: "Approved", time: "Wed", tone: "success" },
          ]}
        />
      </Demo>

      <Demo label="With icon only (decorative)">
        <div className="flex items-center gap-2 text-xs text-sand-400">
          <ClockIcon size={14} /> Timelines auto-trim the connector on the last item.
        </div>
      </Demo>
    </Section>
  );
}
