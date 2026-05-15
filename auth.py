import os
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
# EMAIL / PASSWORD AUTH
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
# GOOGLE OAUTH — handled entirely by Supabase JS SDK in browser
# Python only needs to call set_session() with the tokens the
# JS SDK extracts and passes back via URL query params.
# ══════════════════════════════════════════════════════════════

def get_google_oauth_url(redirect_to: str | None = None) -> str | None:
    """Not used — OAuth is initiated by the JS SDK. Kept for compatibility."""
    return None


def exchange_oauth_code(code: str):
    """Fallback PKCE exchange — should not be needed with JS SDK flow."""
    client = get_supabase_client()
    try:
        return client.auth.exchange_code_for_session({"auth_code": code})
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
# ERROR TRANSLATION
# ══════════════════════════════════════════════════════════════

_ERROR_TABLE = [
    ("invalid login credentials", "wrong_password",   "Incorrect email or password."),
    ("email not confirmed",        "unconfirmed",      "Please confirm your email first."),
    ("user already registered",    "duplicate_email",  "An account with that email already exists."),
    ("password should be at least","weak_password",    "Password must be at least 6 characters."),
    ("unable to validate email",   "invalid_email",    "That doesn't look like a valid email address."),
    ("email rate limit exceeded",  "rate_limit",       "Too many attempts — please wait a few minutes."),
    ("signup is disabled",         "signups_disabled", "New sign-ups are temporarily closed."),
    ("network",                    "network_error",    "Connection problem. Check your internet."),
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
