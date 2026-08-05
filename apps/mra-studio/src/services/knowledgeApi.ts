import type { KnowledgeCard, KnowledgeCardInput } from "../types/knowledge";

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
