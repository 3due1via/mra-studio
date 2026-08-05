import type { UseFormRegister } from "react-hook-form";
import type { KnowledgeCardInput } from "../types/knowledge";

type Props = {
  register: UseFormRegister<KnowledgeCardInput>;
};

export function KnowledgeProcedureSection({ register }: Props) {
  return (
    <section className="editor-section">
      <div className="editor-section-heading">
        <p className="eyebrow">PROCEDURA</p>
        <h3>Intervento tecnico</h3>
        <p>Descrivi passaggi, strumenti e precauzioni necessari per operare correttamente.</p>
      </div>

      <div className="editor-content-grid">
        <label className="field-full">
          Procedura
          <textarea
            {...register("procedure")}
            placeholder="Procedura tecnica ordinata, verificabile e passo per passo..."
          />
        </label>

        <label>
          Strumenti
          <textarea
            {...register("tools")}
            placeholder="Attrezzatura, strumenti di misura e materiali necessari..."
          />
        </label>

        <label>
          Sicurezza
          <textarea
            {...register("safety")}
            placeholder="Pericoli, DPI, precauzioni e controlli prima dell'intervento..."
          />
        </label>
      </div>
    </section>
  );
}
