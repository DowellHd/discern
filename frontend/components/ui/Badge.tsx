export type BadgeVariant = "neutral" | "success" | "warn" | "danger" | "info";

interface Props {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const VARIANTS: Record<BadgeVariant, string> = {
  neutral: "bg-slate-100   text-slate-600",
  info:    "bg-indigo-50   text-indigo-700",
  success: "bg-emerald-50  text-emerald-700",
  warn:    "bg-amber-50    text-amber-700",
  danger:  "bg-red-50      text-red-700",
};

export function Badge({ children, variant = "neutral", className = "" }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold tracking-wide ${VARIANTS[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
