import { useRef, useState } from "react";
import { cx } from "../../lib/cx";
import { UploadIcon, FileIcon, XIcon } from "./Icons";

export function FileUpload({ accept, multiple = true, disabled = false, onFiles, className }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const openPicker = () => {
    if (disabled) return;
    inputRef.current?.click();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (disabled) return;
    setDragging(false);
    onFiles?.(Array.from(e.dataTransfer.files || []));
  };

  return (
    <div className={cx("w-full", className)}>
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        onClick={openPicker}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && openPicker()}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={cx(
          "flex cursor-pointer select-none flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-10 text-center transition-all outline-offset-2 outline-moss-600/60 focus-visible:outline-2",
          dragging
            ? "border-moss-500 bg-moss-50 dark:bg-moss-950/40"
            : "border-sand-300 hover:border-moss-400 hover:bg-sand-50 dark:border-night-700 dark:hover:border-moss-600 dark:hover:bg-night-800/50",
          disabled && "pointer-events-none opacity-50"
        )}
      >
        <span
          className={cx(
            "flex size-12 items-center justify-center rounded-full transition-colors",
            dragging
              ? "bg-moss-100 text-moss-700 dark:bg-moss-900 dark:text-moss-300"
              : "bg-sand-100 text-sand-500 dark:bg-night-800 dark:text-sand-400"
          )}
        >
          <UploadIcon size={22} />
        </span>
        <div>
          <p className="text-sm font-medium text-sand-800 dark:text-sand-200">
            Drop files here or <span className="text-moss-700 underline underline-offset-2 dark:text-moss-300">browse</span>
          </p>
          <p className="mt-1 text-xs text-sand-400">PNG, JPG, or PDF - up to 10 MB each</p>
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        className="hidden"
        onChange={(e) => {
          onFiles?.(Array.from(e.target.files || []));
          e.target.value = "";
        }}
      />
    </div>
  );
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

export function FileList({ files = [], onRemove, className }) {
  if (!files.length) return null;
  return (
    <ul className={cx("flex flex-col gap-2", className)}>
      {files.map((file) => (
        <li
          key={file.id}
          className="flex items-center gap-3 rounded-xl border border-sand-200 bg-white px-4 py-3 dark:border-night-800 dark:bg-night-900"
        >
          <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-sand-100 text-sand-500 dark:bg-night-800 dark:text-sand-400">
            <FileIcon size={16} />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-sand-800 dark:text-sand-200">{file.name}</p>
            <p className="text-xs tabular-nums text-sand-400">{formatSize(file.size)}</p>
          </div>
          <button
            type="button"
            onClick={() => onRemove?.(file.id)}
            aria-label={`Remove ${file.name}`}
            className="shrink-0 rounded-md p-1.5 text-sand-400 transition-colors hover:bg-danger-50 hover:text-danger-600 dark:hover:bg-danger-950/50 dark:hover:text-danger-400"
          >
            <XIcon size={15} />
          </button>
        </li>
      ))}
    </ul>
  );
}
