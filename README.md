# Atlas — Enterprise RAG Knowledge Assistant

The application now provides a working FastAPI service and React workspace with document upload, PDF/DOCX/TXT/MD extraction, SQLite persistence, local evidence retrieval, grounded OpenAI answers, citations, document filtering/deletion, and live analytics.

## Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer

## 1. Run the backend

Open PowerShell in this project folder:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Expected: `Uvicorn running on http://127.0.0.1:8000`. Open:

- Health: http://127.0.0.1:8000/api/health
- Interactive API docs: http://127.0.0.1:8000/docs

Run backend tests with the virtual environment active:

```powershell
python -m pytest -q
```

## 2. Run the frontend

Keep the backend running. Open a second PowerShell window:

```powershell
cd frontend
npm install
npm run dev
```

Expected: Vite prints `http://localhost:5173`. Open that address. The green status banner confirms the browser can reach FastAPI.

For a production build:

```powershell
npm run build
```

## Configuration and security

`backend/.env` is ignored by Git. Never place a real key in frontend code. The Vite development server proxies `/api` to FastAPI, and FastAPI only permits the local Vite origins by default.

Configure AI only in `backend/.env`:

```dotenv
OPENAI_API_KEY=your-new-private-key
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Restart the backend after editing this file. Never put a real key in `.env.example` or paste it into chat. If a key is accidentally shared, revoke it immediately and create a replacement.

Optional bounded agent controls:

```dotenv
AGENTIC_AI_ENABLED=true
AGENT_MAX_STEPS=8
AGENT_MAX_RETRIEVAL_RETRIES=2
AGENT_MAX_TOOL_CALLS=10
```

Agentic features add research planning, evidence retry and verification, risk analysis,
executive insights, a knowledge map, safe analytics templates, human review actions,
and execution observability. Existing chat and document APIs remain unchanged.

## Store documents and comparisons in Supabase

When all Supabase variables below are present, the backend uses Supabase Postgres
instead of SQLite and saves original uploads in a private Storage bucket. Comparison
results are saved in the `comparisons` table. The browser still talks only to FastAPI;
the privileged Supabase key is never placed in frontend code.

### 1. Create and prepare the Supabase project

1. Sign in at https://supabase.com/dashboard and create a project. Save the database
   password in a password manager.
2. Open **SQL Editor**, select **New query**, paste the complete contents of
   `supabase/schema.sql`, and click **Run**. This creates the five application tables,
   enables RLS, and creates a private `documents` Storage bucket.
3. Click **Connect** at the top of the project. Copy the **Session pooler** connection
   string (port `5432`) for a normal long-running FastAPI server. Replace
   `[YOUR-PASSWORD]` with the URL-encoded database password.
4. In **Settings > API Keys**, create/copy a backend **Secret key** beginning with
   `sb_secret_`. Do not use a publishable/anon key and never expose this key in React.
5. Copy the project URL shown in the Connect dialog, such as
   `https://your-project-ref.supabase.co`.

### 2. Configure this backend

Add these values to `backend/.env` (not to `frontend/.env`):

```dotenv
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SECRET_KEY=sb_secret_your_backend_key
SUPABASE_DATABASE_URL=postgresql://postgres.your-project-ref:URL_ENCODED_PASSWORD@aws-0-your-region.pooler.supabase.com:5432/postgres?sslmode=require
SUPABASE_STORAGE_BUCKET=documents
```

The exact database hostname and region come from your own Connect dialog; do not copy
the sample hostname literally. If your password contains characters such as `@`, `#`,
`%`, `:` or `/`, URL-encode it before inserting it into the connection string.

### 3. Install and run

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Then run the frontend in a second terminal, upload two documents, and compare them.

### 4. Verify in Supabase

- **Table Editor > documents**: one metadata/text row per uploaded document.
- **Table Editor > chunks**: extracted searchable chunks and stored embedding JSON.
- **Table Editor > comparisons**: every result generated in Compare Documents.
- **Storage > documents**: the private original PDF/DOCX/TXT/MD files.

Deleting a document in the app removes its Storage object and related database rows.
Existing local SQLite documents are not automatically migrated; re-upload them after
enabling Supabase, or keep a backup of `data/` until migration is complete.

## Deploy to Vercel

Deploy this monorepo as two Vercel projects. Both projects use the same Git repository,
but one has `backend` as its Root Directory and the other has `frontend`.

### Backend Vercel project

1. Push this repository to GitHub, GitLab, or Bitbucket.
2. In Vercel choose **Add New > Project**, import the repository, and set
   **Root Directory** to `backend`.
3. Keep Framework Preset as **Other**. Vercel detects `main.py` as the FastAPI entrypoint
   and installs `requirements.txt` automatically.
4. Add these Production and Preview environment variables:
   `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_DATABASE_URL`,
   `SUPABASE_STORAGE_BUCKET`, `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL`, and
   `OPENAI_EMBEDDING_MODEL`.
5. For `SUPABASE_DATABASE_URL`, use Supabase's **Transaction pooler** URL on port `6543`
   because Vercel is serverless. Include `?sslmode=require`.
6. Initially set `CORS_ORIGINS` to `http://localhost:5173`, deploy, and copy the backend
   URL, for example `https://atlas-api.vercel.app`.

### Frontend Vercel project

1. Import the same repository again and set **Root Directory** to `frontend`.
2. Vercel should detect **Vite**. Confirm Build Command is `npm run build` and Output
   Directory is `dist`.
3. Add `VITE_API_URL=https://atlas-api.vercel.app`, using the actual backend URL and no
   trailing slash, then deploy.
4. Copy the frontend URL, return to the backend project's environment variables, and set
   `CORS_ORIGINS` to that URL, for example `https://atlas-app.vercel.app`.
5. Redeploy the backend, then open the frontend and confirm the green backend-connected
   banner appears.

Vercel Functions limit request bodies to 4.5 MB, so uploads through this hosted FastAPI
endpoint must remain below that size even though local development supports 20 MB. A
future direct-to-Supabase signed-upload flow is required for larger production uploads.

## Common problems

- **`python` is not recognized:** install Python and enable “Add Python to PATH.”
- **PowerShell blocks activation:** run `Set-ExecutionPolicy -Scope Process Bypass`, then activate again.
- **Port already in use:** stop the old process, or run Uvicorn with `--port 8001` and update the proxy in `frontend/vite.config.ts`.
- **Dashboard says backend offline:** start Uvicorn on port 8000, then refresh the browser.
- **`npm` is not recognized:** install the current Node.js LTS release and reopen PowerShell.

## Structure

```text
backend/app/       FastAPI application, routes, schemas, and configuration
backend/tests/     API smoke tests
frontend/src/      React components, hooks, services, types, and styling
data/              Reserved local document, vector, and metadata storage
```
