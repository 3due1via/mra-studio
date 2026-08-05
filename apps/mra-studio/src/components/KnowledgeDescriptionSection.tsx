import type { UseFormRegister } from "react-hook-form";
import type { KnowledgeCardInput } from "../types/knowledge";

type Props = {
  register: UseFormRegister<KnowledgeCardInput>;
};

export function KnowledgeDescriptionSection({ register }: Props) {
  return (
    <section className="editor-section">
      <div className="editor-section-heading">
        <p className="eyebrow">DESCRIZIONE</p>
        <h3>Sintesi tecnica</h3>
        <p>Riassumi lo scopo e il contenuto principale della Knowledge Card.</p>
      </div>

      <div className="editor-single-column">
        <label>
          Riassunto
          <textarea
            {...register("summary")}
            placeholder="Descrizione sintetica, chiara e utile della scheda..."
          />
        </label>
      </div>
    </section>
  );
}
