import Image from "next/image";

const PORTFOLIO_URL = "https://dowellstandley.com";

export function BackSoon() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center text-center px-6 py-12 bg-slate-50">
      <section className="space-y-6 max-w-md">
        <div className="flex items-center justify-center gap-2.5">
          <Image
            src="/icon.png"
            alt=""
            width={40}
            height={40}
            className="w-10 h-10 rounded-xl shadow-lg"
            priority
          />
          <span className="font-bold text-xl tracking-tight text-slate-900">Discern</span>
        </div>

        <div className="space-y-3">
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight">
            We&apos;ll be back soon
          </h1>
          <p className="text-slate-800 text-base leading-relaxed">
            Discern is temporarily unavailable. Thanks for your patience.
          </p>
        </div>

        <p className="text-slate-600 text-sm leading-relaxed">
          Discern is a document-intelligence app that turns photos and scans of paper records into
          structured, searchable data.
        </p>

        <a
          href={PORTFOLIO_URL}
          className="inline-flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition-colors focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 outline-none"
        >
          Visit my portfolio
        </a>
      </section>
    </main>
  );
}
