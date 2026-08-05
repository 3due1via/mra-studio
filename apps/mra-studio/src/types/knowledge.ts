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
