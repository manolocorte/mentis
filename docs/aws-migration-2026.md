# Mentis → AWS Migration Draft (2026 SOTA, cost‑minimized)

> Goal: move Mentis to a **pay‑per‑use, ~$0‑at‑idle** AWS architecture, add a real
> **scraper/ingestion pipeline**, and turn the fake "multi‑agent" router into a genuine
> **multi‑agent RAG**. Scale assumption: 1 researcher, low hundreds of queries/month,
> ~1k‑paper corpus (absorption‑refrigeration / CO₂ biobased solvents).

---

## 1. Current state — honest assessment

The codebase is mid‑refactor (Azure→AWS) and three things the request asks for are **not actually there**:

| Claim | Reality in the code |
|---|---|
| "Multi‑agentic RAG" | `orchestrator.py:79‑90` is a **single‑dispatch router** — classify intent → call **one** agent. Agents never see each other's output; no supervisor, no tool‑use loop, no critic/verify pass. |
| Agents "reason" | `investigator.py` extracts themes/gaps by **token‑frequency counting** (`_derive_themes`/`_derive_gaps`), not LLM reasoning. The LLM is only used in `gap_analyzer` and `synthesizer`. |
| Scraper exists | None. Only REST clients (`scopus_client.py`, `arxiv_client.py`, `crossref_client.py`, `semantic_scholar_client.py`). Scopus full‑text needs an **institutional token** (`SCOPUS_INST_TOKEN`) not present in Lambda env. |
| Serverless ingestion works | `pdf_ingest.ingest_pdfs()` scans a **local dir** baked into the image; the S3 ingestion handler is a `TODO` stub (`sqs_handler.py:93`). `investigator.run()` runs `ingest_pdfs()` **on every query** — a local FS scan inside Lambda. |

Other defects to fix during migration:

- **Embedding dim mismatch (latent bug):** Titan v2 configured at **1024** (`config.py:60`) but all vector columns are hardcoded **`Vector(dim=1536)`** (`document.py:38`, both Alembic migrations, `memory.py:32`). Switching to Bedrock embeddings breaks inserts.
- **Half‑migrated config:** Azure OpenAI + Bedrock + Celery‑on‑Postgres broker all coexist in `config.py`. Dead weight and confusion.
- **No ANN index:** `hybrid.py` does pgvector cosine over a sequential scan (ivfflat deferred "until 100 rows, manual"). Fine at 1k chunks, won't scale.
- **`chat_stream` doesn't stream:** it buffers all Bedrock events then yields (`bedrock_llm.py:93‑105`); API Gateway + Mangum can't stream anyway.
- **CORS `allow_origins=["*"]`** on the HTTP API (`compute/main.tf:161`) with an API‑key auth model — tighten to the CloudFront origin.

The **good** parts to keep: hexagonal ports (`domain/ports/*`), the `VectorStorePort`/`EmbeddingPort`/`LLMPort` abstractions (make swapping infra cheap), Terraform module layout, and React+TS frontend on S3+CloudFront (already in `modules/frontend`).

---

## 2. Target architecture (2026)

```
                ┌──────────────────────────────────────────────────────────┐
  Browser ──►   │ CloudFront ──► S3 (React/TS static site)                   │
                └──────────────────────────────────────────────────────────┘
       │ HTTPS (auth: Cognito JWT or API key)
       ▼
  API Gateway (HTTP API)  ──►  API Lambda (FastAPI/Mangum, ARM64)
                                   │
                                   ▼
                         ┌───────────────────────┐
                         │  Multi‑agent RAG core  │   (§4)
                         │  Supervisor + workers  │
                         └───────────────────────┘
                          │        │          │
              ┌───────────┘        │          └─────────────┐
              ▼                    ▼                         ▼
   Bedrock (Claude + Titan)   Retrieval tool          Code‑interp tool
   - Haiku: routing/classify   - S3 Vectors KB         - Bedrock AgentCore
   - Sonnet: synth/factcheck    (semantic)               Code Interpreter
   - Opus: final drafts only    - DynamoDB/PG (keyword)   (sandbox, $0 idle)
   - prompt caching ON

  ASYNC INGESTION / SCRAPER (§3)
  EventBridge Scheduler ─► Harvester Lambda ─► (OpenAlex/Crossref/Unpaywall/arXiv/Scopus)
                                   │ writes PDF/OA URLs
                                   ▼
                            S3 (documents)  ──S3 event──►  SQS  ──►  Ingestion Lambda
                                                                       │ extract→chunk→embed
                                                                       ▼
                                                          Bedrock KB / S3 Vectors + metadata DB

  Relational/state:  Neon serverless Postgres (scale‑to‑zero)  OR  DynamoDB (all‑AWS, $0 idle)
  Secrets: SSM Parameter Store   Observability: CloudWatch + Bedrock model invocation logs
```

### Service mapping & why (cost‑first)

| Concern | Choice | Why (2026) | Idle cost |
|---|---|---|---|
| API compute | **Lambda (ARM64) + HTTP API GW** | Already wired (Mangum). Cheapest at this scale. | **$0** |
| Agent runtime | **Lambda‑native supervisor (Bedrock Converse tool‑use)**; graduate to **Bedrock AgentCore Runtime** if sessions/concurrency grow | AgentCore GA'd ~Apr 2026 with A2A multi‑agent + managed Memory/Gateway, but bills per vCPU/GB‑hour + 12 components — overkill for 1 user. Lambda loop = $0 idle. | **$0** (Lambda) |
| Vector store | **Amazon S3 Vectors** (GA Jan 2026) via **Bedrock Knowledge Bases** | ~90% cheaper than OpenSearch Serverless, sub‑second, fully serverless. Avoids OpenSearch's **~$350/mo** 2‑OCU floor. | **$0** |
| Relational/state (conversations, projects, memory, paper metadata) | **Neon** (scale‑to‑zero) — keeps existing SQLAlchemy/Alembic; or **DynamoDB** single‑table for all‑AWS | Neon free/scale‑to‑zero fits this scale and preserves code. Aurora Serverless v2 floors at **~$43/mo** (0.5 ACU); **Aurora DSQL scales to zero but lacks full pgvector** — so don't use DSQL for vectors. | **~$0** |
| LLM | **Bedrock Claude** — Haiku 4.5 (route/classify), Sonnet 4.x (synth/factcheck), Opus 4.x (final draft only) + **prompt caching** | Tiered models + caching cut 60‑80% of token cost. | **$0** |
| Embeddings | **Titan Embed v2 (1024)** or Cohere v3, or KB‑managed | Cheap ($0.02/M); KB can manage embedding for you. | **$0** |
| Async jobs | **SQS + Lambda** (replace Celery) | Already started in `sqs_handler.py`. | **$0** |
| Scheduling | **EventBridge Scheduler** | Cron for nightly harvests. | **$0** |
| Code execution (thermo cycle calcs) | **AgentCore Code Interpreter** (managed sandbox) or a locked‑down Lambda | Replaces `azure_code_exec`. Pay‑per‑use sandbox. | **$0** |
| Frontend | **S3 + CloudFront** | Already in `modules/frontend`. | ~$0 |
| Secrets | **SSM Parameter Store** (SecureString) | Already used (`config._resolve_ssm_secrets`). Free tier. | $0 |

**Decision:** lead with **Lambda‑native multi‑agent + S3 Vectors KB + Neon**. It is the cheapest stack that satisfies "$0 at idle" while still being 2026‑current. AgentCore is documented as the **scale‑up path**, not the day‑1 choice.

---

## 3. Scraper & ingestion pipeline (new)

A two‑stage, legal, polite harvester — **prefer open metadata/OA full‑text over scraping paywalls**:

**Stage A — Harvester Lambda** (triggered by EventBridge Scheduler, e.g. nightly, + on‑demand):
1. Query **OpenAlex** (free, no token), **Crossref**, **arXiv**, and **Scopus** (when token available) for the domain seed queries + the citation graph of the ~7 seed papers (`project_research_domain`).
2. For each work, resolve a **legal full‑text PDF URL via Unpaywall** (OA only) — never scrape paywalled Scopus PDFs.
3. Deduplicate by DOI against the metadata DB; enqueue new items.

**Stage B — Fetcher + Ingestion:**
4. Fetcher Lambda downloads OA PDFs (respect `robots.txt`, rate‑limit, backoff) → **S3 `documents/`** bucket. For JS‑heavy pages, use a **Playwright/Chromium Lambda container** (or Firecrawl) — kept off the hot path.
5. **S3 `ObjectCreated` event → SQS → Ingestion Lambda**: extract text (pdfminer/`pypdf`, or **Textract** for scanned PDFs), chunk, then either push to **Bedrock Knowledge Base** (managed embed+index into S3 Vectors) **or** embed with Titan and `upsert` via `VectorStorePort`.
6. Write paper metadata (title, DOI, authors, year, citations) to the relational/state DB.

**Fixes folded in:** delete the per‑query `ingest_pdfs()` call from `investigator.run()`; make ingestion fully event‑driven (implement the `sqs_handler._handle_ingest_pdf` stub); add `robots`/rate‑limit/`User‑Agent` + `Retry‑After` handling to all outbound clients.

---

## 4. Multi‑agent RAG (the real thing)

Replace the single‑dispatch router with a **supervisor + specialist workers** running a **Bedrock Converse tool‑use loop** (or AgentCore A2A at scale). Each worker is an LLM with a focused system prompt and tools; the supervisor plans, delegates, and runs a **reflexion/critic loop** before answering.

```
            ┌─────────────── Supervisor / Planner (Haiku) ───────────────┐
            │ decompose query → plan → delegate → assemble → verify       │
            └─────────────────────────────────────────────────────────────┘
               │            │              │              │            │
               ▼            ▼              ▼              ▼            ▼
        Retriever     Investigator     Synthesizer    Fact‑checker  Code‑interp
        (hybrid KB    (LLM themes/    (drafts w/      (verifies     (thermo
         + keyword,   gaps + cites,   citations,      each claim    cycle calcs,
         RRF fusion)  not token‑freq) Sonnet)         vs chunks,    AgentCore
                                                      adversarial)  sandbox)
                                  ▲                        │
                                  └──── reflexion loop ─────┘  (revise until claims grounded)
```

- **Supervisor (Haiku):** cheap router/planner; decides which workers to call and in what order; loops until the critic passes or a max‑iteration cap.
- **Retriever tool:** keep the **RRF hybrid** idea from `hybrid.py` but back semantic search with **S3 Vectors/KB** and keyword with the metadata DB's full‑text. Expose as a Converse tool.
- **Investigator (Sonnet):** real LLM theme/gap analysis over retrieved chunks (delete token‑frequency `_derive_*`).
- **Synthesizer (Sonnet):** drafts answer **with inline citations** to chunk/DOI.
- **Fact‑checker / Critic (Sonnet):** for each claim, re‑retrieves and verifies grounding; sends failures back to the synthesizer (reflexion). This is the single biggest quality win for a research assistant.
- **Code interpreter:** runs refrigeration‑cycle / thermodynamic calculations in a sandbox; feeds numbers back to the synthesizer.

**Cost controls baked in:** Haiku for routing & verification triage, Sonnet for generation, Opus **only** for final paper drafts; **Bedrock prompt caching** on the large system prompts + retrieved context; cap reflexion iterations (e.g. 2). Keep the hexagonal ports — agents call `LLMPort`/`VectorStorePort`/`EmbeddingPort`, so the same code runs locally or on Lambda/AgentCore.

---

## 5. Phased migration plan

Each phase is independently deployable and leaves the app working.

- **Phase 0 — Hygiene (no infra):** fix the 1024/1536 dim mismatch (parameterize columns to `bedrock_embed_dim`), delete Azure + Celery config paths, remove `ingest_pdfs()` from the query hot path, tighten CORS. *Unblocks Bedrock embeddings.*
- **Phase 1 — State DB:** stand up **Neon** (or DynamoDB), move `DATABASE_URL` to SSM, run Alembic. Confirm conversations/memory/papers persist.
- **Phase 2 — Vector store:** create **Bedrock Knowledge Base over S3 Vectors**; implement an `S3VectorsStore`/KB adapter behind `VectorStorePort`; backfill the ~1k existing PDFs.
- **Phase 3 — Ingestion pipeline:** implement event‑driven S3→SQS→Lambda ingestion (kill the local‑dir scan); migrate `_handle_ingest_pdf`.
- **Phase 4 — Scraper:** Harvester + Fetcher Lambdas, EventBridge schedule, OpenAlex/Unpaywall integration.
- **Phase 5 — Multi‑agent RAG:** build supervisor + worker tool‑use loop + critic reflexion; swap `orchestrator.handle()` over to it behind a feature flag.
- **Phase 6 — Frontend & auth:** wire React app to the new API, add Cognito JWT (or keep API key), deploy to S3/CloudFront.
- **Phase 7 — Observability & guardrails:** CloudWatch dashboards, Bedrock invocation logging, **Bedrock Guardrails**, cost alarms/budgets. *Optional later:* lift the agent core to **AgentCore Runtime** if you outgrow Lambda's 15‑min / concurrency limits.

---

## 6. Cost estimate (this scale)

| Component | Driver | Est. monthly |
|---|---|---|
| Lambda (API + workers, ARM64) | hundreds of invocations | **~$0** (free tier) |
| API Gateway HTTP | low traffic | <$1 |
| S3 Vectors + S3 storage | ~1k papers, low queries | ~$1‑3 |
| Neon (scale‑to‑zero) / DynamoDB | low | **$0** free tier |
| SQS + EventBridge | low | ~$0 |
| Bedrock (tiered + caching) | ~200 queries/mo | **~$5‑10** |
| CloudFront + S3 site | low | ~$1 |
| **Total** | | **≈ $7‑15 / month, ~$0 at idle** |

**Things that would blow the budget (avoid):** OpenSearch Serverless (**~$350/mo** floor), Aurora Serverless v2 (**~$43/mo** floor), always‑on AgentCore sessions, Opus for routine queries.

---

## 7. Open decisions for you

1. **State DB:** Neon (keep SQLAlchemy/Alembic, fastest) vs DynamoDB (all‑AWS, more rewrite). Default rec: **Neon**.
2. **Agent runtime now:** Lambda‑native loop (cheapest) vs Bedrock AgentCore (more managed, more $). Default rec: **Lambda‑native**, AgentCore as scale path.
3. **Scope of scraping:** OA‑only via OpenAlex/Unpaywall (legal, simple) vs add headless browser scraping for non‑OA pages (more infra, legal care). Default rec: **OA‑only first**.
4. **Auth:** keep API key vs add Cognito. Default rec: API key now, Cognito if multi‑user.

### Sources (2026 grounding)
- [Amazon S3 Vectors GA (AWS Blog)](https://aws.amazon.com/blogs/aws/amazon-s3-vectors-now-generally-available-with-increased-scale-and-performance/) · [InfoQ](https://www.infoq.com/news/2026/01/aws-s3-vectors-ga/) · [S3 Vectors](https://aws.amazon.com/s3/features/vectors/)
- [OpenSearch Serverless pricing floor](https://cloudburn.io/blog/amazon-opensearch-pricing) · [OpenSearch pricing](https://aws.amazon.com/opensearch-service/pricing/)
- [Bedrock AgentCore pricing](https://aws.amazon.com/bedrock/agentcore/pricing/) · [AgentCore overview](https://aws.amazon.com/bedrock/agentcore/)
- [Aurora Serverless v2 vs DSQL cost analysis](https://www.doit.com/blog/comparing-aurora-distributed-sql-vs-aurora-serverless-v2-a-practical-cost-analysis) · [Neon vs Aurora serverless](https://www.vantage.sh/blog/neon-vs-aws-aurora-serverless-postgres-cost-scale-to-zero)
</content>
</invoke>
