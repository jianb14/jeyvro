import { Section, Demo } from "./shared";
import { Input } from "../components/ui/Input";
import { Textarea } from "../components/ui/Textarea";
import { Select } from "../components/ui/Select";
import { Button } from "../components/ui/Button";
import { SearchIcon, MailIcon, EyeIcon } from "../components/ui/Icons";

export function FormsSection() {
  return (
    <Section
      id="forms"
      title="Form Controls"
      description="Inputs, textarea, at select na may label, hint, error, leading/trailing icons, sizes, at disabled states."
    >
      <Demo label="Input — variants & states" className="w-full">
        <div className="grid w-full gap-5 md:grid-cols-2">
          <Input label="Full name" placeholder="Juan Dela Cruz" hint="Your name as it appears on your ID." />
          <Input label="Email address" type="email" placeholder="juan@example.com" leadingIcon={MailIcon} />
          <Input label="Search" placeholder="Search components…" leadingIcon={SearchIcon} size="sm" />
          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            trailingIcon={EyeIcon}
            hint="Minimum 8 characters."
          />
          <Input label="Error state" defaultValue="juaneexample.com" error="Please enter a valid email address." leadingIcon={MailIcon} />
          <Input label="Disabled" placeholder="Not editable" disabled />
        </div>
      </Demo>

      <Demo label="Textarea & Select">
        <Textarea
          className="w-full sm:max-w-xs"
          label="Project description"
          placeholder="Describe your project…"
          rows={4}
          hint="Max 500 characters."
        />
        <Select className="w-full sm:max-w-xs" label="Role" defaultValue="">
          <option value="" disabled>
            Choose a role…
          </option>
          <option>Designer</option>
          <option>Developer</option>
          <option>Product Manager</option>
          <option>QA Engineer</option>
        </Select>
        <Select className="w-full sm:max-w-xs" label="Priority" defaultValue="high" error="Required field." size="sm">
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </Select>
        <Select className="w-full sm:max-w-xs" label="Disabled select" disabled>
          <option>Unavailable</option>
        </Select>
      </Demo>

      <Demo label="Sign-in Card — composed pattern">
        <form
          className="flex w-full max-w-sm flex-col gap-4"
          onSubmit={(e) => e.preventDefault()}
        >
          <Input label="Email" type="email" placeholder="juan@example.com" leadingIcon={MailIcon} required />
          <Input label="Password" type="password" placeholder="••••••••" required />
          <Button type="submit" className="mt-2 w-full">
            Sign in
          </Button>
        </form>
      </Demo>
    </Section>
  );
}
