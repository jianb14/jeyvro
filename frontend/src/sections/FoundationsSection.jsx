import { Demo, Section } from "./shared";

const SCALES = [
  { name: "Moss — Brand", shades: ["#f3f7f0", "#e4ecdc", "#cad9bf", "#a7c096", "#84a471", "#678a53", "#4f6d3f", "#405734", "#35462c", "#2d3b27", "#151f10"] },
  { name: "Sand — Neutral", shades: ["#faf9f6", "#f2f0ea", "#e5e1d6", "#d3ccbb", "#b7ad97", "#a1937a", "#89795f", "#6e614c", "#574e3f", "#474035", "#2a261f"] },
  { name: "Success", shades: ["#f0f7f1", "#dcecdc", "#bcdabb", "#92c194", "#67a46c", "#4a8a53", "#3a6f43", "#305937", "#29472f", "#233b29", "#102116"] },
  { name: "Warning", shades: ["#fbf7ef", "#f5ebd6", "#ead4ab", "#ddb97c", "#d0a054", "#c28c40", "#a67332", "#855a2b", "#6d492a", "#5c3d26", "#351f13"] },
  { name: "Danger", shades: ["#fbf3f2", "#f6e3e1", "#eecfcb", "#e0aca6", "#d08880", "#c26b62", "#ad544b", "#904440", "#773c3a", "#653635", "#381918"] },
  { name: "Info", shades: ["#f2f7fa", "#e3edf4", "#c8ddec", "#a2c5de", "#7aa9cd", "#5c8fb9", "#4b759f", "#405f83", "#3a506d", "#34455c", "#1e2a3a"] },
];

const STEPS = ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"];

function SwatchRow({ scale }) {
  return (
    <div>
      <p className="mb-2 text-sm font-medium text-sand-800 dark:text-sand-200">{scale.name}</p>
      <div className="flex overflow-hidden rounded-xl border border-sand-200 dark:border-night-800">
        {scale.shades.map((hex, i) => (
          <div key={hex} className="group relative h-14 flex-1" style={{ backgroundColor: hex }} title={`${scale.name} ${STEPS[i]} · ${hex}`}>
            <span className="absolute inset-x-0 bottom-1 hidden text-center text-[9px] font-medium text-white mix-blend-difference group-hover:block">
              {STEPS[i]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function FoundationsSection() {
  return (
    <Section
      id="foundations"
      title="Foundations"
      description="Ang brand base ng Jeyvro — calm na moss green, mainit na sand neutrals, at malalambot na semantic tones. Walang gradients, walang sakit sa mata."
    >
      <Demo label="Color Palette">
        <div className="flex w-full flex-col gap-5">
          {SCALES.map((s) => (
            <SwatchRow key={s.name} scale={s} />
          ))}
        </div>
      </Demo>

      <Demo label="Typography — Plus Jakarta Sans Display + Outfit Body">
        <div className="flex w-full flex-col gap-5">
          <div className="border-b border-sand-200 pb-4 dark:border-night-800">
            <p className="font-display text-4xl font-semibold tracking-tight text-sand-900 dark:text-sand-100">Design with calm intent.</p>
            <p className="mt-1 text-xs text-sand-400">Plus Jakarta Sans · 600 · Display headings</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="font-display text-2xl font-semibold text-sand-900 dark:text-sand-100">Heading / H2</p>
              <p className="mt-1 text-xs text-sand-400">Plus Jakarta Sans · 24px · 600</p>
            </div>
            <div>
              <p className="font-display text-xl font-semibold text-sand-900 dark:text-sand-100">Heading / H3</p>
              <p className="mt-1 text-xs text-sand-400">Plus Jakarta Sans · 20px · 600</p>
            </div>
            <div>
              <p className="text-base text-sand-700 dark:text-sand-300">Body text — ang Outfit ay malinis at readable kahit maliit.</p>
              <p className="mt-1 text-xs text-sand-400">Outfit · 16px · 400</p>
            </div>
            <div>
              <p className="text-sm text-sand-700 dark:text-sand-300">Secondary body — para sa descriptions at helper text.</p>
              <p className="mt-1 text-xs text-sand-400">Outfit · 14px · 400</p>
            </div>
          </div>
        </div>
      </Demo>

      <Demo label="Radius & Shadows">
        <div className="grid w-full grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {[
            { name: "rounded-lg", cls: "rounded-lg" },
            { name: "rounded-xl", cls: "rounded-xl" },
            { name: "rounded-2xl", cls: "rounded-2xl" },
            { name: "shadow-soft", cls: "rounded-2xl shadow-soft" },
            { name: "shadow-lift", cls: "rounded-2xl shadow-lift" },
          ].map((s) => (
            <div key={s.name} className={`flex h-16 items-center justify-center border border-sand-200 bg-white dark:border-night-700 dark:bg-night-900 ${s.cls}`}>
              <span className="text-[10px] font-medium text-sand-400">{s.name}</span>
            </div>
          ))}
        </div>
      </Demo>
    </Section>
  );
}
