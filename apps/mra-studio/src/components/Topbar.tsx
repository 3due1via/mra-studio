import { useAuth } from "../auth/AuthContext";

export function Topbar() {
  const { user, logout } = useAuth();
  return (
    <header className="topbar mra-topbar">
      <div className="topbar-search-wrap">
        <span>⌕</span><input className="global-search" placeholder="Cerca scheda, componente, guasto, codice o procedura..." /><kbd>CTRL + K</kbd>
      </div>
      <div className="topbar-actions">
        <button type="button" className="icon-button" aria-label="Tema">☼</button>
        <button type="button" className="icon-button notification-button" aria-label="Notifiche">◇<b>7</b></button>
        <button type="button" className="icon-button" aria-label="Aiuto">?</button>
        <button className="profile-button" type="button" onClick={() => void logout()} title="Disconnetti">
          <span className="avatar">{user?.display_name.slice(0, 2).toUpperCase()}</span>
          <span><strong>{user?.display_name}</strong><small>{user?.role}</small></span><span>Esci</span>
        </button>
      </div>
    </header>
  );
}
