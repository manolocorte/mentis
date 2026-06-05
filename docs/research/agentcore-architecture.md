# Building a Multi-Agent Whitepaper Research Assistant on AWS Bedrock AgentCore

> Research compiled 2026-06-05. AgentCore is fast-moving; this reflects the GA state (Oct 2025) plus updates through mid-2026. All claims are cited inline with URLs at the bottom.

---

## 0. TL;DR

- **Amazon Bedrock AgentCore went GA on 2025-10-13** in 9 regions. It is a set of *independent, composable* managed services (Runtime, Gateway, Memory, Identity, Observability, Browser, Code Interpreter, plus newer Policy and Agent Registry). You can adopt any subset. Pricing is consumption-based and notably **bills only active CPU/memory — I/O wait and idle are free**, which matters a lot for LLM-bound agents. [1][2][13]
- **AWS's recommended framework is Strands Agents SDK**, but Runtime is framework-agnostic and explicitly supports **LangGraph and CrewAI** too. [3][6]
- For a **Claude Code-style transcript UI**, the right primitive is the **AG-UI protocol** now natively supported by AgentCore Runtime (`--protocol AGUI`). AG-UI defines ~16–20 typed SSE events (RUN_STARTED, TEXT_MESSAGE_*, TOOL_CALL_START/ARGS/END/RESULT, STEP_*, STATE_DELTA, RUN_FINISHED/ERROR) that map almost 1:1 onto collapsible tool-call cards and streaming tokens. [7][8][14]
- **Human-in-the-loop** is implemented at the *framework* layer (Strands `BeforeToolCallEvent` interrupts; LangGraph `interrupt()` / `HumanInTheLoopMiddleware`) and surfaces through AgentCore via session persistence + a custom approval event over the stream. There is no separate "approval API" — you model it yourself. [9][10][12]
- **The pragmatic "tonight" path is to NOT use AgentCore yet**: build the agent in Strands (or LangGraph) + Bedrock behind a FastAPI SSE endpoint locally / on Lambda. The migration to AgentCore Runtime later is a ~10-line wrapper change (`BedrockAgentCoreApp` + `@app.entrypoint`). See §7.

---

## 1. AgentCore Components, GA Status, Regions, Pricing

### GA status & regions
GA announced **2025-10-13**. Available in **9 regions**: US East (N. Virginia, Ohio), US West (Oregon), Asia Pacific (Mumbai, Singapore, Sydney, Tokyo), Europe (Frankfurt, Ireland). At GA all services gained **VPC, PrivateLink, CloudFormation, and resource tagging** support. [1][2]

### Components

| Component | What it does | Notes (GA / 2026) |
|---|---|---|
| **Runtime** | Serverless, session-isolated container host for agents. Scales 0→thousands of sessions. **8-hour max execution** per session (good for long research jobs). MicroVM isolation. | Framework-agnostic. Protocols: HTTP (`/invocations`), MCP, **A2A** (agent-to-agent, added at GA), and **AG-UI** (for UIs). [1][2][6] |
| **Gateway** | Turns existing **REST APIs (OpenAPI), Smithy models, Lambda functions, API Gateway, and existing MCP servers** into a single managed **MCP** endpoint with tool discovery + inbound/outbound auth. "Zero-code MCP tool creation." | Target types: Lambda, OpenAPI, Smithy, MCP server, API Gateway. Supports IAM *and* OAuth authz. [4][11] |
| **Memory** | Managed short-term (conversation) + long-term (extracted facts/semantic) memory so you don't run your own vector store for context. | GA added a **self-managed strategy** giving full control of extraction/consolidation pipelines. [1] |
| **Identity** | OAuth 2.0 / IAM identity for agents; secure vault for refresh tokens; lets an agent act on behalf of a user or itself. | "Identity-aware authorization" at GA. **No extra charge when used via Runtime/Gateway.** [1][13] |
| **Observability** | End-to-end traces, spans, operational metrics across all AgentCore services via **OpenTelemetry → CloudWatch**; also exports to Datadog, Dynatrace, Langfuse, LangSmith, Arize. | Billed at standard CloudWatch rates. [1][13] |
| **Browser** | Managed, isolated headless browser so agents can navigate web apps at scale (useful for fetching/reading papers behind JS). | Billed like Runtime (vCPU/GB-hr). Browser-profile S3 storage billed from 2026-04-15. [1][13] |
| **Code Interpreter** | Secure isolated sandbox for agent-generated code execution (data analysis, chart/table generation from extracted paper data). | Billed like Runtime. [1][13] |
| **Policy** (newer) | Policy/guardrail layer; reached GA per AWSInsider Mar 2026. | Verify current state in console. [1a] |
| **Agent Registry** (preview) | Discover/catalog agents & tools. | Free tier then per-record pricing. [13] |

### Pricing model (consumption-based, no upfront) [13]
- **Runtime / Browser / Code Interpreter (active compute):** **$0.0895 / vCPU-hour** + **$0.00945 / GB-hour**, per-second billing, 128 MB min. **Idle / I/O-wait is free** if nothing is actively computing — the big cost lever for LLM-bound agents (typically 30–70% I/O wait). [2][13]
- **Gateway:** API invocations (ListTools/InvokeTool/Ping) **$0.005 / 1,000**; semantic tool Search API **$0.025 / 1,000**; tool indexing **$0.02 / 100 tools / month**. [13]
- **Memory:** short-term **$0.25 / 1,000 events**; long-term storage **$0.75 / 1,000 records/month** (built-in strategies) or **$0.25** (self-managed/override); retrieval **$0.50 / 1,000 retrievals**. [13]
- **Identity:** **$0.010 / 1,000 tokens or API keys** for non-AWS resources; **free via Runtime/Gateway**. [13]
- **Observability:** standard CloudWatch rates. [13]
- **Network egress** billed at standard EC2 rates from 2025-11-01. [2]
- **Model inference (Bedrock tokens) is billed separately** — see §6 for Claude tiers.

---

## 2. Frameworks on AgentCore Runtime + Multi-Agent Orchestration

Runtime is **framework-agnostic** — it runs any container that honors the HTTP/MCP/A2A/AG-UI contract. AWS officially lists **Strands Agents, LangGraph, and CrewAI** as supported. [6]

### What AWS recommends
**Strands Agents SDK** (AWS open-source, Python + TypeScript, v1.0 mid-2025) is the first-party path. It's *model-driven*: you give the model a prompt + tools and let it plan, rather than hand-authoring a graph. If you're already on AWS/Bedrock, **Strands + AgentCore is the most frictionless path** (native IAM/VPC/secrets). LangGraph suits you when you want an explicit, deterministic state machine; CrewAI for role-based crews. [3][5]

### Multi-agent orchestration (supervisor + workers)
Strands offers three composition styles: [3a]
- **Agents-as-tools** — a supervisor agent exposes worker agents as callable tools. This is the cleanest "supervisor/router → workers" pattern and what you want for the whitepaper assistant (router picks a worker; worker does the task; supervisor synthesizes).
- **Graph** (`GraphBuilder`) — structured, explicit DAG of agents.
- **Swarm** — parallel agents with handoffs.
- **Workflow** — chain agents in code.

For our use case:
- **Supervisor (router)** classifies the query and decides which workers to call, possibly **in parallel** (literature-search worker + web worker + PDF-ingest worker).
- **Workers** are specialized agents (each with its own tools + model tier).
- On AgentCore you can run the whole multi-agent graph **inside one Runtime container**, or split workers into **separate Runtimes communicating via A2A** for independent scaling. For "tonight," one container is simpler; A2A is the scale-out option later. [1][6]

LangGraph equivalent: a `StateGraph` with a supervisor node routing to worker subgraphs; AWS has a dedicated guide for **serverless LangGraph multi-agent on AgentCore**. [3b]

---

## 3. Streaming Agent Events to a Claude Code-Style Frontend

### The protocol stack
AgentCore Runtime's `InvokeAgentRuntime` API returns a **streaming response** (binary payload up to 100 MB in, streamed chunks out). Two ways to model the event stream:

1. **Raw SSE / NDJSON** via the **HTTP protocol contract**: your container serves `POST /invocations` returning `Content-Type: text/event-stream` with `data: {...}` lines, plus `GET /ping`. You define your own event JSON. Runtime is a pass-through proxy (handles SigV4/OAuth, session isolation, scaling). [15][16]
2. **AG-UI protocol** (recommended for a rich UI): deploy with `--protocol AGUI`. Container still listens on **port 8080**, `/invocations` for HTTP/SSE (or `/ws` for WebSocket). Runtime proxies requests unmodified. AG-UI gives you a **standard typed event vocabulary** that frontends (CopilotKit, the AG-UI TS client SDK) already understand. [7][14]

### SSE vs WebSocket
- **SSE** (one-directional server→client) is the default and simplest, and is what AG-UI uses for streaming. Perfect for streaming tokens + tool events to the transcript. Use this.
- **WebSocket** (`/ws`, port 8080) when you need true bidirectional/interactive sessions (e.g., live mid-stream user input). Both can coexist on one container. [15][7]
- Note: SSE supports concurrent/parallel runs naturally — each browser fetch is its own `Session-Id` (`X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` header), and Runtime isolates sessions. So multiple parallel agent conversations are first-class. [7][16]

### AG-UI event types → UI rendering
AG-UI defines ~16–20 events across 5 categories. The ones you render: [8][14]

| AG-UI event | UI rendering (Claude Code style) |
|---|---|
| `RUN_STARTED` / `RUN_FINISHED` / `RUN_ERROR` | Turn lifecycle; show spinner / done / error banner under the user turn |
| `STEP_STARTED` / `STEP_FINISHED` | Group sub-steps (e.g., a sub-agent phase) |
| `TEXT_MESSAGE_START` / `TEXT_MESSAGE_CONTENT` (delta) / `TEXT_MESSAGE_END` | **Streaming tokens** — append `delta` to the assistant bubble |
| `TOOL_CALL_START` (tool_call_id, tool_name) | Open a **collapsible tool-call card** ("Calling `scopus_search`…") |
| `TOOL_CALL_ARGS` (delta) | Stream args into the card |
| `TOOL_CALL_END` | Mark call dispatched |
| `TOOL_CALL_RESULT` | Fill card body with result; collapse by default |
| `STATE_SNAPSHOT` / `STATE_DELTA` | Sync shared state (e.g., running citation list) to a side panel |
| `CUSTOM` / `RAW` | **Carry your own events** — e.g., `sub_agent_started`, `approval_request` (see §4) |
| `REASONING_START` (+ reasoning deltas) | Show "thinking" disclosure |

**Sub-agent activity:** model each worker as nested `STEP_STARTED/FINISHED` blocks, or emit `CUSTOM` events (`{type:"CUSTOM", name:"sub_agent", value:{agent:"literature", phase:"start"}}`) so the frontend can render an indented sub-transcript card — exactly the Claude Code "Task(...)" nested view.

### Minimal AG-UI server (Strands, from AWS docs) [7]
```python
# my_agui_server.py
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from ag_ui_strands import StrandsAgent
from ag_ui.core import RunAgentInput
from ag_ui.encoder import EventEncoder
from strands import Agent
from strands.models.bedrock import BedrockModel

model = BedrockModel(model_id="us.anthropic.claude-sonnet-...", region_name="us-west-2")
strands_agent = Agent(model=model, system_prompt="You are a research assistant.")
agui_agent = StrandsAgent(agent=strands_agent, name="research", description="...")

app = FastAPI()

@app.post("/invocations")
async def invocations(input_data: dict, request: Request):
    encoder = EventEncoder(accept=request.headers.get("accept"))
    async def gen():
        run_input = RunAgentInput(**input_data)
        async for event in agui_agent.run(run_input):
            yield encoder.encode(event)          # yields AG-UI SSE frames
    return StreamingResponse(gen(), media_type=encoder.get_content_type())

@app.get("/ping")
async def ping(): return JSONResponse({"status": "Healthy"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
```
Deploy: `agentcore configure -e my_agui_server.py --protocol AGUI` → `agentcore deploy`. Frontend consumes via the **AG-UI TS client** or **CopilotKit** React components. [7]

---

## 4. Human-in-the-Loop / Permission Gating

There is **no dedicated AgentCore approval API** — HITL is implemented in the *framework* and surfaced over your event stream. [12]

### Strands
Intercept with a **`BeforeToolCallEvent` interrupt** (hook). When a sensitive tool (e.g., "spend Scopus quota", "write to S3") is about to run, the hook fires an `interrupt()` that **pauses the agent loop** until a human responds. You can set `event.cancel = True` (with optional message) to deny, or feed an edited input to approve-with-changes. [9][12]

### LangGraph
Use the built-in **`interrupt()`** inside a node, or **`HumanInTheLoopMiddleware`** with `interrupt_on={tool_name: {...}}`. Decision types: **approve / edit / reject / respond**. `interrupt()` pauses the graph at that line and returns control to the caller with a payload; resuming passes the human's decision back. State is checkpointed so the graph can resume exactly where it paused. [10][12]

### How it surfaces through AgentCore (the end-to-end loop)
1. Worker hits a gated tool → framework interrupt fires.
2. Your entrypoint emits an **`approval_request` event** over the stream (AG-UI `CUSTOM` event carrying `{tool, args, call_id}`). Frontend renders an **approve/deny/edit panel** under the turn.
3. The run **pauses**. Because Runtime gives **session persistence across invocations** (same `Session-Id`), the agent state survives the wait — even for long human delays (up to the 8-hour session window, and via async/`add_async_task` + `HealthyBusy` ping status for long pauses). [12][17]
4. Human clicks Approve/Deny/Edit → frontend calls `InvokeAgentRuntime` again **with the same Session-Id** carrying the decision → framework resumes from the checkpoint with the human's value. [12][17]
5. Frontend tip: persist `sessionId`/`instanceId` in `sessionStorage` so an approval panel can be re-shown on reload. [12]

For long human waits, mark the agent busy via **`add_async_task` / `complete_async_task`** so Runtime keeps the session warm (`HealthyBusy`). [17]

---

## 5. External Research Tools via AgentCore Gateway

Gateway is how you expose a **university / Scopus-style search API**, **web search**, and **PDF ingestion** as agent tools through a single MCP endpoint, with managed auth. [4][11]

### Pattern A — Scopus/university API (you have an API key)
- **If you have an OpenAPI spec:** create a **Gateway OpenAPI target** pointing at the Scopus base URL; attach the API key as an **outbound credential** (API-key auth) — Gateway proxies every operation as an MCP tool. Zero glue code. [4][11]
- **If no clean spec / need shaping:** wrap calls in a **Lambda target**. The Lambda holds the API key (from Secrets Manager via AgentCore Identity), calls Scopus, normalizes results (title/abstract/DOI/authors), and returns them. Gateway turns the Lambda into MCP tools (`scopus_search`, `scopus_get_abstract`). Best for rate-limiting, field mapping, and combining endpoints. [4]
- **Outbound auth & secrets** handled by **AgentCore Identity** (token vault) so the key never lives in agent code. [1][4]

### Pattern B — Web search
Either an OpenAPI/Lambda target wrapping a search provider (Brave/Tavily/SerpAPI), **or** connect an existing **web-search MCP server** as a Gateway MCP target. Gateway unifies it under the same MCP endpoint with tool discovery. [4][11]

### Pattern C — PDF ingestion
Lambda target: input = S3 URI or URL; Lambda fetches the PDF (use **AgentCore Browser** for JS-gated/paywalled-preview pages), extracts text (Textract or a PDF lib), chunks it, and either returns text or writes embeddings/records into **AgentCore Memory** or your vector store. Exposed as tools `ingest_pdf`, `search_corpus`. For analysis/plots over extracted tables, hand off to **Code Interpreter**. [1][4]

**Semantic tool selection:** with many tools, enable Gateway's **Search API** so the supervisor finds the right tool by intent instead of stuffing every tool schema into the prompt (cheaper context, billed $0.025/1k searches). [13]

---

## 6. Reference Architecture

```
                                  ┌─────────────────────────────────────────────────────┐
   React + TypeScript SPA         │  Browser                                            │
   (Vite, AG-UI TS client /       │  - Chat transcript                                  │
    CopilotKit)                   │  - Under each user turn: streaming tokens,          │
                                  │    collapsible TOOL_CALL cards, nested SUB-AGENT    │
                                  │    cards, approve/deny/edit panels                  │
                                  │  - Parallel turns = parallel SSE connections        │
                                  └───────────────┬─────────────────────────────────────┘
                                                  │ HTTPS  (SSE  text/event-stream)
                                                  │ Authorization: Bearer (Cognito OAuth)
                                                  │ X-Amzn-Bedrock-AgentCore-Runtime-Session-Id
                                                  ▼
                          ┌───────────────────────────────────────────────┐
                          │  Streaming API edge                           │
                          │  Option 1: direct InvokeAgentRuntime          │
                          │  Option 2: thin Lambda/FastAPI proxy that     │
                          │    re-streams (auth, CORS, fan-in)            │
                          └───────────────────────┬───────────────────────┘
                                                  │  InvokeAgentRuntime (AG-UI / SSE)
                                                  ▼
   ┌───────────────────────────── AgentCore RUNTIME (8080, --protocol AGUI) ──────────────────────────────┐
   │                                                                                                       │
   │   SUPERVISOR / ROUTER agent  (Claude Haiku  — cheap classify + route)                                 │
   │        │  agents-as-tools  / GraphBuilder                                                              │
   │        ├──────────────┬───────────────────┬───────────────────────┐                                  │
   │        ▼              ▼                   ▼                       ▼                                    │
   │  LIT-SEARCH worker  WEB worker        PDF-INGEST worker     DRAFTER worker                             │
   │  (Claude Sonnet)    (Claude Sonnet)   (Claude Sonnet)       (Claude Opus — final whitepaper draft)     │
   │        │              │                   │                       │                                    │
   │   emits AG-UI: RUN/STEP/TEXT/TOOL_CALL_*/CUSTOM(sub_agent, approval_request)                           │
   │        │              │                   │                                                            │
   │   BeforeToolCall interrupt → approval_request event → pause (session persisted) → resume w/ decision   │
   └────────┼──────────────┼───────────────────┼──────────────────────────────────────────────────────────┘
            │ MCP          │ MCP               │ MCP / S3
            ▼              ▼                   ▼
   ┌──────────────── AgentCore GATEWAY (single managed MCP endpoint, tool discovery) ───────────────┐
   │  OpenAPI/Lambda target: scopus_search, scopus_get_abstract  (API key via Identity vault)        │
   │  Lambda/MCP target:     web_search                                                              │
   │  Lambda target:         ingest_pdf  ─────────────► S3 (paper corpus)   + AgentCore Browser       │
   └────────────────────────────────────────────────────────────────────────────────────────────────┘

   Cross-cutting AgentCore services:
     • MEMORY      short-term conversation + long-term semantic (citations, prior findings)
     • IDENTITY    OAuth/IAM + secret vault for Scopus key (free via Runtime/Gateway)
     • OBSERVABILITY OTEL → CloudWatch (traces of every agent/tool/sub-agent span)

   Model cost tiers (Bedrock, billed separately, ~$/M tokens, cross-region +~10%):
     Haiku 4.5  $1 / $5     → router + cheap classification
     Sonnet 4.6 $3 / $15    → worker reasoning + tool use
     Opus 4.6   $5 / $25    → final whitepaper drafting only
   (Use prompt caching ≈ up to 90% off cached input; batch ≈ 50% off for non-interactive jobs.)
```
Sources for tiers/pricing: [18][13]. Architecture pattern synthesized from [1][3a][6][7].

---

## 7. The Pragmatic "Tonight" Fallback (and the migration delta)

**Recommendation: build tonight WITHOUT AgentCore.** Write the agent in **Strands (or LangGraph) + Bedrock** behind a **FastAPI SSE** endpoint, run it locally (and/or on Lambda with streaming responses). The agent *logic, tools, prompts, and event format are identical* to what AgentCore expects — so the lift later is tiny. [7][19]

### Tonight stack
- **Agent:** Strands `Agent` with Bedrock models; supervisor via agents-as-tools; tools as plain Python functions (Scopus via `requests` + your key, web search, PDF ingest).
- **Streaming:** FastAPI `POST /invocations` returning `StreamingResponse(..., media_type="text/event-stream")`, yielding from `agent.stream_async(...)`. Emit **AG-UI-shaped events now** (or your own NDJSON) so the React UI is final from day one.
- **HITL:** Strands `BeforeToolCallEvent` interrupt → emit `approval_request` SSE event → pause → resume on next request with the decision (keep session state in-process or in Redis/DynamoDB).
- **Frontend:** the same React + AG-UI client / CopilotKit transcript.
- **Optional Lambda:** deploy the FastAPI app on Lambda with **streaming response** (or a Lambda that proxies/re-streams). [15a]

### What changes when you migrate to AgentCore Runtime
The diff is intentionally small. From the Strands deploy guide: [19]
```python
# LOCAL (FastAPI)                          # AGENTCORE RUNTIME
from fastapi import FastAPI                from bedrock_agentcore.runtime import BedrockAgentCoreApp
app = FastAPI()                            app = BedrockAgentCoreApp()
agent = Agent(...)                         agent = Agent(...)              # unchanged

@app.post("/invocations")                  @app.entrypoint
async def invocations(payload, request):   async def agent_invocation(payload):
    ...                                        user_message = payload.get("prompt")
    return StreamingResponse(gen(), ...)       async for event in agent.stream_async(user_message):
                                                   yield event             # Runtime handles SSE framing

if __name__ == "__main__":                 if __name__ == "__main__":
    uvicorn.run(app, port=8080)                app.run()
```
**Concrete migration checklist:**
1. Swap FastAPI wrapper → `BedrockAgentCoreApp` + `@app.entrypoint` (or keep FastAPI and just add `--protocol AGUI` if using AG-UI). [7][19]
2. `pip install bedrock-agentcore` (+ `ag-ui-strands` if AG-UI); add to `requirements.txt`. [7][19]
3. Build an **ARM64** container on **port 8080** with `/invocations` + `/ping` (the toolkit/CLI does this for you). [15][16]
4. `agentcore configure --protocol AGUI` → `agentcore deploy` (or `agentcore create`/`dev`/`deploy` with the new `@aws/agentcore` CLI). [7][19]
5. Move tool API keys from local env → **Identity vault / Secrets Manager**; optionally relocate tools behind **Gateway** (no agent code change — just point the MCP client at the Gateway URL). [4][13]
6. Switch session state from your in-process/Redis store → **Runtime session persistence** (same `Session-Id`) and optionally **AgentCore Memory**. [17]
7. Wire **Observability** by enabling OTEL (env vars) — no logic change. [1][13]

**What does NOT change:** agent graph, prompts, model selection/tiers, tool function bodies, the AG-UI/SSE event vocabulary, and the React frontend. That's the whole point of building AG-UI-shaped from the start.

### Tonight-vs-AgentCore tradeoff

| | Tonight (Strands + FastAPI/Lambda SSE) | AgentCore Runtime |
|---|---|---|
| Time to first demo | Hours | Days (auth, container, deploy) |
| Streaming UI | Full control, you frame SSE | Native AG-UI, less to build |
| Session/memory | DIY (Redis/Dynamo) | Managed (persistence + Memory) |
| Long human pauses | DIY keep-alive | Built-in (8h session, async ping) |
| Scaling | You manage | 0→thousands, isolated |
| Tool auth/secrets | Env / your code | Identity vault + Gateway |
| Cost at idle | Lambda/EC2 billed while up | Idle/I-O-wait free |
| Migration cost later | — | ~10-line wrapper + container + CLI |

**Verdict:** Build tonight on Strands + Bedrock + FastAPI SSE, emitting **AG-UI-shaped events** and using framework-level HITL interrupts. This gets a working Claude Code-style transcript fast, keeps you 100% on AWS/Bedrock, and makes the eventual AgentCore Runtime migration a wrapper swap rather than a rewrite. Adopt AgentCore Gateway/Identity/Memory/Observability incrementally once the core agent works.

---

## Sources
1. AWS ML Blog — AgentCore is now GA (components, A2A, GA features): https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-agentcore-is-now-generally-available/
1a. AWSInsider — AgentCore Policy reaches GA (Mar 2026): https://awsinsider.net/blogs/awsinsider-release-radar/2026/03/amazon-bedrock-agentcore.aspx
2. AWS What's New — AgentCore GA (date, 9 regions, egress billing): https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/
3. Strands Agents SDK home: https://strandsagents.com/
3a. Strands multi-agent patterns (agents-as-tools, Graph, Swarm, Workflow): https://strandsagents.com/docs/user-guide/concepts/multi-agent/multi-agent-patterns/
3b. AWS ML Blog — serverless LangGraph multi-agent on AgentCore: https://aws.amazon.com/blogs/machine-learning/build-highly-scalable-serverless-langgraph-multi-agent-systems-in-aws-with-amazon-bedrock-agentcore/
4. AWS ML Blog — Introducing AgentCore Gateway (OpenAPI/Smithy/Lambda targets): https://aws.amazon.com/blogs/machine-learning/introducing-amazon-bedrock-agentcore-gateway-transforming-enterprise-ai-agent-tool-development/
5. Strands deep dive (architectures & observability): https://aws.amazon.com/blogs/machine-learning/strands-agents-sdk-a-technical-deep-dive-into-agent-architectures-and-observability/
6. AWS ML Blog — Strands + AgentCore + LibreChat (Runtime supports LangGraph/CrewAI/Strands): https://aws.amazon.com/blogs/machine-learning/build-and-scale-adoption-of-ai-agents-for-education-with-strands-agents-amazon-bedrock-agentcore-and-librechat/
7. AWS Docs — Deploy AG-UI servers in AgentCore Runtime (server code, --protocol AGUI, port 8080, SSE/WS): https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-agui.html
8. CopilotKit — Master the 17 AG-UI event types: https://www.copilotkit.ai/blog/master-the-17-ag-ui-event-types-for-building-agents-the-right-way
9. Strands Agents — Interrupts (BeforeToolCallEvent, cancel): https://strandsagents.com/docs/user-guide/concepts/interrupts/
10. LangChain — building HITL agents with interrupt(): https://www.langchain.com/blog/making-it-easier-to-build-human-in-the-loop-agents-with-interrupt
11. AWS Docs — AgentCore Gateway core concepts (targets): https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-core-concepts.html
12. AWS ML Blog — HITL constructs for agentic workflows (interrupt→pause→resume, frontend sessionStorage): https://aws.amazon.com/blogs/machine-learning/human-in-the-loop-constructs-for-agentic-workflows-in-healthcare-and-life-sciences/
13. AWS — AgentCore Pricing (all component rates, idle-free): https://aws.amazon.com/bedrock/agentcore/pricing/
14. AG-UI core events spec: https://docs.ag-ui.com/sdk/js/core/events
15. AWS Docs — Runtime HTTP protocol contract (/invocations, /ping, SSE, /ws, ARM64 port 8080): https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-http-protocol-contract.html
15a. GitHub — proxy AgentCore stream via Lambda streaming response: https://github.com/msysh/agentcore-and-lambda-stream-response
16. AWS Docs — Invoke an AgentCore Runtime agent (InvokeAgentRuntime, Session-Id): https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-invoke-agent.html
17. AWS Docs — Async & long-running agents (add_async_task, HealthyBusy, session reuse): https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-long-run.html
18. AWS Bedrock pricing 2026 / Claude tiers (Opus 4.6 $5/$25, Sonnet 4.6 $3/$15, Haiku 4.5 $1/$5, +~10% cross-region): https://aws.amazon.com/bedrock/pricing/  and  https://benchlm.ai/blog/posts/claude-api-pricing
19. Strands Docs — Deploy to AgentCore Runtime (Python: BedrockAgentCoreApp, @app.entrypoint, stream_async, agentcore CLI): https://strandsagents.com/docs/user-guide/deploy/deploy_to_bedrock_agentcore/python/
