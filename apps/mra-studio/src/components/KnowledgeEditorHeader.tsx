import { Button } from "./Button";

type Props = {
  isEditing: boolean;
  isSubmitting: boolean;
  onCancel: () => void;
};

export function KnowledgeEditorHeader({
  isEditing,
  isSubmitting,
  onCancel,
}: Props) {
  return (
    <header className="knowledge-editor-header">
      <div>
        <p className="eyebrow">KNOWLEDGE EDITOR</p>
        <h2>{isEditing ? "Modifica Knowledge Card" : "Nuova Knowledge Card"}</h2>
        <p className="knowledge-editor-subtitle">
          Compila i dati tecnici principali e salva la scheda nel Knowledge Engine.
        </p>
      </div>

      <div className="editor-actions">
        <Button type="button" className="button-secondary" onClick={onCancel}>
          Annulla
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Salvataggio..." : "Salva"}
        </Button>
      </div>
    </header>
  );
}
