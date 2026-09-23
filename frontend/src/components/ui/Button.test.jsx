import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button } from "./Button";

describe("Button", () => {
  it("renders its children as a button", () => {
    render(<Button>Add to cart</Button>);
    expect(screen.getByRole("button", { name: "Add to cart" })).toBeInTheDocument();
  });

  it("is disabled while loading", () => {
    render(<Button loading>Save changes</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
