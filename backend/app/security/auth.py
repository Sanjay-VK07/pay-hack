import ipaddress
import secrets
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

api_key_header_scheme = APIKeyHeader(
    name="X-AgentShield-Key",
    auto_error=False,
    description="AgentShield API Key for mutating endpoints (configured via AGENTSHIELD_API_KEY in environment)",
)

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Bearer authorization token matching AGENTSHIELD_API_KEY",
)

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


def is_loopback(host: Optional[str]) -> bool:
    """Return True if the given host string represents a loopback/local address."""
    if not host:
        return False
    if host in LOOPBACK_HOSTS:
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback
    except ValueError:
        return False


def verify_mutation_auth(
    request: Request,
    api_key: Optional[str] = Security(api_key_header_scheme),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> Dict[str, Any]:
    """
    Lightweight authentication and loopback protection guard for mutating API routes.

    Rules:
    1. If AGENTSHIELD_API_KEY is configured in backend environment:
       - Every mutating request MUST provide a valid key via `X-AgentShield-Key` or `Authorization: Bearer <key>`.
       - Invalid or missing keys are rejected with HTTP 401 Unauthorized.
    2. If AGENTSHIELD_API_KEY is NOT configured:
       - If REQUIRE_MUTATION_AUTH=true, mutating requests are rejected with HTTP 401.
       - Non-loopback client IPs (e.g. external network interfaces) are REJECTED with HTTP 403 Forbidden.
       - Loopback clients (127.0.0.1, ::1, testclient) are permitted for frictionless local demo evaluation
         if ALLOW_LOOPBACK_MUTATIONS=true.
    """
    token = api_key or (bearer.credentials if bearer else None)
    client_host = request.client.host if request.client else "testclient"

    # Scenario 1: AGENTSHIELD_API_KEY is configured in environment
    if settings.AGENTSHIELD_API_KEY:
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Authentication required for mutating operations: provide X-AgentShield-Key or Authorization Bearer header.",
            )
        if not secrets.compare_digest(token, settings.AGENTSHIELD_API_KEY):
            raise HTTPException(
                status_code=401,
                detail="Invalid API key or authorization token.",
            )
        return {
            "authenticated": True,
            "actor": "authenticated_api_client",
            "client_host": client_host,
        }

    # Scenario 2: AGENTSHIELD_API_KEY is NOT configured
    if token:
        # A token was provided, but backend has no AGENTSHIELD_API_KEY configured to compare against
        raise HTTPException(
            status_code=401,
            detail="AGENTSHIELD_API_KEY is not configured in backend environment; cannot validate provided token.",
        )

    if settings.REQUIRE_MUTATION_AUTH:
        raise HTTPException(
            status_code=401,
            detail="Mutation authentication is required (REQUIRE_MUTATION_AUTH=true), but AGENTSHIELD_API_KEY is unset in backend environment.",
        )

    # Validate loopback confinement
    if not is_loopback(client_host):
        raise HTTPException(
            status_code=403,
            detail=(
                f"Forbidden: Unauthenticated mutating operations are blocked for non-loopback clients ({client_host}). "
                "To permit mutating operations from remote hosts, configure AGENTSHIELD_API_KEY in backend/.env."
            ),
        )

    if not settings.ALLOW_LOOPBACK_MUTATIONS:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Unauthenticated loopback mutations are disabled (ALLOW_LOOPBACK_MUTATIONS=false).",
        )

    return {
        "authenticated": False,
        "mode": "loopback_demo_unauthenticated",
        "client_host": client_host,
    }
