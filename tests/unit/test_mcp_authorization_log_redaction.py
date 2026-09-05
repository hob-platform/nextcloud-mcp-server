"""Regression tests for /mcp Authorization-header logging."""

from nextcloud_mcp_server.app import _redacted_authorization_for_log


def test_mcp_authorization_log_redacts_bearer_token():
    marker = _redacted_authorization_for_log("Bearer eyJsecret.payload.signature")

    assert marker == "Bearer <redacted>"
    assert "eyJsecret" not in marker
    assert "payload" not in marker


def test_mcp_authorization_log_redacts_basic_credentials():
    marker = _redacted_authorization_for_log("Basic dXNlcjpzZWNyZXQ=")

    assert marker == "Basic <redacted>"
    assert "dXNlcjpzZWNyZXQ=" not in marker
