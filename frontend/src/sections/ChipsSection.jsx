import { useState } from "react";
import { Section, Demo } from "./shared";
import { Chip } from "../components/ui/Chip";
import { Rating } from "../components/ui/Rating";
import { StarIcon, ZapIcon } from "../components/ui/Icons";

const TONES = ["neutral", "moss", "success", "warning", "danger", "info"];
const VARIANTS = ["soft", "solid", "outline"];

export function ChipsSection() {
  const [tags, setTags] = useState(["Design", "Frontend", "React", "Tailwind"]);
  const [picked, setPicked] = useState(new Set(["Urgent"]));
  const [rating, setRating] = useState(4);

  const togglePick = (label) => {
    setPicked((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  return (
    <Section
      id="chips"
      title="Chips, Tags & Rating"
      description="Chips para sa filters at labels, at star rating na may hover preview."
    >
      <Demo label="Chips — 6 tones × 3 variants">
        <div className="flex flex-col gap-3">
          {VARIANTS.map((variant) => (
            <div key={variant} className="flex flex-wrap items-center gap-2">
              {TONES.map((tone) => (
                <Chip key={tone} tone={tone} variant={variant} label={tone} />
              ))}
            </div>
          ))}
        </div>
      </Demo>

      <Demo label="Chips — removable">
        <div className="flex flex-wrap items-center gap-2">
          {tags.map((tag) => (
            <Chip
              key={tag}
              tone="moss"
              variant="soft"
              label={tag}
              removable
              onRemove={() => setTags((t) => t.filter((x) => x !== tag))}
            />
          ))}
          {tags.length === 0 && <p className="text-xs text-sand-400">Wala nang tags — refresh mo ang page para bumalik.</p>}
        </div>
      </Demo>

      <Demo label="Chips — selectable (click to toggle)">
        <div className="flex flex-wrap items-center gap-2">
          {["Urgent", "Bug", "Feature", "Docs", "Design"].map((label) => (
            <Chip
              key={label}
              label={label}
              dot
              selected={picked.has(label)}
              onClick={() => togglePick(label)}
            />
          ))}
        </div>
        <p className="mt-2 w-full text-xs text-sand-400">Selected: {[...picked].join(", ") || "wala"}</p>
      </Demo>

      <Demo label="Chips — sizes, icon & disabled">
        <Chip size="sm" tone="moss" label="Small" dot />
        <Chip size="md" tone="moss" label="Medium" />
        <Chip tone="warning" icon={ZapIcon} label="Lightning deal" />
        <Chip tone="neutral" icon={StarIcon} variant="outline" label="Starred" />
        <Chip tone="moss" label="Locked" disabled removable />
      </Demo>

      <Demo label="Rating">
        <div className="flex flex-col gap-4">
          <Rating value={rating} onChange={setRating} showValue />
          <Rating value={4} readonly />
          <Rating value={2} readonly size="sm" showValue />
          <Rating value={5} readonly size="lg" />
        </div>
      </Demo>
    </Section>
  );
}
