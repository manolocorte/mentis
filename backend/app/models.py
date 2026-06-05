"""Bedrock model factory — one helper per cost tier."""
from __future__ import annotations

from strands.models.bedrock import BedrockModel

from .config import get_settings


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
