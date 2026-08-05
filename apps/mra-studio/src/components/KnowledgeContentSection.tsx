import type { UseFormRegister } from "react-hook-form";
import type { KnowledgeCardInput } from "../types/knowledge";

type Props = {
  register: UseFormRegister<KnowledgeCardInput>;
};

export function KnowledgeContentSection({ register }: Props) {
  return (
    <section className="editor-section">
      <div className="editor-section-heading">
        <p className="eyebrow">CONTENUTO TECNICO</p>
        <h3>Diagnosi e procedura</h3>
        <p>Organizza la conoscenza necessaria per comprendere e risolvere il problema.</p>
      </div>

      <div className="editor-content-grid">
        <label className="field-full">
          Riassunto
          <textarea
            {...register("summary")}
            placeholder="Descrizione sintetica della scheda..."
          />
        </label>

        <label>
          Sintomi
          <textarea
            {...register("symptoms")}
            placeholder="Segnali e sintomi osservabili..."
          />
        </label>

        <label>
          Cause
          <textarea
            {...register("causes")}
            placeholder="Cause probabili e condizioni correlate..."
          />
        </label>

        <label>
          Diagnosi
          <textarea
            {...register("diagnosis")}
            placeholder="Controlli e criteri di diagnosi..."
          />
        </label>

        <label>
          Procedura
          <textarea
            {...register("procedure")}
            placeholder="Procedura tecnica passo per passo..."
          />
        </label>

        <label>
          Strumenti
          <textarea
            {...register("tools")}
            placeholder="Attrezzatura e strumenti necessari..."
          />
        </label>

        <label>
          Sicurezza
          <textarea
            {...register("safety")}
            placeholder="Pericoli, DPI e precauzioni..."
          />
        </label>
      </div>
    </section>
  );
}
