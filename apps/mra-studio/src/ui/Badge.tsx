import type { HTMLAttributes } from "react";

type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger" | "ai" | "gold";

type Props = HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone };

export function MraBadge({ tone = "neutral", className = "", ...props }: Props) {
  return <span {...props} className={`mra-badge mra-badge-${tone} ${className}`.trim()} />;
}
