import uuid
from typing import Dict, Any, Tuple
from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc)

class PayPalSimulator:
    """
    Clearly labeled PayPal Sandbox Integration Simulator.
    Used when live Sandbox API credentials are not supplied in the environment.
    Strictly flags responses with 'is_simulated': True and 'integration_mode': 'SIMULATED_SANDBOX'.
    """
    def __init__(self):
        self.integration_mode = "SIMULATED_SANDBOX"

    def create_simulated_order(self, amount: float, currency: str = "USD") -> Dict[str, Any]:
        order_id = f"SIM-ORD-{uuid.uuid4().hex[:12].upper()}"
        return {
            "id": order_id,
            "status": "CREATED",
            "intent": "CAPTURE",
            "is_simulated": True,
            "integration_mode": self.integration_mode,
            "purchase_units": [{
                "reference_id": f"REF-{uuid.uuid4().hex[:8]}",
                "amount": {"currency_code": currency, "value": f"{amount:.2f}"}
            }],
            "create_time": utcnow().isoformat()
        }

    def capture_simulated_order(self, order_id: str, amount: float, currency: str = "USD") -> Dict[str, Any]:
        capture_id = f"SIM-CAP-{uuid.uuid4().hex[:12].upper()}"
        return {
            "id": order_id,
            "status": "COMPLETED",
            "is_simulated": True,
            "integration_mode": self.integration_mode,
            "purchase_units": [{
                "payments": {
                    "captures": [{
                        "id": capture_id,
                        "status": "COMPLETED",
                        "amount": {"value": f"{amount:.2f}", "currency_code": currency},
                        "seller_protection": {"status": "ELIGIBLE"},
                        "create_time": utcnow().isoformat()
                    }]
                }
            }]
        }

    def get_simulated_capture(self, capture_id: str, amount: float = 2890.0, currency: str = "USD") -> Dict[str, Any]:
        return {
            "id": capture_id,
            "status": "COMPLETED",
            "amount": {"value": f"{amount:.2f}", "currency_code": currency},
            "final_capture": True,
            "seller_protection": {
                "status": "ELIGIBLE",
                "dispute_categories": ["ITEM_NOT_RECEIVED", "UNAUTHORIZED_TRANSACTION"]
            },
            "seller_receivable_breakdown": {
                "gross_amount": {"value": f"{amount:.2f}", "currency_code": currency},
                "paypal_fee": {"value": f"{(amount * 0.0349 + 0.49):.2f}", "currency_code": currency},
                "net_amount": {"value": f"{(amount - (amount * 0.0349 + 0.49)):.2f}", "currency_code": currency}
            },
            "is_simulated": True,
            "integration_mode": self.integration_mode,
            "create_time": utcnow().isoformat()
        }

    def refund_simulated_capture(
        self,
        capture_id: str,
        amount: float,
        currency: str = "USD",
        note_to_payer: str = "AgentShield Fraud Reversal"
    ) -> Dict[str, Any]:
        refund_id = f"SIM-REF-{uuid.uuid4().hex[:12].upper()}"
        return {
            "id": refund_id,
            "status": "COMPLETED",
            "capture_id": capture_id,
            "is_simulated": True,
            "integration_mode": self.integration_mode,
            "amount": {"value": f"{amount:.2f}", "currency_code": currency},
            "note_to_payer": note_to_payer,
            "create_time": utcnow().isoformat()
        }
