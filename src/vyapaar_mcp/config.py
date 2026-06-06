"""Configuration management using Pydantic Settings.

All config is loaded from environment variables with the VYAPAAR_ prefix.
Secrets MUST be provided via env vars (never hardcoded).
In production, secrets are injected via Vault/K8s Secrets.
"""

from __future__ import annotations

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


class VyapaarConfig(BaseSettings):
    """Application configuration loaded from environment variables.

    All fields prefixed with VYAPAAR_ in the environment.
    Example: VYAPAAR_RAZORPAY_KEY_ID -> razorpay_key_id
    """

    model_config = SettingsConfigDict(
        env_prefix="VYAPAAR_",
        case_sensitive=False,
        env_file=".env",
        extra="ignore",
    )

    # --- Razorpay X ---
    razorpay_key_id: str = Field(description="Razorpay API Key ID")
    razorpay_key_secret: str = Field(description="Razorpay API Key Secret")
    razorpay_webhook_secret: str = Field(
        default="",
        description="Razorpay Webhook Signing Secret (optional if using polling)",
    )
    razorpay_account_number: str = Field(
        default="",
        description="RazorpayX account number for API polling (from Dashboard > My Account)",
    )

    # --- Google Safe Browsing v4 ---
    google_safe_browsing_key: str = Field(
        description="Dedicated Google Safe Browsing API Key (not a generative AI key)"
    )

    # --- Redis ---
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for atomic budget tracking",
    )

    # --- PostgreSQL ---
    postgres_dsn: str = Field(
        description="PostgreSQL connection string for audit logs/policies",
    )

    # --- Server ---
    host: str = Field(default="0.0.0.0", description="Server bind host")
    port: int = Field(default=8000, description="Server bind port")
    log_level: str = Field(default="INFO", description="Logging level")

    # --- Polling Mode (alternative to webhooks) ---
    poll_interval: int = Field(
        default=30,
        description="Polling interval in seconds for Razorpay API (5-300)",
    )
    auto_poll: bool = Field(
        default=False,
        description="Enable automatic background polling on server start",
    )
    dev_mode: bool = Field(
        default=False,
        description="Enable development mode (allows mock payouts, disables signature check)",
    )

    # --- Slack (Human-in-the-Loop) ---
    slack_bot_token: str = Field(
        default="",
        description="Slack Bot Token (xoxb-...) for approval notifications",
    )
    slack_channel_id: str = Field(
        default="",
        description="Slack Channel ID for approval requests",
    )
    slack_signing_secret: str = Field(
        default="",
        description="Slack Signing Secret for verifying interactive callbacks",
    )

    # --- Telegram (Human-in-the-Loop, alternative to Slack) ---
    telegram_bot_token: str = Field(
        default="",
        description="Telegram Bot token from @BotFather",
    )
    telegram_chat_id: str = Field(
        default="",
        description="Telegram chat/group/channel ID for approval requests",
    )

    # --- Rate Limiting ---
    rate_limit_max_requests: int = Field(
        default=10,
        description="Max payout requests per agent per window (default 10/min)",
    )
    rate_limit_window_seconds: int = Field(
        default=60,
        description="Rate limit sliding window in seconds (default 60)",
    )

    # --- Circuit Breaker ---
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        description="Consecutive failures before circuit opens",
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=30,
        description="Seconds to wait before half-open recovery attempt",
    )

    # --- Razorpay API Base ---
    razorpay_api_base: str = Field(
        default="https://api.razorpay.com/v1",
        description="Razorpay API base URL",
    )

    # --- Google Safe Browsing API ---
    safe_browsing_api_url: str = Field(
        default="https://safebrowsing.googleapis.com/v4/threatMatches:find",
        description="Google Safe Browsing Lookup API endpoint",
    )

    # --- GLEIF (Legal Entity Identifier) ---
    gleif_api_url: str = Field(
        default="https://api.gleif.org/api/v1/lei-records",
        description="GLEIF API base URL for vendor entity verification",
    )

    # --- ntfy Notifications (Slack fallback) ---
    ntfy_topic: str = Field(
        default="",
        description="ntfy topic name for push notifications (acts as Slack fallback)",
    )
    ntfy_url: str = Field(
        default="https://ntfy.sh",
        description="ntfy server URL (public ntfy.sh or self-hosted)",
    )
    ntfy_auth_token: str = Field(
        default="",
        description="ntfy auth token for protected topics (optional)",
    )

    # --- Anomaly Detection ---
    anomaly_risk_threshold: float = Field(
        default=0.75,
        description="Risk score threshold (0-1) above which transactions are flagged as anomalous",
    )

    # --- Governance Pipeline (6-layer enforcement) ---
    governance_check_gstin: bool = Field(
        default=True,
        description="Auto-reject payouts with invalid GSTIN format in notes",
    )
    governance_check_ifsc: bool = Field(
        default=True,
        description="Auto-reject payouts with invalid IFSC format",
    )
    governance_check_sanctions: bool = Field(
        default=True,
        description="Auto-reject payouts when vendor matches sanctions watchlist",
    )
    governance_check_anomaly: bool = Field(
        default=True,
        description="Hold payouts flagged as anomalous by ML scorer",
    )
    governance_sanctions_reject_score: float = Field(
        default=0.8,
        description="OpenSanctions match score above which payout is rejected",
    )
    governance_anomaly_hold: bool = Field(
        default=True,
        description="Hold (vs reject) anomalous transactions for human review",
    )
    governance_live_gst: bool = Field(
        default=False,
        description="Enable live GSTIN verification (Browserwire/GSP) in governance pipeline",
    )

    # --- Exa Search (vendor research / adverse media) ---
    exa_api_key: str = Field(
        default="",
        description="Exa API key for vendor research and adverse media screening",
    )

    # --- Browserwire (government portal APIs) ---
    browserwire_url: str = Field(
        default="",
        description="Browserwire server base URL for GST/MCA portal manifests",
    )
    browserwire_api_key: str = Field(
        default="",
        description="Browserwire API key (if required by deployment)",
    )

    # --- GSP GST API (production tier) ---
    gsp_api_url: str = Field(
        default="",
        description="GSP provider API base URL (Cashfree Secure ID, ClearTax, etc.)",
    )
    gsp_api_key: str = Field(
        default="",
        description="GSP API key for live GSTIN verification",
    )

    # --- HyperAPI (invoice OCR) ---
    hyperapi_api_key: str = Field(
        default="",
        description="HyperAPI key for invoice OCR and document extraction",
    )
    hyperapi_base_url: str = Field(
        default="https://api.hyperbots.com",
        description="HyperAPI base URL",
    )

    # --- DenchClaw CRM Integration ---
    denchclaw_url: str = Field(
        default="http://localhost:3100",
        description="DenchClaw web UI URL for CRM object sync",
    )
    denchclaw_enabled: bool = Field(
        default=True,
        description="Enable sync of audit logs and vendors to DenchClaw CRM",
    )
    denchclaw_sync_auto: bool = Field(
        default=True,
        description="Auto-sync governance decisions to DenchClaw on each audit write",
    )

    # ============================================
    # Generic LLM Configuration (LiteLLM)
    # ============================================
    # Any provider via LiteLLM: azure/xxx, openai/xxx, anthropic/xxx,
    # gemini/xxx, groq/xxx, ollama/xxx, etc.
    llm_model: str = Field(
        default="",
        description="LiteLLM model identifier (e.g. 'azure/kimi-k2.5', 'gpt-4o', 'anthropic/claude-3-opus')",
    )
    llm_api_key: str = Field(
        default="",
        description="API key for the LLM provider",
    )
    llm_base_url: str = Field(
        default="",
        description="Base URL / API endpoint override (optional, e.g. for Azure or local models)",
    )
    llm_api_version: str = Field(
        default="",
        description="API version for provider-specific endpoints (e.g. Azure)",
    )
    llm_temperature: float = Field(
        default=0.7,
        description="Default sampling temperature for chat completions",
    )
    llm_max_tokens: int = Field(
        default=2000,
        description="Default max tokens for chat completions",
    )
    delegation_llm_model: str = Field(
        default="",
        description="LiteLLM model for sub-agent delegation (defaults to llm_model or openai/gpt-4o-mini)",
    )

    # ============================================
    # Legacy Azure AI Services — backward compat
    # ============================================
    # DEPRECATED: Prefer llm_model / llm_api_key / llm_base_url above.
    # These fields are auto-mapped by _migrate_legacy_llm_config.

    azure_openai_endpoint: str = Field(
        default="",
        description="DEPRECATED: use VYAPAAR_LLM_BASE_URL. Azure AI Services endpoint.",
    )
    azure_openai_api_key: str = Field(
        default="",
        description="DEPRECATED: use VYAPAAR_LLM_API_KEY. Azure AI API key.",
    )
    azure_openai_deployment: str = Field(
        default="",
        description="DEPRECATED: use VYAPAAR_LLM_MODEL. Azure model deployment name.",
    )
    azure_foundry_project_id: str = Field(
        default="",
        description="Azure AI Foundry Project ID (optional)",
    )
    azure_openai_api_version: str = Field(
        default="2024-05-01-preview",
        description="DEPRECATED: use VYAPAAR_LLM_API_VERSION. Azure AI Services API version.",
    )

    # --- Security Proxy (Deterministic Controls) ---
    # A security proxy sits between your agent and MCP servers/LLM
    # to enforce deterministic access policies instead of probabilistic guardrails.
    security_proxy_enabled: bool = Field(
        default=False,
        description="Enable security proxy layer for deterministic security controls",
    )
    security_proxy_url: str = Field(
        default="http://localhost:9000",
        description="Security proxy URL for local proxy endpoint",
    )
    policy_set_id: str = Field(
        default="",
        description="Policy set ID defining allow/deny rules",
    )

    # --- Azure Foundry Guardrails (Probabilistic - Use with caution) ---
    # Note: Azure's probabilistic guardrails can be bypassed.
    # We recommend deterministic controls for production.
    azure_guardrails_enabled: bool = Field(
        default=False,
        description="Enable Azure guardrails (jailbreak, prompt injection)",
    )
    azure_guardrails_severity: int = Field(
        default=1,
        description="Moderation severity threshold: 0=low, 1=medium, 2=high",
    )

    # ============================================
    # Dual LLM Quarantine Pattern (Security Layer)
    # ============================================
    # Reference: Dual LLM Quarantine Pattern
    #
    # The Dual LLM pattern defends against the "lethal trifecta":
    # - Indirect prompt injection via untrusted tool outputs
    # - Sensitive data leakage through compromised context
    # - Task drift caused by malicious instructions embedded in data

    # --- Context Tainting ---
    taint_sources: str = Field(
        default="handle_razorpay_webhook,poll_razorpay_payouts,check_vendor_reputation,verify_vendor_entity,score_transaction_risk",
        description="Comma-separated list of tools that mark context as untrusted",
    )

    # --- Dual LLM Validation Tier ---
    dual_llm_tools: str = Field(
        default="poll_razorpay_payouts,score_transaction_risk",
        description="Tools requiring security LLM validation when context is tainted",
    )

    # --- Security LLM Configuration (Generic) ---
    security_llm_model: str = Field(
        default="",
        description="Security validation LLM model identifier (LiteLLM format)",
    )
    security_llm_api_key: str = Field(
        default="",
        description="API key for security LLM",
    )
    security_llm_base_url: str = Field(
        default="",
        description="Base URL for security LLM",
    )

    # Legacy aliases (auto-mapped by _migrate_legacy_llm_config)
    security_llm_url: str = Field(
        default="http://localhost:9001/v1",
        description="DEPRECATED: use VYAPAAR_SECURITY_LLM_BASE_URL. Security LLM endpoint.",
    )
    security_llm_key: str = Field(
        default="",
        description="DEPRECATED: use VYAPAAR_SECURITY_LLM_API_KEY. Security LLM API key.",
    )
    dual_llm_max_rounds: int = Field(
        default=5,
        description="Max validation rounds before forcing deny (prevents loops)",
    )

    # --- Quarantine Enforcement ---
    quarantine_strict: bool = Field(
        default=True,
        description="Strict mode: if security LLM fails/unavailable, DENY the tool call",
    )
    quarantine_audit_log: bool = Field(
        default=True,
        description="Log all security LLM validation decisions for audit",
    )


    @model_validator(mode="after")
    def _migrate_legacy_llm_config(self) -> Self:
        """Auto-map legacy Azure OpenAI / dual-LLM fields to generic keys."""
        # --- Primary LLM migration ---
        if not self.llm_model and self.azure_openai_deployment:
            self.llm_model = f"azure/{self.azure_openai_deployment}"
        if not self.llm_api_key and self.azure_openai_api_key:
            self.llm_api_key = self.azure_openai_api_key
        if not self.llm_base_url and self.azure_openai_endpoint:
            self.llm_base_url = self.azure_openai_endpoint
        if not self.llm_api_version and self.azure_openai_api_version:
            self.llm_api_version = self.azure_openai_api_version

        # --- Delegation LLM default ---
        if not self.delegation_llm_model and self.llm_model:
            self.delegation_llm_model = self.llm_model
        elif not self.delegation_llm_model:
            self.delegation_llm_model = "openai/gpt-4o-mini"

        # --- Security LLM migration ---
        if not self.security_llm_model:
            self.security_llm_model = self.delegation_llm_model
        elif "/" not in self.security_llm_model:
            # Old plain model names (e.g. "gpt-4o-mini") default to openai provider
            self.security_llm_model = f"openai/{self.security_llm_model}"
        if not self.security_llm_api_key and self.security_llm_key:
            self.security_llm_api_key = self.security_llm_key
        if not self.security_llm_base_url and self.security_llm_url:
            default_url = "http://localhost:9001/v1"
            if self.security_llm_url != default_url:
                self.security_llm_base_url = self.security_llm_url
            else:
                self.security_llm_base_url = default_url
        return self

def load_config() -> VyapaarConfig:
    """Load and validate configuration from environment."""
    return VyapaarConfig()  # type: ignore[call-arg]
