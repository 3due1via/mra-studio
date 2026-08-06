# MRA Studio — v0.6.0

MRA Studio è un MVP full-stack per organizzare conoscenza tecnica e progetti. Questa versione consolida una base riproducibile con React, FastAPI, PostgreSQL, Alembic e Docker Compose.

## Requisiti

- Docker Desktop con Docker Compose v2;
- in alternativa, per lo sviluppo frontend locale: Node.js 22 e pnpm 10.15;
- in alternativa, per il backend locale: Python 3.13 e PostgreSQL 17.

## Setup

1. Copia `.env.example` in `.env`.
2. Modifica le credenziali solo se necessario. I valori inclusi sono esclusivamente per sviluppo locale.
3. Costruisci e avvia i servizi:

```bash
docker compose up --build
```

Compose avvia PostgreSQL, applica `alembic upgrade head`, avvia l'API e infine il frontend.

## Avvio e arresto

```bash
docker compose up --build
docker compose down
```

Per eliminare anche i dati PostgreSQL locali:

```bash
docker compose down --volumes
```

Questo secondo comando è distruttivo e non deve essere usato se i dati devono essere conservati.

## URL locali

- Studio: http://localhost:5173
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Versione: http://localhost:8000/version

## Migrazioni database

L'API non crea più lo schema con `Base.metadata.create_all()`. Lo schema è gestito da Alembic. La migrazione iniziale è deterministica ed è destinata a un database nuovo: se trova tabelle MRA preesistenti senza baseline, fallisce invece di considerarle implicitamente compatibili.

Dentro il container API:

```bash
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic current
```

### Database MRA preesistente

Non eseguire direttamente `alembic upgrade head` su un database MRA preesistente non ancora gestito da Alembic. Effettua prima un backup verificato, quindi esegui il controllo read-only:

```bash
docker compose run --rm api python -m scripts.baseline_existing_db
```

Il controllo confronta rigorosamente tabelle, colonne, tipi, nullability, primary key, foreign key, unique constraint e indici. Non crea, modifica o elimina strutture o dati. Se viene rilevato schema drift, la baseline viene rifiutata e occorre preparare una migrazione di riconciliazione.

Solo dopo una verifica riuscita, registra esplicitamente la baseline:

```bash
docker compose run --rm api python -m scripts.baseline_existing_db --stamp
```

Con `--stamp` viene scritto esclusivamente il marker Alembic `20260806_0001`; le tabelle applicative e i dati non vengono modificati.

### Downgrade baseline

La migrazione iniziale è intenzionalmente irreversibile. `alembic downgrade base` fallisce senza eliminare tabelle o dati. Per ricostruire un ambiente di sviluppo usa un database vuoto; per database importanti usa esclusivamente procedure di ripristino da backup verificate.

Per creare una nuova migrazione durante lo sviluppo:

```bash
docker compose run --rm api alembic revision --autogenerate -m "descrizione"
docker compose run --rm api alembic upgrade head
```

## Test

Test backend unitari e di sistema:

```bash
docker compose run --rm api pytest -q
```

I test di integrazione PostgreSQL richiedono `TEST_DATABASE_URL`, usano lo schema creato da Alembic e cancellano i dati applicativi tra i test tramite `TRUNCATE`. Non puntare mai questa variabile a un database contenente dati da conservare; per sicurezza il nome deve contenere `test`.

Frontend:

```bash
pnpm install --frozen-lockfile
pnpm typecheck:studio
pnpm build:studio
```

La pipeline GitHub Actions esegue migrazioni, test backend con un PostgreSQL dedicato, typecheck e build frontend.

## Struttura monorepo

```text
apps/
  mra-studio/   React, TypeScript e Vite
  mra-api/      FastAPI, SQLAlchemy e Alembic
  mra-worker/   worker pianificato
packages/       package condivisi pianificati
infrastructure/ predisposizione infrastrutturale
docs/           architettura e documentazione
```

Il workspace pnpm include `apps/*` e `packages/*`. I package condivisi sono ancora segnaposto.

## Stato dei moduli

### Implementato

- shell e navigazione frontend;
- CRUD Knowledge Card;
- relazioni e revisioni Knowledge Card;
- ripristino revisioni;
- quality score nel frontend;
- CRUD progetti;
- creazione ambienti e oggetti;
- PostgreSQL, migrazioni Alembic e API OpenAPI.

### Parziale

- dashboard: usa dati reali per alcune sezioni e dati dimostrativi per altre;
- workflow editoriale: stati disponibili, ma senza autorizzazioni e audit;
- ricerca: codice, titolo, categoria e stato;
- design system: presente nell'app frontend, non ancora estratto in un package.

### Pianificato

- autenticazione, utenti, ruoli e permessi;
- audit e notifiche;
- worker asincrono, Redis e storage S3/MinIO;
- media, manuali, Academy, quiz, marketplace e partner;
- ricerca avanzata/semantica e funzioni AI;
- backup ed esportazione.
