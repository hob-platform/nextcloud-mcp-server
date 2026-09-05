"""Unit tests for BearerAuthMiddleware."""

import base64
import json
import logging

import pytest

from nextcloud_mcp_server.app import BearerAuthMiddleware


class MockApp:
    """Mock ASGI app for testing middleware."""

    def __init__(self):
        self.called = False
        self.received_scope = None

    async def __call__(self, scope, receive, send):
        self.called = True
        self.received_scope = scope


def _jwt_with_claims(claims: dict[str, object]) -> str:
    def encode(data: dict[str, object]) -> str:
        payload = json.dumps(data, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")

    return f"{encode({'alg': 'none'})}.{encode(claims)}.sig"


@pytest.mark.unit
async def test_bearer_auth_middleware_extracts_token_and_nextcloud_uid():
    """Bearer pass-through stores the raw token and preferred DAV username."""
    mock_app = MockApp()
    middleware = BearerAuthMiddleware(mock_app)

    token = _jwt_with_claims(
        {
            "nextcloud_uid": "ki-asst-mislav",
            "preferred_username": "service-account-ki-asst-mislav-lab",
        }
    )
    scope = {
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
    }

    await middleware(scope, None, None)  # type: ignore[arg-type]

    assert mock_app.called
    assert scope["state"]["bearer_auth"]["token"] == token
    assert scope["state"]["bearer_auth"]["username"] == "ki-asst-mislav"


@pytest.mark.unit
async def test_bearer_auth_middleware_falls_back_to_preferred_username():
    """preferred_username is used when nextcloud_uid is absent."""
    mock_app = MockApp()
    middleware = BearerAuthMiddleware(mock_app)

    token = _jwt_with_claims({"preferred_username": "alice"})
    scope = {
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
    }

    await middleware(scope, None, None)  # type: ignore[arg-type]

    assert scope["state"]["bearer_auth"]["username"] == "alice"


@pytest.mark.unit
async def test_bearer_auth_middleware_ignores_wrong_auth_scheme():
    """Non-Bearer Authorization headers are ignored."""
    mock_app = MockApp()
    middleware = BearerAuthMiddleware(mock_app)

    scope = {
        "type": "http",
        "headers": [(b"authorization", b"Basic dXNlcjpwYXNz")],
    }

    await middleware(scope, None, None)  # type: ignore[arg-type]

    assert mock_app.called
    assert "bearer_auth" not in scope.get("state", {})


@pytest.mark.unit
async def test_bearer_auth_middleware_non_http_scope():
    """WebSocket scopes pass through unchanged."""
    mock_app = MockApp()
    middleware = BearerAuthMiddleware(mock_app)

    scope = {
        "type": "websocket",
        "headers": [(b"authorization", b"Bearer token")],
    }

    await middleware(scope, None, None)  # type: ignore[arg-type]

    assert mock_app.called
    assert "state" not in scope


@pytest.mark.unit
async def test_bearer_auth_middleware_does_not_log_token(caplog):
    """The raw Bearer token must never appear in middleware logs."""
    mock_app = MockApp()
    middleware = BearerAuthMiddleware(mock_app)

    token = _jwt_with_claims({"preferred_username": "alice"})
    scope = {
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
    }

    caplog.set_level(logging.DEBUG, logger="nextcloud_mcp_server.app")

    await middleware(scope, None, None)  # type: ignore[arg-type]

    assert token not in caplog.text
    assert "alice" not in caplog.text


@pytest.mark.unit
async def test_bearer_auth_middleware_malformed_jwt_keeps_token_without_username():
    """Malformed tokens are still passed through; context rejects missing username."""
    mock_app = MockApp()
    middleware = BearerAuthMiddleware(mock_app)

    scope = {
        "type": "http",
        "headers": [(b"authorization", b"Bearer opaque-token")],
    }

    await middleware(scope, None, None)  # type: ignore[arg-type]

    assert scope["state"]["bearer_auth"]["token"] == "opaque-token"
    assert scope["state"]["bearer_auth"]["username"] is None
