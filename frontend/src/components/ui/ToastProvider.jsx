/**
 * App-wide toast queue (Phase 6) — a single ToastViewport for the whole
 * app, so the shared Navbar and every page raise toasts without stacking
 * duplicate viewports. Wraps lib/useToasts (the queue engine).
 */
/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext } from "react";
import { useToasts } from "../../lib/useToasts";
import { ToastViewport } from "./Toast";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const { toasts, push, dismiss } = useToasts();
  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used inside <ToastProvider>");
  return context;
}