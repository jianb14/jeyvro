import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { HeroBanner } from "./HeroBanner";

// The banner's CTAs are react-router <Link>s, so it needs a router context.
// MemoryRouter (not BrowserRouter) keeps the test out of jsdom's history.
function renderBanner() {
  return render(
    <MemoryRouter>
      <HeroBanner />
    </MemoryRouter>
  );
}

describe("HeroBanner", () => {
  it("renders the hero copy in Title Case, without the eyebrow label", () => {
    renderBanner();
    // The "Marketplace" eyebrow badge is gone — it repeated what the navbar
    // already says and pushed the whole card taller.
    expect(screen.queryByText("Marketplace")).not.toBeInTheDocument();
    const heading = screen.getByRole("heading", { level: 1 });
    // Title Case, not the shouty all-caps version the banner shipped with.
    expect(heading.className).not.toContain("uppercase");
    expect(heading).toHaveTextContent("Local Goods");
    expect(heading).toHaveTextContent("Chosen With Care");
    // The subtitle has to speak to shoppers, and match the heading — the old
    // line advertised the marketplace API, which means nothing to a buyer.
    expect(
      screen.getByText(/Independent sellers, honest prices, and stock you can trust/)
    ).toBeInTheDocument();
    expect(screen.queryByText(/marketplace API/i)).not.toBeInTheDocument();
  });

  it("sends both calls to action to their real destinations", () => {
    renderBanner();
    expect(screen.getByRole("link", { name: /Browse products/i })).toHaveAttribute(
      "href",
      "/products"
    );
    expect(screen.getByRole("link", { name: /Sell on Jeyvro/i })).toHaveAttribute(
      "href",
      "/sell"
    );
  });

  it("reserves the photo's box and loads it eagerly", () => {
    renderBanner();
    const photo = screen.getByRole("img");
    // Explicit dimensions declare the CDN's real ratio (frontend-performance).
    expect(photo).toHaveAttribute("width");
    expect(photo).toHaveAttribute("height");
    expect(photo).toHaveAttribute("alt");
    // Above the fold: never lazy.
    expect(photo).toHaveAttribute("loading", "eager");
  });

  it("keeps the photo out of flow so it cannot set the banner's height", () => {
    renderBanner();
    const photo = screen.getByRole("img");
    // The row height belongs to the copy column alone. A square photo left in
    // normal flow would drag the card to its own aspect ratio — the banner used
    // to fill the viewport and push the first shelf off-screen.
    expect(photo.className).toContain("absolute");
    // Out of flow still has to fill its clipped column, not float at 0x0.
    expect(photo.className).toContain("inset-0");
  });

  it("falls back to a branded panel when the photo cannot load", () => {
    renderBanner();
    fireEvent.error(screen.getByRole("img"));
    // The only accessible image was the photo; the fallback mark is
    // decorative (empty alt), so an image query has nothing left to match.
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    // The copy must survive the failure — the hero is still a hero.
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
  });

  it("anchors the portrait photo over the model instead of centring it", () => {
    const { container } = renderBanner();
    const photo = screen.getByRole("img");
    // The source is portrait and the column is landscape, so only a band of the
    // photo is ever visible. Centring that band slices through the model's face;
    // the anchor pins it to the head-and-goods range (about 11–47% of the frame).
    expect(photo.className).toContain("object-cover");
    expect(photo.className).not.toContain("object-center");
    expect(photo.className).toMatch(/object-\[50%_\d+%\]/);
    // The stage needs a floor of its own: the copy column alone was too short
    // to show a portrait photo as anything more than a sliver of backdrop.
    expect(container.querySelector("[class*='lg:min-h']")).not.toBeNull();
  });
});
