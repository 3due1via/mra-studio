import { Button } from "./Button";

type Props = {
  status: string;
  score: number;
  isSubmitting: boolean;
  onSaveDraft: () => void;
  onSendToReview: () => void;
  onPublish: () => void;
};

export function KnowledgeWorkflowBar({
  status,
  score,
  isSubmitting,
  onSaveDraft,
  onSendToReview,
  onPublish,
}: Props) {
  const canPublish = score >= 85;

  return (
    <section className="knowledge-workflow-bar" aria-label="Workflow editoriale">
      <div className="workflow-current-state">
        <span>Stato corrente</span>
        <strong>{status || "draft"}</strong>
      </div>

      <div className="workflow-steps" aria-label="Stati workflow">
        <span className={status === "draft" ? "active" : ""}>Bozza</span>
        <i />
        <span className={status === "review" ? "active" : ""}>Revisione</span>
        <i />
        <span className={status === "published" ? "active" : ""}>Pubblicata</span>
      </div>

      <div className="workflow-actions">
        <Button type="button" className="button-secondary" disabled={isSubmitting} onClick={onSaveDraft}>
          Salva bozza
        </Button>
        <Button type="button" className="button-review" disabled={isSubmitting} onClick={onSendToReview}>
          Invia in revisione
        </Button>
        <Button
          type="button"
          className="button-publish"
          disabled={isSubmitting || !canPublish}
          onClick={onPublish}
          title={canPublish ? "Pubblica la Knowledge Card" : "Serve almeno l’85% di completezza"}
        >
          Pubblica
        </Button>
      </div>
    </section>
  );
}
