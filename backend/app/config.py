"""
Centralised application settings, loaded from environment variables (.env).

Keeping all configuration here — rather than scattered os.getenv() calls —
is what lets us validate required settings once at startup and keeps
secrets out of source code (OWASP A05:2021 - Security Misconfiguration).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/mindsync"
    db_pool_size: int = 10          # connections kept open and ready (see app/database.py: _engine_options)
    db_max_overflow: int = 10       # extra connections allowed during a burst

    # Auth
    jwt_secret: str = "change-me-to-a-long-random-value"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Experimental task-fit model (app/ml). OFF by default: it was trained on SIMULATED data, so letting it
    # change the ranking would add our own assumptions with no real evidence behind them. The ranking is then
    # the transparent formula only. Set ML_ENABLED=true to try the blend; ml_weight is the model's share of
    # the final score (0 = pure formula, 1 = pure model).
    ml_enabled: bool = False
    ml_weight: float = 0.3

    # Rank tasks by work pressure (how much work is left vs time left) as well as deadline and energy fit.
    # False = the original deadline + energy heuristic only (kept as the evaluation baseline).
    smart_ranking: bool = True

    # Email deadline alerts. Leave smtp_host blank to run WITHOUT a mail server:
    # the alert emails are then saved as .eml files in backend/outbox instead of being sent.
    reminders_enabled: bool = True
    reminder_hours_before: int = 48          # alert when a deadline is within this many hours
    reminder_check_minutes: int = 15         # how often the background check runs
    task_reminders_enabled: bool = True      # Update 28: the Settings page e-mail reminders (off for a student until they switch them on)
    task_reminder_check_minutes: int = 5
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""                      # defaults to smtp_user when blank
    smtp_starttls: bool = True
    app_url: str = "http://localhost:5173"   # link shown in the alert emails

    # Language-model assistant (app/ai). The key is read ONLY from backend/.env and is never sent to the browser.
    # "auto" = use OpenAI when a key is present, otherwise the built-in rules. "off" = never call a model. "mock" = tests/demo.
    # "off" (default) = never call a model. "gemini" / "openai" / "auto" switch a provider on, and only when its key is also set.
    ai_provider: str = "off"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"           # check the free models for your account in Google AI Studio before switching on
    gemini_price_in_per_m: float = 0.0                # US dollars per million tokens; 0 = free plan
    gemini_price_out_per_m: float = 0.0
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    openai_api_key: str = ""
    openai_model: str = "gpt-6-luna"                 # cheapest current OpenAI text model (see docs/AI_MODEL_SELECTION.md)
    openai_base_url: str = "https://api.openai.com/v1"
    ai_timeout_seconds: float = 8.0
    ai_total_deadline_seconds: float = 10.0           # the student never waits longer than this for the model in total, retries included
    ai_max_retries: int = 2                          # extra tries after a timeout / 429 / 5xx
    ai_max_output_tokens: int = 900
    # gpt-6-luna defaults to "medium" reasoning, which adds billed reasoning tokens and latency and can use up the output cap.
    # These tasks are extraction and wording, so "none" is used (supported by gpt-6-luna and gpt-6.1-terra per OpenAI's docs of 29 Oct 2026).
    # Leave blank to send no reasoning_effort at all (for a model that does not accept it).
    ai_reasoning_effort: str = "none"
    ai_user_daily_calls: int = 40                    # per signed-in student per day
    ai_allow_guests: bool = False                    # guests use the built-in rules unless this is switched on
    ai_guest_daily_calls_per_ip: int = 5
    ai_monthly_budget_usd: float = 5.0               # all AI calls stop for the month when this is reached
    ai_price_in_per_m: float = 0.10                  # US dollars per million input tokens (update if the price changes)
    ai_price_out_per_m: float = 0.50

    # AI Learning Studio (app/studio). Every limit is checked on the server; the browser cannot raise them.
    studio_min_chars: int = 300                      # shorter text cannot make a useful pack
    studio_max_chars: int = 24000                    # about 6,000 words; larger documents must be split (also keeps free-tier requests small)
    studio_max_upload_mb: int = 5
    studio_max_pdf_pages: int = 80
    studio_extract_seconds: float = 20.0
    studio_timeout_seconds: float = 75.0             # the one AI call may take this long, then it is abandoned
    studio_max_output_tokens: int = 9000
    studio_user_daily_attempts: int = 5              # generation attempts per student per day (failed attempts count too)
    studio_user_monthly_attempts: int = 20
    studio_global_daily_attempts: int = 40           # all students together, per day: protects a free-tier daily quota
    simple_doc_max_mb: int = 10                       # largest document a student can keep in My Notebook
    simple_plan_timeout_seconds: float = 30.0         # the AI may take this long to write a study plan, then the built-in engine takes over
    studio_cooldown_seconds: int = 45                # minimum gap between two generations by one student
    studio_max_packs_per_user: int = 30
    studio_premium_multiplier: int = 5               # a future premium plan multiplies the per-student allowances; there is no payment code

    # CORS
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
