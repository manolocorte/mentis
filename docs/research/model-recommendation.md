# Mentis LLM Model Recommendation — Cost + Capability (single-user, hard €50/mo budget)

**Date:** 2026-06-05
**Scope:** Which LLMs should the Mentis agentic scientific-whitepaper assistant use, per agent role, to keep one active researcher under **€50/month** while producing journal-grade English technical writing in thermal/chemical engineering (CO2 absorption-refrigeration domain).
**Bias of this analysis:** cheap Chinese/open models are taken seriously, not dismissed. We only escalate to a premium model where the data justifies it.

> FX assumption: **€1 ≈ $1.08** (mid-2026). €50 ≈ **$54**. All prices below are USD per million tokens (MTok) unless noted.

---

## TL;DR — Recommended per-role tiering

| Agent role | Recommended (BUDGET) | Quality upgrade (if budget allows) | Why |
|---|---|---|---|
| **Router / intent** | DeepSeek V4-Flash (non-thinking) — $0.14/$0.28 | Claude Haiku 4.5 — $1/$5 | Trivial classification; cheapest competent JSON/tool model wins. |
| **Web-search worker** | DeepSeek V4-Flash | GLM-4.7-Flash / Qwen3 | Strong tool-calling (BFCL), cheap, summarizes search hits. |
| **Literature-search worker** | DeepSeek V4-Flash | Claude Haiku 4.5 | Same; Haiku if API-call orchestration gets fiddly. |
| **RAG synthesizer** | DeepSeek V4-Flash / Qwen3-Max | **Claude Sonnet 4.6** — $3/$15 | Multi-doc grounded synthesis; cheap models OK *with* RAG grounding. |
| **Final drafter** | **Claude Sonnet 4.6** | Claude Opus 4.8 — $5/$25 | Journal-grade English prose + lowest citation-fabrication risk. |
| **Fact-check / citation-verify pass** | Claude Sonnet 4.6 (or Haiku 4.5) | Claude Sonnet 4.6 | Tool competence required for verify pass to actually work (see §1c). |
| **Embeddings** | **Amazon Titan Embed v2 (1024-d)** — $0.02 | Cohere Embed v3 — $0.10 | Already in stack; 5× cheaper than Cohere/equal to OpenAI-small. |

**Bottom line:** The recommended hybrid (cheap-open for router + workers + synthesis, **Claude Sonnet 4.6 for final drafting and citation verification**) lands at **~$8–18/month (≈ €7–17)** at realistic single-user volume — comfortably under €50. An **all-Anthropic** setup also fits (~$10–25/mo) if you keep the final drafter on Sonnet rather than Opus. The budget only breaks if you (a) make the final drafter **Opus** *and* run many long drafts/month, or (b) blow up context by not capping retrieval top-k / reflexion loops. See §2.

---

## 1. Capability: the two things that matter for Mentis

Mentis needs two distinct competencies. They do **not** rank models the same way, which is the whole reason a tiered/hybrid setup wins.

### (a) Agentic tool-use / function-calling + multi-step reasoning

Two benchmarks matter, and they tell *different* stories — read both:

**BFCL v3 (Berkeley Function Calling Leaderboard)** — strict schema/format function-calling, multi-turn:

| Model | BFCL v3 | Note |
|---|---|---|
| GLM-4.5 Thinking (Z.ai) | **76.7** | Top open model |
| Qwen3-32B / Qwen3-Max (Alibaba) | 74.9–75.7 | Excellent + cheap |
| GLM-4.7-Flash | 74.6 | Cheap + strong |
| **Amazon Nova Pro 1.0** | **67.9** | Best AWS-native non-Claude |
| Kimi K2.5 | 64.5 | Solid |
| Llama 4 Scout | 55.7 | Mediocre |
| Claude Opus 4 | 25.3 | **Artifact — see below** |

Source: BFCL v3 leaderboard (pricepertoken / llm-stats / Gorilla). The very low Claude score is a **known measurement artifact**: BFCL penalizes Anthropic's tool-call *format* (Claude emits tool calls in a style the strict AST/format checker scores harshly), not Claude's real-world tool competence. Do **not** conclude Claude is bad at tools.

**tau-bench / tau2-bench** — *agentic* end-to-end tasks (a model must hold a goal, call tools, react to results across many turns). This mirrors Mentis's supervisor loop far better than BFCL:

| Model | tau-bench | Note |
|---|---|---|
| Claude Sonnet 4.6 | **~87.5** | Class-leading agentic |
| Claude Sonnet 4.5 | 86.2 | |
| Claude Sonnet 4.5 (airline subset) | 70.0 | Hardest subset |
| MiniMax M1 80K (airline) | 62.0 | |
| GLM-4.5-Air (airline) | 60.8 | Best cheap-open on hardest subset |
| Claude Haiku 4.5 | reaches ~90% of Sonnet 4.5 in agentic coding evals at $0.80/$4 | Strong for its tier |

**Reading:** For *simple, well-scoped* tool calls (route this query; call OpenAlex with these params; summarize these 8 hits), the cheap Chinese models (DeepSeek V4-Flash, Qwen3, GLM-4.x) are **good enough** — they top BFCL and cost 5–35× less. For the *hardest, longest* agentic chains, Claude (Sonnet) is meaningfully more reliable on tau-bench. Mentis's per-worker tool calls are individually simple, so **cheap-open is fine for routing + workers + synthesis**, and you reserve Claude for where multi-step reliability and prose quality compound — the final draft + the verification pass.

### (b) Long-form scientific/technical English writing

Human-preference and writing-specific signals (LMArena / Chatbot Arena ELO + writing benchmarks, mid-2026):

- **Top of arena:** Claude Opus 4.7/4.8 variants lead (≈1567 ELO), with **Qwen3.7-Max, GLM-5.1, Claude Sonnet 4.6, Kimi K2.6, Gemini 3.5 Flash** clustered just behind.
- **Best Chinese for English prose:** GLM-5/5.1 and Kimi K2.6 are the strongest open writers (Arena ELO ~1445–1451); Qwen3.x-Max is competitive and the strongest *agentic* open writer.
- **Caveat for cheap Chinese models on English scientific prose:** they are strong but show two recurring issues for journal-grade English: (1) occasional register/idiom drift ("translationese") in long technical passages, and (2) **higher citation-fabrication tendency** when not tightly grounded (§1c). DeepSeek V4-Flash in particular is optimized for cost/coding throughput, not literary English — fine for *synthesis notes*, weaker for *publication prose*.

**Reading:** Cheap-open models are "good enough" for **internal synthesis, summaries, gap analysis, and first-pass section drafts**. For the **final, publication-grade draft** (the ~3,000–6,000-word artifact that a journal editor sees), Claude Sonnet 4.6 (or Opus for the truly final polish) is the right call — both for prose register and for the citation-integrity reasons below. This is exactly the split the existing `docs/aws-bedrock-models.md` already gestures at; this report makes it quantitative and adds the cheap-open option for the lower tiers.

### (c) Citation hallucination — the dominant scientific risk, and mitigations

This is the single biggest quality risk for Mentis and it gets *worse* with cheaper/smaller models:

- Across 13 SOTA models, citation hallucination rates ranged **14.2%–94.9%**, varying by domain (Lancet / GhostCite / arXiv 2602.06718).
- Smaller/weaker models fabricate more: **~47% (GPT-4-class) up to ~77% (Llama-2-7B)** for CS reference titles; field-specific fabrication 6%–29% even for GPT-4o (mental-health study, EurekAlert/medicalxpress).
- Fabricated citations in *published* papers rose **~12×** from 2023 to Q4 2025 — this is a live, escalating problem, not theoretical.

**Mitigations (in priority order for Mentis):**

1. **Retrieval-grounding (RAG) — primary defense.** Mentis already retrieves real papers (S3 Vectors + lexical RRF) and feeds chunks into context. *Rule:* the drafter may only cite from the retrieved corpus / tool results, never from parametric memory. Grounding is the best-evidenced reducer of fabricated references (multiple 2025–2026 RAG surveys; PaperQA; VeriCite arXiv 2510.11394). It does not eliminate ungrounded sentences, so combine with (2).
2. **Post-hoc citation/URL verification pass.** A verification tool (resolve DOI/URL, confirm title+authors+year against Crossref/OpenAlex — Mentis already has these ports) is dramatic: a Wayback-style "urlhealth" agentic check reduced non-resolving citations **26×** (GPT-5.1), **79×** (Gemini 2.5 Pro), **6.4×** (Claude Sonnet 4.5) (arXiv 2604.03173).
3. **Run the verify pass on a *capable* model.** Critical finding from the same paper: the verification step **only works if the model is competent enough to act on tool results.** GPT-5-nano *called* the verify tool but failed to fix anything across 14 rounds. **Implication for Mentis:** do not run the citation-verify pass on the cheapest tier — use Claude Sonnet 4.6 (or at minimum Haiku 4.5), even though synthesis upstream can be cheap-open.
4. **Mentis's existing `fact-check → revise` reflexion loop** is the right shape; cap it (§2) to control cost, and point its tool at the real literature APIs.

---

## 2. Workload cost model (single user)

### Per-session token assumptions

A "session" = one researcher question that triggers the full `router → retrieve → investigate → synthesize → (fact-check → revise)*` pipeline. Two session archetypes:

**A. Light Q&A / lookup session** (most sessions):

| Step | Model tier | Input tok | Output tok |
|---|---|---|---|
| Router/intent | cheap | 600 | 150 |
| 2× web/lit workers (tool calls + summarize hits) | cheap | 2× (8,000 in / 800 out) | |
| RAG synthesizer (top-k=8 chunks ≈ 6k tok ctx) | cheap/mid | 9,000 | 1,200 |
| 1 fact-check pass | mid | 6,000 | 600 |
| **Per light session** | | **≈ 33,600 in** | **≈ 4,350 out** |

**B. Full draft session** (the expensive one — produces a 3,000–6,000-word section/draft):

| Step | Model tier | Input tok | Output tok |
|---|---|---|---|
| Router | cheap | 600 | 150 |
| 3× workers (broader search) | cheap | 3× (10,000 / 1,000) | |
| RAG synthesizer (top-k=12 ≈ 9k ctx, multi-call) | mid | 25,000 | 3,000 |
| Final drafter (large grounding ctx ~25k + outline) | premium | 30,000 | 8,000 (≈6k words) |
| fact-check → revise ×2 (capped) | mid/premium | 2× (28,000 / 4,000) | |
| **Per full-draft session** | | **≈ 145,600 in** | **≈ 23,150 out** |

### Monthly volume assumption (one active researcher)

Stated assumption: **80 light sessions + 8 full-draft sessions per month** (≈ 4 questions/workday + ~2 drafts/week). This is an *active* user; a casual user is roughly half this.

Monthly totals (pre-caching):
- Light: 80 × (33.6k in + 4.35k out) = **2.69M in + 0.35M out**
- Draft: 8 × (145.6k in + 23.15k out) = **1.16M in + 0.19M out**
- **Combined ≈ 3.85M input + 0.54M output tokens/month**, plus ~0.5M embedding tokens (ingestion + queries).

### Pricing inputs used (USD / MTok, on-demand)

| Model | In (miss) | In (cache hit) | Out |
|---|---|---|---|
| DeepSeek V4-Flash | 0.14 | 0.0028 | 0.28 |
| DeepSeek V4-Pro | 0.435 | 0.0036 | 0.87 |
| Qwen3-Max (approx) | ~0.50 | — | ~3.00 |
| GLM (5.x approx) | ~1.40 | — | ~4.40 |
| Kimi K2.x (approx) | ~1.20 | — | ~4.50 |
| Amazon Nova Micro | 0.035 | — | 0.14 |
| Amazon Nova Lite | 0.06 | — | 0.24 |
| Amazon Nova Pro | 0.80 | — | 3.20 |
| Claude Haiku 4.5 | 1.00 | 0.10 | 5.00 |
| Claude Sonnet 4.6 | 3.00 | 0.30 | 15.00 |
| Claude Opus 4.8 | 5.00 | 0.50 | 25.00 |
| Titan Embed v2 | 0.02 | — | — |

Cache hit = 0.1× input on Anthropic; ~0.02–0.1× on DeepSeek. Bedrock on-demand runs ~20–35% above first-party list for some models — treat AWS-side numbers as +25% headroom.

### Strategy costs (monthly, single user, before caching)

Distribute the 3.85M in / 0.54M out across tiers. For "tiered" strategies, roughly: workers+router+synth carry **~2.7M in / 0.3M out** at the cheap tier; the draft+verify premium portion carries **~1.0M in / 0.23M out** at the premium tier (light sessions add a small mid-tier fact-check share, ~0.15M in / 0.02M out).

**(a) All-Anthropic tiered** — Haiku (router/workers), Sonnet (synth/fact-check), Opus (final draft):
- Cheap tier on Haiku: 2.7M×$1 + 0.3M×$5 = $2.70 + $1.50 = **$4.20**
- Mid (Sonnet synth/fact-check): ~0.9M×$3 + 0.12M×$15 = $2.70 + $1.80 = **$4.50**
- Premium **Opus** final draft (8 drafts ≈ 0.24M in + 0.064M out): 0.24M×$5 + 0.064M×$25 = $1.20 + $1.60 = **$2.80**
- Embeddings: **$0.01**
- **Total ≈ $11.5/mo (≈ €10.6).** Swap Opus→Sonnet for final draft ⇒ **~$10/mo**. **Fits.**

**(b) Cheap-open tiered (RECOMMENDED)** — DeepSeek V4-Flash (router/workers/synth), Sonnet 4.6 (final draft + verify):
- Cheap tier (DeepSeek V4-Flash): 2.7M×$0.14 + 0.3M×$0.28 = $0.38 + $0.08 = **$0.46**
- Premium Sonnet final draft + verify (~1.0M in + 0.23M out): 1.0M×$3 + 0.23M×$15 = $3.00 + $3.45 = **$6.45**
- Light-session fact-check on Haiku (~0.15M in / 0.02M out): ~$0.25
- Embeddings: **$0.01**
- **Total ≈ $7.2/mo (≈ €6.7).** **Comfortably fits.** This is the sweet spot.

**(c) All-cheap-open** — DeepSeek V4-Flash everywhere, DeepSeek V4-Pro or GLM/Qwen for the draft:
- Everything-cheap: 3.7M×$0.14 + 0.5M×$0.28 = $0.52 + $0.14 = **$0.66**
- If final draft uses GLM-5.1 (~$1.40/$4.40) for 8 drafts (0.24M/0.064M): $0.34 + $0.28 = **$0.62**
- Embeddings: **$0.01**
- **Total ≈ $0.7–1.3/mo (≈ €0.7–1.2).** Cheapest by far — but accepts the highest citation-fabrication and prose-register risk (§4).

### Effect of prompt caching and capping

- **Prompt caching** matters most for the large *grounding context* reused across the synth → draft → fact-check → revise chain. With Anthropic cache hits at 0.1× input, the repeated ~25–30k-token grounding block in draft sessions drops from $3/MTok to $0.30/MTok on reads. Realistically this trims the **premium-draft input cost by 40–60%**, taking strategy (b)'s Sonnet portion from ~$6.45 to **~$4–5/mo**. DeepSeek caching (hit ≈ $0.0028) makes the cheap tier essentially free on repeated context.
- **Capping reflexion iterations** (e.g., max 2 revise loops, not unbounded) caps the most expensive multiplier. Each extra revise loop in a draft session adds ~28k in + 4k out at premium ≈ **+$0.14/session**; unbounded loops are how budgets silently die.
- **Capping retrieval top-k** (8 for Q&A, 12 for drafts) bounds the grounding context. Going top-k=30 would ~2.5× the synth+draft input tokens and push premium-draft input cost up proportionally.

### Where the budget breaks

| Scenario | Approx monthly | Under €50? |
|---|---|---|
| Recommended (b), with caching | ~$5–7 | Yes (huge headroom) |
| All-Anthropic, Sonnet final draft, caching | ~$8–12 | Yes |
| All-Anthropic, **Opus** final draft, caching | ~$10–18 | Yes |
| All-cheap-open | ~$1 | Yes (quality risk) |
| **(b) but final drafter = Opus, 20 drafts/mo, no caching** | ~$35–45 | Borderline |
| **Heavy user: 200 light + 30 drafts/mo, Opus draft, no caching, top-k=30, uncapped loops** | **~$120–180** | **NO — breaks** |

**Conclusion:** At the stated single-user volume, **every sensible strategy fits under €50 with large margin.** The budget only breaks under heavy volume *combined with* premium final-drafting on Opus *and* failure to cache/cap. The €50 ceiling is effectively a guardrail against runaway reflexion loops and uncapped top-k, not against model choice.

---

## 3. Concrete per-role assignment (with config hints)

| Role | BUDGET pick | Why cheapest-good-enough | Quality upgrade |
|---|---|---|---|
| **Router / intent** | DeepSeek V4-Flash | JSON/tool classification is trivial; top-tier BFCL at $0.14/$0.28. (Nova Micro $0.035/$0.14 is even cheaper if you stay AWS-native.) | Claude Haiku 4.5 |
| **Web-search worker** | DeepSeek V4-Flash | Simple tool call + summarize; cheap-open excels here. | GLM-4.7-Flash / Qwen3 |
| **Literature-search worker** | DeepSeek V4-Flash | OpenAlex/Crossref/arXiv calls are well-scoped. | Claude Haiku 4.5 |
| **RAG synthesizer** | DeepSeek V4-Flash → Qwen3-Max if quality dips | Grounded multi-doc synthesis; cheap-open fine *because* it's grounded. | **Claude Sonnet 4.6** |
| **Final drafter** | **Claude Sonnet 4.6** | Journal-grade English register + lowest fabrication risk; the artifact a journal sees. | Claude Opus 4.8 (final polish only) |
| **Fact-check / citation-verify** | Claude Sonnet 4.6 (Haiku 4.5 acceptable) | Verify pass *only works on a competent model* (§1c); do NOT run on cheapest tier. | Claude Sonnet 4.6 |
| **Embeddings** | **Titan Embed v2 (1024-d)** | $0.02/MTok, already in stack, configurable dims, normalized. | Cohere Embed v3 (English) |

**AWS-native note:** Mentis runs on Bedrock. DeepSeek and Qwen *are* available on Bedrock (Marketplace / serverless in some regions) but availability/region is uneven — defer to the parallel Bedrock-pricing/availability table. If a given cheap-open model isn't available in your Bedrock region, the **AWS-native budget fallback is the Amazon Nova family** (Nova Micro for router, Nova Lite for workers, Nova Pro for synthesis — Nova Pro scores a respectable 67.9 BFCL v3). Nova keeps everything inside Bedrock with no extra vendor/egress and still leaves the final draft on Claude.

---

## 4. Honest tradeoffs & risks

1. **Cheap-open citation fabrication is real.** DeepSeek/Qwen/GLM at the synthesis tier will sometimes invent or mis-attribute references. This is *acceptable only because* (a) synthesis is RAG-grounded to the retrieved corpus, and (b) a Claude-tier verification pass runs afterward. Remove either guardrail and the all-cheap-open strategy becomes scientifically unsafe.
2. **English register risk.** Long technical prose from DeepSeek-class models can read as "translationese." Keeping the *final* draft on Claude Sonnet/Opus is the cheapest insurance for journal-grade output. Do not put the final drafter on the cheapest tier to save ~$5/mo — the budget doesn't require it.
3. **BFCL ≠ real agentic skill for Claude.** Claude's low BFCL score is a format artifact; tau-bench (closer to Mentis's loop) shows Claude Sonnet leading. Don't over-index on BFCL when choosing the verify/draft tier.
4. **Bedrock availability + markup.** Cheap-open models may not be in your Bedrock region, and Bedrock on-demand can run ~20–35% above first-party list. If region availability is poor, the Nova fallback (or calling DeepSeek's first-party API outside Bedrock) is the lever — but mixing a non-Bedrock provider adds an outbound integration + secret to manage.
5. **Verification pass needs a capable model** (§1c) — running it on Nova Micro/DeepSeek-Flash risks "calls the tool, ignores the result." Budget for Sonnet (or at least Haiku) on that one step.
6. **The €50 budget is generous for this workload.** The genuine risk is not model unit price but **uncapped reflexion loops and large top-k** silently inflating premium-tier input tokens. Enforce: max 2 revise loops, top-k ≤ 12 for drafts, and prompt caching on the grounding block.

---

## Recommended setup (the one to ship)

- **Router + web worker + literature worker + RAG synthesizer:** DeepSeek V4-Flash (or Nova Micro/Lite/Pro if staying strictly AWS-native).
- **Final drafter + citation-verification pass:** Claude Sonnet 4.6 (escalate the *final polish only* to Opus 4.8 if a specific draft is submission-bound).
- **Embeddings:** Titan Embed v2, 1024-d (already configured).
- **Guardrails:** RAG-grounded citing only; post-hoc DOI/URL verify pass on Claude; cap reflexion to 2 loops; top-k 8 (Q&A) / 12 (draft); prompt-cache the grounding block.
- **Estimated cost at active single-user volume (88 sessions/mo): ~$5–8/month (≈ €5–7) with caching** — roughly **85–90% under the €50 ceiling.** Even an all-Anthropic-with-Opus-drafts variant stays ~$10–18/mo. The budget is safe unless usage rises ~6–10× *and* loops/top-k go uncapped.

**Citation-hallucination mitigation (the deliverable's key control):** RAG-ground all citations to the retrieved corpus → run a post-hoc DOI/URL verification pass (resolve against Crossref/OpenAlex) → run that pass on a competent model (Sonnet 4.6, not the cheapest tier), because verification only works when the model can act on tool results. Evidenced reductions: RAG grounding is the best-documented primary reducer; agentic URL/citation verification cut non-resolving citations 6–79× across models.

---

## Key sources

- DeepSeek API pricing (V4-Flash/Pro, cache) — https://api-docs.deepseek.com/quick_start/pricing
- Anthropic Claude pricing (Haiku 4.5 / Sonnet 4.6 / Opus 4.8, caching, batch) — https://platform.claude.com/docs/en/about-claude/pricing and https://benchlm.ai/blog/posts/claude-api-pricing
- Amazon Bedrock / Nova pricing — https://aws.amazon.com/bedrock/pricing/ and https://aws.amazon.com/nova/pricing/
- BFCL v3 leaderboard (GLM/Qwen/Nova/Kimi/Claude scores) — https://pricepertoken.com/leaderboards/benchmark/bfcl-v3 , https://gorilla.cs.berkeley.edu/leaderboard.html , https://llm-stats.com/benchmarks/bfcl-v3
- tau-bench agentic leaderboard (Claude Sonnet leads; GLM-Air on airline) — https://benchlm.ai/benchmarks/tauBench , https://llm-stats.com/benchmarks/tau-bench-airline , https://www.morphllm.com/claude-benchmarks
- LMArena / Chatbot Arena writing & overall ELO (Claude Opus lead; Qwen3.7-Max, GLM-5.1, Kimi K2.6 cluster) — https://benchlm.ai/blog/posts/best-chinese-llm , https://llm-stats.com/
- Citation hallucination rates — GhostCite https://arxiv.org/pdf/2602.06718 ; Lancet audit https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(26)00603-3/fulltext ; mental-health study https://www.eurekalert.org/news-releases/1106130
- Citation/URL verification mitigation (6–79× reduction; needs capable model) — https://arxiv.org/html/2604.03173v1
- RAG grounding reduces hallucination / citation reliability — VeriCite https://arxiv.org/pdf/2510.11394 ; PaperQA https://arxiv.org/pdf/2312.07559 ; groundedness study https://arxiv.org/pdf/2404.07060
- Embeddings pricing (Titan v2 vs Cohere vs OpenAI) — https://pricepertoken.com/embedding , https://aws.amazon.com/bedrock/pricing/
- Mentis internal baseline — `docs/aws-bedrock-models.md`
