import os

import streamlit as st
from supabase import Client, create_client


@st.cache_resource
def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY environment variables.")
    return create_client(url, key)


def get_admin_emails() -> set[str]:
    raw = os.environ.get("ADMIN_EMAILS", "")
    return {entry.strip().lower() for entry in raw.split(",") if entry.strip()}


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

    # Backward-compatible fallback if profiles table is unavailable.
    if email and email.lower() in get_admin_emails():
        return "admin"
    return "user"


def login_with_email_password(email: str, password: str):
    client = get_supabase_client()
    return client.auth.sign_in_with_password({"email": email, "password": password})


def signup_with_email_password(email: str, password: str):
    client = get_supabase_client()
    return client.auth.sign_up({"email": email, "password": password})


def logout_current_user() -> None:
    client = get_supabase_client()
    client.auth.sign_out()


def get_current_user():
    return st.session_state.get("auth_user")
