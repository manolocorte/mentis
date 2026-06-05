"""Runtime configuration. All values overridable via env or a local .env file.

Model IDs default to EU cross-region inference profiles (eu.*) so they work from
eu-south-2 (Spain). VERIFY exact IDs + access in the Bedrock console once creds are live.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="", case_sensitive=False, extra="ignore"
    )

    aws_region: str = "eu-south-2"  # Spain (opt-in region, enabled); carries the full Nova + Claude catalog

    # --- Bedrock model tiers (EU inference profiles; confirm IDs in console) ---
    model_supervisor: str = "eu.amazon.nova-pro-v1:0"      # orchestration + tool use (cheap, decent)
    model_worker: str = "eu.amazon.nova-lite-v1:0"          # cheap research/summarize
    model_draft: str = "eu.anthropic.claude-sonnet-4-6"   # journal-grade prose
    model_verify: str = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"   # citation verification
    embed_model: str = "amazon.titan-embed-text-v2:0"

    # --- Research tools ---
    scopus_api_key: str | None = None
    scopus_insttoken: str | None = None  # USAL institutional token for off-campus full access
    scopus_base_url: str = "https://api.elsevier.com/content"
    contact_email: str | None = None  # OpenAlex/Unpaywall polite pool

    # --- App ---
    api_key: str | None = None
    conversation_store: str = "local"        # "local" | "dynamo"
    dynamo_table: str = "mentis"
    store_path: str = ".data/mentis.db"
    history_limit: int = 12                   # recent messages fed to the agent for continuity
    allowed_origins: str = "*"
    max_tool_steps: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
