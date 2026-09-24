/**
 * ProductArt — flat placeholder art for products without uploaded images
 * (presentation-only; no gradients). Lives in its own component file so
 * both ProductCard and the product-detail gallery render the same
 * placeholder (react-refresh: component files export only components).
 */
export function ProductArt({ seed = 0, className }) {
  const palettes = [
    { bg: "#e4ecdc", fg: "#84a471" },
    { bg: "#f2f0ea", fg: "#b7ad97" },
    { bg: "#e3edf4", fg: "#7aa9cd" },
    { bg: "#f5ebd6", fg: "#d0a054" },
    { bg: "#f6e3e1", fg: "#d08880" },
    { bg: "#dcecdc", fg: "#67a46c" },
  ];
  const p = palettes[seed % palettes.length];
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      aria-hidden="true"
      preserveAspectRatio="xMidYMid slice"
    >
      <rect width="100" height="100" fill={p.bg} />
      <rect x="30" y="26" width="40" height="48" rx="6" fill={p.fg} />
      <rect x="36" y="34" width="28" height="20" rx="3" fill="#ffffff" opacity="0.85" />
      <rect x="36" y="60" width="18" height="5" rx="2.5" fill="#ffffff" opacity="0.6" />
    </svg>
  );
}