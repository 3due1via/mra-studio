export type KnowledgeCard = {
  id: string;
  code: string;
  title: string;
  category: string;
  status: string;
  version: string;
  summary: string;
  symptoms: string;
  causes: string;
  diagnosis: string;
  procedure: string;
  tools: string;
  safety: string;
  created_at: string;
  updated_at: string;
};

export type KnowledgeCardInput = Omit<
  KnowledgeCard,
  "id" | "created_at" | "updated_at"
>;

export type KnowledgeRelationType =
  | "related_to"
  | "requires"
  | "uses"
  | "replaces"
  | "part_of"
  | "references";

export type KnowledgeRelation = {
  id: string;
  source_id: string;
  target_id: string;
  relation_type: KnowledgeRelationType;
  note: string;
  target_code: string;
  target_title: string;
  target_category: string;
  created_at: string;
};

export type KnowledgeRelationInput = {
  target_id: string;
  relation_type: KnowledgeRelationType;
  note: string;
};

export type KnowledgeRevision = {
  id: string;
  card_id: string;
  revision_number: number;
  action: "create" | "update" | "restore" | string;
  note: string;
  snapshot: KnowledgeCardInput;
  created_at: string;
};
