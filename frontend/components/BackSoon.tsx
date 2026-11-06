import Image from "next/image";

const PORTFOLIO_URL = "https://dowellstandley.com";

const STEPS = [
  {
    title: "Upload",
    text: "Snap or drop a photo or scan of a paper record.",
    path: "M12 16V4m0 0l-4 4m4-4l4 4M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3",
  },
  {
    title: "Detect & read",
    text: "Fields are located and read with computer vision and OCR.",
    path: "M3 7V5a2 2 0 012-2h2M17 3h2a2 2 0 012 2v2M21 17v2a2 2 0 01-2 2h-2M7 21H5a2 2 0 01-2-2v-2M7 12h10",
  },
  {
    title: "Review",
    text: "Edit the results, each field with a confidence score.",
    path: "M5 13l4 4L19 7",
  },
  {
    title: "Search",
    text: "Find any record again as structured, searchable data.",
    path: "M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z",
  },
];

export function BackSoon() {
  return (
    <main className="relative isolate min-h-screen overflow-hidden bg-navy-950 px-6 py-16 text-slate-100 flex items-center justify-center">
      <style>{`
        @keyframes bs-scan { 0% { top: 6%; opacity: 0; } 10% { opacity: 1; } 90% { opacity: 1; } 100% { top: 94%; opacity: 0; } }
        @keyframes bs-rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
        @keyframes bs-pop { from { opacity: 0; transform: scale(.85); } to { opacity: 1; transform: none; } }
        .bs-scan { top: 50%; }
        @media (prefers-reduced-motion: no-preference) {
          .bs-scan { animation: bs-scan 3.2s ease-in-out infinite; }
          .bs-rise { opacity: 0; animation: bs-rise .7s ease-out forwards; }
          .bs-pop { opacity: 0; animation: bs-pop .5s ease-out forwards; }
          .bs-d1 { animation-delay: .1s; } .bs-d2 { animation-delay: .25s; }
          .bs-d3 { animation-delay: .4s; } .bs-d4 { animation-delay: .6s; }
          .bs-f1 { animation-delay: .9s; } .bs-f2 { animation-delay: 1.3s; } .bs-f3 { animation-delay: 1.7s; }
        }
      `}</style>

      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute left-1/2 top-[-15%] h-[520px] w-[820px] -translate-x-1/2 rounded-full bg-brand-600/30 blur-[120px]" />
        <div className="absolute bottom-[-20%] left-[-10%] h-[400px] w-[520px] rounded-full bg-sky-500/15 blur-[120px]" />
      </div>

      <section className="mx-auto w-full max-w-3xl text-center">
        <div className="bs-rise bs-d1 flex items-center justify-center gap-2.5">
          <Image
            src="/icon.png"
            alt=""
            width={40}
            height={40}
            className="w-10 h-10 rounded-xl shadow-[0_0_24px_rgb(99_102_241/0.5)]"
            priority
          />
          <span className="font-bold text-xl tracking-tight">Discern</span>
        </div>

        <h1 className="bs-rise bs-d2 mt-8 text-5xl sm:text-6xl font-extrabold tracking-tight leading-[1.1]">
          <span className="bg-gradient-to-r from-indigo-300 via-violet-300 to-sky-300 bg-clip-text text-transparent">
            We&apos;ll be back soon
          </span>
        </h1>
        <p className="bs-rise bs-d3 mt-4 text-lg text-slate-100">
          Discern is temporarily unavailable. Thanks for your patience.
        </p>

        {/* Animated document scan */}
        <div aria-hidden="true" className="bs-rise bs-d3 mx-auto mt-10 w-full max-w-xs">
          <div className="relative rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-2xl backdrop-blur">
            <div className="space-y-3">
              <div className="h-2.5 w-2/5 rounded bg-white/25" />
              <div className="relative h-8 rounded-md border border-indigo-300/70 bg-indigo-400/10">
                <span className="bs-pop bs-f1 absolute -top-2 right-2 rounded bg-emerald-400 px-1.5 text-[10px] font-bold leading-4 text-slate-900">
                  98%
                </span>
              </div>
              <div className="h-2.5 w-3/5 rounded bg-white/15" />
              <div className="relative h-8 rounded-md border border-indigo-300/70 bg-indigo-400/10">
                <span className="bs-pop bs-f2 absolute -top-2 right-2 rounded bg-emerald-400 px-1.5 text-[10px] font-bold leading-4 text-slate-900">
                  94%
                </span>
              </div>
              <div className="h-2.5 w-1/2 rounded bg-white/15" />
              <div className="relative h-8 rounded-md border border-indigo-300/70 bg-indigo-400/10">
                <span className="bs-pop bs-f3 absolute -top-2 right-2 rounded bg-emerald-400 px-1.5 text-[10px] font-bold leading-4 text-slate-900">
                  99%
                </span>
              </div>
            </div>
            <div className="bs-scan pointer-events-none absolute inset-x-3 h-0.5 rounded bg-gradient-to-r from-transparent via-sky-300 to-transparent shadow-[0_0_14px_rgb(125_211_252/0.9)]" />
          </div>
        </div>

        <p className="bs-rise bs-d4 mx-auto mt-8 max-w-xl text-base text-slate-300 leading-relaxed">
          A document-intelligence app that turns photos and scans of paper records into
          structured, searchable data.
        </p>

        <ol className="bs-rise bs-d4 mt-8 grid gap-3 text-left sm:grid-cols-2">
          {STEPS.map(({ title, text, path }, i) => (
            <li
              key={title}
              className="flex gap-3 rounded-xl border border-white/10 bg-white/[0.04] p-4"
            >
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-400/15 text-indigo-300">
                <svg
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path d={path} />
                </svg>
              </div>
              <div>
                <h2 className="text-sm font-semibold">
                  <span className="text-slate-400">{i + 1}. </span>
                  {title}
                </h2>
                <p className="mt-0.5 text-sm text-slate-300">{text}</p>
              </div>
            </li>
          ))}
        </ol>

        <a
          href={PORTFOLIO_URL}
          className="bs-rise bs-d4 mt-10 inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-500 text-white text-sm font-semibold px-6 py-3 rounded-xl transition-colors focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-2 focus-visible:ring-offset-navy-950 outline-none"
        >
          Visit my portfolio
        </a>
      </section>
    </main>
  );
}
