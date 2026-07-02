"use client";
import { useEffect, useState } from "react";
import Image from "next/image";

type Mode = "android" | "ios" | null;

export function InstallBanner() {
  const [mode, setMode] = useState<Mode>(null);
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // Already installed or dismissed recently
    if (window.matchMedia("(display-mode: standalone)").matches) return;
    if (localStorage.getItem("pwa-banner-dismissed")) return;

    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const isMobile = /Mobi|Android/i.test(navigator.userAgent) || isIOS;
    if (!isMobile) return;

    if (isIOS) {
      setMode("ios");
      return;
    }

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setMode("android");
    };
    window.addEventListener("beforeinstallprompt", handler as EventListener);
    return () => window.removeEventListener("beforeinstallprompt", handler as EventListener);
  }, []);

  function dismiss() {
    setDismissed(true);
    localStorage.setItem("pwa-banner-dismissed", "1");
  }

  async function install() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") dismiss();
    else setDeferredPrompt(null);
  }

  if (!mode || dismissed) return null;

  return (
    <div className="fixed bottom-0 inset-x-0 z-50 p-4 pointer-events-none">
      <div className="pointer-events-auto mx-auto max-w-sm rounded-2xl shadow-2xl border border-slate-700 bg-slate-900 text-white p-4 flex items-start gap-3">
        <Image
          src="/icon-192x192.png"
          alt="Discern"
          width={48}
          height={48}
          className="rounded-xl flex-shrink-0"
        />
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm">Add Discern to your home screen</p>
          {mode === "ios" ? (
            <p className="text-slate-400 text-xs mt-0.5">
              Tap the <strong className="text-slate-300">Share</strong> button then{" "}
              <strong className="text-slate-300">Add to Home Screen</strong>
            </p>
          ) : (
            <p className="text-slate-400 text-xs mt-0.5">
              Install for quick access — no App Store needed
            </p>
          )}
          {mode === "android" && (
            <button
              onClick={install}
              className="mt-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg transition-colors"
            >
              Install
            </button>
          )}
        </div>
        <button
          onClick={dismiss}
          aria-label="Dismiss"
          className="text-slate-500 hover:text-slate-300 flex-shrink-0 transition-colors"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
