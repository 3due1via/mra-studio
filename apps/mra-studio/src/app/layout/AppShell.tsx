import { Outlet } from "react-router-dom";
import { Sidebar } from "../../components/Sidebar";
import { Topbar } from "../../components/Topbar";
import { AssistantPanel } from "../../components/AssistantPanel";
import { StatusBar } from "../../components/StatusBar";

export function AppShell() {
  return (
    <div className="app-shell">
      <Topbar />
      <div className="main-grid">
        <Sidebar />
        <main className="workspace"><Outlet /></main>
        <AssistantPanel />
      </div>
      <StatusBar />
    </div>
  );
}
