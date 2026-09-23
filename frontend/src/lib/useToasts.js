import { useState } from "react";

/**
 * Toast queue state. Lives in lib/ (not in Toast.jsx) so that component
 * files only export components (react-refresh/only-export-components).
 */
export function useToasts() {
  const [toasts, setToasts] = useState([]);

  const push = (toast) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), toast.duration || 4000);
  };

  const dismiss = (id) => setToasts((prev) => prev.filter((t) => t.id !== id));

  return { toasts, push, dismiss };
}
