/**
 * Client-side form validation (UX only — §10.1: the server is always the
 * gate). Required checks live here so every form shows the same red inline
 * message instead of the browser's native validation bubble: forms opt out
 * of native validation with `noValidate` and call `validate()` from their
 * submit handler.
 *
 * Messages use the API's `{error, detail?, field_errors?}` field_errors
 * shape (arrays of messages) so client checks and server results share one
 * bucket and render through the same `Input error` prop.
 */
import { useState } from "react";

export const REQUIRED_MESSAGE = "This field is required.";

/** Blank / whitespace-only / missing values, keyed by field name. */
export function requiredErrors(values, names) {
  const errors = {};
  for (const name of names) {
    const value = values?.[name];
    if (value == null || String(value).trim() === "") {
      errors[name] = [REQUIRED_MESSAGE];
    }
  }
  return errors;
}

function omitKey(object, key) {
  const next = { ...object };
  delete next[key];
  return next;
}

/**
 * Field-error state for one form: client required checks on submit, server
 * `field_errors` after a failed request, and per-field clearing as the user
 * fixes a field (ux-patterns: validate on submit, clear as they type).
 */
export function useRequiredFields(values, names) {
  const [fieldErrors, setFieldState] = useState({});

  const validate = () => {
    const missing = requiredErrors(values, names);
    setFieldState(missing);
    return Object.keys(missing).length === 0;
  };

  const clearField = (name) => {
    setFieldState((errors) => (errors[name] === undefined ? errors : omitKey(errors, name)));
  };

  /** Replace the bucket with server field_errors (or a derived message). */
  const setFieldErrors = (errors) => setFieldState(errors || {});

  return { fieldErrors, validate, clearField, setFieldErrors };
}
