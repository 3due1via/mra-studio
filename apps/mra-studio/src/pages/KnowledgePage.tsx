import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../components/Button";
import { KnowledgeEditor } from "../components/KnowledgeEditor";
import { PageHeader } from "../components/PageHeader";
import {
  createKnowledgeCard,
  deleteKnowledgeCard,
  listKnowledgeCards,
  updateKnowledgeCard,
} from "../services/knowledgeApi";
import type { KnowledgeCard, KnowledgeCardInput } from "../types/knowledge";

export function KnowledgePage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [editing, setEditing] = useState<KnowledgeCard | null | undefined>();
  const [message, setMessage] = useState("");
  const queryClient = useQueryClient();

  const cards = useQuery({
    queryKey: ["knowledge-cards", search, status],
    queryFn: () => listKnowledgeCards(search, status),
  });

  const save = useMutation({
    mutationFn: (values: KnowledgeCardInput) =>
      editing
        ? updateKnowledgeCard(editing.id, values)
        : createKnowledgeCard(values),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["knowledge-cards"] });
      setMessage(editing ? "Knowledge Card aggiornata." : "Knowledge Card creata.");
      setEditing(undefined);
    },
  });

  const remove = useMutation({
    mutationFn: deleteKnowledgeCard,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["knowledge-cards"] });
      setMessage("Knowledge Card eliminata.");
    },
  });

  const visibleCards = useMemo(() => cards.data ?? [], [cards.data]);

  if (editing !== undefined) {
    return (
      <>
        {save.isError ? <div className="notice error">{String(save.error)}</div> : null}
        <KnowledgeEditor
          card={editing}
          onCancel={() => setEditing(undefined)}
          onSave={(values) => save.mutateAsync(values)}
          onRestored={(restoredCard) => {
            setEditing(restoredCard);
            setMessage("Revisione ripristinata.");
          }}
        />
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="KNOWLEDGE ENGINE"
        title="Knowledge"
        description="Crea, modifica, cerca ed elimina Knowledge Card salvate realmente in PostgreSQL."
        actions={<Button onClick={() => { setMessage(""); setEditing(null); }}>+ Nuova Knowledge Card</Button>}
      />

      {message ? <div className="notice success">{message}</div> : null}
      {remove.isError ? <div className="notice error">{String(remove.error)}</div> : null}

      <section className="toolbar panel">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Cerca per codice, titolo o categoria..."
          aria-label="Cerca Knowledge Card"
        />
        <select value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Filtra per stato">
          <option value="">Tutti gli stati</option>
          <option value="draft">Bozza</option>
          <option value="review">In revisione</option>
          <option value="verified">Verificata</option>
          <option value="approved">Approvata</option>
          <option value="published">Pubblicata</option>
          <option value="archived">Archiviata</option>
          <option value="rejected">Rifiutata</option>
        </select>
      </section>

      {cards.isLoading ? <section className="empty-state"><h2>Caricamento...</h2></section> : null}
      {cards.isError ? <section className="empty-state error-box"><h2>Errore API</h2><p>{String(cards.error)}</p></section> : null}

      {!cards.isLoading && !cards.isError && visibleCards.length === 0 ? (
        <section className="empty-state">
          <h2>Nessuna Knowledge Card</h2>
          <p>Crea la prima scheda e salvala nel database PostgreSQL.</p>
          <Button onClick={() => setEditing(null)}>Crea Knowledge Card</Button>
        </section>
      ) : null}

      {visibleCards.length > 0 ? (
        <section className="table-card">
          <table>
            <thead>
              <tr>
                <th>Codice</th><th>Titolo</th><th>Categoria</th><th>Stato</th><th>Versione</th><th>Azioni</th>
              </tr>
            </thead>
            <tbody>
              {visibleCards.map((card) => (
                <tr key={card.id}>
                  <td className="code-cell">{card.code}</td>
                  <td>{card.title}</td>
                  <td>{card.category}</td>
                  <td><span className={`status-badge status-${card.status}`}>{card.status}</span></td>
                  <td>{card.version}</td>
                  <td className="row-actions">
                    <Button className="button-secondary" onClick={() => setEditing(card)}>Modifica</Button>
                    <Button className="button-danger" disabled={remove.isPending} onClick={() => {
                      if (window.confirm(`Eliminare ${card.code}?`)) remove.mutate(card.id);
                    }}>Elimina</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
    </>
  );
}
