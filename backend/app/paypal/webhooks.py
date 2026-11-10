from typing import Dict, Any, Tuple
from app.config import settings
from app.paypal.client import PayPalClient

class PayPalWebhooks:
    def __init__(self, client: PayPalClient = None):
        self.client = client or PayPalClient()
        self.webhook_id = settings.PAYPAL_WEBHOOK_ID

    def verify_webhook_signature(
        self,
        headers: Dict[str, str],
        body: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Validates incoming PayPal webhook event with PayPal signature verification endpoint.
        """
        if not settings.PAYPAL_CLIENT_ID or not self.webhook_id:
            # Fallback simulated webhook verification for demo/sandbox without webhook ID
            return True, "SIMULATED_WEBHOOK_VERIFIED"

        payload = {
            "auth_algo": headers.get("paypal-auth-algo"),
            "cert_url": headers.get("paypal-cert-url"),
            "transmission_id": headers.get("paypal-transmission-id"),
            "transmission_sig": headers.get("paypal-transmission-sig"),
            "transmission_time": headers.get("paypal-transmission-time"),
            "webhook_id": self.webhook_id,
            "webhook_event": body
        }

        resp, err = self.client.post("/v1/notifications/verify-webhook-signature", payload)
        if err or not resp:
            return False, f"Signature verification error: {err}"

        status = resp.get("verification_status")
        if status == "SUCCESS":
            return True, "SUCCESS"
        return False, f"Verification failed with status: {status}"
