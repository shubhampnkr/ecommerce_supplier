"""
Central configuration – all values sourced from environment / .env file.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Meesho ────────────────────────────────────────────────────────────────
    meesho_email: str
    meesho_password: str
    meesho_supplier_id: str = ""

    # Meesho supplier portal URL constants
    meesho_login_url: str = "https://supplier.meesho.com/login"
    meesho_dashboard_url: str = "https://supplier.meesho.com/dashboard"

    # ── LLM ───────────────────────────────────────────────────────────────────
    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_model_anthropic: str = "claude-opus-4-5"
    llm_model_openai: str = "gpt-4o"
    llm_temperature: float = 0.2

    # ── Email / SMTP ──────────────────────────────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    report_recipient_email: str
    report_cc_emails: str = ""  # comma-separated

    @property
    def cc_list(self) -> list[str]:
        return [e.strip() for e in self.report_cc_emails.split(",") if e.strip()]

    # ── Report ────────────────────────────────────────────────────────────────
    report_download_dir: Path = Path("./reports/downloads")
    report_schedule_time: str = "08:00"
    report_timezone: str = "Asia/Kolkata"

    # ── Browser ───────────────────────────────────────────────────────────────
    headless: bool = True
    browser_timeout: int = 60_000
    slow_mo: int = 0

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_dir: Path = Path("./logs")

    @field_validator("report_download_dir", "log_dir", mode="before")
    @classmethod
    def _make_dir(cls, v):
        p = Path(v)
        p.mkdir(parents=True, exist_ok=True)
        return p


# Singleton
settings = Settings()  # type: ignore[call-arg]
