import { useState } from "react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SearchInput } from "./SearchInput";

function Harness({ initial = "" }) {
  const [value, setValue] = useState(initial);
  return (
    <SearchInput
      label="Search products"
      value={value}
      onChange={(event) => setValue(event.target.value)}
    />
  );
}

describe("SearchInput", () => {
  it("shows the clear button only when there is text", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    expect(screen.getByLabelText("Search products")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Clear search" })).toBeNull();

    await user.type(screen.getByLabelText("Search products"), "shoes");
    expect(screen.getByRole("button", { name: "Clear search" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear search" }));
    expect(screen.queryByRole("button", { name: "Clear search" })).toBeNull();
  });

  it("empties the field when the clear button is clicked", async () => {
    const user = userEvent.setup();
    render(<Harness initial="running shoes" />);
    const field = screen.getByLabelText("Search products");

    await user.click(screen.getByRole("button", { name: "Clear search" }));

    expect(field).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Clear search" })).toBeNull();
  });

  it("keeps typing and clearing in sync with the parent state", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const field = screen.getByLabelText("Search products");

    await user.type(field, "bag");
    expect(field).toHaveValue("bag");

    await user.click(screen.getByRole("button", { name: "Clear search" }));
    expect(field).toHaveValue("");
  });
});
