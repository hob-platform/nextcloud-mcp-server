"""Unit tests for multi-user Bearer pass-through context wiring."""

from types import SimpleNamespace

import pytest

from nextcloud_mcp_server.config import Settings
from nextcloud_mcp_server.context import _get_client_from_bearer_auth

pytestmark = pytest.mark.unit


def _ctx_with_state(state: dict[str, object]):
    return SimpleNamespace(
        request_context=SimpleNamespace(request=SimpleNamespace(scope={"state": state}))
    )


def test_bearer_auth_context_builds_nextcloud_client(monkeypatch):
    """Context builds a per-request Nextcloud client from Bearer state."""
    settings = Settings(
        nextcloud_host="https://cloud.example.org",
        deployment_mode="multi_user_bearer",
    )
    monkeypatch.setattr("nextcloud_mcp_server.context.get_settings", lambda: settings)

    calls = {}
    expected_client = object()

    def fake_from_token(*, base_url: str, token: str, username: str):
        calls.update({"base_url": base_url, "token": token, "username": username})
        return expected_client

    monkeypatch.setattr(
        "nextcloud_mcp_server.context.NextcloudClient.from_token",
        staticmethod(fake_from_token),
    )

    ctx = _ctx_with_state(
        {
            "bearer_auth": {
                "token": "secret-token-value",
                "username": "ki-asst-mislav",
            }
        }
    )

    client = _get_client_from_bearer_auth(ctx)  # type: ignore[arg-type]

    assert client is expected_client
    assert calls == {
        "base_url": "https://cloud.example.org",
        "token": "secret-token-value",
        "username": "ki-asst-mislav",
    }


def test_bearer_auth_context_requires_authorization_state(monkeypatch):
    """Missing Bearer request state fails closed."""
    settings = Settings(
        nextcloud_host="https://cloud.example.org",
        deployment_mode="multi_user_bearer",
    )
    monkeypatch.setattr("nextcloud_mcp_server.context.get_settings", lambda: settings)

    ctx = _ctx_with_state({})

    with pytest.raises(ValueError, match="Bearer token not found"):
        _get_client_from_bearer_auth(ctx)  # type: ignore[arg-type]


def test_bearer_auth_context_requires_username_claim(monkeypatch):
    """DAV path construction needs a stable Nextcloud username claim."""
    settings = Settings(
        nextcloud_host="https://cloud.example.org",
        deployment_mode="multi_user_bearer",
    )
    monkeypatch.setattr("nextcloud_mcp_server.context.get_settings", lambda: settings)

    ctx = _ctx_with_state({"bearer_auth": {"token": "secret-token-value"}})

    with pytest.raises(ValueError, match="supported Nextcloud username claim"):
        _get_client_from_bearer_auth(ctx)  # type: ignore[arg-type]


def test_bearer_auth_context_requires_nextcloud_host(monkeypatch):
    """NEXTCLOUD_HOST is still required in pass-through mode."""
    settings = Settings(deployment_mode="multi_user_bearer")
    monkeypatch.setattr("nextcloud_mcp_server.context.get_settings", lambda: settings)

    ctx = _ctx_with_state(
        {"bearer_auth": {"token": "secret-token-value", "username": "alice"}}
    )

    with pytest.raises(ValueError, match="NEXTCLOUD_HOST"):
        _get_client_from_bearer_auth(ctx)  # type: ignore[arg-type]
