import { MraBadge, MraButton, MraCard, MraProgress, MraSectionHeader, MraStatCard } from "../ui";

export function DesignSystemPage() {
  return (
    <div className="design-system-page">
      <MraSectionHeader eyebrow="BUILD 014" title="Design System MRA" description="Componenti ufficiali riutilizzabili per Creator, Academy, Shop e Assistente." actions={<MraBadge tone="success">ATTIVO</MraBadge>} />

      <section className="design-system-stats">
        <MraStatCard icon="▦" label="COMPONENTI" value="6" note="Prima libreria ufficiale" tone="blue" />
        <MraStatCard icon="✓" label="COERENZA UI" value="100%" note="Colori e spaziature unificati" tone="green" />
        <MraStatCard icon="✦" label="PRONTO PER AI" value="Sì" note="Pannelli e badge dedicati" tone="purple" />
        <MraStatCard icon="◆" label="IDENTITÀ MRA" value="1.0" note="Blu notte e oro tecnico" tone="gold" />
      </section>

      <div className="design-system-grid">
        <MraCard eyebrow="AZIONI" title="Pulsanti ufficiali" className="design-demo-card">
          <div className="design-button-row"><MraButton>Salva scheda</MraButton><MraButton tone="gold">Pubblica</MraButton><MraButton tone="secondary">Anteprima</MraButton><MraButton tone="ghost">Annulla</MraButton><MraButton tone="danger">Elimina</MraButton></div>
        </MraCard>
        <MraCard eyebrow="STATI" title="Badge e segnalazioni" className="design-demo-card">
          <div className="design-button-row"><MraBadge>Bozza</MraBadge><MraBadge tone="info">In revisione</MraBadge><MraBadge tone="success">Pubblicata</MraBadge><MraBadge tone="warning">Da verificare</MraBadge><MraBadge tone="danger">Errore</MraBadge><MraBadge tone="ai">AI</MraBadge></div>
        </MraCard>
        <MraCard eyebrow="QUALITÀ" title="Avanzamento e completezza" className="design-demo-card">
          <div className="design-progress-stack"><MraProgress value={38} label="Bozza iniziale" /><MraProgress value={72} label="Pronto al lavoro" tone="gold" /><MraProgress value={94} label="Qualità scheda" tone="green" /><MraProgress value={81} label="Controllo AI" tone="purple" /></div>
        </MraCard>
        <MraCard eyebrow="CARD" title="Contenitore tecnico" tone="blue" interactive className="design-demo-card">
          <p className="design-copy">Questo componente diventerà la base di schede, progetti, procedure, corsi, kit e contenuti media.</p>
          <div className="design-card-footer"><MraBadge tone="gold">MRA CORE</MraBadge><MraButton size="sm" tone="secondary">Apri componente</MraButton></div>
        </MraCard>
      </div>
    </div>
  );
}
