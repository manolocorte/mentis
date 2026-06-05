# Mentis

Single-user, multi-agent assistant for **researching and drafting scientific whitepapers** in
chemical/thermal engineering (absorption refrigeration, CO₂ / biobased solvents).

## Architecture (lean)

- **`backend/`** — [Strands Agents](https://strandsagents.com) (Bedrock) multi-agent supervisor behind a FastAPI **SSE** stream.
  - Nova **supervisor** orchestrates tools; a Claude Sonnet **drafter** sub-agent writes journal-grade prose.
  - Tools: `search_literature` (OpenAlex, free), `scopus_search` (your key), `fetch_pdf_text`, `verify_doi`.
  - Research is done **live per session** — no persistent vector store.
- **`frontend/`** — React + Vite + Tailwind, **Claude Code-style streaming transcript** (live tokens + collapsible tool-call cards).
- **Region:** `eu-south-2` (Spain). **Models:** Amazon Nova + Claude via EU inference profiles.
- **Storage:** conversations in a local JSON store (swap to DynamoDB on-demand at deploy).
- **Cost:** < €50/mo single user (~€2–12 in practice; almost all of it Bedrock tokens).
- **AgentCore-ready:** lifts into AgentCore Runtime later with a ~10-line wrapper change.

## Run locally

```powershell
# Backend (needs AWS creds with Bedrock access in eu-south-2)
cd backend
py -3.12 -m venv ..\.venv                       # once
..\.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env                           # set region / creds
..\.venv\Scripts\uvicorn app.server:app --port 8080

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                                       # http://localhost:3000
```

## Research notes

`docs/research/` — scientific-paper conventions (Spain), model cost/options, and the AgentCore
architecture analysis that informed this design.
