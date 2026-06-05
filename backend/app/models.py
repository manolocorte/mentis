"""Bedrock model factory — one helper per cost tier, plus a direct Converse helper
(with model fallback) used by the Validator.
"""
from __future__ import annotations

import boto3
from strands.models.bedrock import BedrockModel

from .config import get_settings

_client = None


def _runtime():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name=get_settings().aws_region)
    return _client


def converse_text(system: str, prompt: str, model_ids: list[str], *, max_tokens: int = 600) -> str:
    """Single non-streaming Converse call; tries each model in order (Claude → Nova fallback)."""
    cl = _runtime()
    last: Exception | None = None
    for mid in model_ids:
        try:
            r = cl.converse(
                modelId=mid,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": max_tokens, "temperature": 0.0},
            )
            return r["output"]["message"]["content"][0]["text"]
        except Exception as e:  # noqa: BLE001
            last = e
    raise last if last else RuntimeError("no models configured")


def validator_models() -> list[str]:
    s = get_settings()
    return [s.model_verify, s.model_worker]  # Claude Haiku → Nova Lite fallback


def _model(model_id: str, *, temperature: float, max_tokens: int) -> BedrockModel:
    s = get_settings()
    return BedrockModel(
        model_id=model_id,
        region_name=s.aws_region,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=True,
    )


def supervisor_model() -> BedrockModel:
    return _model(get_settings().model_supervisor, temperature=0.2, max_tokens=1500)


def worker_model() -> BedrockModel:
    return _model(get_settings().model_worker, temperature=0.2, max_tokens=1500)


def draft_model() -> BedrockModel:
    return _model(get_settings().model_draft, temperature=0.3, max_tokens=4000)


def verify_model() -> BedrockModel:
    return _model(get_settings().model_verify, temperature=0.0, max_tokens=800)
