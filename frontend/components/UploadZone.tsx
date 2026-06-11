"use client";
import { useCallback, useState } from "react";

interface Props {
  onFile: (file: File) => void;
  loading: boolean;
}

export function UploadZone({ onFile, loading }: Props) {
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) onFile(file);
    },
    [onFile]
  );

  return (
    <label
      className={`flex flex-col items-center justify-center w-full h-56 border-2 border-dashed rounded-2xl cursor-pointer transition-colors
        ${dragging ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-white hover:bg-slate-50"}
        ${loading ? "opacity-50 pointer-events-none" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <input
        type="file"
        accept="image/png,image/jpeg,image/tiff"
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
        }}
        disabled={loading}
      />
      {loading ? (
        <div className="flex flex-col items-center gap-2 text-indigo-600">
          <Spinner />
          <span className="text-sm font-medium">Extracting…</span>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2 text-slate-500">
          <UploadIcon />
          <p className="text-sm font-semibold">Drag &amp; drop or click to upload</p>
          <p className="text-xs">PNG, JPEG, TIFF · max 20 MB</p>
        </div>
      )}
    </label>
  );
}

function UploadIcon() {
  return (
    <svg className="w-10 h-10 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="w-8 h-8 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}
