from typing import Dict, Any, Optional, Tuple
from app.paypal.client import PayPalClient

class PayPalRefunds:
    def __init__(self, client: Optional[PayPalClient] = None):
        self.client = client or PayPalClient()

    def get_capture_details(self, capture_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return self.client.get(f"/v2/payments/captures/{capture_id}")

    def get_refund_details(self, refund_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Retrieves verified refund details from PayPal Sandbox: GET /v2/payments/refunds/{refund_id}
        """
        return self.client.get(f"/v2/payments/refunds/{refund_id}")

    def refund_capture(
        self,
        capture_id: str,
        amount: Optional[float] = None,
        currency: str = "USD",
        note_to_payer: str = "AgentShield Fraud Mitigation Refund",
        idempotency_key: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Executes a refund against an existing verified PayPal capture.
        Strict verification: capture must be in COMPLETED status.
        """
        # First verify capture state
        capture, err = self.get_capture_details(capture_id)
        if err or not capture:
            return None, f"Capture verification failed for {capture_id}: {err}"

        capture_status = capture.get("status")
        if capture_status != "COMPLETED":
            return None, f"Capture {capture_id} has status '{capture_status}' and is not eligible for refund (must be COMPLETED)."

        payload: Dict[str, Any] = {
            "note_to_payer": note_to_payer
        }
        if amount is not None:
            payload["amount"] = {
                "value": f"{amount:.2f}",
                "currency_code": currency
            }

        endpoint = f"/v2/payments/captures/{capture_id}/refund"
        return self.client.post(endpoint, payload, idempotency_key=idempotency_key)
