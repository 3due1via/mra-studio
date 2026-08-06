import type { ReactNode } from "react";
import { MraCard } from "./Card";

type Props = {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  note?: string;
  tone?: "default" | "blue" | "gold" | "green" | "purple" | "orange";
};

export function MraStatCard({ icon, label, value, note, tone = "default" }: Props) {
  return (
    <MraCard tone={tone} className="mra-stat-card">
      <div className="mra-stat-icon">{icon}</div>
      <div className="mra-stat-copy"><span>{label}</span><strong>{value}</strong>{note ? <small>{note}</small> : null}</div>
      <div className="mra-stat-bars" aria-hidden="true"><i /><i /><i /><i /><i /><i /></div>
    </MraCard>
  );
}
