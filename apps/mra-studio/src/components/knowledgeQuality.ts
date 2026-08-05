import type { KnowledgeCardInput } from "../types/knowledge";

export type QualityItem = {
  key: keyof KnowledgeCardInput;
  label: string;
  weight: number;
};

export const qualityItems: QualityItem[] = [
  { key: "code", label: "Codice", weight: 10 },
  { key: "title", label: "Titolo", weight: 15 },
  { key: "category", label: "Categoria", weight: 10 },
  { key: "summary", label: "Riassunto", weight: 10 },
  { key: "symptoms", label: "Sintomi", weight: 10 },
  { key: "causes", label: "Cause", weight: 10 },
  { key: "diagnosis", label: "Diagnosi", weight: 15 },
  { key: "procedure", label: "Procedura", weight: 10 },
  { key: "tools", label: "Strumenti", weight: 5 },
  { key: "safety", label: "Sicurezza", weight: 5 },
];

export function hasContent(value: unknown): boolean {
  return typeof value === "string" && value.trim().length > 0;
}

export function calculateQuality(values: KnowledgeCardInput): number {
  return qualityItems
    .filter((item) => hasContent(values[item.key]))
    .reduce((total, item) => total + item.weight, 0);
}
