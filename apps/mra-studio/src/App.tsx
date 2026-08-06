import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./app/layout/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { KnowledgePage } from "./pages/KnowledgePage";
import { ModulePage } from "./pages/ModulePage";
import { DesignSystemPage } from "./pages/DesignSystemPage";
import { ReadyToWorkPage } from "./pages/ReadyToWorkPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { ProjectDetailPage } from "./pages/ProjectDetailPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:projectId" element={<ProjectDetailPage />} />

        <Route path="/categories" element={<ModulePage title="Categorie" />} />
        <Route path="/tags" element={<ModulePage title="Etichette" />} />
        <Route path="/revisions" element={<ModulePage title="Storico modifiche" />} />
        <Route path="/drafts" element={<ModulePage title="Bozze" />} />
        <Route path="/documents" element={<ModulePage title="PDF e documenti" />} />
        <Route path="/procedures" element={<ModulePage title="Procedure" />} />
        <Route path="/assistant" element={<ModulePage title="Assistente tecnico" />} />
        <Route path="/graph" element={<ModulePage title="Mappa collegamenti" />} />
        <Route path="/torques" element={<ModulePage title="Coppie di serraggio" />} />
        <Route path="/backup" element={<ModulePage title="Backup ed esportazione" />} />
        <Route path="/manuals" element={<ModulePage title="Manuals" />} />
        <Route path="/academy" element={<ModulePage title="Academy" />} />
        <Route path="/quiz" element={<ModulePage title="Quiz" />} />
        <Route path="/media" element={<ModulePage title="Media" />} />
        <Route path="/pronto-al-lavoro" element={<ReadyToWorkPage />} />
        <Route path="/marketplace" element={<ModulePage title="Marketplace" />} />
        <Route path="/partners" element={<ModulePage title="Partners" />} />
        <Route path="/laboratory" element={<ModulePage title="Laboratory" />} />
        <Route path="/analytics" element={<ModulePage title="Analytics" />} />
        <Route path="/users" element={<ModulePage title="Users" />} />
        <Route path="/settings" element={<ModulePage title="Settings" />} />
        <Route path="/design-system" element={<DesignSystemPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
