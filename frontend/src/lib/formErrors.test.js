import { describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { REQUIRED_MESSAGE, requiredErrors, useRequiredFields } from "./formErrors";

describe("requiredErrors", () => {
  it("flags blank, whitespace-only, and missing values", () => {
    const errors = requiredErrors({ email: "", password: "   ", phone: null }, [
      "email",
      "password",
      "phone",
      "absent",
    ]);
    expect(errors).toEqual({
      email: [REQUIRED_MESSAGE],
      password: [REQUIRED_MESSAGE],
      phone: [REQUIRED_MESSAGE],
      absent: [REQUIRED_MESSAGE],
    });
  });

  it("returns the API field_errors shape and no entries when filled", () => {
    expect(requiredErrors({ email: "a@b.co" }, ["email"])).toEqual({});
  });
});

describe("useRequiredFields", () => {
  it("stays quiet until validate() runs, then reports every missing field", () => {
    const { result } = renderHook(() =>
      useRequiredFields({ email: "", password: "s3cret" }, ["email", "password"])
    );

    expect(result.current.fieldErrors).toEqual({});

    let ok;
    act(() => {
      ok = result.current.validate();
    });

    expect(ok).toBe(false);
    expect(result.current.fieldErrors).toEqual({ email: [REQUIRED_MESSAGE] });
  });

  it("passes and clears the bucket when everything is filled", () => {
    const { result } = renderHook(() => useRequiredFields({ email: "a@b.co" }, ["email"]));

    let ok;
    act(() => {
      ok = result.current.validate();
    });

    expect(ok).toBe(true);
    expect(result.current.fieldErrors).toEqual({});
  });

  it("clears one field as the user fixes it, and holds server field_errors", () => {
    const { result } = renderHook(() =>
      useRequiredFields({ email: "", password: "" }, ["email", "password"])
    );

    act(() => {
      result.current.validate();
    });
    act(() => {
      result.current.clearField("email");
    });
    expect(result.current.fieldErrors).toEqual({ password: [REQUIRED_MESSAGE] });

    act(() => {
      result.current.setFieldErrors({ email: ["Enter a valid email address."] });
    });
    expect(result.current.fieldErrors).toEqual({ email: ["Enter a valid email address."] });
  });
});
