"""Regression tests for request logging secret redaction."""

import logging

from httpx import Request

from nextcloud_mcp_server.client import log_request


async def test_request_logging_redacts_authorization_header(caplog):
    """Debug request logs must not include Basic or Bearer credentials."""
    token = "secret-token-value"
    request = Request(
        "GET",
        "https://cloud.example.org/ocs/v2.php/cloud/user",
        headers={"Authorization": f"Bearer {token}"},
    )

    caplog.set_level(logging.DEBUG, logger="nextcloud_mcp_server.client")

    await log_request(request)

    assert token not in caplog.text
    assert "Bearer" not in caplog.text
    assert "<redacted>" in caplog.text
