import type { ReactNode } from "react";

type Props = { eyebrow?: string; title: ReactNode; description?: ReactNode; actions?: ReactNode };

export function MraSectionHeader({ eyebrow, title, description, actions }: Props) {
  return (
    <header className="mra-section-header">
      <div>{eyebrow ? <span>{eyebrow}</span> : null}<h2>{title}</h2>{description ? <p>{description}</p> : null}</div>
      {actions ? <div>{actions}</div> : null}
    </header>
  );
}
