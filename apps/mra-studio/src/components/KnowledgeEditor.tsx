import { useEffect } from "react";
import { useForm } from "react-hook-form";
import type { KnowledgeCard, KnowledgeCardInput } from "../types/knowledge";
import { KnowledgeContentSection } from "./KnowledgeContentSection";
import { KnowledgeEditorFooter } from "./KnowledgeEditorFooter";
import { KnowledgeEditorHeader } from "./KnowledgeEditorHeader";
import { KnowledgeGeneralSection } from "./KnowledgeGeneralSection";

const empty: KnowledgeCardInput = {
  code: "",
  title: "",
  category: "",
  status: "draft",
  version: "1.0.0",
  summary: "",
  symptoms: "",
  causes: "",
  diagnosis: "",
  procedure: "",
  tools: "",
  safety: "",
};

type Props = {
  card?: KnowledgeCard | null;
  onCancel: () => void;
  onSave: (values: KnowledgeCardInput) => Promise<void>;
};

function toFormValues(card?: KnowledgeCard | null): KnowledgeCardInput {
  if (!card) return empty;

  return {
    code: card.code,
    title: card.title,
    category: card.category,
    status: card.status,
    version: card.version,
    summary: card.summary,
    symptoms: card.symptoms,
    causes: card.causes,
    diagnosis: card.diagnosis,
    procedure: card.procedure,
    tools: card.tools,
    safety: card.safety,
  };
}

export function KnowledgeEditor({ card, onCancel, onSave }: Props) {
  const { register, handleSubmit, reset, watch, formState } =
    useForm<KnowledgeCardInput>({ defaultValues: empty });

  useEffect(() => {
    reset(toFormValues(card));
  }, [card, reset]);

  const status = watch("status");
  const version = watch("version");

  return (
    <form className="editor-card" onSubmit={handleSubmit(onSave)}>
      <KnowledgeEditorHeader
        isEditing={Boolean(card)}
        isSubmitting={formState.isSubmitting}
        onCancel={onCancel}
      />

      <div className="knowledge-editor-body">
        <KnowledgeGeneralSection register={register} isEditing={Boolean(card)} />
        <KnowledgeContentSection register={register} />
      </div>

      <KnowledgeEditorFooter
        status={status}
        version={version}
        isEditing={Boolean(card)}
      />
    </form>
  );
}
