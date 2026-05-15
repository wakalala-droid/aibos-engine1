"""
AI-BOS · Login Screen (login.py)
═══════════════════════════════════════════════════════
Google OAuth handled entirely by the Supabase JS SDK
running in the browser. The JS SDK stores the PKCE
verifier in localStorage (survives redirects), completes
the exchange, then passes access_token + refresh_token
back to Python via URL query params using postMessage.

Why JS SDK instead of Python:
  - Google blocked implicit flow (response_type=token)
  - Supabase Python PKCE loses verifier on redirect
    because Streamlit restarts the Python process
  - JS SDK keeps verifier in localStorage across the
    full redirect cycle — no process restart issue
═══════════════════════════════════════════════════════
"""

import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from auth import (
    get_supabase_client,
    get_profile_role,
)

# ══════════════════════════════════════════════════════════════
# SUPABASE JS SDK — full OAuth handler
# Injects the Supabase JS SDK, initiates Google sign-in,
# handles the redirect callback, and posts tokens to Python.
# ══════════════════════════════════════════════════════════════

def _make_oauth_html(supabase_url: str, supabase_key: str, app_url: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background:#090d1e;
    display:flex; align-items:center; justify-content:center;
    min-height:100vh; font-family:'Segoe UI',sans-serif;
    padding:24px;
  }}
  .card {{
    background:#090d1e;
    border:1px solid rgba(99,179,237,.18);
    border-radius:20px;
    padding:52px 44px 44px;
    width:100%; max-width:400px;
    box-shadow:0 32px 80px rgba(0,0,0,.7);
    text-align:center;
  }}
  .logo {{
    font-size:34px; font-weight:800;
    background:linear-gradient(90deg,#60a5fa,#06b6d4);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    margin-bottom:6px; letter-spacing:-.5px;
  }}
  .tagline {{
    font-size:9px; color:#2d4a70;
    letter-spacing:.16em; text-transform:uppercase;
    margin-bottom:40px; font-family:monospace;
  }}
  .google-btn {{
    display:flex; align-items:center; justify-content:center; gap:12px;
    background:#fff; color:#1f2937;
    border-radius:12px; padding:15px 20px; width:100%;
    font-size:15px; font-weight:600;
    border:none; cursor:pointer;
    box-shadow:0 2px 8px rgba(0,0,0,.18);
    transition:box-shadow .2s, transform .15s;
    margin-bottom:20px;
  }}
  .google-btn:hover {{
    box-shadow:0 8px 24px rgba(0,0,0,.26);
    transform:translateY(-1px);
  }}
  .google-btn:disabled {{
    opacity:.6; cursor:not-allowed; transform:none;
  }}
  .hint {{
    font-size:10px; color:#2d4a70;
    font-family:monospace; line-height:1.9; margin-top:4px;
  }}
  .error {{
    background:rgba(239,68,68,.08);
    border:1px solid rgba(239,68,68,.3);
    border-left:3px solid #ef4444;
    border-radius:8px; padding:12px 16px; margin-bottom:16px;
    font-size:13px; color:#fca5a5; line-height:1.5; text-align:left;
  }}
  .spinner {{
    display:none; font-size:11px; color:#4a6285;
    font-family:monospace; margin-top:12px;
  }}
  .footer {{
    margin-top:40px; font-size:9px; color:#1a2e4a; font-family:monospace;
  }}
</style>
</head>
<body>
<div class="card">
  <div class="logo">AI-BOS</div>
  <div class="tagline">Financial Intelligence Platform</div>

  <div class="error" id="err" style="display:none"></div>

  <button class="google-btn" id="gbtn" onclick="signInWithGoogle()">
    <svg width="20" height="20" viewBox="0 0 18 18">
      <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.717v2.258h2.908C16.658 14.017 17.64 11.71 17.64 9.2z"/>
      <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/>
      <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/>
      <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z"/>
    </svg>
    Continue with Google
  </button>

  <div class="hint">
    You'll be taken to Google to sign in.<br>
    Afterwards you'll land on your dashboard.
  </div>
  <div class="spinner" id="spin">⟳ Completing sign-in…</div>

  <div class="footer">AI-BOS · Financial Intelligence Platform</div>
</div>

<script>
const SUPABASE_URL = "{supabase_url}";
const SUPABASE_KEY = "{supabase_key}";
const APP_URL      = "{app_url}";

const {{ createClient }} = supabase;
const _sb = createClient(SUPABASE_URL, SUPABASE_KEY);

function showError(msg) {{
  var el = document.getElementById('err');
  el.textContent = '⚠ ' + msg;
  el.style.display = 'block';
  document.getElementById('spin').style.display = 'none';
  document.getElementById('gbtn').disabled = false;
}}

async function signInWithGoogle() {{
  document.getElementById('gbtn').disabled = true;
  document.getElementById('err').style.display = 'none';
  document.getElementById('spin').style.display = 'block';

  const redirectTo = APP_URL || window.location.origin;

  const {{ data, error }} = await _sb.auth.signInWithOAuth({{
    provider: 'google',
    options: {{
      redirectTo: redirectTo,
      queryParams: {{ access_type: 'offline', prompt: 'consent' }},
    }}
  }});

  if (error) {{
    showError(error.message || 'Google sign-in failed. Please try again.');
  }}
  // If no error, browser navigates to Google automatically
}}

// ── Handle callback: if we're back from Google with a session ──
async function handleCallback() {{
  // The JS SDK automatically exchanges the code in the URL
  const {{ data: {{ session }}, error }} = await _sb.auth.getSession();

  if (error) {{
    showError('Sign-in could not be completed: ' + error.message);
    return;
  }}

  if (session && session.access_token) {{
    // Pass tokens to Streamlit (parent window) via URL params
    const url = new URL(window.parent.location.href);
    url.searchParams.set('sb_access_token',  session.access_token);
    url.searchParams.set('sb_refresh_token', session.refresh_token || '');
    url.searchParams.set('sb_user_email',    session.user?.email || '');
    url.searchParams.set('sb_user_id',       session.user?.id    || '');
    url.hash = '';
    try {{
      window.parent.location.replace(url.toString());
    }} catch(e) {{
      window.location.replace(url.toString());
    }}
    return;
  }}

  // Also check URL hash for implicit tokens (fallback)
  const hash = window.parent.location.hash || window.location.hash;
  if (hash && hash.includes('access_token')) {{
    const params = new URLSearchParams(hash.substring(1));
    const at = params.get('access_token');
    if (at) {{
      const {{ data: s2, error: e2 }} = await _sb.auth.setSession({{
        access_token:  at,
        refresh_token: params.get('refresh_token') || '',
      }});
      if (!e2 && s2.session) {{
        const url = new URL(window.parent.location.href);
        url.hash = '';
        url.searchParams.set('sb_access_token',  s2.session.access_token);
        url.searchParams.set('sb_refresh_token', s2.session.refresh_token || '');
        url.searchParams.set('sb_user_email',    s2.session.user?.email || '');
        url.searchParams.set('sb_user_id',       s2.session.user?.id    || '');
        try {{
          window.parent.location.replace(url.toString());
        }} catch(e) {{
          window.location.replace(url.toString());
        }}
      }}
    }}
  }}
}}

// Run callback handler on every load
handleCallback();
</script>
</body>
</html>
"""


# ══════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINTS
# ══════════════════════════════════════════════════════════════

def handle_oauth_callback():
    """
    Call at the very top of dashboard.py on every page load.
    Reads tokens passed back from the JS SDK and authenticates.
    """
    _init_login_state()
    _process_js_sdk_callback()


def render_login_screen():
    """Renders the full-page Google OAuth login handled by Supabase JS SDK."""
    _init_login_state()
    _process_js_sdk_callback()

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


def _qp(name: str) -> str:
    v = st.query_params.get(name, "")
    return (v[0] if isinstance(v, list) else v) or ""


# ══════════════════════════════════════════════════════════════
# CALLBACK PROCESSOR
# Reads tokens from URL params set by the JS SDK
# ══════════════════════════════════════════════════════════════

def _process_js_sdk_callback():
    """
    The Supabase JS SDK completes OAuth in the browser and puts
    the resulting tokens into URL query params. We read them here
    and call set_session() to authenticate in Python.
    """
    access_token  = _qp("sb_access_token")
    refresh_token = _qp("sb_refresh_token")
    user_email    = _qp("sb_user_email")
    user_id       = _qp("sb_user_id")

    if not access_token:
        return

    # Clear the tokens from the URL immediately
    st.query_params.clear()

    # If JS SDK passed user info directly, use it
    if user_id and user_email:
        try:
            db = get_supabase_client()
            db.auth.set_session(str(access_token), str(refresh_token))
        except Exception:
            pass
        _set_authenticated(str(user_id), str(user_email))
        st.rerun()
        return

    # Otherwise call set_session and extract user from response
    try:
        db      = get_supabase_client()
        session = db.auth.set_session(str(access_token), str(refresh_token))
        user    = _extract_user(session)
        if user:
            _set_authenticated(
                str(_attr(user, "id")    or ""),
                str(_attr(user, "email") or user_email),
            )
            st.rerun()
            return
    except Exception:
        pass

    st.session_state.login_error     = "Sign-in could not be completed. Please try again."
    st.session_state.show_login_page = True
    st.rerun()


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


# ══════════════════════════════════════════════════════════════
# SHARED UI HELPERS
# ══════════════════════════════════════════════════════════════

def _show_error(msg: str):
    if msg:
        st.markdown(f"""
        <div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.3);
                    border-left:3px solid #ef4444;border-radius:8px;padding:12px 16px;
                    margin-bottom:16px;font-family:'Outfit',sans-serif;font-size:13px;
                    color:#fca5a5;line-height:1.5;">⚠ {msg}</div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# SCREEN: CHECK EMAIL
# ══════════════════════════════════════════════════════════════

def _screen_check_email():
    email = st.session_state.pending_email or "your inbox"
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:center;min-height:92vh;">
    <div style="background:#090d1e;border:1px solid rgba(99,179,237,.18);border-radius:20px;
                padding:52px 44px 44px;width:100%;max-width:400px;text-align:center;
                box-shadow:0 32px 80px rgba(0,0,0,.7);">
        <div style="font-family:'Outfit',sans-serif;font-size:34px;font-weight:800;
                    background:linear-gradient(90deg,#60a5fa,#06b6d4);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    margin-bottom:6px;">AI-BOS</div>
        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                    letter-spacing:.16em;text-transform:uppercase;margin-bottom:36px;">
            Financial Intelligence Platform</div>
        <div style="font-size:52px;margin-bottom:16px;">📬</div>
        <div style="font-family:'Outfit',sans-serif;font-size:22px;font-weight:700;
                    color:#e2eeff;margin-bottom:10px;">Check your email</div>
        <div style="font-family:'Outfit',sans-serif;font-size:14px;color:#4a6285;
                    line-height:1.7;margin-bottom:24px;">
            We sent a confirmation link to<br>
            <span style="color:#60a5fa;font-weight:600;">{email}</span><br><br>
            Click the link — you'll be signed in and taken to
            the dashboard automatically.<br><br>
            <span style="font-size:12px;color:#2d4a70;">
                Can't find it? Check your spam folder.
            </span>
        </div>
    </div></div>
    """, unsafe_allow_html=True)
    if st.button("← Back to sign in", use_container_width=True):
        st.session_state.login_screen = "login"
        st.session_state.login_error  = None
        st.rerun()


# ══════════════════════════════════════════════════════════════
# SCREEN: RESET SENT
# ══════════════════════════════════════════════════════════════

def _screen_reset_sent():
    st.markdown("""
    <div style="display:flex;align-items:center;justify-content:center;min-height:92vh;">
    <div style="background:#090d1e;border:1px solid rgba(99,179,237,.18);border-radius:20px;
                padding:52px 44px 44px;width:100%;max-width:400px;text-align:center;
                box-shadow:0 32px 80px rgba(0,0,0,.7);">
        <div style="font-size:52px;margin-bottom:16px;">🔑</div>
        <div style="font-family:'Outfit',sans-serif;font-size:22px;font-weight:700;
                    color:#e2eeff;margin-bottom:10px;">Reset link sent</div>
        <div style="font-family:'Outfit',sans-serif;font-size:14px;color:#4a6285;line-height:1.7;">
            Follow the link in your email to set a new password,
            then sign in again with Google.
        </div>
    </div></div>
    """, unsafe_allow_html=True)
    if st.button("← Back to sign in", use_container_width=True):
        st.session_state.login_screen = "login"
        st.session_state.login_error  = None
        st.rerun()


# ══════════════════════════════════════════════════════════════
# SCREEN: MAIN LOGIN — JS SDK Google OAuth
# ══════════════════════════════════════════════════════════════

def _screen_login():
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", "")
    app_url      = os.environ.get("APP_URL", "")

    if st.session_state.login_error:
        _show_error(st.session_state.login_error)
        st.session_state.login_error = None

    if supabase_url and supabase_key:
        html = _make_oauth_html(supabase_url, supabase_key, app_url)
        components.html(html, height=520, scrolling=False)
    else:
        st.error("SUPABASE_URL and SUPABASE_KEY are not configured.")
