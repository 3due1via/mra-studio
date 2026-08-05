import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./app/layout/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { KnowledgePage } from "./pages/KnowledgePage";
import { ModulePage } from "./pages/ModulePage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/manuals" element={<ModulePage title="Manuals" />} />
        <Route path="/academy" element={<ModulePage title="Academy" />} />
        <Route path="/quiz" element={<ModulePage title="Quiz" />} />
        <Route path="/media" element={<ModulePage title="Media" />} />
        <Route path="/marketplace" element={<ModulePage title="Marketplace" />} />
        <Route path="/partners" element={<ModulePage title="Partners" />} />
        <Route path="/laboratory" element={<ModulePage title="Laboratory" />} />
        <Route path="/analytics" element={<ModulePage title="Analytics" />} />
        <Route path="/users" element={<ModulePage title="Users" />} />
        <Route path="/settings" element={<ModulePage title="Settings" />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
