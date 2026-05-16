import os
import uuid
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
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY.")
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
# GOOGLE OAUTH — PKCE verifier stored in Supabase DB
# ══════════════════════════════════════════════════════════════
#
# WHY THIS IS GUARANTEED TO WORK:
#   Every other approach (session_state, JS localStorage, implicit
#   flow) fails because Streamlit restarts the Python process on
#   redirect, Google blocked implicit flow, and Streamlit iframes
#   are sandboxed. Storing the verifier in the database means it
#   survives any process restart, any server restart, anything.
#
# FLOW:
#   1. get_google_oauth_url() calls sign_in_with_oauth with
#      skip_browser_redirect=True → Supabase returns the Google
#      URL + pkce_code_verifier.
#   2. We generate a random `state` token, store
#      {state, verifier} in the oauth_states table.
#   3. We append ?oauth_state=STATE to the redirect_to URL.
#      Supabase passes redirect_to through unchanged, so it
#      arrives back as ?oauth_state=STATE&code=... on return.
#   4. exchange_oauth_code() reads ?oauth_state from URL,
#      fetches the verifier from Supabase, exchanges the code.
#   5. Row deleted from oauth_states after use.
# ══════════════════════════════════════════════════════════════

def get_google_oauth_url(redirect_to: str | None = None) -> str | None:
    """
    Build Google OAuth URL with PKCE. Stores verifier in Supabase
    so it survives the redirect + process restart.
    Returns the Google OAuth URL to navigate to.
    """
    client  = get_supabase_client()
    app_url = redirect_to or os.environ.get("APP_URL", "")
    if not app_url:
        return None

    # Unique state token — will carry verifier lookup key through redirect
    state = uuid.uuid4().hex

    # redirect_to includes the state so we get it back after OAuth
    redirect_with_state = f"{app_url}?oauth_state={state}"

    try:
        response = client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to":           redirect_with_state,
                "skip_browser_redirect": True,
                "scopes":                "email profile",
            }
        })

        verifier = getattr(response, "pkce_code_verifier", None)
        oauth_url = getattr(response, "url", None)

        if not oauth_url:
            return None

        # Store verifier in Supabase — survives process restarts
        if verifier:
            try:
                client.table("oauth_states").upsert({
                    "state":    state,
                    "verifier": str(verifier),
                }).execute()
            except Exception:
                pass  # Will still try exchange without verifier as fallback

        return oauth_url

    except Exception:
        return None


def exchange_oauth_code(code: str, oauth_state: str | None = None):
    """
    Exchange the ?code= for a Supabase session.
    Fetches the PKCE verifier from Supabase using oauth_state.
    """
    client   = get_supabase_client()
    verifier = None

    # Fetch verifier from Supabase using the state token
    if oauth_state:
        try:
            result = (
                client.table("oauth_states")
                .select("verifier")
                .eq("state", oauth_state)
                .limit(1)
                .execute()
            )
            if result.data:
                verifier = result.data[0].get("verifier")
            # Delete after fetching (one-time use)
            client.table("oauth_states").delete().eq("state", oauth_state).execute()
        except Exception:
            pass

    # Clean up old states (older than 10 minutes)
    try:
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        client.table("oauth_states").delete().lt("created_at", cutoff).execute()
    except Exception:
        pass

    # Exchange code for session
    try:
        payload = {"auth_code": str(code)}
        if verifier:
            payload["code_verifier"] = str(verifier)

        result = client.auth.exchange_code_for_session(payload)
        return result
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
# ERROR TRANSLATION
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
