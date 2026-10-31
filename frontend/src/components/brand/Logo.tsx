import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  subtitle?: string;
  className?: string;
  wordmark?: boolean;
}

const sizes = {
  sm: { box: "h-7 w-7", icon: 14, text: "text-base" },
  md: { box: "h-9 w-9", icon: 18, text: "text-lg" },
  lg: { box: "h-11 w-11", icon: 22, text: "text-xl" },
};

export function Logo({ size = "md", subtitle, className, wordmark = true }: LogoProps) {
  const s = sizes[size];
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <div className={cn("gradient-primary shadow-glow flex items-center justify-center rounded-xl", s.box)}>
        <Sparkles size={s.icon} className="text-white" strokeWidth={2.5} />
      </div>
      {wordmark && (
        <div className="flex flex-col leading-tight">
          <span className={cn("font-extrabold tracking-tight", s.text)}>CONSILIUM</span>
          {subtitle && <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{subtitle}</span>}
        </div>
      )}
    </div>
  );
}
