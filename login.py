"""
AI-BOS · Login Screen  (login.py)
═══════════════════════════════════════════════════════
Google OAuth only — implicit flow — no PKCE.
Sign in → straight to dashboard, no email/password form.

Flow:
  1. User clicks "Continue with Google"
  2. Google authenticates, redirects back with #access_token in hash
  3. JS bridge (injected via components.html) converts hash → ?access_token=
  4. Streamlit reruns, Python reads ?access_token, calls set_session()
  5. _set_authenticated() fires, show_login_page=False, st.rerun() → dashboard
═══════════════════════════════════════════════════════
"""

import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from auth import (
    get_supabase_client,
    get_profile_role,
    get_google_oauth_url,
)

# ══════════════════════════════════════════════════════════════
# JS BRIDGE
# Runs in the Streamlit component iframe (allow-same-origin).
# Reads the Supabase implicit-flow hash fragment and rewrites the
# parent URL so Python can pick up the tokens as query params.
# Injected on EVERY page load via handle_oauth_callback() so it
# fires even before render_login_screen() is called.
# ══════════════════════════════════════════════════════════════
_OAUTH_BRIDGE_JS = """
<script>
(function() {
    // Read the hash from the parent window (main Streamlit page)
    var hash = '';
    try { hash = window.parent.location.hash; } catch(e) {}
    if (!hash) { try { hash = window.location.hash; } catch(e) {} }
    if (!hash || hash.length < 2) return;

    var p = new URLSearchParams(hash.substring(1));
    var at = p.get('access_token');
    if (!at) return;

    // Build new URL with tokens as query params so Python can read them
    var url;
    try { url = new URL(window.parent.location.href); }
    catch(e) { url = new URL(window.location.href); }

    url.hash = '';
    url.searchParams.set('access_token',  at);
    url.searchParams.set('refresh_token', p.get('refresh_token') || '');
    url.searchParams.set('sb_type',       p.get('type')          || '');

    try { window.parent.location.replace(url.toString()); }
    catch(e) { window.location.replace(url.toString()); }
})();
</script>
"""

# ══════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINTS
# ══════════════════════════════════════════════════════════════

def handle_oauth_callback():
    """
    ALWAYS call this at the top of dashboard.py.
    Injects the JS bridge (every load) and processes any tokens in the URL.
    """
    _init_login_state()
    # Always inject bridge — even when not showing login screen,
    # so the hash→query conversion fires on the callback page load.
    try:
        components.html(_OAUTH_BRIDGE_JS, height=0, scrolling=False)
    except Exception:
        pass
    _process_callback()


def render_login_screen():
    """Renders the Google-only login card."""
    _inject_css()
    _init_login_state()

    # Inject bridge again inside login screen (belt-and-suspenders)
    try:
        components.html(_OAUTH_BRIDGE_JS, height=0, scrolling=False)
    except Exception:
        pass

    _process_callback()

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
# CSS
# ══════════════════════════════════════════════════════════════
_LOGIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Outfit:wght@300;400;500;600;700;800&display=swap');

.aibos-login-wrap {
    display:flex; align-items:center; justify-content:center;
    min-height:92vh; padding:24px;
}
.aibos-login-card {
    background:#090d1e;
    border:1px solid rgba(99,179,237,.18);
    border-radius:20px;
    padding:52px 44px 44px;
    width:100%; max-width:400px;
    box-shadow:0 32px 80px rgba(0,0,0,.7);
}
.aibos-logo {
    font-family:'Outfit',sans-serif;
    font-size:34px; font-weight:800;
    background:linear-gradient(90deg,#60a5fa,#06b6d4);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    margin-bottom:6px; letter-spacing:-.5px;
}
.aibos-tagline {
    font-family:'DM Mono',monospace;
    font-size:9px; color:#2d4a70;
    letter-spacing:.16em; text-transform:uppercase;
    margin-bottom:40px;
}
.aibos-google-btn {
    display:flex; align-items:center; justify-content:center; gap:12px;
    background:#ffffff; color:#1f2937; text-decoration:none;
    border-radius:12px; padding:15px 20px; width:100%;
    font-family:'Outfit',sans-serif; font-size:15px; font-weight:600;
    border:none; cursor:pointer;
    transition:box-shadow .2s, transform .15s;
    box-shadow:0 2px 8px rgba(0,0,0,.18);
    margin-bottom:24px;
}
.aibos-google-btn:hover {
    box-shadow:0 8px 24px rgba(0,0,0,.26);
    transform:translateY(-1px);
    text-decoration:none; color:#1f2937;
}
.aibos-error {
    background:rgba(239,68,68,.08);
    border:1px solid rgba(239,68,68,.3);
    border-left:3px solid #ef4444;
    border-radius:8px; padding:12px 16px; margin-bottom:16px;
    font-family:'Outfit',sans-serif; font-size:13px; color:#fca5a5;
    line-height:1.5;
}
.aibos-info {
    background:rgba(59,130,246,.08);
    border:1px solid rgba(59,130,246,.25);
    border-left:3px solid #3b82f6;
    border-radius:8px; padding:12px 16px; margin-bottom:16px;
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
    """Persist auth, fetch role, clear login, push to dashboard."""
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
    st.session_state.show_login_page  = False  # ← exit login
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
        if u:
            return u
        s = result.get("session")
        if isinstance(s, dict):
            return s.get("user")
        return getattr(s, "user", None) if s else None
    if hasattr(result, "user") and result.user:
        return result.user
    if hasattr(result, "session"):
        s = result.session
        return s.get("user") if isinstance(s, dict) else getattr(s, "user", None)
    return None


def _attr(obj, name):
    if obj is None:
        return None
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def _qp(name: str) -> str:
    v = st.query_params.get(name, "")
    return (v[0] if isinstance(v, list) else v) or ""


# ══════════════════════════════════════════════════════════════
# CORE CALLBACK PROCESSOR
# ══════════════════════════════════════════════════════════════

def _process_callback():
    """
    Reads tokens from URL query params (put there by the JS bridge)
    or a PKCE code. On success → dashboard. On failure → login + error.
    """
    db = get_supabase_client()

    access_token  = _qp("access_token")
    refresh_token = _qp("refresh_token")
    sb_type       = _qp("sb_type")
    code          = _qp("code")

    # Nothing to process
    if not access_token and not code:
        return

    # ── Implicit flow: access_token in query params ─────────────────
    if access_token:
        st.query_params.clear()

        # Recovery = password reset link, don't auto-login
        if sb_type == "recovery":
            st.session_state.login_screen    = "reset_sent"
            st.session_state.show_login_page = True
            st.rerun()
            return

        try:
            session = db.auth.set_session(str(access_token), str(refresh_token))
            user    = _extract_user(session)
            if user:
                _set_authenticated(
                    str(_attr(user, "id")    or ""),
                    str(_attr(user, "email") or ""),
                )
                st.rerun()   # ✅ → dashboard
                return
        except Exception:
            pass

        # set_session failed
        st.session_state.login_error     = "Google sign-in could not be completed. Please try again."
        st.session_state.show_login_page = True
        st.rerun()
        return

    # ── PKCE fallback: ?code= in URL ────────────────────────────────
    # (Should not happen with implicit flow, but handle gracefully)
    if code:
        st.query_params.clear()
        try:
            response = db.auth.exchange_code_for_session({"auth_code": str(code)})
            user     = _extract_user(response)
            if user:
                _set_authenticated(
                    str(_attr(user, "id")    or ""),
                    str(_attr(user, "email") or ""),
                )
                st.rerun()   # ✅ → dashboard
                return
        except Exception:
            pass

        st.session_state.login_error     = "Google sign-in could not be completed. Please try again."
        st.session_state.show_login_page = True
        st.rerun()


# ══════════════════════════════════════════════════════════════
# SHARED UI HELPERS
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
    if st.button("← Back", use_container_width=True):
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
    if st.button("← Back to sign in", use_container_width=True):
        st.session_state.login_screen = "login"
        st.session_state.login_error  = None
        st.rerun()
    _card_close()


# ══════════════════════════════════════════════════════════════
# SCREEN: MAIN — Google button only
# ══════════════════════════════════════════════════════════════

def _screen_login():
    _card_open()
    _logo()

    if st.session_state.login_error:
        _show_error(st.session_state.login_error)
        st.session_state.login_error = None

    app_url   = os.environ.get("APP_URL", "")
    oauth_url = get_google_oauth_url(redirect_to=app_url or None)

    if oauth_url:
        st.markdown(f"""
        <a href="{oauth_url}" class="aibos-google-btn" target="_self">
            <svg width="20" height="20" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.717v2.258h2.908C16.658 14.017 17.64 11.71 17.64 9.2z"/>
                <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/>
                <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/>
                <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z"/>
            </svg>
            Continue with Google
        </a>
        <div style="text-align:center;font-family:'DM Mono',monospace;font-size:10px;
                    color:#2d4a70;line-height:1.9;">
            You'll be taken to Google to sign in.<br>
            Afterwards you'll land on your dashboard.
        </div>
        """, unsafe_allow_html=True)
    else:
        _show_info("Google login is not configured. Set SUPABASE_URL, SUPABASE_KEY, and APP_URL.")

    st.markdown("""
    <div style="margin-top:40px;text-align:center;
                font-family:'DM Mono',monospace;font-size:9px;color:#1a2e4a;">
        AI-BOS · Financial Intelligence Platform
    </div>""", unsafe_allow_html=True)

    _card_close()
