import { afterEach, describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { PromoStrip } from "./PromoStrip";

function mockCampaigns(payload) {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, json: async () => payload })));
}
function rejectCampaigns() {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 500, json: async () => ({ detail: "Boom" }) })));
}
function renderStrip() {
  return render(
    <MemoryRouter>
      <PromoStrip />
    </MemoryRouter>
  );
}

// Snake_case exactly as the API sends it: mapCampaign renames these to the
// camelCase contract the component reads, and the test proves the whole chain.
const LIVE = {
  id: 1,
  name: "Fashion Week",
  scope: "platform",
  store_id: null,
  store_name: null,
  description: "Handwoven pieces, marked down.",
  promotion_count: 3,
  starts_at: "2020-01-01T00:00:00Z",
  ends_at: "2999-12-31T00:00:00Z",
  is_active: true,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PromoStrip", () => {
  it("renders a live campaign from the API, below the category grid", async () => {
    mockCampaigns([LIVE]);
    renderStrip();

    // Campaigns are a database fact: the banner text is the server's name,
    // never a hardcoded "Summer Sale" that drifts from the data.
    expect(await screen.findByText("Fashion Week")).toBeInTheDocument();
    expect(screen.getByText(/3 active offers/)).toBeInTheDocument();
  });

  it("hides the whole strip when nothing is on offer", async () => {
    mockCampaigns([]);
    const { container } = renderStrip();
    // An empty promo band advertises a marketplace with nothing on offer.
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it("drops a campaign whose window has already closed", async () => {
    // The server filters is_active but not the date window, so an expired
    // campaign must not still be advertised on the storefront.
    mockCampaigns([{ ...LIVE, ends_at: "2020-06-01T00:00:00Z" }]);
    const { container } = renderStrip();
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it("does not let a failed promo fetch break the page below it", async () => {
    rejectCampaigns();
    const { container } = renderStrip();
    // The band simply never appears; the rest of the homepage still renders.
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});