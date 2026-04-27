from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

from .models import ICP, Offer


class BeReachConfig(BaseModel):
    api_key: str = Field(default_factory=lambda: os.getenv("BEREACH_API_KEY", ""))
    # Public SDK exposes api.bereach.ai; spec may use api.berea.ch. Keep configurable.
    base_url: str = "https://api.bereach.ai"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    jitter_min_seconds: float = 3.0
    jitter_max_seconds: float = 8.0
    delay_between_connections_min_seconds: float = 5.0
    delay_between_connections_max_seconds: float = 10.0
    daily_connection_limit: int = 12
    weekly_connection_limit: int = 60
    daily_profile_visit_limit: int = 60
    working_hours_only: bool = True
    weekend_pause: bool = True
    dry_run: bool = False

    @field_validator("base_url")
    @classmethod
    def no_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")


class GoogleConfig(BaseModel):
    service_account_file: str = Field(default_factory=lambda: os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""))
    spreadsheet_id: str = ""
    spreadsheet_title: str = ""
    drive_folder_name: str = "Client-CRM"
    prospects_tab: str = "PROSPECTS"
    rejected_tab: str = "REJETES"


class DeliveryConfig(BaseModel):
    channel: str = "telegram"  # telegram | discord | none
    telegram_bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = ""
    discord_webhook_url: str = Field(default_factory=lambda: os.getenv("DISCORD_WEBHOOK_URL", ""))


class LLMConfig(BaseModel):
    provider: str = "openrouter"  # openrouter | none
    api_key: str = Field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "qwen/qwen3-coder:free"
    temperature: float = 0.1
    enabled: bool = True


class HermesConfig(BaseModel):
    profile_slug: str = ""
    install_skills: bool = True
    cron_schedule: str = "0 6 * * 1-5"
    delivery_target: str = "telegram"


class ClientConfig(BaseModel):
    client_name: str
    slug: str
    icp: ICP
    offre: Offer
    bereach: BeReachConfig = Field(default_factory=BeReachConfig)
    google: GoogleConfig = Field(default_factory=GoogleConfig)
    delivery: DeliveryConfig = Field(default_factory=DeliveryConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    hermes: HermesConfig = Field(default_factory=HermesConfig)

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        return value.lower().strip().replace(" ", "-")


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_config(path: str | Path) -> ClientConfig:
    file_path = Path(path).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Config introuvable: {file_path}")
    data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
    data = _expand_env(data)
    try:
        cfg = ClientConfig.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Config invalide dans {file_path}:\n{exc}") from exc
    if not cfg.hermes.profile_slug:
        cfg.hermes.profile_slug = cfg.slug
    if not cfg.google.spreadsheet_title:
        cfg.google.spreadsheet_title = f"{cfg.client_name} - CRM PROSPECTION"
    return cfg


def save_config(cfg: ClientConfig, path: str | Path) -> None:
    file_path = Path(path).expanduser().resolve()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        yaml.safe_dump(cfg.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
