import { useState } from "react";
import { Section, Demo } from "./shared";
import { Checkbox } from "../components/ui/Checkbox";
import { Radio, RadioGroup } from "../components/ui/Radio";
import { Switch } from "../components/ui/Switch";

export function SelectionSection() {
  const [plan, setPlan] = useState("pro");
  const [prefs, setPrefs] = useState({ email: true, push: false, sms: true });

  return (
    <Section
      id="selection"
      title="Selection Controls"
      description="Checkbox (may indeterminate state), radio groups, at switches — controlled at uncontrolled."
    >
      <Demo label="Checkbox">
        <div className="flex flex-col gap-3">
          <Checkbox label="Email notifications" description="Get updates about your projects" defaultChecked />
          <Checkbox label="Push notifications" description="Real-time alerts on your device" />
          <Checkbox label="Select all" indeterminate />
          <Checkbox label="Disabled option" disabled />
          <Checkbox label="Disabled checked" disabled defaultChecked />
        </div>
      </Demo>

      <Demo label="Radio Group">
        <RadioGroup value={plan} onChange={setPlan}>
          <Radio value="starter" label="Starter" description="Free · 1 project" />
          <Radio value="pro" label="Pro" description="₱499/mo · Unlimited projects" />
          <Radio value="team" label="Team" description="₱1,299/mo · 10 seats" />
          <Radio value="enterprise" label="Enterprise" disabled description="Contact sales" />
        </RadioGroup>
        <p className="mt-2 text-xs text-sand-400">Selected: {plan}</p>
      </Demo>

      <Demo label="Switch">
        <div className="flex flex-col gap-4">
          <Switch
            label="Email updates"
            description={prefs.email ? "On — you'll receive weekly digests" : "Off"}
            checked={prefs.email}
            onChange={(v) => setPrefs((p) => ({ ...p, email: v }))}
          />
          <Switch
            label="Push notifications"
            checked={prefs.push}
            onChange={(v) => setPrefs((p) => ({ ...p, push: v }))}
          />
          <Switch
            label="SMS alerts"
            size="sm"
            checked={prefs.sms}
            onChange={(v) => setPrefs((p) => ({ ...p, sms: v }))}
          />
          <Switch label="Disabled on" defaultChecked disabled />
          <Switch label="Disabled off" disabled />
        </div>
      </Demo>
    </Section>
  );
}
