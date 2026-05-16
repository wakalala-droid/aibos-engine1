"""
AI-BOS · Login Screen (login.py)
═══════════════════════════════════════════════════════
Clean original UI restored.
Google OAuth — PKCE verifier stored in Supabase DB.
═══════════════════════════════════════════════════════
"""

import os
import streamlit as st
import pandas as pd
from auth import (
    get_supabase_client,
    get_profile_role,
    get_google_oauth_url,
    exchange_oauth_code,
)

# ══════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINTS
# ══════════════════════════════════════════════════════════════

def handle_oauth_callback():
    """Call at the very top of dashboard.py on every page load."""
    _init_login_state()
    _handle_oauth_callback()


def render_login_screen():
    """Renders the Google-only login card."""
    _inject_css()
    _init_login_state()
    _handle_oauth_callback()

    if st.session_state.is_authenticated:
        st.session_state.show_login_page = False
        st.rerun()
        return

    screen = st.session_state.get("login_screen", "login")
    if screen == "check_email":
        _screen_check_email()
    elif screen == "reset_sent":
        _screen_reset_sent()
    else:
        _screen_login()


# ══════════════════════════════════════════════════════════════
# CSS — original clean design restored
# ══════════════════════════════════════════════════════════════
_LOGIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,400;0,500;1,400&family=Outfit:wght@300;400;500;600;700;800&display=swap');

.aibos-login-wrap {
    display:flex; align-items:center; justify-content:center;
    min-height:88vh; padding:24px;
}
.aibos-login-card {
    background:#090d1e;
    border:1px solid rgba(99,179,237,.15);
    border-radius:20px;
    padding:44px 40px 36px;
    width:100%; max-width:420px;
    box-shadow:0 24px 64px rgba(0,0,0,.5);
}
.aibos-logo {
    font-family:'Outfit',sans-serif;
    font-size:32px; font-weight:800;
    background:linear-gradient(90deg,#60a5fa,#06b6d4);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    margin-bottom:4px; letter-spacing:-.5px;
}
.aibos-tagline {
    font-family:'DM Mono',monospace;
    font-size:9px; color:#2d4a70;
    letter-spacing:.14em; text-transform:uppercase;
    margin-bottom:32px;
}
.aibos-google-btn {
    display:flex; align-items:center; justify-content:center; gap:10px;
    background:#fff; color:#1f2937; text-decoration:none;
    border-radius:10px; padding:11px 20px; width:100%;
    font-family:'Outfit',sans-serif; font-size:14px; font-weight:600;
    border:none; cursor:pointer; transition:box-shadow .2s;
    box-shadow:0 1px 3px rgba(0,0,0,.12);
}
.aibos-google-btn:hover {
    box-shadow:0 4px 16px rgba(0,0,0,.18);
    text-decoration:none; color:#1f2937;
}
.aibos-error {
    background:rgba(239,68,68,.08);
    border:1px solid rgba(239,68,68,.25);
    border-left:3px solid #ef4444;
    border-radius:8px; padding:10px 14px; margin-bottom:14px;
    font-family:'Outfit',sans-serif; font-size:13px; color:#fca5a5;
    line-height:1.5;
}
.aibos-success {
    background:rgba(16,185,129,.08);
    border:1px solid rgba(16,185,129,.25);
    border-left:3px solid #10b981;
    border-radius:8px; padding:10px 14px; margin-bottom:14px;
    font-family:'Outfit',sans-serif; font-size:13px; color:#6ee7b7;
    line-height:1.5;
}
.aibos-info {
    background:rgba(59,130,246,.08);
    border:1px solid rgba(59,130,246,.25);
    border-left:3px solid #3b82f6;
    border-radius:8px; padding:10px 14px; margin-bottom:14px;
    font-family:'Outfit',sans-serif; font-size:13px; color:#93c5fd;
    line-height:1.5;
}
.aibos-confirm-icon { font-size:52px; margin-bottom:16px; }
.aibos-confirm-title {
    font-family:'Outfit',sans-serif; font-size:22px;
    font-weight:700; color:#e2eeff; margin-bottom:10px;
}
.aibos-confirm-body {
    font-family:'Outfit',sans-serif; font-size:14px;
    color:#4a6285; line-height:1.7; margin-bottom:24px;
}
.aibos-confirm-email { color:#60a5fa; font-weight:600; }
</style>
"""

def _inject_css():
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════

def _init_login_state():
    defaults = {
        "login_screen":     "login",
        "login_error":      None,
        "login_success":    None,
        "pending_email":    "",
        "auth_user":        None,
        "is_authenticated": False,
        "chat_loaded":      False,
        "show_login_page":  False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _set_authenticated(user_id: str, email: str):
    db   = get_supabase_client()
    role = get_profile_role(user_id, email)
    st.session_state.auth_user = {
        "id":       user_id,
        "email":    email,
        "role":     role,
        "is_admin": role == "admin",
    }
    st.session_state.is_authenticated = True
    st.session_state.chat_loaded      = False
    st.session_state.show_login_page  = False
    st.session_state.login_error      = None
    try:
        db.table("profiles").upsert({
            "id":           user_id,
            "email":        email,
            "role":         role,
            "last_seen_at": pd.Timestamp.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass


def _extract_user(result):
    if result is None:
        return None
    if isinstance(result, dict):
        u = result.get("user")
        if u: return u
        s = result.get("session")
        if isinstance(s, dict): return s.get("user")
        return getattr(s, "user", None) if s else None
    if hasattr(result, "user") and result.user:
        return result.user
    if hasattr(result, "session"):
        s = result.session
        return s.get("user") if isinstance(s, dict) else getattr(s, "user", None)
    return None


def _attr(obj, name):
    if obj is None: return None
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def _qp(name: str) -> str:
    v = st.query_params.get(name, "")
    return (v[0] if isinstance(v, list) else v) or ""


# ══════════════════════════════════════════════════════════════
# OAUTH CALLBACK
# ══════════════════════════════════════════════════════════════

def _handle_oauth_callback():
    code        = _qp("code")
    oauth_state = _qp("oauth_state")

    if not code:
        return

    st.query_params.clear()

    with st.spinner("Completing sign-in…"):
        response = exchange_oauth_code(code, oauth_state or None)

    user = _extract_user(response)
    if user:
        _set_authenticated(
            str(_attr(user, "id")    or ""),
            str(_attr(user, "email") or ""),
        )
        st.rerun()
        return

    st.session_state.login_error     = "Sign-in could not be completed. Please try again."
    st.session_state.show_login_page = True
    st.rerun()


# ══════════════════════════════════════════════════════════════
# UI HELPERS
# ══════════════════════════════════════════════════════════════

def _card_open():
    st.markdown(
        '<div class="aibos-login-wrap"><div class="aibos-login-card">',
        unsafe_allow_html=True,
    )

def _card_close():
    st.markdown("</div></div>", unsafe_allow_html=True)

def _logo():
    st.markdown("""
    <div class="aibos-logo">AI-BOS</div>
    <div class="aibos-tagline">Financial Intelligence Platform</div>
    """, unsafe_allow_html=True)

def _show_error(msg: str):
    if msg:
        st.markdown(f'<div class="aibos-error">⚠ {msg}</div>', unsafe_allow_html=True)

def _show_success(msg: str):
    if msg:
        st.markdown(f'<div class="aibos-success">✓ {msg}</div>', unsafe_allow_html=True)

def _show_info(msg: str):
    if msg:
        st.markdown(f'<div class="aibos-info">ℹ {msg}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# SCREEN: CHECK EMAIL
# ══════════════════════════════════════════════════════════════

def _screen_check_email():
    _card_open()
    _logo()
    email = st.session_state.pending_email or "your inbox"
    st.markdown(f"""
    <div style="text-align:center;padding:8px 0 24px;">
        <div class="aibos-confirm-icon">📬</div>
        <div class="aibos-confirm-title">Check your email</div>
        <div class="aibos-confirm-body">
            We sent a confirmation link to<br>
            <span class="aibos-confirm-email">{email}</span><br><br>
            Click the link — you'll be signed in and taken to
            the dashboard automatically.<br><br>
            <span style="font-size:12px;color:#2d4a70;">
                Can't find it? Check your spam folder.
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Back to sign in", use_container_width=True):
        st.session_state.login_screen = "login"
        st.session_state.login_error  = None
        st.rerun()
    _card_close()


# ══════════════════════════════════════════════════════════════
# SCREEN: RESET SENT
# ══════════════════════════════════════════════════════════════

def _screen_reset_sent():
    _card_open()
    _logo()
    st.markdown("""
    <div style="text-align:center;padding:8px 0 24px;">
        <div class="aibos-confirm-icon">🔑</div>
        <div class="aibos-confirm-title">Reset link sent</div>
        <div class="aibos-confirm-body">
            Follow the link in your email to set a new password,
            then sign in again with Google.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Back to sign in", use_container_width=True):
        st.session_state.login_screen = "login"
        st.session_state.login_error  = None
        st.rerun()
    _card_close()


# ══════════════════════════════════════════════════════════════
# SCREEN: MAIN LOGIN — original clean design
# ══════════════════════════════════════════════════════════════

def _screen_login():
    _card_open()
    _logo()

    if st.session_state.login_error:
        _show_error(st.session_state.login_error)
        st.session_state.login_error = None

    if st.session_state.get("login_success"):
        _show_success(st.session_state.login_success)
        st.session_state.login_success = None

    app_url   = os.environ.get("APP_URL", "")
    oauth_url = get_google_oauth_url(redirect_to=app_url or None)

    if oauth_url:
        st.markdown(f"""
        <a href="{oauth_url}" class="aibos-google-btn" target="_self">
            <svg width="18" height="18" viewBox="0 0 18 18">
                <path fill="#4285F4"
                    d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209
                    1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567
                    2.684-3.874 2.684-6.615z"/>
                <path fill="#34A853"
                    d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344
                    0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/>
                <path fill="#FBBC05"
                    d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996
                    8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/>
                <path fill="#EA4335"
                    d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891
                    11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 6.29C4.672
                    4.163 6.656 3.58 9 3.58z"/>
            </svg>
            Continue with Google
        </a>
        """, unsafe_allow_html=True)
    else:
        _show_info("Google login is not configured. Set SUPABASE_URL, SUPABASE_KEY and APP_URL.")

    # Footer
    st.markdown("""
    <div style="margin-top:24px;text-align:center;
                font-family:'DM Mono',monospace;font-size:9px;color:#1e3050;">
        AI-BOS · Financial Intelligence Platform
    </div>""", unsafe_allow_html=True)

    _card_close()
