"""Centralized settings, loaded from environment with SSM resolution in Lambda.

All infrastructure is pay-per-use: DynamoDB (single table), S3 Vectors (semantic
search), S3 (documents), SQS (ingestion), Bedrock (LLM + embeddings). Nothing here
assumes an always-on resource.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    app_env: str = Field(default="dev")

    # --- AWS / region ---
    aws_region_name: str = Field(default="us-east-1")

    # --- DynamoDB (single-table) ---
    table_name: str = Field(default="mentis-dev")

    # --- S3 ---
    documents_bucket: str = Field(default="mentis-dev-documents")

    # --- S3 Vectors ---
    vector_bucket: str = Field(default="mentis-dev-vectors")
    vector_index_chunks: str = Field(default="chunks")
    vector_index_memory: str = Field(default="memory")

    # --- SQS ---
    ingest_queue_url: Optional[str] = Field(default=None)

    # --- Bedrock models (tiered for cost) ---
    bedrock_region: str = Field(default="us-east-1")
    bedrock_router_model: str = Field(default="anthropic.claude-haiku-4-5-20251001")
    bedrock_chat_model: str = Field(default="anthropic.claude-sonnet-4-6")
    bedrock_draft_model: str = Field(default="anthropic.claude-opus-4-8")
    bedrock_embed_model: str = Field(default="amazon.titan-embed-text-v2:0")
    bedrock_embed_dim: int = Field(default=1024)

    # --- Auth ---
    api_key: Optional[str] = Field(default=None)
    api_key_ssm: Optional[str] = Field(default=None)

    # --- Scraper / sources ---
    unpaywall_email: Optional[str] = Field(default=None)
    unpaywall_email_ssm: Optional[str] = Field(default=None)
    # University source (added later): API key + optional base URL.
    university_api_key: Optional[str] = Field(default=None)
    university_api_key_ssm: Optional[str] = Field(default=None)
    university_base_url: Optional[str] = Field(default=None)

    log_level: str = Field(default="INFO")

    # Agentic loop bounds (cost guardrails)
    max_reflexion_iterations: int = Field(default=2)
    retrieve_top_k: int = Field(default=8)


def _resolve_ssm(settings: Settings) -> None:
    """Resolve any *_ssm parameter paths into their concrete values (Lambda)."""
    pairs = [
        ("api_key_ssm", "api_key"),
        ("unpaywall_email_ssm", "unpaywall_email"),
        ("university_api_key_ssm", "university_api_key"),
    ]
    names = {getattr(settings, src): dst for src, dst in pairs if getattr(settings, src)}
    if not names:
        return
    try:
        import boto3

        ssm = boto3.client("ssm", region_name=settings.aws_region_name)
        resp = ssm.get_parameters(Names=list(names.keys()), WithDecryption=True)
        for param in resp.get("Parameters", []):
            dst = names.get(param["Name"])
            if dst:
                object.__setattr__(settings, dst, param["Value"])
    except Exception as exc:  # local dev / no SSM access — fall back to env values
        logger.debug("SSM resolution skipped: %s", exc)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _resolve_ssm(settings)
    logging.getLogger("mentis").setLevel(settings.log_level.upper())
    return settings


__all__ = ["Settings", "get_settings"]
