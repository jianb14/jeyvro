import { Section, Demo } from "./shared";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "../components/ui/Card";
import { Table, THead, TH, TBody, TR, TD } from "../components/ui/Table";
import { Badge } from "../components/ui/Badge";
import { Avatar } from "../components/ui/Avatar";
import { Button } from "../components/ui/Button";
import { Kbd } from "../components/ui/Kbd";
import { Divider } from "../components/ui/Divider";
import { EditIcon, MoreHorizontalIcon, HeartIcon, ArrowRightIcon } from "../components/ui/Icons";

const MEMBERS = [
  { name: "Maria Santos", role: "Product Designer", status: "Active", tone: "success" },
  { name: "Juan Dela Cruz", role: "Frontend Dev", status: "Active", tone: "success" },
  { name: "Ana Lopez", role: "Product Manager", status: "Away", tone: "warning" },
  { name: "Paolo Mendoza", role: "QA Engineer", status: "Invited", tone: "info" },
];

export function DataDisplaySection() {
  return (
    <Section
      id="data-display"
      title="Data Display"
      description="Cards, tables, keyboard keys, at dividers — para malinis na pagpapakita ng data."
    >
      <Demo label="Cards">
        <div className="grid w-full gap-5 md:grid-cols-2">
          <Card hover>
            <CardHeader>
              <CardTitle>Team workspace</CardTitle>
              <CardDescription>Collaborate with your team in real time.</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-sand-600 dark:text-sand-300">
              Includes unlimited projects, version history, and shared component libraries.
            </CardContent>
            <CardFooter>
              <Button size="sm" trailingIcon={ArrowRightIcon}>Open workspace</Button>
              <Button size="sm" variant="ghost" leadingIcon={HeartIcon}>Save</Button>
            </CardFooter>
          </Card>

          <Card>
            <CardContent className="flex items-center gap-4 p-6">
              <Avatar name="Maria Santos" size="lg" status="online" />
              <div className="flex flex-1 flex-col">
                <p className="font-medium text-sand-900 dark:text-sand-100">Maria Santos</p>
                <p className="text-sm text-sand-500 dark:text-sand-400">Product Designer</p>
                <div className="mt-2 flex gap-2">
                  <Badge tone="success" variant="soft" size="sm" dot>Active</Badge>
                  <Badge tone="moss" variant="outline" size="sm">Admin</Badge>
                </div>
              </div>
              <Button variant="ghost" size="icon-sm" aria-label="More options"><MoreHorizontalIcon size={16} /></Button>
            </CardContent>
          </Card>
        </div>
      </Demo>

      <Demo label="Table" className="w-full">
        <Table>
          <THead>
            <tr>
              <TH>Member</TH>
              <TH>Role</TH>
              <TH>Status</TH>
              <TH className="text-right">Actions</TH>
            </tr>
          </THead>
          <TBody>
            {MEMBERS.map((m) => (
              <TR key={m.name}>
                <TD>
                  <span className="flex items-center gap-3">
                    <Avatar name={m.name} size="sm" />
                    <span className="font-medium text-sand-900 dark:text-sand-100">{m.name}</span>
                  </span>
                </TD>
                <TD>{m.role}</TD>
                <TD>
                  <Badge tone={m.tone} variant="soft" size="sm" dot>{m.status}</Badge>
                </TD>
                <TD className="text-right">
                  <span className="inline-flex justify-end gap-1">
                    <Button variant="ghost" size="icon-sm" aria-label={`Edit ${m.name}`}><EditIcon size={15} /></Button>
                    <Button variant="ghost" size="icon-sm" aria-label={`More for ${m.name}`}><MoreHorizontalIcon size={15} /></Button>
                  </span>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </Demo>

      <Demo label="Kbd & Divider">
        <div className="flex flex-wrap items-center gap-3">
          <Kbd>⌘</Kbd>
          <Kbd>K</Kbd>
          <Kbd>Shift</Kbd>
          <Kbd>Enter</Kbd>
          <Kbd>Esc</Kbd>
        </div>
        <div className="w-full">
          <Divider label="Section" />
          <p className="py-4 text-sm text-sand-500 dark:text-sand-400">Content after the labeled divider.</p>
          <Divider />
        </div>
      </Demo>
    </Section>
  );
}
