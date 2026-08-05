import type { KnowledgeCardInput } from "../types/knowledge";
import { calculateQuality, hasContent, qualityItems } from "./knowledgeQuality";

type Props = {
  values: KnowledgeCardInput;
  isDirty: boolean;
};

export function KnowledgeQualityPanel({ values, isDirty }: Props) {
  const score = calculateQuality(values);
  const missing = qualityItems.filter((item) => !hasContent(values[item.key]));
  const publishable = score >= 85;

  return (
    <aside className="knowledge-quality-panel" aria-label="Qualità Knowledge Card">
      <div className="quality-panel-heading">
        <div>
          <p className="eyebrow">QUALITY GATE</p>
          <h3>Completezza</h3>
        </div>
        <strong className="quality-score">{score}%</strong>
      </div>

      <div className="quality-progress" aria-label={`Completezza ${score}%`}>
        <span style={{ width: `${score}%` }} />
      </div>

      <div className={`quality-publication ${publishable ? "ready" : "blocked"}`}>
        <span>{publishable ? "Pubblicabile" : "Non pubblicabile"}</span>
        <strong>{publishable ? "SÌ" : "NO"}</strong>
      </div>

      <ul className="quality-checklist">
        {qualityItems.map((item) => {
          const complete = hasContent(values[item.key]);
          return (
            <li key={item.key} className={complete ? "complete" : "missing"}>
              <span>{complete ? "✓" : "○"}</span>
              <span>{item.label}</span>
              <small>{item.weight}%</small>
            </li>
          );
        })}
      </ul>

      {missing.length > 0 ? (
        <p className="quality-hint">
          Mancano: {missing.slice(0, 3).map((item) => item.label).join(", ")}
          {missing.length > 3 ? ` e altri ${missing.length - 3}` : ""}.
        </p>
      ) : (
        <p className="quality-hint success">Tutti i campi controllati sono completi.</p>
      )}

      <div className={`save-state ${isDirty ? "dirty" : "saved"}`}>
        <span className="save-state-dot" />
        {isDirty ? "Modifiche non salvate" : "Dati sincronizzati"}
      </div>
    </aside>
  );
}
