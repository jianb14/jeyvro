import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Input } from "./Input";

describe("Input error wiring", () => {
  it("renders the red message and links it to the control", () => {
    render(<Input label="Email" error="This field is required." />);

    const field = screen.getByLabelText("Email");
    const message = screen.getByText("This field is required.");

    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveAttribute("aria-describedby", message.id);
    expect(message).toHaveClass("text-danger-600");
  });

  it("links the hint when there is no error", () => {
    render(<Input label="Phone" hint="Optional — sellers may call." />);

    const field = screen.getByLabelText("Phone");
    const hint = screen.getByText("Optional — sellers may call.");

    expect(field).not.toHaveAttribute("aria-invalid");
    expect(field).toHaveAttribute("aria-describedby", hint.id);
  });
});
