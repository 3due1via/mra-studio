import { useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import type { KnowledgeCard, KnowledgeCardInput } from "../types/knowledge";
import { KnowledgeDescriptionSection } from "./KnowledgeDescriptionSection";
import { KnowledgeDiagnosisSection } from "./KnowledgeDiagnosisSection";
import { KnowledgeEditorFooter } from "./KnowledgeEditorFooter";
import { KnowledgeEditorHeader } from "./KnowledgeEditorHeader";
import { KnowledgeGeneralSection } from "./KnowledgeGeneralSection";
import { KnowledgeProcedureSection } from "./KnowledgeProcedureSection";
import { KnowledgeRelationsSection } from "./KnowledgeRelationsSection";
import { KnowledgeRevisionsSection } from "./KnowledgeRevisionsSection";
import { KnowledgeQualityPanel } from "./KnowledgeQualityPanel";
import type { KnowledgeTab } from "./KnowledgeTabs";
import { KnowledgeSectionNav } from "./KnowledgeSectionNav";
import { KnowledgeInspectorPanel } from "./KnowledgeInspectorPanel";
import { KnowledgeWorkflowBar } from "./KnowledgeWorkflowBar";
import { calculateQuality } from "./knowledgeQuality";

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
  onRestored: (card: KnowledgeCard) => void;
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

export function KnowledgeEditor({ card, onCancel, onSave, onRestored }: Props) {
  const [activeTab, setActiveTab] = useState<KnowledgeTab>("general");
  const { register, handleSubmit, reset, watch, setValue, formState } =
    useForm<KnowledgeCardInput>({ defaultValues: empty });

  useEffect(() => {
    reset(toFormValues(card));
    setActiveTab("general");
  }, [card, reset]);

  const values = watch();
  const score = calculateQuality(values);

  const saveWithStatus = useCallback(
    (status: KnowledgeCardInput["status"]) => {
      setValue("status", status, { shouldDirty: true });
      void handleSubmit((formValues) => onSave({ ...formValues, status }))();
    },
    [handleSubmit, onSave, setValue],
  );

  useEffect(() => {
    const saveWithKeyboard = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        saveWithStatus(values.status || "draft");
      }
    };

    window.addEventListener("keydown", saveWithKeyboard);
    return () => window.removeEventListener("keydown", saveWithKeyboard);
  }, [saveWithStatus, values.status]);

  return (
    <form className="editor-card" onSubmit={handleSubmit(onSave)}>
      <KnowledgeEditorHeader
        isEditing={Boolean(card)}
        isSubmitting={formState.isSubmitting}
        onCancel={onCancel}
      />

      <div className="knowledge-pro-workspace">
        <KnowledgeSectionNav
          activeSection={activeTab}
          onChange={setActiveTab}
          hasSavedCard={Boolean(card)}
        />

        <main className="knowledge-pro-main">
          <div className="knowledge-pro-section-header">
            <div>
              <p className="eyebrow">AREA DI LAVORO</p>
              <h3>{activeTab === "general" ? "Dati generali" : activeTab === "description" ? "Descrizione tecnica" : activeTab === "diagnosis" ? "Diagnosi" : activeTab === "procedure" ? "Procedura operativa" : activeTab === "relations" ? "Collegamenti" : "Storico modifiche"}</h3>
            </div>
            <span className="knowledge-pro-focus-badge">Modalità concentrata</span>
          </div>

          <div className="knowledge-editor-body knowledge-editor-tab-panel">
          {activeTab === "general" ? (
            <KnowledgeGeneralSection register={register} isEditing={Boolean(card)} />
          ) : null}

          {activeTab === "description" ? (
            <KnowledgeDescriptionSection register={register} />
          ) : null}

          {activeTab === "diagnosis" ? (
            <KnowledgeDiagnosisSection register={register} />
          ) : null}

          {activeTab === "procedure" ? (
            <KnowledgeProcedureSection register={register} />
          ) : null}

          {activeTab === "relations" ? (
            <KnowledgeRelationsSection card={card} />
          ) : null}

          {activeTab === "revisions" ? (
            <KnowledgeRevisionsSection card={card} onRestored={onRestored} />
          ) : null}
          </div>
        </main>

        <KnowledgeInspectorPanel
          values={values}
          isDirty={formState.isDirty}
          isEditing={Boolean(card)}
        />
      </div>

      <KnowledgeWorkflowBar
        status={values.status}
        score={score}
        isSubmitting={formState.isSubmitting}
        onSaveDraft={() => saveWithStatus("draft")}
        onSendToReview={() => saveWithStatus("review")}
        onPublish={() => saveWithStatus("published")}
      />

      <KnowledgeEditorFooter
        status={values.status}
        version={values.version}
        isEditing={Boolean(card)}
        isDirty={formState.isDirty}
      />
    </form>
  );
}
