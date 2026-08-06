export function Topbar() {
  return (
    <header className="topbar mra-topbar">
      <div className="topbar-search-wrap">
        <span>⌕</span>
        <input className="global-search" placeholder="Cerca scheda, componente, guasto, codice o procedura..." />
        <kbd>CTRL + K</kbd>
      </div>
      <div className="topbar-actions">
        <button type="button" className="icon-button" aria-label="Tema">☼</button>
        <button type="button" className="icon-button notification-button" aria-label="Notifiche">♢<b>7</b></button>
        <button type="button" className="icon-button" aria-label="Aiuto">?</button>
        <button className="profile-button" type="button">
          <span className="avatar">FM</span>
          <span><strong>Francesco Munno</strong><small>Amministratore</small></span>
          <span>⌄</span>
        </button>
      </div>
    </header>
  );
}
