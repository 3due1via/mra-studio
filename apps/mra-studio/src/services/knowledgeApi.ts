import type { KnowledgeCard, KnowledgeCardInput, KnowledgeRelation, KnowledgeRelationInput, KnowledgeRevision } from "../types/knowledge";
import { apiRequest } from "./apiClient";

const endpoint = "/api/v1/knowledge-cards";
export function listKnowledgeCards(search = "", status = "") { const params = new URLSearchParams(); if (search) params.set("search", search); if (status) params.set("status", status); return apiRequest<KnowledgeCard[]>(`${endpoint}?${params}`); }
export const createKnowledgeCard = (input: KnowledgeCardInput) => apiRequest<KnowledgeCard>(endpoint, { method: "POST", body: JSON.stringify(input) });
export const updateKnowledgeCard = (id: string, input: Partial<KnowledgeCardInput>) => apiRequest<KnowledgeCard>(`${endpoint}/${id}`, { method: "PUT", body: JSON.stringify(input) });
export const deleteKnowledgeCard = (id: string) => apiRequest<void>(`${endpoint}/${id}`, { method: "DELETE" });
export const listKnowledgeRelations = (sourceId: string) => apiRequest<KnowledgeRelation[]>(`${endpoint}/${sourceId}/relations`);
export const createKnowledgeRelation = (sourceId: string, input: KnowledgeRelationInput) => apiRequest<KnowledgeRelation>(`${endpoint}/${sourceId}/relations`, { method: "POST", body: JSON.stringify(input) });
export const deleteKnowledgeRelation = (sourceId: string, relationId: string) => apiRequest<void>(`${endpoint}/${sourceId}/relations/${relationId}`, { method: "DELETE" });
export const listKnowledgeRevisions = (cardId: string) => apiRequest<KnowledgeRevision[]>(`${endpoint}/${cardId}/revisions`);
export const restoreKnowledgeRevision = (cardId: string, revisionId: string) => apiRequest<KnowledgeCard>(`${endpoint}/${cardId}/revisions/${revisionId}/restore`, { method: "POST" });
