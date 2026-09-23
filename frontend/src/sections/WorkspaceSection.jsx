import { useEffect, useState } from "react";
import { Section, Demo } from "./shared";
import { FileUpload, FileList } from "../components/ui/FileUpload";
import { EmptyState } from "../components/ui/EmptyState";
import { Drawer } from "../components/ui/Drawer";
import { CommandPalette } from "../components/ui/CommandPalette";
import { Button } from "../components/ui/Button";
import {
  InboxIcon,
  SearchIcon,
  PlusIcon,
  UploadIcon,
  SettingsIcon,
  HomeIcon,
  MoonIcon,
  LogOutIcon,
  FileIcon,
  UserIcon,
} from "../components/ui/Icons";

const COMMAND_GROUPS = [
  {
    group: "Actions",
    items: [
      { label: "New project", icon: PlusIcon, shortcut: "N", onSelect: () => {} },
      { label: "Upload file", icon: UploadIcon, shortcut: "U", onSelect: () => {} },
      { label: "New document", icon: FileIcon, onSelect: () => {} },
    ],
  },
  {
    group: "Navigation",
    items: [
      { label: "Go to Overview", icon: HomeIcon, onSelect: () => {} },
      { label: "Open Form Controls", icon: FileIcon, onSelect: () => {} },
      { label: "View members", icon: UserIcon, onSelect: () => {} },
    ],
  },
  {
    group: "Settings",
    items: [
      { label: "Toggle dark mode", icon: MoonIcon, shortcut: "T", onSelect: () => {} },
      { label: "Open settings", icon: SettingsIcon, shortcut: "S", onSelect: () => {} },
      { label: "Log out", icon: LogOutIcon, onSelect: () => {} },
    ],
  },
];

export function WorkspaceSection() {
  const [files, setFiles] = useState([]);
  const [drawer, setDrawer] = useState(null);
  const [palette, setPalette] = useState(false);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPalette((o) => !o);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const addFiles = (incoming) => {
    setFiles((prev) => [
      ...prev,
      ...incoming.map((f, i) => ({ id: `${Date.now()}-${i}`, name: f.name, size: f.size })),
    ]);
  };

  return (
    <Section
      id="workspace"
      title="Workspace Patterns"
      description="File upload, empty states, drawers, at command palette — ang mga kapanahunang pattern ng app."
    >
      <Demo label="File Upload — drag & drop (functional)" className="w-full">
        <div className="flex w-full flex-col gap-4">
          <FileUpload onFiles={addFiles} />
          <FileList files={files} onRemove={(id) => setFiles((f) => f.filter((x) => x.id !== id))} />
        </div>
      </Demo>

      <Demo label="Empty States">
        <div className="grid w-full gap-5 md:grid-cols-2">
          <EmptyState
            icon={InboxIcon}
            title="Walang messages pa"
            description="Kapag may nagpadala ng message, makikita rito ang preview."
            action={
              <Button size="sm" variant="outline">
                Adjust filters
              </Button>
            }
          />
          <EmptyState
            compact
            icon={SearchIcon}
            title="No results found"
            description="Try a different keyword or clear the filters."
            action={
              <Button size="sm" variant="secondary">
                Clear filters
              </Button>
            }
          />
        </div>
      </Demo>

      <Demo label="Drawer — side panels">
        <Button variant="outline" onClick={() => setDrawer("right")}>
          Open right drawer
        </Button>
        <Button variant="outline" onClick={() => setDrawer("left")}>
          Open left drawer
        </Button>

        <Drawer
          open={drawer === "right"}
          onClose={() => setDrawer(null)}
          side="right"
          title="Workspace settings"
          description="Manage your team and preferences."
          footer={
            <>
              <Button variant="ghost" onClick={() => setDrawer(null)}>
                Cancel
              </Button>
              <Button onClick={() => setDrawer(null)}>Save changes</Button>
            </>
          }
        >
          <p className="leading-relaxed">
            Ang drawer ay slide-in panel mula sa kanan — perfect para sa settings, details, at
            quick edits nang hindi nawawala ang page context. Pindutin ang <b>Esc</b> o i-click
            ang backdrop para magsara.
          </p>
        </Drawer>

        <Drawer
          open={drawer === "left"}
          onClose={() => setDrawer(null)}
          side="left"
          size="sm"
          title="Navigation"
          description="Slide mula sa kaliwa."
        >
          <p className="leading-relaxed">Kasing-gawi ng mobile nav drawers — may backdrop blur din.</p>
        </Drawer>
      </Demo>

      <Demo label="Command Palette — press Ctrl+K anywhere">
        <Button onClick={() => setPalette(true)} leadingIcon={SearchIcon}>
          Open command palette
        </Button>
        <p className="w-full text-xs text-sand-400">
          May keyboard shortcut: <b>Ctrl+K</b>. Gamitin ang <b>↑ ↓</b> para mag-navigate at{" "}
          <b>Enter</b> para pumili.
        </p>

        <CommandPalette open={palette} onClose={() => setPalette(false)} groups={COMMAND_GROUPS} />
      </Demo>
    </Section>
  );
}
