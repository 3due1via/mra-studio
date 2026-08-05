export function Topbar() {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">MRA</div>
        <div><strong>MRA Studio</strong><span>Professional Technical Knowledge Platform</span></div>
      </div>
      <div className="topbar-actions">
        <input className="global-search" placeholder="Cerca in MRA..." />
        <button className="profile-button"><span className="avatar">FM</span>Francesco</button>
      </div>
    </header>
  );
}
