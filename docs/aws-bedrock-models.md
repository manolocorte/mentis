# AWS Bedrock Model Recommendations for Mentis

## Selected Models

### Chat / LLM — `anthropic.claude-sonnet-4-20250514`

**Why Claude Sonnet 4:**
- Best price/performance ratio for research tasks (vs Opus which is 5x more expensive)
- Strong at structured output (JSON intent classification), citation handling, academic writing
- 200K context window — handles large prompt contexts with many retrieved chunks
- ~$3/M input tokens, ~$15/M output tokens

**Alternatives:**
- `anthropic.claude-haiku-4-5-20251001` — 10x cheaper, good for intent classification only. Could use as a cost optimization: Haiku for classification, Sonnet for synthesis/drafting.
- `anthropic.claude-opus-4-20250514` — highest quality but $15/$75 per M tokens. Only worth it for final paper drafting where quality is critical.
- `amazon.nova-pro-v1:0` — Amazon's own model, cheaper but weaker at academic writing and citation handling.

### Embeddings — `amazon.titan-embed-text-v2:0`

**Why Titan Embed v2:**
- $0.02/M tokens — 5x cheaper than OpenAI ada-002
- Supports configurable dimensions (256, 512, 1024) — we use 1024
- Good multilingual support (relevant for Spanish/English research)
- Normalized embeddings out of the box

**Alternatives:**
- `cohere.embed-english-v3` — slightly better quality for English-only, similar price
- `cohere.embed-multilingual-v3` — better for mixed-language corpora

## Cost Estimates (Light Research Use)

| Task | Model | Tokens/query | Queries/month | Monthly cost |
|------|-------|-------------|---------------|-------------|
| Intent classification | Sonnet | ~500 | 200 | $0.30 |
| RAG synthesis | Sonnet | ~3,000 | 150 | $2.50 |
| Literature review | Sonnet | ~5,000 | 20 | $1.00 |
| Paper drafting | Sonnet | ~8,000 | 10 | $1.20 |
| Fact checking | Sonnet | ~3,000 | 30 | $0.50 |
| Gap analysis | Sonnet | ~2,000 | 50 | $0.50 |
| Embeddings | Titan v2 | ~1,000 | 500 | $0.01 |
| **Total** | | | | **~$6/month** |

## Configuration

In `.env`:
```
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_CHAT_MODEL=anthropic.claude-sonnet-4-20250514
BEDROCK_EMBED_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_EMBED_DIM=1024
```

Ensure AWS credentials are configured:
```bash
aws configure
# Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env
```

## Bedrock Model Access

You need to **request access** to models in the AWS console before using them:
1. Go to **Amazon Bedrock** → **Model access**
2. Enable: `Anthropic Claude Sonnet 4`, `Amazon Titan Text Embeddings V2`
3. Access is usually granted instantly for these models
