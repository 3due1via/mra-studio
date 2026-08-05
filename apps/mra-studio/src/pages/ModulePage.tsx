import { PageHeader } from "../components/PageHeader";
export function ModulePage({title}:{title:string}) {
  return <>
    <PageHeader eyebrow="MRA MODULE" title={title} description={`Il modulo ${title} è collegato al routing ufficiale.`} />
    <section className="empty-state"><h2>{title} pronto</h2><p>Le funzioni verranno aggiunte nei prossimi build.</p></section>
  </>;
}
