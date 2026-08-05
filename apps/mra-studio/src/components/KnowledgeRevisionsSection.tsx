import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listKnowledgeRevisions,
  restoreKnowledgeRevision,
} from "../services/knowledgeApi";
import type { KnowledgeCard } from "../types/knowledge";
import { Button } from "./Button";

type Props = {
  card?: KnowledgeCard | null;
  onRestored: (card: KnowledgeCard) => void;
};

const actionLabels: Record<string, string> = {
  create: "Creazione",
  update: "Modifica",
  restore: "Ripristino",
};

export function KnowledgeRevisionsSection({ card, onRestored }: Props) {
  const queryClient = useQueryClient();
  const revisions = useQuery({
    queryKey: ["knowledge-revisions", card?.id],
    queryFn: () => listKnowledgeRevisions(card!.id),
    enabled: Boolean(card?.id),
  });

  const restore = useMutation({
    mutationFn: (revisionId: string) =>
      restoreKnowledgeRevision(card!.id, revisionId),
    onSuccess: async (restoredCard) => {
      await queryClient.invalidateQueries({ queryKey: ["knowledge-cards"] });
      await queryClient.invalidateQueries({
        queryKey: ["knowledge-revisions", card?.id],
      });
      onRestored(restoredCard);
    },
  });

  if (!card) {
    return (
      <section className="revisions-empty">
        <h3>Revisioni disponibili dopo il primo salvataggio</h3>
        <p>Salva la nuova Knowledge Card per iniziare la cronologia.</p>
      </section>
    );
  }

  if (revisions.isLoading) {
    return <section className="revisions-empty">Caricamento revisioni...</section>;
  }

  if (revisions.isError) {
    return (
      <section className="revisions-empty error-box">
        {String(revisions.error)}
      </section>
    );
  }

  return (
    <section className="knowledge-revisions-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">VERSION ENGINE</p>
          <h3>Cronologia revisioni</h3>
        </div>
        <span className="revision-count">{revisions.data?.length ?? 0}</span>
      </div>

      {restore.isError ? (
        <div className="notice error">{String(restore.error)}</div>
      ) : null}

      <div className="revision-list">
        {(revisions.data ?? []).map((revision, index) => (
          <article className="revision-card" key={revision.id}>
            <div className="revision-number">#{revision.revision_number}</div>
            <div className="revision-content">
              <div className="revision-meta">
                <strong>{actionLabels[revision.action] ?? revision.action}</strong>
                <span>{new Date(revision.created_at).toLocaleString("it-IT")}</span>
              </div>
              <h4>{revision.snapshot.title || "Senza titolo"}</h4>
              <p>
                {revision.snapshot.status} · versione {revision.snapshot.version}
              </p>
              {revision.note ? <small>{revision.note}</small> : null}
            </div>
            <Button
              type="button"
              className="button-secondary"
              disabled={index === 0 || restore.isPending}
              onClick={() => {
                if (
                  window.confirm(
                    `Ripristinare la revisione #${revision.revision_number}?`,
                  )
                ) {
                  restore.mutate(revision.id);
                }
              }}
            >
              {index === 0 ? "Corrente" : "Ripristina"}
            </Button>
          </article>
        ))}
      </div>
    </section>
  );
}
