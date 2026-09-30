import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { PasswordInput } from "./PasswordInput";

describe("PasswordInput reveal toggle", () => {
  it("starts masked and flips the input type when revealed", async () => {
    const user = userEvent.setup();
    render(<PasswordInput label="Password" />);

    const field = screen.getByLabelText("Password");
    expect(field).toHaveAttribute("type", "password");

    await user.click(screen.getByRole("button", { name: "Show password" }));
    expect(field).toHaveAttribute("type", "text");
  });

  it("announces the mode and swaps the accessible name", async () => {
    const user = userEvent.setup();
    render(<PasswordInput label="Password" />);

    const toggle = screen.getByRole("button", { name: "Show password" });
    expect(toggle).toHaveAttribute("aria-pressed", "false");

    await user.click(toggle);
    // The name now describes the action that reverses it, and the pressed
    // state describes the mode the field is actually in.
    const hide = screen.getByRole("button", { name: "Hide password" });
    expect(hide).toHaveAttribute("aria-pressed", "true");
  });

  it("never submits the form it sits inside", () => {
    const onSubmit = vi.fn((event) => event.preventDefault());
    render(
      <form onSubmit={onSubmit}>
        <PasswordInput label="Password" />
      </form>
    );

    // type="button" is the whole reason this is safe: a bare button inside a
    // form defaults to submit, and clicking "show password" would then post the
    // half-filled login form.
    expect(screen.getByRole("button", { name: "Show password" })).toHaveAttribute("type", "button");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("reports visibility changes to a controlled parent", async () => {
    const user = userEvent.setup();
    const onVisibleChange = vi.fn();

    function Controlled() {
      const [visible, setVisible] = useState(false);
      return (
        <PasswordInput
          label="Password"
          visible={visible}
          onVisibleChange={(next) => {
            setVisible(next);
            onVisibleChange(next);
          }}
        />
      );
    }

    render(<Controlled />);
    await user.click(screen.getByRole("button", { name: "Show password" }));

    expect(onVisibleChange).toHaveBeenCalledWith(true);
    expect(screen.getByLabelText("Password")).toHaveAttribute("type", "text");
  });

  it("keeps error text wired to the field it belongs to", () => {
    render(<PasswordInput label="Password" error="This field is required." />);

    const field = screen.getByLabelText("Password");
    const message = screen.getByText("This field is required.");

    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveAttribute("aria-describedby", message.id);
  });
});
