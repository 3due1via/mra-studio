import type { HTMLAttributes, ReactNode } from "react";

type CardTone = "default" | "blue" | "gold" | "green" | "purple" | "orange";

type Props = HTMLAttributes<HTMLElement> & {
  tone?: CardTone;
  interactive?: boolean;
  eyebrow?: string;
  title?: ReactNode;
  actions?: ReactNode;
};

export function MraCard({ tone = "default", interactive = false, eyebrow, title, actions, className = "", children, ...props }: Props) {
  return (
    <article {...props} className={`mra-card mra-card-${tone} ${interactive ? "mra-card-interactive" : ""} ${className}`.trim()}>
      {eyebrow || title || actions ? (
        <header className="mra-card-header">
          <div>{eyebrow ? <span>{eyebrow}</span> : null}{title ? <h3>{title}</h3> : null}</div>
          {actions ? <div className="mra-card-actions">{actions}</div> : null}
        </header>
      ) : null}
      {children}
    </article>
  );
}
