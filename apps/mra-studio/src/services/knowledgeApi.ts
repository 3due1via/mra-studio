import type {
  KnowledgeCard,
  KnowledgeCardInput,
  KnowledgeRelation,
  KnowledgeRelationInput,
} from "../types/knowledge";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const endpoint = `${BASE}/api/v1/knowledge-cards`;

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Errore API");
  }
  return response.json() as Promise<T>;
}

export async function listKnowledgeCards(
  search = "",
  status = ""
): Promise<KnowledgeCard[]> {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (status) params.set("status", status);
  return parse(await fetch(`${endpoint}?${params.toString()}`));
}

export async function createKnowledgeCard(
  input: KnowledgeCardInput
): Promise<KnowledgeCard> {
  return parse(
    await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input)
    })
  );
}

export async function updateKnowledgeCard(
  id: string,
  input: Partial<KnowledgeCardInput>
): Promise<KnowledgeCard> {
  return parse(
    await fetch(`${endpoint}/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input)
    })
  );
}

export async function deleteKnowledgeCard(id: string): Promise<void> {
  const response = await fetch(`${endpoint}/${id}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Impossibile eliminare la Knowledge Card");
}


export async function listKnowledgeRelations(
  sourceId: string,
): Promise<KnowledgeRelation[]> {
  return parse(
    await fetch(`${endpoint}/${sourceId}/relations`),
  );
}

export async function createKnowledgeRelation(
  sourceId: string,
  input: KnowledgeRelationInput,
): Promise<KnowledgeRelation> {
  return parse(
    await fetch(`${endpoint}/${sourceId}/relations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  );
}

export async function deleteKnowledgeRelation(
  sourceId: string,
  relationId: string,
): Promise<void> {
  const response = await fetch(
    `${endpoint}/${sourceId}/relations/${relationId}`,
    { method: "DELETE" },
  );
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Impossibile eliminare la relazione");
  }
}

export async function listKnowledgeRevisions(
  cardId: string,
): Promise<import("../types/knowledge").KnowledgeRevision[]> {
  return parse(
    await fetch(`${endpoint}/${cardId}/revisions`),
  );
}

export async function restoreKnowledgeRevision(
  cardId: string,
  revisionId: string,
): Promise<KnowledgeCard> {
  return parse(
    await fetch(`${endpoint}/${cardId}/revisions/${revisionId}/restore`, {
      method: "POST",
    }),
  );
}
