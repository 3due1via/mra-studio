import { apiRequest } from "./apiClient";
import type { AuditEvent, AuditEventPage, AuditFilters } from "../types/audit";

export function listAuditEvents(filters: AuditFilters = {}, cursor?: string) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); });
  if (cursor) params.set("cursor", cursor);
  return apiRequest<AuditEventPage>(`/api/v1/audit-events?${params}`);
}
export const getAuditEvent = (id: string) => apiRequest<AuditEvent>(`/api/v1/audit-events/${id}`);
