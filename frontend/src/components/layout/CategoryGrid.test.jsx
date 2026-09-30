import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CategoryGrid } from "./CategoryGrid";

// Cards are react-router <Link>s, so the grid needs a router context.
function renderGrid(props) {
  return render(
    <MemoryRouter>
      <CategoryGrid {...props} />
    </MemoryRouter>
  );
}

const FOOD = {
  id: 1,
  parent: null,
  name: "Food",
  slug: "food",
  productCount: 4,
  coverImage: "http://api/media/food.jpg",
};
const EMPTY = {
  id: 2,
  parent: null,
  name: "Beauty",
  slug: "beauty",
  productCount: 0,
  coverImage: null,
};

describe("CategoryGrid", () => {
  it("renders one card per category, linking to the browse page", () => {
    renderGrid({ categories: [FOOD, EMPTY] });

    // The grid is a projection of the database tree, so a category a staff
    // member created must appear with no code change of its own.
    expect(screen.getAllByRole("link")).toHaveLength(2);
    expect(screen.getByRole("link", { name: /Food/ })).toHaveAttribute(
      "href",
      "/category/food"
    );
  });

  it("shows the server-resolved product count, honestly including zero", () => {
    renderGrid({ categories: [FOOD, EMPTY] });

    expect(screen.getByText("4 items")).toBeInTheDocument();
    // An empty department still says so rather than vanishing: a storefront
    // that quietly drops empty categories looks broken, not curated.
    expect(screen.getByText("0 items")).toBeInTheDocument();
  });

  it("uses the server's cover photo and falls back to a branded panel", () => {
    const { container } = renderGrid({ categories: [FOOD, EMPTY] });

    // The cover photo is the one real product image on the page; the empty
    // category renders the logo mark instead, never a <img> with no src
    // (which would ship as a broken-image icon).
    const photos = [...container.querySelectorAll("img")];
    const covers = photos.filter((img) => img.getAttribute("src") !== "/jeyvro-mark.png");
    expect(covers).toHaveLength(1);
    expect(covers[0]).toHaveAttribute("src", "http://api/media/food.jpg");
    // The decorative cover is empty-alt: the category name is already the
    // accessible label, so a screen reader must not read the photo twice.
    expect(covers[0]).toHaveAttribute("alt", "");
    // The empty category's branded panel is a real element, not a missing img.
    expect(photos.some((img) => img.getAttribute("src") === "/jeyvro-mark.png")).toBe(true);
  });

  it("renders nothing at all when there are no categories", () => {
    const { container } = renderGrid({ categories: [] });
    expect(container).toBeEmptyDOMElement();
  });

  it("shows card-shaped skeletons while loading", () => {
    const { container } = renderGrid({ categories: null, loading: true });
    // Skeletons reserve the card's real shape so the grid does not reflow
    // when the data lands.
    expect(container.querySelectorAll(".aspect-\\[4\\/3\\]")).toHaveLength(4);
    expect(screen.queryAllByRole("link")).toHaveLength(0);
  });
});