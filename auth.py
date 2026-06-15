from __future__ import annotations

import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlencode, urlparse

from .const import (
    OAUTH_AUTHORIZE_URL,
    OAUTH_CLIENT_ID,
    OAUTH_REDIRECT_URI,
    OAUTH_SCOPES,
    OAUTH_STYLE_ID,
)


def create_code_verifier() -> str:
    """Generate a cryptographically random PKCE code verifier."""
    return base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()


def create_code_challenge(verifier: str) -> str:
    """Derive the PKCE code challenge from the verifier (S256 method)."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def create_state() -> str:
    return secrets.token_urlsafe(32)


def build_authorization_url(code_verifier: str, state: str) -> str:
    """Return the SingleKey ID login URL the user must open in a browser."""
    params = {
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(OAUTH_SCOPES),
        "state": state,
        "code_challenge": create_code_challenge(code_verifier),
        "code_challenge_method": "S256",
        "prompt": "login",
        "style_id": OAUTH_STYLE_ID,
    }
    return f"{OAUTH_AUTHORIZE_URL}?{urlencode(params)}"


def extract_code_from_redirect(redirect_url: str, expected_state: str | None = None) -> str:
    """Pull the authorization code out of the redirect URL (or bare code) the user pastes.

    Accepts:
      - Full redirect URI:  com.bosch.tt.dashtt.pointt://app/login?code=XXX&state=YYY
      - Browser error page URL that contains code= in the query string
      - Bare authorization code (if the user only copies the code value)

    Raises ValueError on auth errors or state mismatch.
    """
    value = redirect_url.strip()

    # If it looks like a URL, parse it
    if "://" in value or value.startswith("http"):
        parsed = urlparse(value)
        # query may be empty for custom schemes; try fragment too
        raw = parsed.query or parsed.fragment
        params = parse_qs(raw)

        if "error" in params:
            desc = params.get("error_description", params["error"])[0]
            raise ValueError(f"OAuth error: {desc}")

        if expected_state:
            got_state = params.get("state", [None])[0]
            if got_state and got_state != expected_state:
                raise ValueError("OAuth state mismatch — please restart the login flow")

        code = params.get("code", [None])[0]
        if not code:
            raise ValueError("No authorization code found in the redirect URL")
        return code

    # Assume the user pasted just the raw code
    if len(value) > 10:
        return value

    raise ValueError("Could not find an authorization code in the pasted value")
