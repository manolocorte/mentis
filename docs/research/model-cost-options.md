# Cost-Effective LLM Options for Mentis on AWS Bedrock / AgentCore

**Use case:** Agentic, single-user scientific whitepaper research + writing assistant. Must run on AWS (Bedrock / AgentCore), stay **under €50/month**, prefer EU data residency (Spanish university research data), and consider cheaper non-Anthropic / Chinese / open-weight alternatives.

**Date compiled:** 2026-06-05. All prices are USD per 1M tokens, on-demand "Standard" tier, unless noted. **€50 ≈ $54** at ~1.08 USD/EUR — budget the stack against roughly **$52/month** to be safe.

> Verification note: prices and region availability were checked against AWS's own model cards and pricing/announcement pages where possible. Third-party aggregators were used only to corroborate. Where AWS docs and third parties disagreed, the AWS doc wins and is flagged.

---

## 1. Comparison table — models GA on Bedrock (serverless, pay-per-token)

| Model | Host / status | $ in /1M | $ out /1M | Context | Tool use? | EU available? | Notes |
|---|---|---|---|---|---|---|---|
| **Claude Haiku 4.5** | Bedrock GA serverless | 1.00 | 5.00 | 200K | Yes (best-in-class) | Yes — Frankfurt + EU Geo profile | Cheapest strong-agent Claude. Prompt caching supported. |
| **Claude Sonnet 4.5 / 4.6** | Bedrock GA serverless | 3.00 | 15.00 | 200K (1M beta) | Yes (best-in-class) | Yes — Frankfurt + EU Geo | Quality default for writing; pricey at volume. |
| **Claude Opus 4.5 / 4.6 / 4.8** | Bedrock GA serverless | 5.00 | 25.00 | 200K | Yes | Yes — EU Geo profile (`eu.anthropic.*`) | Overkill for single-user budget. |
| **Amazon Nova Micro** | Bedrock GA serverless | 0.035–0.08* | 0.14–0.32* | 128K | Yes | Yes — EU Geo | Cheapest text model on Bedrock. *Pricing varies by region/source; AWS US-East page shows 0.08/0.32, aggregators cite 0.035/0.14.* |
| **Amazon Nova Lite** | Bedrock GA serverless | 0.06–0.30* | 0.24–1.20* | 300K | Yes | Yes — EU Geo | Multimodal, very cheap, 300K context. Prompt caching supported. |
| **Amazon Nova Pro** | Bedrock GA serverless | 0.80 | 3.20 | 300K | Yes | Yes — EU Geo | Strong price/quality; caching supported, no cache-write surcharge. |
| **Amazon Nova Premier** | Bedrock GA serverless | 1.20 (US) | 4.80 (US) | 1M | Yes | Limited — check region | Frontier Nova; teacher model for distillation. |
| **DeepSeek V3.2** | Bedrock GA serverless | 0.62 | 1.85 | 164K | Yes (Converse) | **EU: Stockholm + London ONLY** (In-Region; **no Geo/Global**) | Best reasoning $/token. Launched Dec 2025. Max output only 8K. |
| **DeepSeek V3.1 / R1** | Bedrock GA serverless | ~low | ~low | 128K | V3.1 tool-calling was flaky in Converse early on | Frankfurt/London/Stockholm | Superseded by V3.2 for most uses. |
| **Qwen3 Coder Next** | Bedrock GA serverless | 0.60 | 1.44 | 256K | Yes (Converse, MCP) | **EU: Frankfurt, Ireland, Milan, Stockholm, London** (In-Region; **no Geo/Global**) | Cheapest agentic open model with broad EU coverage. 16K max output. |
| **Qwen3 235B / 32B** | Bedrock GA serverless | low | low | 256K | Yes | Ireland, London, Milan, Stockholm | Frankfurt not listed for all variants — verify per model. |
| **MiniMax M2.1** | Bedrock GA serverless (Feb 2026) | n/p | n/p | large | Yes (coding/agentic) | Verify in console | Added via Project Mantle batch. |
| **GLM 4.7 / 4.7 Flash** (Zhipu) | Bedrock GA serverless (Feb 2026) | n/p | n/p | large | Yes | Verify in console | Flash = cost-efficient tier. |
| **Kimi K2.5** (Moonshot) | Bedrock GA serverless (Feb 2026) | n/p | n/p | large | Yes (reasoning) | Verify in console | Reasoning-focused. |
| **Meta Llama 3.x / 4** | Bedrock GA serverless | low | low | up to 128K+ | Yes | Yes (several EU regions) | Open-weight, decent value; Qwen3/DeepSeek generally better $/quality for this task now. |
| **Mistral (Large/Small)** | Bedrock GA serverless | varies | varies | 32K–128K | Yes | Yes — EU regions, EU-headquartered vendor | Good GDPR-story alternative if you want a European vendor. |
| **Cohere Command** | Bedrock GA serverless | varies | varies | 128K | Yes | Yes — EU | Contractually won't train on customer data. |
| **AI21 Jamba** | Bedrock GA serverless | low | low | up to 256K | Limited | Yes | Niche; not recommended here. |

\* Nova low-tier per-token pricing is inconsistent across sources. The AWS pricing page (US East) showed **Micro 0.08/0.32, Lite 0.30/1.20** at fetch time; multiple aggregators cite the older/other-region **Micro 0.035/0.14, Lite 0.06/0.24**. Confirm in the Bedrock console for your chosen EU region before relying on it. Either way Nova is the cheapest tier.

`n/p` = AWS has not published per-token pricing on the public pricing page yet for the Feb-2026 Project Mantle batch (MiniMax M2.1, GLM 4.7/Flash, Kimi K2.5); pull live rates from the Bedrock console / pricing page.

### Critical regional caveat (verified against AWS model cards)
The Chinese open-weight serverless models on Bedrock are **In-Region only — they do NOT support EU Geo cross-region inference or Global cross-region inference**. This was confirmed on the official model cards:
- **DeepSeek V3.2** EU regions = **Stockholm (eu-north-1), London (eu-west-2)** only. (No Frankfurt, no Ireland, no Paris, no Spain.)
- **Qwen3 Coder Next** EU regions = **Frankfurt, Ireland, Milan, Stockholm, London**. (No Paris, no Spain.)

Anthropic Claude and Amazon Nova, by contrast, DO support the **EU Geo cross-region inference profile** (`eu.*` model IDs), which keeps routing inside the EU geography while giving higher throughput.

---

## 2. Access paths for models NOT natively serverless on Bedrock

| Path | What it is | Cost reality for single-user €50/mo |
|---|---|---|
| **Bedrock serverless (GA)** | Fully managed, pay-per-token, no infra. | ✅ Ideal. This is where DeepSeek V3.2, Qwen3, Nova, Claude all live. |
| **Bedrock Marketplace** | Deploy a model card to a **dedicated managed endpoint** (you pay per-hour for the instance). | ❌ A single GPU endpoint runs ~$1–12+/hr = hundreds–thousands/mo. Blows the budget for one user. |
| **Bedrock Custom Model Import** | Import open-weight fine-tunes; serverless-style billing for supported architectures, but with cold-start / min-capacity charges. | ⚠️ Only if a model you need isn't GA. Watch idle/min-capacity costs. |
| **SageMaker JumpStart** | One-click deploy to a SageMaker endpoint (you own the instance). | ❌ Same per-hour GPU economics as Marketplace. Not for one user. |
| **External API from AgentCore Runtime** | Your agent (running in AgentCore, GA in Frankfurt/Ireland/Paris/Stockholm/London) calls DeepSeek/Qwen/OpenRouter/Together/Fireworks over HTTPS. | ⚠️ Cheapest raw tokens, but **data leaves AWS** and (for a Chinese vendor's own API) **leaves the EU / goes to China**. See governance verdict. |

**Bottom line:** For a single user on €50/mo, **only Bedrock serverless pay-per-token is economically viable.** Any path that provisions a GPU (Marketplace, JumpStart, most Custom Model Import) will exceed the budget many times over even if idle.

---

## 3. EU region recommendation

Account default is **eu-north-1 (Stockholm)** which historically had a thinner Bedrock catalog but is now surprisingly well-positioned because it carries **both DeepSeek V3.2 and Qwen3** in-region, plus Claude and Nova.

| Region | Claude (Geo) | Nova | DeepSeek V3.2 | Qwen3 Coder Next | AgentCore |
|---|---|---|---|---|---|
| eu-central-1 Frankfurt | ✅ | ✅ | ❌ | ✅ | ✅ |
| eu-west-1 Ireland | ✅ | ✅ | ❌ | ✅ | ✅ |
| eu-west-3 Paris | ✅ (Geo) | ✅ | ❌ | ❌ | ✅ |
| eu-south-2 Spain | partial | partial | ❌ | ❌ | check |
| **eu-north-1 Stockholm** | ✅ | ✅ | **✅** | **✅** | ✅ |
| eu-west-2 London (non-EU post-Brexit) | ✅ | ✅ | ✅ | ✅ | ✅ |

**Recommendation:**
- **If you want the cheapest Chinese open-weight models in-region AND a single region: stay on eu-north-1 (Stockholm).** It uniquely covers DeepSeek V3.2 + Qwen3 + Claude (Geo) + Nova + AgentCore, and it is a genuine EU member-state region (good for Spanish university data residency under GDPR).
- **If you prioritize the richest Claude/Nova catalog and lowest latency to Spain: eu-central-1 (Frankfurt) or eu-west-1 (Ireland).** Both have Claude (EU Geo), Nova, Qwen3, and AgentCore — but **not** DeepSeek V3.2. Frankfurt has the broadest overall model selection.
- **Avoid London (eu-west-2) for university data residency:** the UK is outside the EU/EEA, so it's a third-country transfer under GDPR even though AWS labels it "Europe."
- **Spain (eu-south-2)** is attractive for residency but has the thinnest catalog — don't pin the architecture to it.

**Net:** Use **eu-north-1 (Stockholm)** as the primary if DeepSeek V3.2 matters; otherwise **eu-central-1 (Frankfurt)** for the broadest catalog. Both keep data in the EU.

---

## 4. Data governance verdict (the key distinction)

**This is the single most important point for university data.**

- **Running a Chinese OPEN-WEIGHT model (DeepSeek, Qwen, GLM, Kimi, MiniMax) as a fully managed serverless model ON Amazon Bedrock = SAFE for university research data.** AWS hosts the model weights inside AWS infrastructure. AWS states plainly: *"Users' inputs and model outputs aren't shared with any model providers,"* content is *"not used to improve the base models,"* and data is *encrypted in transit and at rest*. **No data is sent to DeepSeek, Alibaba, Zhipu, Moonshot, or any servers in China.** You also get Bedrock Guardrails, IAM, CloudTrail, and (when you pick an EU region) EU data residency.

- **Calling a Chinese vendor's HOSTED API directly (e.g., api.deepseek.com, Alibaba DashScope, Moonshot) = NOT safe for university data.** Your prompts and documents are transmitted to that vendor's servers, typically in China, under their terms — outside the EU, outside GDPR-compliant control, and potentially used for training. **Do not do this with research data.**

**Plain verdict:** It is perfectly fine — and cost-effective — to use DeepSeek V3.2 or Qwen3 **on Bedrock in an EU region**. It is NOT fine to call the same models via their native Chinese-hosted APIs. The model's national origin is irrelevant once the weights run inside AWS EU; what matters is where inference happens and who sees the data. Same logic applies to the "external API from AgentCore" path — only use it with EU/US providers you trust (and never for sensitive data without a DPA).

---

## 5. Embeddings (cheapest good options on Bedrock)

| Model | Host | $ /1M tokens | Dims | Quality (MTEB-ish) | Notes |
|---|---|---|---|---|---|
| **Amazon Titan Text Embeddings V2** | Bedrock | **$0.20** (≈$0.02/1M per some sources — see note) | up to 1024 (256/512/1024) | ~OpenAI 3-small level | Cheapest on Bedrock; EU in-region; English-strong. |
| **Cohere Embed (Multilingual / v3/v4)** | Bedrock | **$1.00** (input) | 1024 | Top tier, ~65 MTEB v2; 100+ languages | 5× cost of Titan but best multilingual + hybrid (dense+sparse). |
| **BGE-M3 (open weight)** | Self-host / SageMaker | infra cost only | 1024 | ~63 MTEB; 100+ langs; hybrid | Free weights but needs an endpoint — GPU cost kills the budget for one user. |
| **Qwen embeddings (open)** | Self-host | infra cost only | varies | Strong | Same self-host cost problem. |

> Titan V2 price note: AWS lists Titan Text Embeddings V2 at **$0.00002 per 1K tokens = $0.02 per 1M tokens** on the pricing page; one aggregator restated it as "$0.20 per 1M." The AWS unit ($0.02/1M) is the authoritative figure — verify in console. Either way Titan is dramatically cheaper than Cohere.

**Recommendation:** For a scientific assistant where source papers and queries may be in Spanish + English (and citations in other languages), **Cohere Embed Multilingual** is worth the 5× premium for cross-lingual retrieval quality. If your corpus is overwhelmingly English, **Titan V2** is the budget pick and embeddings cost will be negligible (cents/month at single-user scale). Do **not** self-host BGE/Qwen for one user — the GPU endpoint cost dwarfs API embedding cost.

---

## 6. Prompt caching on Bedrock

- **Supported models:** Amazon Nova (Micro, Lite, Pro), Anthropic Claude (3.5 Haiku, 3.7 Sonnet, and the 4.x family: Haiku 4.5, Sonnet 4.5/4.6, Opus 4.5/4.6). Open-weight Chinese models: caching support not yet documented on their cards — assume **no** until confirmed.
- **Discount:** **Cache reads ~90% cheaper** than normal input tokens. Example (Claude Sonnet 4.5): normal input $3.00/1M → **cache read $0.10/1M; cache write $1.25/1M**.
- **Cost-model difference:** **Anthropic** charges extra for cache *writes* (~25% premium). **Amazon Nova** has **no cache-write surcharge** — caching is essentially free upside on Nova.
- **Minimum checkpoint size:** Claude 3.7 Sonnet ≥1,024 tokens; Claude 4.x (Opus 4.5/4.6, Haiku 4.5, Sonnet 4.5) ≥4,096 tokens per checkpoint.
- **Why it matters for Mentis:** A research assistant re-sends the same large system prompt + retrieved paper context across turns. Caching that prefix can cut input cost ~90%, which is the single biggest lever for staying under €50/mo when using Claude.

---

## Cheapest viable stack (recommended)

**Goal: maximum quality per euro, EU-resident, agentic, < €50/mo for one user.**

**Tier-it by job (model routing):**
1. **Default / heavy reasoning + agent loop:** **DeepSeek V3.2** ($0.62/$1.85) in **eu-north-1 Stockholm**, OR **Qwen3 Coder Next** ($0.60/$1.44) in **Frankfurt/Stockholm**. Both support Converse tool-use and cost ~5–8× less than Claude Sonnet. Data stays in AWS EU.
2. **High-stakes final writing / nuanced synthesis:** **Claude Haiku 4.5** ($1/$5) or selectively **Sonnet 4.5** ($3/$15) via the **EU Geo profile**, **with prompt caching** on the system prompt + paper context (cache reads $0.10/1M). Use sparingly for final passes only.
3. **Cheap bulk classification / routing / summaries:** **Amazon Nova Lite or Micro** (cents/1M), EU Geo, caching free.
4. **Embeddings (RAG over papers):** **Cohere Embed Multilingual** ($1/1M) if Spanish+multilingual corpus; **Titan V2** (~$0.02–0.20/1M) if mostly English. Cost is negligible at single-user scale.
5. **Orchestration:** **AgentCore Runtime** (GA in Frankfurt, Ireland, Paris, Stockholm, London) calling Bedrock models in-region — no data leaves AWS.

**Why this fits €50/mo:** A single user generating, say, ~5M input + ~1M output tokens/month of agent traffic on DeepSeek V3.2/Qwen3 costs roughly **$3–9/month**. Reserving Claude (with caching) for final writing adds a few more dollars. Embeddings are pennies. You stay comfortably under budget with quality headroom.

**Single-region simplest answer:** **eu-north-1 (Stockholm)** — it is the only EU member-state region that carries DeepSeek V3.2 + Qwen3 + Claude (Geo) + Nova + AgentCore together, giving you the full cheap-to-premium ladder in one GDPR-compliant region.

---

## Key source URLs

- Amazon Bedrock pricing — https://aws.amazon.com/bedrock/pricing/
- DeepSeek on Bedrock (overview) — https://aws.amazon.com/bedrock/deepseek/
- DeepSeek-R1 fully managed serverless (data-privacy statement) — https://aws.amazon.com/blogs/aws/deepseek-r1-now-available-as-a-fully-managed-serverless-model-in-amazon-bedrock/
- DeepSeek-V3.1 on Bedrock — https://aws.amazon.com/blogs/aws/deepseek-v3-1-now-available-in-amazon-bedrock/
- DeepSeek V3.2 model card (regions: Stockholm/London EU; In-Region only; Converse) — https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-deepseek-deepseek-v3-2.html
- Qwen on Bedrock (overview) — https://aws.amazon.com/bedrock/qwen/
- Qwen3 Coder Next model card (regions incl. Frankfurt/Ireland/Milan/Stockholm/London; In-Region only) — https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-qwen-qwen3-coder-next.html
- Qwen3 fully managed on Bedrock — https://aws.amazon.com/about-aws/whats-new/2025/09/qwen3-models-fully-managed-amazon-bedrock/
- Six new open-weight models (DeepSeek V3.2, MiniMax M2.1, GLM 4.7/Flash, Kimi K2.5, Qwen3 Coder Next) — https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-bedrock-adds-support-six-open-weights-models/
- Serverless third-party model terms (data handling) — https://aws.amazon.com/legal/bedrock/third-party-models/
- Regional availability (models by region) — https://docs.aws.amazon.com/bedrock/latest/userguide/models-region-compatibility.html
- Prompt caching (docs) — https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html
- Prompt caching (product page) — https://aws.amazon.com/bedrock/prompt-caching/
- Titan Text Embeddings — https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html
- AgentCore supported regions — https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-regions.html
- AgentCore GA — https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/
- Claude Haiku 4.5 model card — https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html
- Claude Sonnet 4.6 model card — https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-4-6.html

---

## Caveats / things to verify in the AWS console before committing

1. **Nova low-tier per-token pricing** differs across sources (Micro 0.035 vs 0.08 in). Confirm for your EU region.
2. **Feb-2026 Project Mantle models** (MiniMax M2.1, GLM 4.7/Flash, Kimi K2.5) — per-token prices not yet on the public pricing page; pull live.
3. **DeepSeek/Qwen tool-use in Converse:** DeepSeek V3.1 had `tool_choice` gaps early in Converse. V3.2 and Qwen3 Coder Next list Converse support, but **smoke-test tool-calling reliability** before building the agent loop on them — Claude/Nova remain the most robust tool-callers.
4. **Titan V2 embedding unit price** ($0.02 vs $0.20 per 1M) — confirm in console.
5. **Chinese open-weight models do not support EU Geo/Global cross-region** — you are pinned to specific in-region availability. Plan capacity/quotas accordingly.
