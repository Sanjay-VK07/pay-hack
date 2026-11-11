"""
Safe unit and integration tests for AgentShield PayPal Sandbox Adapter.
- All HTTP calls to PayPal are mocked (never touches live network).
- Uses isolated in-memory or mocked sessions (never modifies existing database).
- Validates URL safety, credential handling, error parsing, and financial safeguards.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.config import Settings
from app.paypal.auth import PayPalAuth
from app.paypal.client import PayPalClient
from app.paypal.orders import PayPalOrders
from app.paypal.refunds import PayPalRefunds


def test_settings_prohibits_live_paypal_endpoints():
    """Verify that only the exact official PayPal Sandbox host is accepted."""
    s = Settings()
    for disallowed in (
        "https://api-m.paypal.com",
        "https://api.paypal.com",
        "https://api-m.sandbox.paypal.com.attacker.example",
        "http://api-m.sandbox.paypal.com",
        "https://attacker.example",
    ):
        s.PAYPAL_BASE_URL = disallowed
        with pytest.raises(ValueError, match="exact PayPal Sandbox API host"):
            _ = s.validated_paypal_base_url

    s.PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com"
    assert s.validated_paypal_base_url == "https://api-m.sandbox.paypal.com"
    s.PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com/"
    assert s.validated_paypal_base_url == "https://api-m.sandbox.paypal.com"


def test_paypal_auth_missing_credentials():
    """Verify that missing credentials safely return an error and simulator mode."""
    with patch("app.paypal.auth.settings") as mock_settings:
        mock_settings.PAYPAL_CLIENT_ID = ""
        mock_settings.PAYPAL_CLIENT_SECRET = ""
        mock_settings.validated_paypal_base_url = "https://api-m.sandbox.paypal.com"

        auth = PayPalAuth()
        token, err = auth.get_access_token()
        assert token is None
        assert err == "PAYPAL_CREDENTIALS_MISSING"

        status = auth.test_connectivity()
        assert status["credentials_status"] == "MISSING"
        assert status["oauth_status"] == "NOT_CONFIGURED"
        assert status["mode"] == "SIMULATED_SANDBOX"


def test_paypal_auth_token_success_and_caching():
    """Verify that successful OAuth response caches access token."""
    with patch("app.paypal.auth.settings") as mock_settings, \
         patch("requests.post") as mock_post:
        mock_settings.PAYPAL_CLIENT_ID = "mock_client_id"
        mock_settings.PAYPAL_CLIENT_SECRET = "mock_secret"
        mock_settings.validated_paypal_base_url = "https://api-m.sandbox.paypal.com"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "SANDBOX_MOCK_TOKEN_ABC",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_post.return_value = mock_resp

        auth = PayPalAuth()
        token, err = auth.get_access_token()
        assert token == "SANDBOX_MOCK_TOKEN_ABC"
        assert err is None
        assert mock_post.call_count == 1

        # Second call should use cached token without additional network request
        token2, err2 = auth.get_access_token()
        assert token2 == "SANDBOX_MOCK_TOKEN_ABC"
        assert err2 is None
        assert mock_post.call_count == 1


def test_paypal_auth_token_failure_reports_failed():
    """Verify that OAuth failure (e.g. 401 invalid_client) reports FAILED."""
    with patch("app.paypal.auth.settings") as mock_settings, \
         patch("requests.post") as mock_post:
        mock_settings.PAYPAL_CLIENT_ID = "invalid_id"
        mock_settings.PAYPAL_CLIENT_SECRET = "invalid_secret"
        mock_settings.validated_paypal_base_url = "https://api-m.sandbox.paypal.com"

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = '{"error": "invalid_client", "error_description": "Client Authentication failed"}'
        mock_post.return_value = mock_resp

        auth = PayPalAuth()
        token, err = auth.get_access_token()
        assert token is None
        assert "PayPal Auth Error 401" in err

        status = auth.test_connectivity()
        assert status["credentials_status"] == "CONFIGURED"
        assert status["oauth_status"] == "FAILED"
        assert status["connectivity"] == "UNREACHABLE"


def test_paypal_client_error_parsing_extracts_details():
    """Verify that PayPal 422 errors extract detailed issue descriptions."""
    with patch("app.paypal.client.PayPalAuth") as mock_auth_cls, \
         patch("requests.post") as mock_post:
        mock_auth = MagicMock()
        mock_auth.get_access_token.return_value = ("TEST_TOKEN", None)
        mock_auth_cls.return_value = mock_auth

        client = PayPalClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 422
        mock_resp.json.return_value = {
            "name": "UNPROCESSABLE_ENTITY",
            "message": "Business validation failed.",
            "debug_id": "DEBUG_9876",
            "details": [
                {
                    "issue": "ORDER_NOT_APPROVED",
                    "description": "Order must be approved by buyer before capture."
                }
            ]
        }
        mock_post.return_value = mock_resp

        result, err = client.post("/v2/checkout/orders/ORDER_1/capture", {})
        assert result is None
        assert "ORDER_NOT_APPROVED" in err
        assert "Order must be approved by buyer before capture" in err
        assert "DEBUG_9876" in err


def test_paypal_orders_create_order_payload():
    """Verify that PayPalOrders.create_order formats CAPTURE intent and return/cancel URLs."""
    with patch("app.paypal.client.PayPalAuth") as mock_auth_cls, \
         patch("requests.post") as mock_post:
        mock_auth = MagicMock()
        mock_auth.get_access_token.return_value = ("TEST_TOKEN", None)
        mock_auth_cls.return_value = mock_auth

        client = PayPalClient()
        orders_svc = PayPalOrders(client)

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "id": "5O190127TN364715T",
            "status": "CREATED",
            "links": [
                {
                    "href": "https://www.sandbox.paypal.com/checkoutnow?token=5O190127TN364715T",
                    "rel": "approve",
                    "method": "GET"
                }
            ]
        }
        mock_post.return_value = mock_resp

        result, err = orders_svc.create_order(
            amount=150.00,
            currency="USD",
            reference_id="TXN_TEST_100",
            idempotency_key="REQ_IDEM_1"
        )
        assert err is None
        assert result["id"] == "5O190127TN364715T"

        # Check call arguments
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["intent"] == "CAPTURE"
        assert payload["purchase_units"][0]["reference_id"] == "TXN_TEST_100"
        assert payload["purchase_units"][0]["amount"]["value"] == "150.00"
        assert payload["purchase_units"][0]["amount"]["currency_code"] == "USD"
        assert "application_context" in payload
        assert "return_url" in payload["application_context"]


def test_paypal_refunds_blocks_uncaptured_or_pending():
    """Verify that PayPalRefunds blocks refund if capture status is not COMPLETED."""
    with patch("app.paypal.client.PayPalAuth") as mock_auth_cls, \
         patch("requests.get") as mock_get:
        mock_auth = MagicMock()
        mock_auth.get_access_token.return_value = ("TEST_TOKEN", None)
        mock_auth_cls.return_value = mock_auth

        client = PayPalClient()
        refunds_svc = PayPalRefunds(client)

        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {
            "id": "CAP_TEST_PENDING",
            "status": "PENDING",
            "amount": {"value": "200.00", "currency_code": "USD"}
        }
        mock_get.return_value = mock_get_resp

        result, err = refunds_svc.refund_capture(capture_id="CAP_TEST_PENDING", amount=200.00)
        assert result is None
        assert "must be COMPLETED" in err
