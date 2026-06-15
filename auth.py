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
    """Extract the authorization code from whatever the user pastes.

    Accepts (in order of preference):
      1. Full redirect URI:  com.bosch.tt.dashtt.pointt://app/login?code=XXX&state=YYY
      2. Any URL containing code= in the query string or fragment
      3. A bare authorization code copied from the page source

    On Chrome, the redirect to the custom app scheme is silent — the code appears
    in the page source of the singlekey-id.com callback page.  Users are instructed
    to do Ctrl+U → search "code=" → paste the bare code value here.

    Raises ValueError on auth errors, state mismatch, or unparseable input.
    """
    value = redirect_url.strip()

    # ── URL path: anything that looks like a URL ──────────────────────────────
    if "://" in value or value.startswith("http") or value.startswith("?"):
        # Normalise: if user pasted just the query string (e.g. "?code=X&state=Y")
        if value.startswith("?"):
            value = "https://x/" + value

        parsed = urlparse(value)
        raw = parsed.query or parsed.fragment
        params = parse_qs(raw)

        if "error" in params:
            desc = params.get("error_description", params["error"])[0]
            raise ValueError(f"OAuth error from server: {desc}")

        if expected_state:
            got_state = params.get("state", [None])[0]
            if got_state and got_state != expected_state:
                raise ValueError("OAuth state mismatch — please restart the login flow")

        code = params.get("code", [None])[0]
        if code:
            return code
        raise ValueError("No authorization code found in the URL")

    # ── Bare code path: user copied just the code value from the page source ──
    # OAuth2 authorization codes are typically 20+ characters of base64url.
    # Reject very short strings to catch obvious mistakes (e.g. pasting the URL
    # field label or a single word).
    if len(value) >= 20 and " " not in value and "\n" not in value:
        return value

    raise ValueError(
        "Paste the authorization code from the page source (Ctrl+U → search 'code='), "
        "or the full redirect URL if your browser showed one."
    )
