# Mentis

Serverless, multi-agent RAG research assistant for absorption-refrigeration /
CO₂-refrigerant literature. Rebuilt (v0.2) on a pay-per-use AWS stack — **~$0 at idle**.

> The previous Docker/Azure + SQLAlchemy/pgvector implementation is preserved under
> [`.legacy/`](.legacy/). See [`docs/aws-migration-2026.md`](docs/aws-migration-2026.md)
> for the rationale and service choices.

## Architecture

| Concern | Service |
|---|---|
| API + agents | **Lambda** (ARM64) behind **API Gateway HTTP API** |
| LLM | **Bedrock Claude** — Haiku (route) → Sonnet (synthesize/verify) → Opus (draft) + prompt caching |
| Embeddings | **Bedrock Titan v2** (1024-d) |
| Semantic search | **Amazon S3 Vectors** (index `chunks` + `memory`) |
| State (projects, conversations, papers, documents, memory) | **DynamoDB** single table |
| PDFs / artifacts | **S3** |
| Async ingestion | **SQS** → worker Lambda |
| Scraper schedule | **EventBridge Scheduler** → harvester Lambda |
| Frontend | static **React/Vite** on **S3 + CloudFront** |
| Secrets | **SSM Parameter Store** |

### Multi-agent RAG

`router → retrieve → investigate → synthesize → (fact-check → revise)*`

A **supervisor** (`mentis/application/agents/supervisor.py`) classifies intent, then
runs specialist agents — **retriever** (hybrid S3 Vectors + lexical RRF), **investigator**
(LLM themes/findings/gaps), **synthesizer** (cited answer, can call the retrieve tool),
and an adversarial **fact-checker** that drives a bounded **reflexion loop**. A **coder**
agent handles thermodynamic calculations via a sandboxed `run_python` tool.

### Scraper

Pluggable `PaperSourcePort` sources: **OpenAlex**, **Crossref**, **arXiv**, with
**Unpaywall** resolving legal open-access PDFs. A gated **university (Scopus)** source
activates automatically once `UNIVERSITY_API_KEY` is set — no code change.

## Layout

```
mentis/
  domain/            # models + ports (hexagonal core, no infra)
  adapters/
    inbound/         # api.py (FastAPI/Mangum), worker.py (SQS), harvester.py (schedule)
    outbound/        # bedrock_llm, bedrock_embedding, s3_vectors, dynamo_store,
                     #   s3_object_store, sqs_queue, local_code_exec, sources/
  application/       # rag, chunking, ingestion, harvest, tools, agents/, container
infra/               # Terraform (DynamoDB, S3, S3 Vectors, Lambdas, API GW, SQS,
                     #   EventBridge, CloudFront)
frontend/            # static React + TypeScript (Vite)
tests/               # unit tests with in-memory fakes
.legacy/             # the previous implementation (preserved)
```

## Local development

```bash
python -m pip install -r requirements-dev.txt
cp .env.example .env            # fill in for live AWS, or leave defaults for tests
pytest                          # runs against in-memory fakes (no AWS needed)
uvicorn mentis.adapters.inbound.api:app --reload   # needs AWS creds for Bedrock/Dynamo/S3 Vectors
```

## Deploy

CI/CD is GitHub Actions; **`main` is the single deployable branch → prod** (no non-prod
environments). Every push to `main` builds the ARM64 image, runs `terraform apply`,
and ships the frontend to S3 + CloudFront. Auth is GitHub OIDC (no static AWS keys).

See **[`docs/cicd.md`](docs/cicd.md)** for the one-time bootstrap (state bucket, OIDC
role, repo secrets/variables) and first-deploy steps.

Manual deploy (equivalent), if needed:

1. `cd infra && terraform init -backend-config=... && terraform apply -var='environment=prod' -var='lambda_image_uri=...'`
2. Build & push the image to the created ECR repo, re-apply.
3. Set SSM secrets (`api_key`, `unpaywall_email`).
4. `cd frontend && npm ci && npm run build`, sync `dist/` to the site bucket, invalidate CloudFront.
5. Enable the harvester: set the `HARVEST_ENABLED` repo variable to `true` (or `-var='harvest_enabled=true'`).
