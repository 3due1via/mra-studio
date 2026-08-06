import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonTone = "primary" | "secondary" | "ghost" | "danger" | "gold";
type ButtonSize = "sm" | "md" | "lg";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  tone?: ButtonTone;
  size?: ButtonSize;
  icon?: ReactNode;
  loading?: boolean;
};

export function MraButton({ tone = "primary", size = "md", icon, loading, className = "", children, disabled, ...props }: Props) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`mra-button mra-button-${tone} mra-button-${size} ${className}`.trim()}
    >
      {loading ? <span className="mra-spinner" aria-hidden="true" /> : icon ? <span className="mra-button-icon">{icon}</span> : null}
      <span>{loading ? "Attendi…" : children}</span>
    </button>
  );
}
