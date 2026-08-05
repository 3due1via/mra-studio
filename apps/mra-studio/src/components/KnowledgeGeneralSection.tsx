import type { UseFormRegister } from "react-hook-form";
import type { KnowledgeCardInput } from "../types/knowledge";

type Props = {
  register: UseFormRegister<KnowledgeCardInput>;
  isEditing: boolean;
};

export function KnowledgeGeneralSection({ register, isEditing }: Props) {
  return (
    <section className="editor-section">
      <div className="editor-section-heading">
        <p className="eyebrow">IDENTITÀ</p>
        <h3>Informazioni generali</h3>
        <p>Codice, titolo, classificazione e stato editoriale della scheda.</p>
      </div>

      <div className="form-grid">
        <label>
          Codice
          <input
            {...register("code", { required: true })}
            disabled={isEditing}
            placeholder="KC-000001"
          />
        </label>

        <label className="field-span-2">
          Titolo
          <input
            {...register("title", { required: true })}
            placeholder="Titolo della Knowledge Card"
          />
        </label>

        <label>
          Categoria
          <input
            {...register("category", { required: true })}
            placeholder="Elettronica"
          />
        </label>

        <label>
          Stato
          <select {...register("status")}>
            <option value="draft">Bozza</option>
            <option value="review">In revisione</option>
            <option value="verified">Verificata</option>
            <option value="approved">Approvata</option>
            <option value="published">Pubblicata</option>
            <option value="archived">Archiviata</option>
            <option value="rejected">Rifiutata</option>
          </select>
        </label>

        <label>
          Versione
          <input {...register("version")} placeholder="1.0.0" />
        </label>
      </div>
    </section>
  );
}
