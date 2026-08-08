export type AuditEvent = {
  id: string; occurred_at: string; actor_user_id: string | null; actor_email_snapshot: string | null;
  action: string; entity_type: string; entity_id: string | null; outcome: "success" | "failure";
  request_id: string; changed_fields: string[]; changes: Record<string, unknown>; metadata_json: Record<string, unknown>;
};
export type AuditEventPage = { items: AuditEvent[]; next_cursor: string | null };
export type AuditFilters = Partial<Pick<AuditEvent, "actor_user_id" | "action" | "entity_type" | "entity_id" | "outcome" | "request_id">> & { occurred_from?: string; occurred_to?: string };
