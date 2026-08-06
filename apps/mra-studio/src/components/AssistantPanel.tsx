import { useLocation } from "react-router-dom";

const messages: Record<string, string> = {
  "/dashboard": "Posso aiutarti a trovare un guasto, completare una scheda o preparare una procedura.",
  "/knowledge": "Apri una scheda e chiedimi di controllare completezza, sicurezza e passaggi mancanti.",
};

const activities = [
  ["✎", "Scheda “Motorino tergicristallo” modificata", "2 minuti fa"],
  ["↶", "Nuova revisione creata: REV 008", "15 minuti fa"],
  ["✓", "Scheda “Compressore A/C” pubblicata", "1 ora fa"],
  ["+", "Nuova scheda “Sensore ABS” creata", "2 ore fa"],
  ["▧", "Media aggiunto a “Pompa carburante”", "3 ore fa"],
];

export function AssistantPanel() {
  const { pathname } = useLocation();
  return (
    <aside className="assistant-panel mra-right-rail">
      <section className="rail-card activity-card">
        <header><strong>ATTIVITÀ RECENTI</strong><button type="button">Vedi tutte →</button></header>
        <div className="activity-list">
          {activities.map(([icon, label, time], index) => (
            <article key={label}>
              <span className={`activity-icon activity-${index}`}>{icon}</span>
              <div><strong>{label}</strong><small>Francesco · {time}</small></div>
            </article>
          ))}
        </div>
      </section>

      <section className="rail-card volumes-card">
        <header><strong>INDICE E VOLUMI</strong><button type="button">Scansiona QR</button></header>
        {[
          ["1", "Fondamenti dell’elettronica", "335"],
          ["2", "Alimentazione elettrica", "412"],
          ["3", "Componenti e strumenti", "487"],
          ["4", "Sistemi e reti di comunicazione", "378"],
        ].map(([n, title, count]) => (
          <article key={n}><b>{n}</b><strong>{title}</strong><span>{count}</span></article>
        ))}
        <button className="volumes-link" type="button">Vedi tutti i volumi →</button>
      </section>

      <section className="rail-card assistant-card">
        <header><div><strong>ASSISTENTE TECNICO</strong><small>● Online</small></div><span>✦</span></header>
        <h3>Ciao Francesco! 👋</h3>
        <p>{messages[pathname] ?? "Come posso aiutarti oggi?"}</p>
        <div className="assistant-shortcuts">
          <button type="button">Trova guasti simili</button>
          <button type="button">Suggerisci attrezzi</button>
          <button type="button">Crea procedura guidata</button>
          <button type="button">Controlla sicurezza</button>
        </div>
        <label className="assistant-input"><input placeholder="Fai una domanda tecnica..." /><button type="button">➤</button></label>
      </section>
    </aside>
  );
}
