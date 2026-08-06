import { useMemo, useState } from "react";

type CheckItem = {
  id: string;
  section: "Materiale" | "Attrezzi" | "Sicurezza";
  label: string;
  weight: number;
  price: number;
  note: string;
};

const items: CheckItem[] = [
  { id: "presa", section: "Materiale", label: "Presa elettrica compatibile", weight: 50, price: 8.9, note: "Presa 2P+T 16 A, colore bianco" },
  { id: "giravite", section: "Attrezzi", label: "Giravite a croce isolato", weight: 10, price: 7.5, note: "Isolamento certificato fino a 1.000 V" },
  { id: "torcia", section: "Attrezzi", label: "Torcia o lampada da lavoro", weight: 10, price: 12.9, note: "Illumina la scatola anche senza corrente" },
  { id: "forbici", section: "Attrezzi", label: "Forbici da elettricista", weight: 15, price: 14.9, note: "Lame corte, tacca spelafili e impugnatura isolata" },
  { id: "nastro", section: "Sicurezza", label: "Nastro isolante professionale", weight: 15, price: 2.8, note: "Autoestinguente, conforme CEI EN 60454" },
];

const money = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" });

export function ReadyToWorkPage() {
  const [owned, setOwned] = useState<Record<string, boolean>>({ presa: true });
  const [cart, setCart] = useState<Record<string, boolean>>({});
  const [safetyRead, setSafetyRead] = useState(false);
  const [hideSafety, setHideSafety] = useState(false);

  const completion = useMemo(
    () => items.reduce((total, item) => total + (owned[item.id] || cart[item.id] ? item.weight : 0), 0),
    [owned, cart],
  );
  const selected = items.filter((item) => cart[item.id] && !owned[item.id]);
  const subtotal = selected.reduce((total, item) => total + item.price, 0);
  const discountRate = selected.length >= 5 ? 0.1 : selected.length >= 4 ? 0.08 : selected.length >= 3 ? 0.05 : selected.length >= 2 ? 0.03 : 0;
  const total = subtotal * (1 - discountRate);

  function setAnswer(id: string, value: boolean) {
    setOwned((current) => ({ ...current, [id]: value }));
    if (value) setCart((current) => ({ ...current, [id]: false }));
  }

  return (
    <div className="ready-page">
      <section className="ready-hero">
        <div>
          <p>GUIDA ALL’ACQUISTO E AL LAVORO</p>
          <h1>Pronto al lavoro</h1>
          <h2>Sostituire una presa elettrica</h2>
          <p>Controlla in pochi passaggi se possiedi materiale e attrezzi. MRA ti propone solo ciò che manca.</p>
        </div>
        <div className={`ready-score ${completion === 100 ? "complete" : ""}`}>
          <small>SEI PRONTO AL</small><strong>{completion}%</strong><span>{completion === 100 ? "Puoi iniziare" : "Completa l’occorrente"}</span>
        </div>
      </section>

      <section className="ready-layout">
        <main className="ready-checklist">
          {(["Materiale", "Attrezzi", "Sicurezza"] as const).map((section) => (
            <section className="ready-section" key={section}>
              <header><div><span>{section === "Materiale" ? "▣" : section === "Attrezzi" ? "⚒" : "◇"}</span><div><h3>{section}</h3><small>{section === "Materiale" ? "Prodotti necessari" : section === "Attrezzi" ? "Quello che serve per lavorare bene" : "Elementi per un lavoro più sicuro"}</small></div></div></header>
              {items.filter((item) => item.section === section).map((item) => {
                const available = owned[item.id] || cart[item.id];
                return (
                  <article className={`ready-item ${available ? "available" : "missing"}`} key={item.id}>
                    <div className="ready-item-main">
                      <span className="item-state">{available ? "✓" : "!"}</span>
                      <div><strong>{item.label}</strong><small>{item.note}</small></div>
                      <b>+{item.weight}%</b>
                    </div>
                    <div className="owned-question">
                      <span>Ce l’hai già?</span>
                      <button className={owned[item.id] ? "selected yes" : ""} type="button" onClick={() => setAnswer(item.id, true)}>Sì</button>
                      <button className={owned[item.id] === false ? "selected no" : ""} type="button" onClick={() => setAnswer(item.id, false)}>No</button>
                    </div>
                    {!owned[item.id] ? (
                      <div className="product-offer">
                        <div><span>Consigliato da MRA</span><strong>{money.format(item.price)}</strong></div>
                        <button className={cart[item.id] ? "added" : ""} type="button" onClick={() => setCart((current) => ({ ...current, [item.id]: !current[item.id] }))}>
                          {cart[item.id] ? "✓ Aggiunto" : "+ Aggiungi al carrello"}
                        </button>
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </section>
          ))}

          {!hideSafety ? (
            <section className="safety-notice">
              <header><span>⚠</span><div><h3>Prima di iniziare</h3><p>Disattiva l’interruttore generale, verifica l’assenza di tensione e non lavorare se non sei sicuro. Per lavori sull’impianto elettrico può essere necessario rivolgersi a un professionista abilitato.</p></div></header>
              <label><input type="checkbox" checked={safetyRead} onChange={(event) => setSafetyRead(event.target.checked)} /> Ho letto le indicazioni di sicurezza.</label>
              <label><input type="checkbox" checked={hideSafety} onChange={(event) => setHideSafety(event.target.checked)} /> Non mostrare più questo avviso per questa guida.</label>
            </section>
          ) : (
            <button className="show-safety" type="button" onClick={() => setHideSafety(false)}>Mostra di nuovo le indicazioni di sicurezza</button>
          )}
        </main>

        <aside className="ready-summary">
          <section className="summary-card progress-summary">
            <header><strong>Preparazione</strong><span>{completion}%</span></header>
            <div className="large-progress"><i style={{ width: `${completion}%` }} /></div>
            <ul>
              <li className={completion >= 50 ? "done" : ""}>Materiale principale</li>
              <li className={completion >= 70 ? "done" : ""}>Attrezzi essenziali</li>
              <li className={completion >= 100 ? "done" : ""}>Sicurezza e consumabili</li>
            </ul>
          </section>

          <section className="summary-card cart-summary">
            <header><strong>Il tuo kit</strong><span>{selected.length} articoli</span></header>
            {selected.length ? selected.map((item) => <div className="cart-line" key={item.id}><span>{item.label}</span><strong>{money.format(item.price)}</strong></div>) : <p>Seleziona “No” sugli elementi mancanti e aggiungili al carrello.</p>}
            <div className="discount-ladder">
              <strong>Più acquisti, meno paghi</strong>
              <span className={selected.length >= 2 ? "active" : ""}>2 articoli · -3%</span>
              <span className={selected.length >= 3 ? "active" : ""}>3 articoli · -5%</span>
              <span className={selected.length >= 4 ? "active" : ""}>4 articoli · -8%</span>
              <span className={selected.length >= 5 ? "active" : ""}>Kit completo · -10%</span>
            </div>
            {discountRate > 0 ? <div className="saving"><span>Sconto kit</span><strong>-{Math.round(discountRate * 100)}%</strong></div> : null}
            <div className="cart-total"><span>Totale</span><strong>{money.format(total)}</strong></div>
            <button className="checkout-button" disabled={!selected.length} type="button">Vai al carrello</button>
          </section>

          <section className={`summary-card start-card ${completion === 100 && safetyRead ? "ready" : ""}`}>
            <span>{completion === 100 && safetyRead ? "✓" : "⌛"}</span>
            <h3>{completion === 100 && safetyRead ? "Puoi iniziare il lavoro" : "Non sei ancora pronto"}</h3>
            <p>{completion === 100 ? (safetyRead ? "Hai tutto l’occorrente e hai confermato le indicazioni di sicurezza." : "Conferma di aver letto le indicazioni di sicurezza.") : `Completa ancora il ${100 - completion}% dell’occorrente.`}</p>
            <button disabled={completion < 100 || !safetyRead} type="button">Inizia la guida passo passo</button>
          </section>
        </aside>
      </section>
    </div>
  );
}
