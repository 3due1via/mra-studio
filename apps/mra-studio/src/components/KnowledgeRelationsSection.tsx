import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createKnowledgeRelation,
  deleteKnowledgeRelation,
  listKnowledgeCards,
  listKnowledgeRelations,
} from "../services/knowledgeApi";
import type {
  KnowledgeCard,
  KnowledgeRelationInput,
  KnowledgeRelationType,
} from "../types/knowledge";
import { Button } from "./Button";

const relationLabels: Record<KnowledgeRelationType, string> = {
  related_to: "Correlata a",
  requires: "Richiede",
  uses: "Utilizza",
  replaces: "Sostituisce",
  part_of: "Fa parte di",
  references: "Fa riferimento a",
};

type Props = {
  card: KnowledgeCard | null | undefined;
};

export function KnowledgeRelationsSection({ card }: Props) {
  const [targetId, setTargetId] = useState("");
  const [relationType, setRelationType] =
    useState<KnowledgeRelationType>("related_to");
  const [note, setNote] = useState("");
  const queryClient = useQueryClient();

  const cards = useQuery({
    queryKey: ["knowledge-cards", "relation-options"],
    queryFn: () => listKnowledgeCards(),
    enabled: Boolean(card),
  });

  const relations = useQuery({
    queryKey: ["knowledge-relations", card?.id],
    queryFn: () => listKnowledgeRelations(card!.id),
    enabled: Boolean(card?.id),
  });

  const availableCards = useMemo(
    () => (cards.data ?? []).filter((item) => item.id !== card?.id),
    [cards.data, card?.id],
  );

  const createRelation = useMutation({
    mutationFn: (input: KnowledgeRelationInput) =>
      createKnowledgeRelation(card!.id, input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["knowledge-relations", card?.id],
      });
      setTargetId("");
      setRelationType("related_to");
      setNote("");
    },
  });

  const removeRelation = useMutation({
    mutationFn: (relationId: string) =>
      deleteKnowledgeRelation(card!.id, relationId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["knowledge-relations", card?.id],
      });
    },
  });

  if (!card) {
    return (
      <section className="editor-section relations-empty">
        <p className="eyebrow">KNOWLEDGE GRAPH</p>
        <h3>Salva prima la Knowledge Card</h3>
        <p>
          Le relazioni possono essere aggiunte dopo il primo salvataggio,
          quando la card possiede un identificativo nel database.
        </p>
      </section>
    );
  }

  return (
    <section className="editor-section knowledge-relations-section">
      <header className="section-heading">
        <div>
          <p className="eyebrow">KNOWLEDGE GRAPH</p>
          <h3>Relazioni</h3>
        </div>
        <span className="relation-count">
          {relations.data?.length ?? 0} collegamenti
        </span>
      </header>

      <div className="relation-form">
        <label>
          Knowledge Card collegata
          <select value={targetId} onChange={(event) => setTargetId(event.target.value)}>
            <option value="">Seleziona una card...</option>
            {availableCards.map((item) => (
              <option key={item.id} value={item.id}>
                {item.code} — {item.title}
              </option>
            ))}
          </select>
        </label>

        <label>
          Tipo di relazione
          <select
            value={relationType}
            onChange={(event) =>
              setRelationType(event.target.value as KnowledgeRelationType)
            }
          >
            {Object.entries(relationLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <label className="relation-note-field">
          Nota
          <input
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Motivo o dettaglio del collegamento..."
            maxLength={1000}
          />
        </label>

        <Button
          type="button"
          disabled={!targetId || createRelation.isPending}
          onClick={() =>
            createRelation.mutate({
              target_id: targetId,
              relation_type: relationType,
              note,
            })
          }
        >
          {createRelation.isPending ? "Collegamento..." : "+ Aggiungi relazione"}
        </Button>
      </div>

      {createRelation.isError ? (
        <div className="notice error">{String(createRelation.error)}</div>
      ) : null}

      {relations.isLoading ? <p>Caricamento relazioni...</p> : null}

      {!relations.isLoading && (relations.data?.length ?? 0) === 0 ? (
        <div className="relations-empty-list">
          <strong>Nessuna relazione</strong>
          <span>Collega questa card ad altre Knowledge Card.</span>
        </div>
      ) : null}

      <div className="relation-list">
        {relations.data?.map((relation) => (
          <article className="relation-card" key={relation.id}>
            <div className="relation-direction">
              <span>{card.code}</span>
              <strong>{relationLabels[relation.relation_type]}</strong>
              <span>{relation.target_code}</span>
            </div>
            <div className="relation-card-content">
              <div>
                <h4>{relation.target_title}</h4>
                <p>{relation.target_category}</p>
                {relation.note ? <small>{relation.note}</small> : null}
              </div>
              <Button
                type="button"
                className="button-danger"
                disabled={removeRelation.isPending}
                onClick={() => {
                  if (window.confirm("Eliminare questa relazione?")) {
                    removeRelation.mutate(relation.id);
                  }
                }}
              >
                Rimuovi
              </Button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
