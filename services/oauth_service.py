"""SSO/OAuth login scaffold — standard OAuth2 Authorization Code flow,
provider-agnostic (works with Google, Microsoft/Azure AD, GitHub, Okta, or
any OIDC-compatible provider that exposes the three URLs below).

NOT active by default — nothing in this module runs unless every one of
these env vars is set:
    PATHOLOGYAI_OAUTH_CLIENT_ID
    PATHOLOGYAI_OAUTH_CLIENT_SECRET
    PATHOLOGYAI_OAUTH_AUTHORIZE_URL   e.g. https://accounts.google.com/o/oauth2/v2/auth
    PATHOLOGYAI_OAUTH_TOKEN_URL       e.g. https://oauth2.googleapis.com/token
    PATHOLOGYAI_OAUTH_USERINFO_URL    e.g. https://openidconnect.googleapis.com/v1/userinfo
    PATHOLOGYAI_OAUTH_REDIRECT_URI    e.g. http://localhost:8501 (must exactly match
                                       what you register with the provider)

Those values come from registering an OAuth app with your chosen provider —
only you can do that (it needs your own account with them). Until you do,
is_oauth_enabled() returns False, login.py doesn't show an SSO button, and
nothing here is reachable. This was written and reviewed carefully but could
not be exercised against a live OAuth provider in the sandboxed environment
this was built in — test it against your own provider's app registration
before relying on it, the same way you would any new integration.

Uses plain `requests` (already a hard dependency) for the token exchange
rather than adding authlib as a required package. If you want a more
feature-complete client (PKCE, automatic OIDC discovery), swap it in here —
see the commented `authlib` line in requirements.txt.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import requests
import streamlit as st

CLIENT_ID = os.environ.get("PATHOLOGYAI_OAUTH_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("PATHOLOGYAI_OAUTH_CLIENT_SECRET", "").strip()
AUTHORIZE_URL = os.environ.get("PATHOLOGYAI_OAUTH_AUTHORIZE_URL", "").strip()
TOKEN_URL = os.environ.get("PATHOLOGYAI_OAUTH_TOKEN_URL", "").strip()
USERINFO_URL = os.environ.get("PATHOLOGYAI_OAUTH_USERINFO_URL", "").strip()
REDIRECT_URI = os.environ.get("PATHOLOGYAI_OAUTH_REDIRECT_URI", "http://localhost:8501").strip()
PROVIDER_LABEL = os.environ.get("PATHOLOGYAI_OAUTH_PROVIDER_LABEL", "SSO").strip()


def is_oauth_enabled() -> bool:
    return bool(CLIENT_ID and CLIENT_SECRET and AUTHORIZE_URL and TOKEN_URL and USERINFO_URL)


def build_authorize_url() -> str:
    """URL to send the user to. Stashes a CSRF-protection `state` value in
    session_state so handle_callback() can verify the redirect is genuine."""
    state = secrets.token_urlsafe(24)
    st.session_state["_oauth_state"] = state
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def handle_callback() -> dict[str, Any] | None:
    """Call once near the top of app_create.py. If the current page load is
    the redirect back from the provider (i.e. `code`/`state` are present in
    the URL), exchanges the code for a token and fetches the user's profile.
    Returns the provider's userinfo dict on success, None on anything else —
    including failure, deliberately: a broken/misconfigured OAuth setup
    should never be able to crash the rest of the app."""
    if not is_oauth_enabled():
        return None
    params = st.query_params
    code = params.get("code")
    state = params.get("state")
    if not code or not state:
        return None
    if state != st.session_state.get("_oauth_state"):
        st.error("OAuth state mismatch — possible CSRF attempt or an expired login link. Please try signing in again.")
        st.query_params.clear()
        return None

    try:
        token_resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json().get("access_token")
        if not access_token:
            return None

        userinfo_resp = requests.get(
            USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=15
        )
        userinfo_resp.raise_for_status()
        st.query_params.clear()
        return userinfo_resp.json()
    except Exception as e:
        st.error(f"OAuth sign-in failed: {e}")
        st.query_params.clear()
        return None


def provision_local_account(userinfo: dict[str, Any]) -> dict[str, Any]:
    """Maps an OAuth userinfo payload onto this app's own `users` table —
    creates the account on first login (passwordless: a random, never-used
    password hash, since auth is delegated to the provider from then on) or
    returns the existing one. Keeps SSO users in the same table as regular
    accounts so every other feature (roles, saved analyses, audit log,
    RBAC) works identically no matter how someone signed in."""
    from core.security import hash_password
    from db.database import get_connection, row_to_dict

    email = userinfo.get("email")
    if not email:
        raise ValueError("OAuth provider did not return an email address.")
    full_name = userinfo.get("name") or email.split("@")[0]
    username = email.split("@")[0]

    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        existing = row_to_dict(row)
        if existing:
            existing.pop("password_hash", None)
            return existing
        conn.execute(
            """INSERT INTO users (username, email, password_hash, full_name, role, institution, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                username, email, hash_password(secrets.token_urlsafe(32)), full_name,
                "researcher", "", datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        new_user = row_to_dict(row)
        new_user.pop("password_hash", None)
        return new_user
