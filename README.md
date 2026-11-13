# Krishna Guidance

A production-ready spiritual guidance platform inspired by Bhagavad Gita teachings, built with a Next.js frontend and FastAPI backend.

## Tech stack

- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS, shadcn-style components
- Backend: FastAPI, Python 3.12+
- Database: PostgreSQL
- Vector DB: Qdrant
- Cache: Redis
- Auth: Google SSO + email OTP + JWT
- AI: OpenAI, Anthropic Claude, Gemini, and provider abstraction

## Current implementation status

This workspace now contains:

- Landing page and interactive chat UI shell
- FastAPI backend with modular routes for health, auth, RAG, journaling, and admin
- Google ID-token verification and database-backed email OTP sign-in
- Revocable JWT sessions and protected profile/chat/admin endpoints
- SQLAlchemy model definitions for users, conversations, journal entries, favorites, and source records
- Chapter-level keyword retrieval over an attributed English Gita source
- Verse-level Sanskrit source corpus with revision-specific citations
- OpenAI-backed multilingual chat and semantic retrieval pipeline
- Docker Compose for local app stack

### Scripture corpus prototype

The API retrieves Project Gutenberg eBook #2388, Sir Edwin Arnold's poetic English translation, with lexical keyword search over chapter-level passages. Because that source has no verse alignment, it is never cited with a verse number. A separately sourced Sanskrit mūlapāṭha corpus contains all 700 chapter-and-verse records from Sanskrit Wikisource; the Daily Wisdom endpoint uses it to show an original Sanskrit śloka with a revision-specific source link. The Sanskrit text is contributor-transcribed and is not an independently reviewed critical edition. Its attribution and share-alike terms are documented alongside the corpus.

Authenticated Ask Krishna chat and `/api/v1/rag/search` support English, Hindi, and Sanskrit queries. OpenAI multilingual embeddings retrieve Sanskrit verse candidates from Qdrant; chat can cite only verse IDs returned by retrieval, and the API resolves citations back to the exact source corpus. Explanations are AI-generated, not authoritative translations. A reviewed Hindi translation has not been added.

The local developer setup uses Qdrant's embedded persistent mode and does not require Docker. Production deployments should configure a Qdrant server with `QDRANT_URL` and `QDRANT_API_KEY`. Chat and semantic search require an `OPENAI_API_KEY`; user messages/queries and retrieved Sanskrit excerpts are sent to OpenAI for embeddings/generation. Do not start these features until that data flow is acceptable and the key is configured.

Corpus provenance, attribution, and ingestion instructions are documented in `apps/api/data/corpora/edwin_arnold/README.md` and `apps/api/data/corpora/wikisource_sanskrit/README.md`.

## Monorepo structure

- `apps/web` — web app and PWA shell
- `apps/api` — API service and AI orchestration layer
- `infrastructure/docker` — Docker Compose and container builds
- `docs` — architecture and governance guides

## Local development

### Frontend

```bash
npm install
npm run dev
```

### Backend

With PostgreSQL installed and the `krishna_guidance` database/user created, configure `apps/api/.env` from `.env.example`. Put your local database password in `DATABASE_URL`; do not commit `.env`. Set up an SMTP relay to enable email OTP, and a Google OAuth web client ID to enable Google sign-in.

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

For a development login flow, configure:

- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL`
- `GOOGLE_CLIENT_ID` from your Google OAuth web client

OTP codes are never returned by the API or logged. Sign-in requires working SMTP configuration; Google sign-in requires a valid Google ID token for the configured client ID.

### Run migrations

```bash
cd apps/api
alembic revision -m "describe change"
alembic upgrade head
```

The application does not create tables at startup. Run Alembic migrations before starting the API.

Run backend tests with:

```powershell
pip install -r requirements-dev.txt
pytest
```

### Environment files

Copy the examples before running locally:

```powershell
Copy-Item apps/api/.env.example apps/api/.env
Copy-Item apps/web/.env.local.example apps/web/.env.local
```

Edit `apps/api/.env` and set your PostgreSQL password, a random `JWT_SECRET`, SMTP settings, and (if used) `GOOGLE_CLIENT_ID` and `OPENAI_API_KEY`. The example values are placeholders; never commit `.env`.

After setting `OPENAI_API_KEY`, stop the API if it is running and build the local Sanskrit verse index:

```powershell
cd apps/api
python -m app.scripts.ingest_sanskrit_embeddings
```

The script embeds the source-versioned 700-verse corpus and stores vectors under `apps/api/data/qdrant/`, which is ignored by Git. Add `--replace` only when intentionally rebuilding an existing index.

## Architecture

See `ARCHITECTURE.md` for the full production design.
