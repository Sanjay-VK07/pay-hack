import requests
from typing import Dict, Any, Optional, Tuple
from app.config import settings
from app.paypal.auth import PayPalAuth

class PayPalClient:
    def __init__(self):
        self.auth = PayPalAuth()
        self.base_url = settings.PAYPAL_BASE_URL.rstrip('/')

    def _get_headers(self, idempotency_key: Optional[str] = None) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        token, err = self.auth.get_access_token()
        if err or not token:
            return None, err or "Failed to obtain PayPal token"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        if idempotency_key:
            headers["PayPal-Request-Id"] = idempotency_key

        return headers, None

    def get(self, endpoint: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        headers, err = self._get_headers()
        if err:
            return None, err

        url = f"{self.base_url}{endpoint}"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code in (200, 201):
                return resp.json(), None
            try:
                err_data = resp.json()
                msg = f"PayPal GET error {resp.status_code}: {err_data.get('name', '')} - {err_data.get('message', '')} (Debug ID: {err_data.get('debug_id', 'N/A')})"
            except Exception:
                msg = f"PayPal GET error {resp.status_code}: {resp.text}"
            return None, msg
        except Exception as e:
            return None, f"PayPal request failure: {str(e)}"

    def post(self, endpoint: str, data: Dict[str, Any], idempotency_key: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        headers, err = self._get_headers(idempotency_key=idempotency_key)
        if err:
            return None, err

        url = f"{self.base_url}{endpoint}"
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=15)
            if resp.status_code in (200, 201, 202):
                return resp.json(), None
            try:
                err_data = resp.json()
                msg = f"PayPal POST error {resp.status_code}: {err_data.get('name', '')} - {err_data.get('message', '')} (Debug ID: {err_data.get('debug_id', 'N/A')})"
            except Exception:
                msg = f"PayPal POST error {resp.status_code}: {resp.text}"
            return None, msg
        except Exception as e:
            return None, f"PayPal request failure: {str(e)}"
