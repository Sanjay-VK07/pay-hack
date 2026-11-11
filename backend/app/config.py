import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "AgentShield"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./agentshield.db")
    
    # AI Providers
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "auto")  # 'gemini', 'openai', or 'demo'
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # PayPal Sandbox Configuration
    PAYPAL_CLIENT_ID: str = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    PAYPAL_CLIENT_SECRET: str = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
    PAYPAL_BASE_URL: str = os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com").strip()
    PAYPAL_WEBHOOK_ID: str = os.getenv("PAYPAL_WEBHOOK_ID", "").strip()
    
    # Operational & Demo Mode
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")
    
    # Security Configuration
    # AGENTSHIELD_API_KEY: When set in environment, mutating endpoints require this key
    # via `X-AgentShield-Key` or `Authorization: Bearer <key>`. Never set a hard-coded default.
    AGENTSHIELD_API_KEY: str = os.getenv("AGENTSHIELD_API_KEY", "").strip()
    # If True, mutating endpoints always require authentication even on loopback.
    REQUIRE_MUTATION_AUTH: bool = os.getenv("REQUIRE_MUTATION_AUTH", "false").lower() in ("true", "1", "yes")
    # If True, loopback clients (127.0.0.1, ::1) are permitted for frictionless local demo evaluation
    # when AGENTSHIELD_API_KEY is not configured. Non-loopback clients are ALWAYS blocked without auth.
    ALLOW_LOOPBACK_MUTATIONS: bool = os.getenv("ALLOW_LOOPBACK_MUTATIONS", "true").lower() in ("true", "1", "yes")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")

    @property
    def validated_paypal_base_url(self) -> str:
        url = self.PAYPAL_BASE_URL.rstrip('/')
        allowed_sandbox_url = "https://api-m.sandbox.paypal.com"
        if url != allowed_sandbox_url:
            raise ValueError(
                "AgentShield only permits the exact PayPal Sandbox API host "
                "https://api-m.sandbox.paypal.com; live or custom hosts are prohibited."
            )
        return url

settings = Settings()
