from typing import Dict, Any, Optional, Tuple
from app.paypal.client import PayPalClient

class PayPalOrders:
    def __init__(self, client: Optional[PayPalClient] = None):
        self.client = client or PayPalClient()

    def create_order(
        self,
        amount: float,
        currency: str = "USD",
        reference_id: str = "ORDER_REF_1",
        idempotency_key: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Creates a PayPal Sandbox Order with CAPTURE intent.
        """
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": reference_id,
                    "amount": {
                        "currency_code": currency,
                        "value": f"{amount:.2f}"
                    },
                    "description": "AgentShield Protected FinTech Checkout"
                }
            ]
        }
        return self.client.post("/v2/checkout/orders", payload, idempotency_key=idempotency_key)

    def get_order(self, order_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return self.client.get(f"/v2/checkout/orders/{order_id}")

    def capture_order(self, order_id: str, idempotency_key: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return self.client.post(f"/v2/checkout/orders/{order_id}/capture", {}, idempotency_key=idempotency_key)
