import { useState } from "react";
import { Section, Demo } from "./shared";
import { Modal } from "../components/ui/Modal";
import { Tooltip } from "../components/ui/Tooltip";
import { DropdownMenu, MenuButton } from "../components/ui/DropdownMenu";
import { Button } from "../components/ui/Button";
import { TrashIcon, EditIcon, CopyIcon, DownloadIcon, ExternalLinkIcon } from "../components/ui/Icons";

export function OverlaysSection() {
  const [modal, setModal] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [choice, setChoice] = useState("None yet");

  return (
    <Section
      id="overlays"
      title="Overlays"
      description="Modals, tooltips, at dropdown menus — may keyboard support (ESC), backdrop close, at focus outlines."
    >
      <Demo label="Modal">
        <Button onClick={() => setModal(true)}>Open modal</Button>
        <Button variant="outline" onClick={() => setConfirm(true)}>Open confirm dialog</Button>

        <Modal
          open={modal}
          onClose={() => setModal(false)}
          title="Invite your team"
          description="Send an invite link so teammates can join this workspace."
          footer={
            <>
              <Button variant="ghost" onClick={() => setModal(false)}>Cancel</Button>
              <Button onClick={() => setModal(false)}>Send invite</Button>
            </>
          }
        >
          <p className="leading-relaxed">
            Teammates will get view and edit access to all shared projects. You can change
            permissions anytime from workspace settings.
          </p>
        </Modal>

        <Modal
          open={confirm}
          onClose={() => setConfirm(false)}
          size="sm"
          title="Delete project?"
          description="This action cannot be undone."
          footer={
            <>
              <Button variant="ghost" onClick={() => setConfirm(false)}>Keep it</Button>
              <Button variant="destructive" onClick={() => setConfirm(false)}>Delete forever</Button>
            </>
          }
        >
          <p>The project “Jeyvro Website” and all of its pages will be permanently removed.</p>
        </Modal>
      </Demo>

      <Demo label="Tooltips — 4 placements">
        <Tooltip content="Tooltip sa itaas" placement="top">
          <Button variant="outline">Top</Button>
        </Tooltip>
        <Tooltip content="Tooltip sa ibaba" placement="bottom">
          <Button variant="outline">Bottom</Button>
        </Tooltip>
        <Tooltip content="Tooltip sa kaliwa" placement="left">
          <Button variant="outline">Left</Button>
        </Tooltip>
        <Tooltip content="Tooltip sa kanan" placement="right">
          <Button variant="outline">Right</Button>
        </Tooltip>
      </Demo>

      <Demo label="Dropdown Menu">
        <div className="flex flex-col items-start gap-3">
          <div className="flex flex-wrap gap-4">
            <DropdownMenu
              trigger={<MenuButton>Actions</MenuButton>}
              items={[
                { key: "edit", label: "Edit", icon: EditIcon, shortcut: "⌘E", onSelect: () => setChoice("Edit") },
                { key: "duplicate", label: "Duplicate", icon: CopyIcon, shortcut: "⌘D", onSelect: () => setChoice("Duplicate") },
                { key: "export", label: "Export", icon: DownloadIcon, onSelect: () => setChoice("Export") },
                { key: "sep", divider: true },
                { key: "visit", label: "Visit docs", icon: ExternalLinkIcon, onSelect: () => setChoice("Visit docs") },
                { key: "delete", label: "Delete", icon: TrashIcon, tone: "danger", onSelect: () => setChoice("Delete") },
              ]}
            />
            <DropdownMenu
              align="end"
              trigger={<Button variant="secondary">Overflow menu</Button>}
              items={[
                { key: "a", label: "Archive project", onSelect: () => setChoice("Archive") },
                { key: "b", label: "Move to folder", onSelect: () => setChoice("Move") },
                { key: "sep", divider: true },
                { key: "c", label: "Delete project", icon: TrashIcon, tone: "danger", onSelect: () => setChoice("Delete") },
              ]}
            />
          </div>
          <p className="text-xs text-sand-400">Last action: {choice}</p>
        </div>
      </Demo>
    </Section>
  );
}
