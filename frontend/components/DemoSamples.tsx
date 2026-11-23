"use client";
import { useEffect, useState } from "react";
import { fetchDemoSampleFile, getDemoSamples, type DemoSample } from "@/lib/api";

/** True when the app is running against the offline demo API. */
export const OFFLINE_DEMO = process.env.NEXT_PUBLIC_OFFLINE_DEMO === "true";

interface Props {
  onPick: (file: File) => void;
  disabled?: boolean;
}

/**
 * "Try a sample document": one-click uploads of the synthetic documents bundled with the
 * offline demo. They are read back exactly; any other file gets illustrative values.
 */
export function DemoSamples({ onPick, disabled }: Props) {
  const [samples, setSamples] = useState<DemoSample[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    getDemoSamples()
      .then(setSamples)
      .catch(() => setSamples([]));
  }, []);

  if (samples.length === 0) return null;

  // One chip per template: the first sample of each.
  const firstOfEach = samples.filter((s, i) => samples.findIndex((x) => x.doc_type === s.doc_type) === i);

  async function pick(sample: DemoSample) {
    setBusy(sample.file);
    try {
      onPick(await fetchDemoSampleFile(sample));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section
      aria-label="Sample documents"
      className="rounded-2xl border px-4 py-3.5"
      style={{ background: "rgba(99,102,241,0.06)", borderColor: "rgba(99,102,241,0.25)" }}
    >
      <p className="text-sm font-semibold" style={{ color: "#4338ca" }}>
        Try a sample document
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {firstOfEach.map((s) => (
          <button
            key={s.file}
            type="button"
            onClick={() => pick(s)}
            disabled={disabled || busy !== null}
            className="rounded-full border bg-white px-3 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            {s.label.replace(/ \d+$/, "")}
          </button>
        ))}
      </div>
      <p className="mt-2 text-xs leading-relaxed" style={{ color: "#64748b" }}>
        Offline demo: these synthetic documents are read exactly. Any other file you upload gets
        illustrative values with low confidence, so it lands in the review queue.
      </p>
    </section>
  );
}
