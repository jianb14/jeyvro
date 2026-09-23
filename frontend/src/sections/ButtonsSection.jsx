import { Section, Demo } from "./shared";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Avatar, AvatarGroup } from "../components/ui/Avatar";
import {
  PlusIcon,
  DownloadIcon,
  ArrowRightIcon,
  MailIcon,
  HeartIcon,
  TrashIcon,
  StarIcon,
} from "../components/ui/Icons";

const VARIANTS = ["primary", "secondary", "outline", "ghost", "destructive", "link"];

export function ButtonsSection() {
  return (
    <Section
      id="buttons"
      title="Buttons & Badges"
      description="Anim na button variants sa tatlong sizes, may loading, disabled, at icon support. Kasama rin ang badges at avatars."
    >
      <Demo label="Button Variants">
        {VARIANTS.map((v) => (
          <Button key={v} variant={v}>
            {v.charAt(0).toUpperCase() + v.slice(1)}
          </Button>
        ))}
      </Demo>

      <Demo label="Sizes">
        <Button size="sm" variant="primary">Small</Button>
        <Button size="md" variant="primary">Medium</Button>
        <Button size="lg" variant="primary">Large</Button>
        <Button size="sm" variant="outline">Small</Button>
        <Button size="lg" variant="outline">Large</Button>
      </Demo>

      <Demo label="With Icons">
        <Button leadingIcon={PlusIcon}>New project</Button>
        <Button variant="secondary" leadingIcon={DownloadIcon}>Export</Button>
        <Button variant="outline" trailingIcon={ArrowRightIcon}>Continue</Button>
        <Button variant="ghost" leadingIcon={MailIcon}>Invite</Button>
        <Button variant="destructive" leadingIcon={TrashIcon}>Delete</Button>
      </Demo>

      <Demo label="States">
        <Button loading>Saving…</Button>
        <Button disabled>Disabled</Button>
        <Button variant="outline" disabled>Disabled</Button>
        <Button variant="ghost" loading>Loading</Button>
      </Demo>

      <Demo label="Icon Buttons">
        <Button variant="primary" size="icon" aria-label="Add"><PlusIcon size={18} /></Button>
        <Button variant="secondary" size="icon" aria-label="Favorite"><HeartIcon size={18} /></Button>
        <Button variant="outline" size="icon" aria-label="Star"><StarIcon size={18} /></Button>
        <Button variant="ghost" size="icon-sm" aria-label="Download"><DownloadIcon size={16} /></Button>
        <Button variant="destructive" size="icon-sm" aria-label="Delete"><TrashIcon size={16} /></Button>
      </Demo>

      <Demo label="Badges — 6 tones × 3 variants">
        <div className="flex flex-col gap-3">
          {["solid", "soft", "outline"].map((variant) => (
            <div key={variant} className="flex flex-wrap items-center gap-2">
              {["neutral", "moss", "success", "warning", "danger", "info"].map((tone) => (
                <Badge key={tone} tone={tone} variant={variant}>{tone}</Badge>
              ))}
            </div>
          ))}
        </div>
      </Demo>

      <Demo label="Badges — with dot & icon">
        <Badge dot>Active</Badge>
        <Badge tone="success" dot variant="soft">Published</Badge>
        <Badge tone="warning" dot variant="soft">Pending review</Badge>
        <Badge tone="danger" dot variant="soft">Failed</Badge>
        <Badge tone="info" icon={StarIcon} variant="outline">Featured</Badge>
        <Badge tone="moss" size="sm" dot>Small</Badge>
      </Demo>

      <Demo label="Avatars">
        <Avatar name="Maria Santos" size="xs" />
        <Avatar name="Juan Dela Cruz" size="sm" status="online" />
        <Avatar name="Christian Reyes" size="md" status="away" />
        <Avatar name="Ana Lopez" size="lg" status="busy" />
        <Avatar name="Jeyvro Team" size="xl" status="online" />
      </Demo>

      <Demo label="Avatar Group">
        <AvatarGroup
          size="md"
          people={[
            { name: "Maria Santos" },
            { name: "Juan Dela Cruz" },
            { name: "Ana Lopez" },
            { name: "Christian Reyes" },
            { name: "Paolo Mendoza" },
            { name: "Liza Soberano" },
          ]}
        />
      </Demo>
    </Section>
  );
}
