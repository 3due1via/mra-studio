import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

type Item = { label: string; path: string; icon: string; badge?: string };
type Group = { title: string; items: Item[] };

const groups: Group[] = [
  {
    title: "NAVIGAZIONE",
    items: [
      { label: "Home", path: "/dashboard", icon: "⌂" },
      { label: "I miei progetti", path: "/projects", icon: "▦", badge: "NUOVO" },
      { label: "Tutte le schede", path: "/knowledge", icon: "▤" },
      { label: "Categorie", path: "/categories", icon: "□" },
      { label: "Etichette", path: "/tags", icon: "◇" },
      { label: "Storico modifiche", path: "/revisions", icon: "↶", badge: "8" },
      { label: "Bozze", path: "/drafts", icon: "✎", badge: "5" },
    ],
  },
  {
    title: "CONTENUTI",
    items: [
      { label: "Foto e video", path: "/media", icon: "▧" },
      { label: "PDF e documenti", path: "/documents", icon: "▱" },
      { label: "Procedure", path: "/procedures", icon: "⌁" },
      { label: "Ricambi e materiali", path: "/marketplace", icon: "▣" },
      { label: "Pronto al lavoro", path: "/pronto-al-lavoro", icon: "✓", badge: "NUOVO" },
    ],
  },
  {
    title: "AI E STRUMENTI",
    items: [
      { label: "Assistente tecnico", path: "/assistant", icon: "✦", badge: "AI" },
      { label: "Mappa collegamenti", path: "/graph", icon: "⌘" },
      { label: "Quiz e prove", path: "/quiz", icon: "✣" },
      { label: "Coppie di serraggio", path: "/torques", icon: "⌕" },
    ],
  },
  {
    title: "IMPOSTAZIONI",
    items: [
      { label: "Utenti e permessi", path: "/users", icon: "♙" },
      { label: "Registro attività", path: "/activity", icon: "↺" },
      { label: "Impostazioni", path: "/settings", icon: "⚙" },
      { label: "Design System", path: "/design-system", icon: "◆", badge: "014" },
      { label: "Backup ed esportazione", path: "/backup", icon: "▣" },
    ],
  },
];

export function Sidebar() {
  const { user } = useAuth();
  return (
    <aside className="sidebar mra-sidebar">
      <div className="mra-logo-lockup">
        <div className="mra-gear">⚙</div>
        <div><strong>MRA</strong><span>STUDIO</span></div>
      </div>
      <nav aria-label="Navigazione principale">
        {groups.map((group) => (
          <section className="nav-group" key={group.title}>
            <p>{group.title}</p>
            {group.items.filter((item) => !["/users", "/activity"].includes(item.path) || user?.role === "admin").map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}
              >
                <span className="nav-icon">{item.icon}</span>
                <span>{item.label}</span>
                {item.badge ? <b className="nav-badge">{item.badge}</b> : null}
              </NavLink>
            ))}
          </section>
        ))}
      </nav>
      <div className="plan-card">
        <div><strong>Piano professionale</strong><span>Attivo</span></div>
        <small>Scadenza: 12/12/2026</small>
        <button type="button">Gestisci piano</button>
      </div>
      <div className="sidebar-footer"><span>MRA Studio © 2026</span></div>
    </aside>
  );
}
