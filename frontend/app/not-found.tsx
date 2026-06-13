import Link from "next/link";

export const metadata = { title: "Page not found" };

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-center px-6 bg-slate-50">
      <div className="space-y-6 animate-fade-up">
        <div
          className="mx-auto w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg"
          style={{ background: "linear-gradient(135deg, #6366f1 0%, #4338ca 100%)" }}
        >
          <span className="text-white font-bold text-2xl tracking-tight select-none">D</span>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-bold text-indigo-500 uppercase tracking-widest">404</p>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Page not found</h1>
          <p className="text-slate-500 text-sm max-w-xs mx-auto leading-relaxed">
            This page doesn&apos;t exist or has been moved.
          </p>
        </div>

        <Link
          href="/"
          className="inline-flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition-colors focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 outline-none"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Discern
        </Link>
      </div>
    </div>
  );
}
