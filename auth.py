import os
import urllib.parse
import streamlit as st
from supabase import Client, create_client


# ══════════════════════════════════════════════════════════════
# SUPABASE CLIENT
# ══════════════════════════════════════════════════════════════

@st.cache_resource
def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY environment variables.")
    return create_client(url, key)


# ══════════════════════════════════════════════════════════════
# ROLES
# ══════════════════════════════════════════════════════════════

def get_admin_emails() -> set[str]:
    raw = os.environ.get("ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def get_profile_role(user_id: str, email: str | None = None) -> str:
    client = get_supabase_client()
    try:
        result = (
            client.table("profiles")
            .select("role")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if result.data:
            role = (result.data[0].get("role") or "user").strip().lower()
            return role if role in {"admin", "user"} else "user"
    except Exception:
        pass
    if email and email.lower() in get_admin_emails():
        return "admin"
    return "user"


# ══════════════════════════════════════════════════════════════
# EMAIL / PASSWORD AUTH  (kept for admin use)
# ══════════════════════════════════════════════════════════════

def login_with_email_password(email: str, password: str):
    client = get_supabase_client()
    return client.auth.sign_in_with_password({"email": email, "password": password})


def signup_with_email_password(email: str, password: str):
    client = get_supabase_client()
    return client.auth.sign_up({"email": email, "password": password})


def logout_current_user() -> None:
    client = get_supabase_client()
    try:
        client.auth.sign_out()
    except Exception:
        pass


def get_current_user():
    return st.session_state.get("auth_user")


# ══════════════════════════════════════════════════════════════
# GOOGLE OAUTH  —  IMPLICIT FLOW (no PKCE)
# ══════════════════════════════════════════════════════════════
#
# ROOT CAUSE OF THE REDIRECT-LOOP BUG:
#   Supabase-py v2 defaults to PKCE flow. It stores the code_verifier
#   in memory. When Google redirects back, Streamlit starts a NEW
#   Python session — the verifier is gone — exchange_code_for_session()
#   fails — the error handler shows the login screen again.
#
# FIX:
#   Bypass supabase-py's OAuth helper entirely and build the URL
#   manually with response_type=token (implicit flow).
#   Supabase returns #access_token=… in the URL hash instead of
#   a PKCE code. No verifier is ever needed.
#   Our JS bridge converts the hash to ?access_token=… so Python
#   can read it and call set_session() directly.
# ══════════════════════════════════════════════════════════════

def get_google_oauth_url(redirect_to: str | None = None) -> str | None:
    """
    Returns a Supabase Google OAuth URL that uses IMPLICIT flow.
    Avoids PKCE entirely so no code-verifier is ever stored or lost.
    """
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not supabase_url:
        return None

    app_url = redirect_to or os.environ.get("APP_URL", "")

    params: dict[str, str] = {
        "provider":      "google",
        "response_type": "token",          # ← implicit flow, no PKCE
        "scopes":        "email profile",
    }
    if app_url:
        params["redirect_to"] = app_url

    return f"{supabase_url}/auth/v1/authorize?{urllib.parse.urlencode(params)}"


def exchange_oauth_code(code: str):
    """
    Kept for compatibility. With implicit flow this is never called,
    but it's here as a safety net if PKCE somehow fires.
    """
    client = get_supabase_client()
    try:
        return client.auth.exchange_code_for_session({"auth_code": code})
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
# USER-FRIENDLY ERROR TRANSLATION
# ══════════════════════════════════════════════════════════════

_ERROR_TABLE = [
    ("invalid login credentials", "wrong_password",    "Incorrect email or password."),
    ("email not confirmed",        "unconfirmed",       "Please confirm your email first."),
    ("user already registered",    "duplicate_email",   "An account with that email already exists."),
    ("password should be at least","weak_password",     "Password must be at least 6 characters."),
    ("unable to validate email",   "invalid_email",     "That doesn't look like a valid email address."),
    ("email rate limit exceeded",  "rate_limit",        "Too many attempts — please wait a few minutes."),
    ("signup is disabled",         "signups_disabled",  "New sign-ups are temporarily closed."),
    ("network",                    "network_error",     "Connection problem. Check your internet."),
]


def friendly_auth_error(exception) -> tuple[str, str]:
    raw = str(exception).lower()
    for substring, code, message in _ERROR_TABLE:
        if substring in raw:
            return code, message
    return "unknown", "Something went wrong. Please try again."


def is_email_unconfirmed_error(exception) -> bool:
    raw = str(exception).lower()
    return any(k in raw for k in ("unconfirmed", "email not confirmed",
                                   "user not confirmed", "confirm"))


def is_duplicate_email_error(exception) -> bool:
    code, _ = friendly_auth_error(exception)
    return code == "duplicate_email"
