import { useLocation } from "react-router-dom";

const messages: Record<string, string> = {
  "/dashboard": "Controlla i contenuti presenti e lo stato dei servizi MRA.",
  "/knowledge": "Crea una scheda, salvala e verifica che resti disponibile dopo il riavvio.",
};

export function AssistantPanel() {
  const { pathname } = useLocation();
  return (
    <aside className="assistant-panel">
      <header>
        <span className="assistant-icon">AI</span>
        <div>
          <strong>MRA Assistant</strong>
          <small>Supporto contestuale</small>
        </div>
      </header>
      <div className="assistant-content">
        <p className="eyebrow">SUGGERIMENTO</p>
        <h3>Prossima azione</h3>
        <p>{messages[pathname] ?? "Questo modulo è collegato e pronto per uno sprint dedicato."}</p>
      </div>
      <div className="quality-box">
        <span>Release frontend</span>
        <strong>0.3.2</strong>
        <small>Knowledge Workspace collegato alle API</small>
      </div>
    </aside>
  );
}
