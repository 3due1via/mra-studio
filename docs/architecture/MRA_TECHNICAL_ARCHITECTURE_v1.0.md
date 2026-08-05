# MRA Technical Architecture v1.0

**Prodotto:** MRA Studio  
**Stato:** architettura ufficiale per lo sviluppo  
**Versione:** 1.0

## 1. Obiettivo

MRA Studio è una piattaforma tecnica modulare. La stessa base dati deve alimentare Knowledge, Manuali, Academy, Quiz, Media, Marketplace, Laboratori, Ricerca e AI.

Principi obbligatori:

- unica fonte di verità;
- architettura modulare;
- API versionate;
- dati prima dell’interfaccia;
- revisioni tracciate;
- AI supervisionata;
- audit delle operazioni sensibili;
- build sempre eseguibile.

## 2. Repository

```text
mra-studio/
├── apps/
│   ├── mra-studio/
│   ├── mra-api/
│   └── mra-worker/
├── packages/
│   ├── ui/
│   ├── shared/
│   ├── database/
│   ├── knowledge/
│   ├── auth/
│   ├── media/
│   ├── ai/
│   └── config/
├── infrastructure/
├── docs/
├── scripts/
├── tests/
├── docker-compose.yml
├── package.json
└── pnpm-workspace.yaml
```

## 3. Stack ufficiale

Frontend:

- React;
- TypeScript;
- Vite;
- React Router;
- TanStack Query;
- Zustand;
- React Hook Form;
- Zod.

Backend:

- FastAPI;
- SQLAlchemy 2;
- Alembic;
- Pydantic;
- PostgreSQL;
- Redis.

Infrastruttura:

- Docker Compose;
- Git;
- GitHub Actions;
- MinIO o storage S3 compatibile;
- OpenSearch in una fase successiva.

## 4. Applicazioni

### `apps/mra-studio`

Responsabile di:

- interfaccia;
- routing;
- editor;
- dashboard;
- ricerca;
- notifiche;
- workflow editoriale.

### `apps/mra-api`

Responsabile di:

- API;
- autenticazione;
- permessi;
- validazioni;
- logica applicativa;
- database;
- audit.

### `apps/mra-worker`

Responsabile di:

- PDF;
- importazioni;
- elaborazione media;
- attività asincrone;
- indicizzazione;
- processi AI.

## 5. Domini

I domini ufficiali sono:

- Knowledge;
- Media;
- Manuals;
- Academy;
- Quiz;
- Marketplace;
- Partners;
- Laboratory;
- AI;
- Search;
- Analytics;
- Users and Permissions.

Ogni dominio deve poter evolvere senza duplicare dati o componenti.

## 6. Identificativi

Ogni entità deve avere:

- UUID interno;
- codice pubblico;
- versione;
- stato;
- autore;
- revisore;
- data creazione;
- ultima modifica.

Prefissi:

```text
KC  Knowledge Card
KR  Knowledge Revision
KM  Knowledge Media
CP  Component
SY  Symptom
CS  Cause
DG  Diagnosis
PR  Procedure
TL  Tool
PT  Part
SF  Safety Rule
MN  Manual
LS  Lesson
QZ  Quiz
PD  Product
PN  Partner
LB  Laboratory
```

Esempio:

```text
KC-000000001
CP-000000245
PR-000001032
```

## 7. Knowledge Card

La Knowledge Card è l’aggregato editoriale principale.

Struttura logica:

```text
Knowledge Card
├── Identity
├── Classification
├── Content
├── Safety
├── Symptoms
├── Causes
├── Diagnosis
├── Procedure
├── Tools
├── Parts
├── Laboratory
├── Media
├── Sources
├── Relations
├── Learning
├── Business
├── AI Metadata
└── Governance
```

Campi minimi:

- codice;
- titolo;
- categoria;
- stato;
- versione;
- riassunto;
- descrizione tecnica;
- sicurezza;
- fonti;
- autore;
- revisore;
- quality score.

## 8. Workflow editoriale

Stati ufficiali:

```text
draft
review
verified
approved
published
archived
rejected
```

Flusso:

```text
Draft
→ Review
→ Verified
→ Approved
→ Published
```

Una revisione pubblicata non deve essere sovrascritta. Ogni modifica successiva genera una nuova revisione.

## 9. Versionamento

Regole:

- correzione minore: patch;
- aggiunta compatibile: minor;
- modifica strutturale: major.

Esempio:

```text
1.0.0
1.0.1
1.1.0
2.0.0
```

## 10. Quality Score

Punteggio da 0 a 100.

| Area | Peso |
|---|---:|
| Identità e classificazione | 10 |
| Descrizione tecnica | 15 |
| Sicurezza | 15 |
| Diagnosi | 15 |
| Procedura | 20 |
| Strumenti e ricambi | 10 |
| Fonti | 10 |
| Media | 5 |

Soglie:

```text
0–49    incompleta
50–69   solo uso interno
70–84   pronta per revisione
85–94   pubblicabile
95–100  eccellente
```

Quality Gate minimo per pubblicazione: **85**.

## 11. Knowledge Graph

Tipi di nodo:

- Knowledge Card;
- componente;
- sintomo;
- causa;
- diagnosi;
- procedura;
- strumento;
- ricambio;
- dispositivo;
- veicolo;
- software;
- normativa;
- rischio;
- partner;
- prodotto.

Relazioni principali:

```text
HAS_SYMPTOM
MAY_BE_CAUSED_BY
DIAGNOSED_WITH
REPAIRED_BY
REQUIRES_TOOL
USES_PART
COMPATIBLE_WITH
RELATED_TO
REPLACES
SUPERSEDES
REFERENCES
HAS_MEDIA
HAS_SAFETY_RULE
GENERATES_MANUAL
GENERATES_QUIZ
SOLD_BY
SUPPORTED_BY
```

Ogni relazione deve conservare fonte, autore, stato, peso e data di validazione.

## 12. Modello dati iniziale

```text
users
roles
permissions
user_roles

knowledge_cards
knowledge_revisions
knowledge_sections
knowledge_relations
knowledge_tags
knowledge_sources
knowledge_reviews
knowledge_quality_checks

media_assets
media_links
media_annotations

components
symptoms
causes
diagnoses
procedures
tools
parts
safety_rules

manuals
manual_versions
manual_sections

courses
lessons
quizzes
quiz_questions

partners
suppliers
products
product_links

audit_events
notifications
background_jobs
```

## 13. API

Prefisso:

```text
/api/v1/
```

Risorse:

```text
/api/v1/knowledge-cards
/api/v1/knowledge-revisions
/api/v1/knowledge-relations
/api/v1/media
/api/v1/manuals
/api/v1/courses
/api/v1/quizzes
/api/v1/products
/api/v1/partners
/api/v1/laboratories
/api/v1/search
/api/v1/ai
```

Ogni API deve:

- validare input;
- applicare autorizzazioni;
- gestire errori coerenti;
- supportare filtri e paginazione;
- produrre audit;
- essere documentata in OpenAPI.

## 14. Frontend

Struttura:

```text
src/
├── app/
├── components/
├── features/
├── pages/
├── services/
├── store/
├── hooks/
├── types/
├── utils/
└── styles/
```

Regole:

- le pagine orchestrano;
- i componenti UI non contengono logica di dominio;
- TanStack Query gestisce i dati server;
- Zustand gestisce lo stato globale locale;
- React Hook Form gestisce i form;
- Zod valida form e payload;
- nessun `fetch()` diretto nelle pagine.

## 15. Backend

Struttura:

```text
app/
├── api/
├── core/
├── db/
├── models/
├── schemas/
├── repositories/
├── services/
├── workers/
├── security/
├── audit/
└── tests/
```

Regole:

- router sottili;
- logica nei service;
- accesso dati nei repository;
- schemi separati dai modelli;
- migrazioni Alembic obbligatorie;
- errori tipizzati;
- transazioni esplicite.

## 16. Sicurezza

Ruoli iniziali:

```text
owner
admin
editor
reviewer
technician
partner
teacher
student
viewer
```

Requisiti:

- hashing password;
- autenticazione sicura;
- RBAC;
- permessi granulari;
- audit;
- rate limiting;
- validazione file;
- controllo MIME;
- protezione dei segreti;
- backup.

## 17. Audit

Ogni azione sensibile deve registrare:

- utente;
- azione;
- entità;
- ID;
- stato precedente;
- stato successivo;
- timestamp;
- motivazione.

Azioni obbligatorie:

- creazione;
- modifica;
- eliminazione;
- approvazione;
- pubblicazione;
- archiviazione;
- login;
- cambio permessi;
- esportazione;
- generazione AI.

## 18. Media

I file non devono essere salvati direttamente nel database.

Nel database si salvano:

- UUID;
- codice;
- MIME;
- dimensione;
- hash;
- licenza;
- copyright;
- autore;
- descrizione;
- alt text;
- stato;
- versione;
- posizione storage.

## 19. AI

Flusso ufficiale:

```text
Utente
→ richiesta
→ contesto autorizzato
→ modello
→ proposta
→ revisione umana
→ approvazione
→ salvataggio
```

Ogni output AI deve conservare modello, versione, prompt, parametri, fonti, utente e stato di approvazione.

L’AI non può pubblicare autonomamente contenuti tecnici.

## 20. Ricerca

Fase 1:

- codice;
- titolo;
- categoria;
- stato;
- autore;
- tag;
- testo.

Fase 2:

- sintomo;
- causa;
- componente;
- strumento;
- ricambio;
- compatibilità;
- relazioni.

Fase 3:

- ricerca semantica;
- ricerca ibrida;
- diagnostica guidata;
- percorsi nel Knowledge Graph.

## 21. Test

Ogni build deve verificare:

```text
frontend typecheck
frontend build
backend import
backend test
API health
database connection
Docker Compose startup
```

## 22. Git

Branch:

```text
main
develop
feature/*
fix/*
release/*
hotfix/*
```

Commit:

```text
feat:
fix:
refactor:
test:
docs:
build:
chore:
```

## 23. Definition of Done

Una funzione è completata soltanto se:

- compila;
- i test passano;
- l’API è documentata;
- il database è migrato;
- l’interfaccia è utilizzabile;
- gli errori sono gestiti;
- i permessi sono applicati;
- Docker parte;
- il changelog è aggiornato.

## 24. Decisioni congelate

Sono considerate congelate:

- monorepo;
- React + TypeScript;
- FastAPI;
- PostgreSQL;
- Docker Compose;
- API versionate;
- Knowledge Card come aggregato;
- revisioni immutabili;
- workflow editoriale;
- quality gate;
- AI supervisionata;
- media fuori dal database;
- audit;
- Knowledge Graph.

Ogni variazione richiede un Architecture Decision Record.

## 25. Prossima attività

Ordine operativo:

1. correggere definitivamente la build pnpm/Docker;
2. introdurre migrazioni Alembic;
3. stabilizzare il CRUD Knowledge Card;
4. aggiungere validazioni;
5. aggiungere revisioni;
6. aggiungere quality score;
7. testare persistenza;
8. creare il tag `v0.3.0`.
