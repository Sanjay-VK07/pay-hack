import time
from datetime import datetime, timezone
import requests
from typing import Optional, Tuple, Dict, Any
from app.config import settings

class PayPalAuth:
    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET
        self.base_url = settings.PAYPAL_BASE_URL.rstrip('/')
        self._cached_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    @property
    def has_credentials(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_access_token(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieves an OAuth 2.0 Bearer token from PayPal Sandbox.
        Returns (token, error_message).
        """
        if not self.has_credentials:
            return None, "PAYPAL_CREDENTIALS_MISSING"

        # Check cache
        if self._cached_token and time.time() < (self._token_expires_at - 60):
            return self._cached_token, None

        token_url = f"{self.base_url}/v1/oauth2/token"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US"
        }
        data = {"grant_type": "client_credentials"}

        try:
            response = requests.post(
                token_url,
                auth=(self.client_id, self.client_secret),
                headers=headers,
                data=data,
                timeout=12
            )

            if response.status_code == 200:
                body = response.json()
                self._cached_token = body.get("access_token")
                expires_in = body.get("expires_in", 3600)
                self._token_expires_at = time.time() + expires_in
                return self._cached_token, None
            else:
                return None, f"PayPal Auth Error {response.status_code}: {response.text}"
        except Exception as e:
            return None, f"PayPal Connection Exception: {str(e)}"

    def test_connectivity(self) -> Dict[str, Any]:
        """
        Dynamically tests OAuth 2.0 connectivity and live credentials to PayPal Sandbox.
        Never reports ACTIVE merely because environment variables exist without actual verification.
        """
        if not self.has_credentials:
            return {
                "credentials_status": "MISSING",
                "oauth_status": "NOT_CONFIGURED",
                "connectivity": "SIMULATION_FALLBACK",
                "mode": "SIMULATED_SANDBOX",
                "last_api_verification": None,
                "error_detail": "PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET not configured in environment"
            }

        token, err = self.get_access_token()
        if token and not err:
            return {
                "credentials_status": "CONFIGURED",
                "oauth_status": "AUTHENTICATED",
                "connectivity": "REACHABLE",
                "mode": "LIVE_PAYPAL_SANDBOX",
                "last_api_verification": datetime.now(timezone.utc).isoformat(),
                "error_detail": None
            }
        else:
            return {
                "credentials_status": "CONFIGURED",
                "oauth_status": "FAILED",
                "connectivity": "UNREACHABLE",
                "mode": "SIMULATED_SANDBOX_FALLBACK",
                "last_api_verification": None,
                "error_detail": err
            }
