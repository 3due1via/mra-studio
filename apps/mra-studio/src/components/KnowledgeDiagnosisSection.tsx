import type { UseFormRegister } from "react-hook-form";
import type { KnowledgeCardInput } from "../types/knowledge";

type Props = {
  register: UseFormRegister<KnowledgeCardInput>;
};

export function KnowledgeDiagnosisSection({ register }: Props) {
  return (
    <section className="editor-section">
      <div className="editor-section-heading">
        <p className="eyebrow">DIAGNOSI</p>
        <h3>Sintomi, cause e controlli</h3>
        <p>Documenta il percorso logico che porta all'identificazione del problema.</p>
      </div>

      <div className="editor-content-grid">
        <label>
          Sintomi
          <textarea
            {...register("symptoms")}
            placeholder="Segnali, anomalie e comportamenti osservabili..."
          />
        </label>

        <label>
          Cause
          <textarea
            {...register("causes")}
            placeholder="Cause probabili e condizioni correlate..."
          />
        </label>

        <label className="field-full">
          Diagnosi
          <textarea
            {...register("diagnosis")}
            placeholder="Controlli, misure, valori attesi e criteri di conferma..."
          />
        </label>
      </div>
    </section>
  );
}
