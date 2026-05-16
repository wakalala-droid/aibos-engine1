import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import io
from groq import Groq
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from engine import (
    analyse_pnl,
    forecast_cashflow,
    detect_variances,
    get_structured_analysis,
    forecast_revenue,
    detect_anomalies,
    calculate_breakeven,
    export_excel_report,
    save_chat_message,
    load_chat_history,
    build_chat_context_from_history,
    clear_chat_history,
    send_report_email,
    upsert_subscription,
    get_subscription,
)
from utils import load_financial_file
from auth import (
    get_supabase_client,
    get_current_user,
    get_profile_role,
    logout_current_user,
)
from login import handle_oauth_callback, render_login_screen

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AI-BOS · Intelligence Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════
# DESIGN SYSTEM
# ══════════════════════════════════════════════════════════════
_APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,400;0,500;1,400&family=Outfit:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [data-testid="stApp"] {
    background:#03060d !important; color:#d4ddf0 !important;
    font-family:'Outfit',sans-serif !important;
}
#MainMenu,footer,[data-testid="stDecoration"] { display:none !important; }
[data-testid="stHeader"] {
    background:#050810 !important; background-image:none !important;
}
section[data-testid="stMain"],section.main { padding-top:0.9rem !important; }
.block-container {
    padding-left:0 !important; padding-right:0 !important;
    padding-bottom:1rem !important; max-width:100% !important;
}
[data-testid="stSidebar"] {
    background:#07091a !important;
    border-right:1px solid rgba(99,179,237,.12) !important;
}
[data-testid="stHeader"] button,
[data-testid="stSidebarCollapseButton"] button,
[data-testid="collapsedControl"] button,
[data-testid="stExpandSidebarButton"] button {
    background:transparent !important; border:none !important;
    box-shadow:none !important; color:#d4ddf0 !important;
}
[data-testid="stHeader"] button:hover,
[data-testid="stSidebarCollapseButton"] button:hover {
    background:rgba(99,179,237,0.14) !important;
}
[data-testid="stMetric"] {
    background:#090d1e; border:1px solid rgba(99,179,237,.14);
    border-radius:14px; padding:18px 20px !important;
    position:relative; overflow:hidden;
}
[data-testid="stMetric"]::before {
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background:linear-gradient(90deg,#3b82f6,#06b6d4);
}
[data-testid="stMetricLabel"] {
    font-family:'DM Mono',monospace !important; font-size:10px !important;
    letter-spacing:.1em !important; color:#4a6285 !important; text-transform:uppercase !important;
}
[data-testid="stMetricValue"] {
    font-family:'Outfit',sans-serif !important; font-size:26px !important;
    font-weight:700 !important; color:#e2eeff !important;
}
[data-testid="stMetricDelta"] { font-family:'DM Mono',monospace !important; font-size:11px !important; }
section.main .stButton>button,
[data-testid="stMain"] .stButton>button,
[data-testid="stSidebarUserContent"] .stButton>button {
    background:linear-gradient(135deg,#1d4ed8,#0891b2) !important;
    color:#fff !important; border:none !important; border-radius:10px !important;
    font-family:'Outfit',sans-serif !important; font-weight:600 !important;
    font-size:14px !important; padding:10px 24px !important;
    transition:all .2s !important; letter-spacing:.02em !important;
}
section.main .stButton>button:hover,
[data-testid="stMain"] .stButton>button:hover {
    transform:translateY(-1px) !important;
    box-shadow:0 8px 24px rgba(6,182,212,.25) !important;
}
[data-testid="stFileUploader"] {
    background:#090d1e !important; border:1px dashed rgba(99,179,237,.25) !important;
    border-radius:14px !important; padding:8px !important;
}
[data-testid="stFileUploadDropzone"] { background:transparent !important; }
[data-testid="stChatInput"] textarea {
    background:#090d1e !important; border:1px solid rgba(99,179,237,.2) !important;
    border-radius:12px !important; color:#d4ddf0 !important;
    font-family:'Outfit',sans-serif !important; font-size:14px !important;
}
[data-testid="stChatMessage"] {
    background:#090d1e !important; border:1px solid rgba(99,179,237,.1) !important;
    border-radius:12px !important; margin-bottom:8px !important;
}
[data-testid="stTabs"] [role="tablist"] {
    background:transparent !important;
    border-bottom:1px solid rgba(99,179,237,.12) !important; gap:0 !important;
}
[data-testid="stTabs"] [role="tab"] {
    font-family:'DM Mono',monospace !important; font-size:11px !important;
    font-weight:500 !important; letter-spacing:.06em !important;
    color:#4a6285 !important; padding:10px 20px !important;
    border-radius:0 !important; border-bottom:2px solid transparent !important;
    text-transform:uppercase !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color:#60a5fa !important; border-bottom-color:#60a5fa !important;
    background:transparent !important;
}
[data-testid="stAlert"] {
    border-radius:10px !important; border:none !important;
    font-family:'DM Mono',monospace !important; font-size:12px !important;
}
[data-testid="stDataFrame"] {
    border:1px solid rgba(99,179,237,.12) !important;
    border-radius:12px !important; overflow:hidden !important;
}
hr { border-color:rgba(99,179,237,.1) !important; }
[data-testid="stSpinner"] { color:#60a5fa !important; }
</style>
"""
if hasattr(st, "html"):
    st.html(_APP_CSS)
else:
    st.markdown(_APP_CSS, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# CLIENTS
# ══════════════════════════════════════════════════════════════
@st.cache_resource
def get_ai_client():
    return Groq(api_key=os.environ.get("GROQ_API_KEY"))

client_ai = get_ai_client()
db = None

def _get_db():
    global db
    if db is not None:
        return db
    try:
        db = get_supabase_client()
        return db
    except Exception:
        st.error("Database unavailable. Check SUPABASE_URL and SUPABASE_KEY.")
        return None

# ══════════════════════════════════════════════════════════════
# CHART THEME
# ══════════════════════════════════════════════════════════════
CHART_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Mono", color="#6b87b0", size=11),
    xaxis=dict(gridcolor="rgba(99,179,237,.06)", linecolor="rgba(99,179,237,.1)"),
    yaxis=dict(gridcolor="rgba(99,179,237,.06)", linecolor="rgba(99,179,237,.1)"),
    margin=dict(l=0, r=0, t=32, b=0),
)

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def _augment_alerts(df, base_alerts):
    alerts = list(base_alerts)
    if len(df) < 2:
        return alerts
    cost_change   = df["costs"].pct_change().fillna(0) * 100
    margin_change = df["margin_pct"].diff().fillna(0)
    for idx in range(1, len(df)):
        month = str(df.iloc[idx]["month"])
        if cost_change.iloc[idx] > 18:
            alerts.append({"month": month, "direction": "up",
                           "change_pct": round(float(cost_change.iloc[idx]), 1), "type": "cost_spike"})
        if margin_change.iloc[idx] < -6:
            alerts.append({"month": month, "direction": "drop",
                           "change_pct": round(float(abs(margin_change.iloc[idx])), 1), "type": "margin_drop"})
    return alerts


def _cash_runway_months(df):
    burn              = (df["costs"] - df["revenue"]).clip(lower=0)
    avg_monthly_burn  = float(burn.mean()) if len(burn) else 0.0
    latest_cash_proxy = float(df["profit"].tail(3).sum()) if "profit" in df.columns else 0.0
    if avg_monthly_burn <= 0:
        return 99.0
    return max(0.0, latest_cash_proxy / avg_monthly_burn)


def _weighted_health_score(pnl, alerts, runway_months):
    margin_score   = max(0.0, min(100.0, float(pnl.get("avg_margin", 0)) * 3.2))
    alerts_penalty = min(45.0, len(alerts) * 4.0)
    runway_score   = max(0.0, min(100.0, runway_months * 10.0))
    profit_score   = 100.0 if float(pnl.get("total_profit", 0)) > 0 else 35.0
    weighted = (
        (margin_score * 0.35) + (runway_score * 0.25)
        + (profit_score * 0.20) + ((100.0 - alerts_penalty) * 0.20)
    )
    score = int(round(max(0.0, min(100.0, weighted))))
    label = ("Excellent" if score >= 85 else "Healthy" if score >= 70
             else "At Risk" if score >= 50 else "Critical")
    return score, label


def _build_pdf_report(pnl, score, label, alerts, runway_months):
    buffer = io.BytesIO()
    pdf    = canvas.Canvas(buffer, pagesize=A4)
    w, h   = A4
    y      = h - 60
    lines  = [
        "AI-BOS Executive Intelligence Report", "",
        f"Health Score: {score}/100 ({label})",
        f"Total Revenue: K{float(pnl['total_revenue']):,.0f}",
        f"Total Costs: K{float(pnl['total_costs']):,.0f}",
        f"Total Profit: K{float(pnl['total_profit']):,.0f}",
        f"Average Margin: {float(pnl['avg_margin']):.1f}%",
        f"Cash Runway (estimated): {runway_months:.1f} months",
        f"Alerts: {len(alerts)}",
        f"Best Month: {pnl['best_month']}",
        f"Worst Month: {pnl['worst_month']}",
    ]
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, lines[0])
    y -= 28
    pdf.setFont("Helvetica", 11)
    for line in lines[2:]:
        pdf.drawString(50, y, line)
        y -= 18
        if y < 70:
            pdf.showPage(); y = h - 60; pdf.setFont("Helvetica", 11)
    pdf.save()
    return buffer.getvalue()


# ══════════════════════════════════════════════════════════════
# AUTH — PKCE verifier stored in Supabase DB
# Survives process restarts, server restarts, everything.
# ══════════════════════════════════════════════════════════════
try:
    handle_oauth_callback()
except Exception:
    pass

if (
    st.session_state.get("login_error")
    and not st.session_state.get("is_authenticated", False)
    and not st.session_state.get("show_login_page", False)
):
    st.session_state.show_login_page = True

if st.session_state.get("show_login_page", False):
    render_login_screen()
    st.stop()

authenticated = st.session_state.get("is_authenticated", False)
current_user  = st.session_state.get("auth_user")
guest_mode    = False
if current_user is None:
    guest_mode   = True
    current_user = {
        "id": "guest", "email": "Guest",
        "role": "guest", "is_admin": False,
    }
else:
    try:
        latest_role = get_profile_role(current_user.get("id", ""), current_user.get("email"))
        if latest_role:
            current_user["role"]     = latest_role
            current_user["is_admin"] = latest_role == "admin"
    except Exception:
        current_user["role"]     = current_user.get("role", "user")
        current_user["is_admin"] = current_user.get("is_admin", False)
    st.session_state.auth_user = current_user

# ══════════════════════════════════════════════════════════════
# LOAD PERSISTENT CHAT ON STARTUP
# ══════════════════════════════════════════════════════════════
try:
    if "chat_loaded" not in st.session_state or not st.session_state.get("chat_loaded", False):
        if authenticated:
            try:
                _db = _get_db()
                st.session_state.chat = load_chat_history(_db, current_user.get("id", ""), limit=30) if _db else []
            except Exception:
                st.session_state.chat = []
        else:
            st.session_state.chat = []
        st.session_state.chat_loaded = True

    if "chat"        not in st.session_state: st.session_state.chat        = []
    if "pnl_context" not in st.session_state: st.session_state.pnl_context = None
    if "template_df" not in st.session_state: st.session_state.template_df = None
except Exception:
    st.session_state.chat = []
    st.session_state.chat_loaded = True
    st.session_state.pnl_context = None
    st.session_state.template_df = None

# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding:28px 24px 20px;border-bottom:1px solid rgba(99,179,237,.1);">
        <div style="font-family:'Outfit',sans-serif;font-size:22px;font-weight:800;
                    background:linear-gradient(90deg,#60a5fa,#06b6d4);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    letter-spacing:-.5px;margin-bottom:4px;">AI-BOS</div>
        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                    letter-spacing:.12em;text-transform:uppercase;">Intelligence Platform · v3.0</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    if guest_mode:
        st.markdown(f"""
        <div style="padding:0 8px 12px;">
            <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                        letter-spacing:.1em;text-transform:uppercase;">Guest mode</div>
            <div style="font-family:'Outfit',sans-serif;font-size:13px;color:#d4ddf0;
                        margin-top:4px;">{current_user['email']}</div>
            <div style="font-family:'DM Mono',monospace;font-size:9px;color:#4a6285;
                        margin-top:6px;">Sign in to save reports, chat history, and uploads.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Sign in with Google", use_container_width=True, key="sidebar_login"):
            st.session_state.show_login_page = True
            st.session_state.login_screen    = "login"
            st.rerun()
    else:
        st.markdown(f"""
        <div style="padding:0 8px 12px;">
            <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                        letter-spacing:.1em;text-transform:uppercase;">Signed in as</div>
            <div style="font-family:'Outfit',sans-serif;font-size:13px;color:#d4ddf0;
                        margin-top:4px;">{current_user['email']}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True):
            logout_current_user()
            st.session_state.auth_user        = None
            st.session_state.is_authenticated = False
            st.session_state.chat_loaded      = False
            st.rerun()

    # ── DATA SOURCE ────────────────────────────────────────
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                letter-spacing:.12em;text-transform:uppercase;padding:0 8px;margin-bottom:10px;">
        Data Source
    </div>""", unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload financial data", type=["csv", "xlsx"],
                                label_visibility="collapsed")

    if uploaded is not None and guest_mode:
        st.warning("Sign in to upload financial data and save reports.")
        if st.button("Sign in to upload", use_container_width=True, key="upload_signin"):
            st.session_state.show_login_page = True
            st.session_state.login_screen    = "login"
            st.rerun()

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                letter-spacing:.12em;text-transform:uppercase;padding:0 8px;margin-bottom:6px;">
        AI CFO · Persistent Memory
    </div>
    <div style="font-family:'Outfit',sans-serif;font-size:11px;color:#3d5a80;
                padding:0 8px;margin-bottom:10px;line-height:1.5;">
        Remembers your past conversations.
    </div>""", unsafe_allow_html=True)

    with st.container():
        for msg in st.session_state.get("chat", [])[-6:]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    if question := st.chat_input("Ask your CFO anything…"):
        st.session_state.chat = st.session_state.get("chat", [])
        st.session_state.chat.append({"role": "user", "content": question})
        if not guest_mode:
            try:
                _db = _get_db()
                if _db:
                    save_chat_message(_db, current_user.get("id", ""), "user", question)
            except Exception:
                pass

        context      = st.session_state.pnl_context or "No financial data loaded yet."
        chat_history = st.session_state.get("chat", [])
        messages     = build_chat_context_from_history(chat_history[:-1])
        messages.append({
            "role":    "user",
            "content": f"[Current data: {context}]\n\n{question}",
        })

        with st.spinner("Analysing…"):
            try:
                response = client_ai.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    timeout=30,
                )
                answer = response.choices[0].message.content
                st.session_state.chat.append({"role": "assistant", "content": answer})
                if not guest_mode:
                    try:
                        _db = _get_db()
                        if _db:
                            save_chat_message(_db, current_user.get("id", ""), "assistant", answer)
                    except Exception:
                        pass
                st.rerun()
            except Exception as e:
                st.error(f"Query failed: {e}")

    if st.session_state.get("chat"):
        if st.button("Clear Conversation", use_container_width=True):
            if not guest_mode:
                try:
                    _db = _get_db()
                    if _db:
                        clear_chat_history(_db, current_user.get("id", ""))
                except Exception:
                    pass
            st.session_state.chat = []
            st.rerun()

    # ── ANALYSIS HISTORY ───────────────────────────────────
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                letter-spacing:.12em;text-transform:uppercase;padding:0 8px;margin-bottom:10px;">
        Analysis History
    </div>""", unsafe_allow_html=True)

    if st.button("Load Past Analyses", use_container_width=True):
        if guest_mode:
            st.warning("Sign in to load your saved analyses.")
        else:
            try:
                _db = _get_db()
                if not _db:
                    st.info("Database unavailable.")
                else:
                    query = _db.table("analyses").select("*").order("created_at", desc=True).limit(8)
                    if not current_user["is_admin"]:
                        query = query.eq("user_id", current_user["id"])
                    history = query.execute()
                    if history.data:
                        for record in history.data:
                            date_str = record["created_at"][:10]
                            color    = ("#10b981" if record["health_label"] == "Excellent"
                                        else "#60a5fa" if record["health_label"] == "Healthy" else "#f59e0b")
                            st.markdown(f"""
                            <div style="background:#090d1e;border:1px solid rgba(99,179,237,.1);
                                        border-radius:10px;padding:10px 12px;margin-bottom:8px;">
                                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;">{date_str}</div>
                                <div style="font-family:'Outfit',sans-serif;font-size:13px;font-weight:600;
                                            color:#d4ddf0;margin:3px 0;">K{record['total_revenue']:,.0f} revenue</div>
                                <div style="font-family:'DM Mono',monospace;font-size:11px;color:{color};">
                                    {record['health_score']}/100 · {record['health_label']}</div>
                            </div>""", unsafe_allow_html=True)
                    else:
                        st.info("No history yet.")
            except Exception as e:
                st.error(f"Unable to load analysis history: {e}")

    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                letter-spacing:.12em;text-transform:uppercase;padding:0 8px;margin-bottom:10px;">
        📧 Weekly Report Email
    </div>""", unsafe_allow_html=True)

    if guest_mode:
        st.info("Sign in to enable email report subscriptions and saved settings.")
        with st.expander("Email Report Settings", expanded=False):
            st.markdown("""
            <div style="font-family:'DM Mono',monospace;font-size:11px;color:#4a6285;
                        padding:0 8px 12px;line-height:1.5;">
                Sign in to manage email reports, subscriptions, and saved dashboards.
            </div>""", unsafe_allow_html=True)
    else:
        _db          = _get_db()
        existing_sub = get_subscription(_db, current_user["id"]) if _db else None
        sub_email    = existing_sub["email"] if existing_sub else current_user["email"]
        sub_active   = existing_sub["active"] if existing_sub else False

        with st.expander("Email Report Settings", expanded=False):
            report_email = st.text_input("Delivery email", value=sub_email, key="report_email_input")
            freq         = st.selectbox("Frequency", ["weekly", "monthly"], key="report_freq",
                                        index=0 if not existing_sub else
                                        (0 if existing_sub.get("frequency") == "weekly" else 1))
            col_sub, col_unsub = st.columns(2)

            with col_sub:
                if st.button("Subscribe", use_container_width=True, key="btn_subscribe"):
                    _db = _get_db()
                    if _db:
                        ok = upsert_subscription(_db, current_user["id"], report_email.strip(), freq, active=True)
                        if ok:
                            st.success(f"Subscribed ✓")
                        else:
                            st.error("Failed — check Supabase table.")
                    else:
                        st.error("Subscription unavailable.")

            with col_unsub:
                if existing_sub and st.button("Unsubscribe", use_container_width=True, key="btn_unsub"):
                    _db = _get_db()
                    if _db:
                        upsert_subscription(_db, current_user["id"], sub_email, freq, active=False)
                        st.info("Unsubscribed.")
                    else:
                        st.error("Subscription unavailable.")

            if st.button("📤 Send Test Report Now", use_container_width=True, key="btn_test_email"):
                _test_df = st.session_state.get("_last_df")
                if _test_df is None:
                    st.warning("Upload data first to send a test report.")
                else:
                    with st.spinner("Building and sending…"):
                        try:
                            _t_pnl    = analyse_pnl(_test_df)
                            _t_fc     = forecast_cashflow(_test_df)
                            _t_alerts = _augment_alerts(_test_df, detect_variances(_test_df))
                            _t_runway = _cash_runway_months(_test_df)
                            _t_score, _t_label = _weighted_health_score(_t_pnl, _t_alerts, _t_runway)
                            _t_pdf    = _build_pdf_report(_t_pnl, _t_score, _t_label, _t_alerts, _t_runway)
                            ok, msg   = send_report_email(report_email.strip(), _t_pdf)
                            if ok:
                                st.success(msg)
                            else:
                                st.error(msg)
                        except Exception as ex:
                            st.error(f"Error: {ex}")

            if sub_active:
                st.markdown(f"""
                <div style="background:#090d1e;border:1px solid rgba(16,185,129,.2);
                            border-radius:8px;padding:8px 12px;margin-top:6px;">
                    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#10b981;">
                        ● ACTIVE · {existing_sub.get('frequency','weekly').upper()} reports → {sub_email}</div>
                </div>""", unsafe_allow_html=True)

    # ── ADMIN ──────────────────────────────────────────────
    if current_user["is_admin"]:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                    letter-spacing:.12em;text-transform:uppercase;padding:0 8px;margin-bottom:8px;">
            Admin Control
        </div>""", unsafe_allow_html=True)
        if st.button("View User Activity", use_container_width=True):
            try:
                _db = _get_db()
                if not _db:
                    st.info("Database unavailable.")
                else:
                    users = (_db.table("profiles").select("id,email,last_seen_at")
                              .order("last_seen_at", desc=True).limit(20).execute())
                    for item in users.data or []:
                        st.caption(f"{item.get('email','?')} · {item.get('last_seen_at','N/A')}")
            except Exception:
                st.info("No profiles table yet.")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <a href="https://wa.me/260973759352" target="_blank" style="
        display:block;background:linear-gradient(135deg,#1d4ed8,#0891b2);
        color:#fff;text-decoration:none;border-radius:10px;padding:11px 16px;
        text-align:center;font-family:'Outfit',sans-serif;font-size:13px;
        font-weight:600;letter-spacing:.02em;margin:0 0 8px;">
        💬 Get Full Enterprise Access
    </a>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════
with st.container():
    st.markdown("""
    <div style="padding:28px 40px 24px;border-bottom:1px solid rgba(99,179,237,.08);
                display:flex;align-items:center;justify-content:space-between;">
        <div>
            <div style="font-family:'Outfit',sans-serif;font-size:28px;font-weight:800;
                        color:#e2eeff;letter-spacing:-.5px;margin-bottom:4px;">
                Financial Intelligence Command Centre</div>
            <div style="font-family:'DM Mono',monospace;font-size:10px;color:#2d4a70;
                        letter-spacing:.1em;text-transform:uppercase;">
                AI-BOS · Engine 1 · v3.0 — Excel · Persistent Chat · Scheduled Reports</div>
        </div>
        <div style="font-family:'DM Mono',monospace;font-size:10px;color:#2d4a70;
                    text-align:right;letter-spacing:.08em;">
            SYSTEM STATUS<br><span style="color:#10b981;">● OPERATIONAL</span>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── GUEST BANNER ───────────────────────────────────────
    if guest_mode and not st.session_state.get("guest_banner_dismissed", False):
        st.markdown("""
        <div style="background:linear-gradient(135deg,#090d1e 0%,#0d1530 100%);
                    border:1px solid rgba(99,179,237,.2);border-left:3px solid #3b82f6;
                    margin:0 40px;border-radius:14px;padding:20px 28px;">
            <div style="font-family:'Outfit',sans-serif;font-size:18px;font-weight:600;
                        color:#e2eeff;margin-bottom:4px;">Welcome to AI-BOS</div>
            <div style="font-family:'Outfit',sans-serif;font-size:14px;color:#4a6285;
                        line-height:1.5;margin-bottom:16px;">Sign in to save reports, chat history, and unlock full features.</div>
        </div>""", unsafe_allow_html=True)

        col_guest, col_signin = st.columns([1, 1])
        with col_guest:
            if st.button("Continue as Guest", use_container_width=True, key="guest_continue"):
                st.session_state.guest_banner_dismissed = True
                st.rerun()
        with col_signin:
            if st.button("Sign In with Google", use_container_width=True, key="guest_signin"):
                st.session_state.show_login_page = True
                st.session_state.login_screen    = "login"
                st.rerun()

    template_df    = st.session_state.get("template_df")
    data_available = uploaded is not None or template_df is not None

    # ── NO DATA STATE ──────────────────────────────────────
    if not data_available:
        st.markdown("""
        <div style="display:flex;align-items:center;justify-content:center;min-height:60vh;padding:40px;">
            <div style="text-align:center;max-width:520px;">
                <div style="font-size:56px;margin-bottom:24px;opacity:.25;">⚡</div>
                <div style="font-family:'Outfit',sans-serif;font-size:22px;font-weight:700;
                            color:#e2eeff;margin-bottom:12px;">Upload your financial data to begin</div>
                <div style="font-family:'Outfit',sans-serif;font-size:14px;color:#2d4a70;
                            line-height:1.7;margin-bottom:32px;">
                    CSV or Excel with <span style="color:#60a5fa;font-family:'DM Mono',monospace;font-size:12px;">month</span>,
                    <span style="color:#60a5fa;font-family:'DM Mono',monospace;font-size:12px;">revenue</span>,
                    <span style="color:#60a5fa;font-family:'DM Mono',monospace;font-size:12px;">costs</span> columns.
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;text-align:left;">
                    <div style="background:#090d1e;border:1px solid rgba(99,179,237,.1);border-radius:12px;padding:16px;">
                        <div style="font-size:20px;margin-bottom:8px;">📊</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:12px;font-weight:600;color:#d4ddf0;margin-bottom:4px;">P&L Analysis</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:11px;color:#2d4a70;">Profit · margin · variance</div>
                    </div>
                    <div style="background:#090d1e;border:1px solid rgba(99,179,237,.1);border-radius:12px;padding:16px;">
                        <div style="font-size:20px;margin-bottom:8px;">📥</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:12px;font-weight:600;color:#d4ddf0;margin-bottom:4px;">Excel Export</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:11px;color:#2d4a70;">Formatted workbook · 5 sheets</div>
                    </div>
                    <div style="background:#090d1e;border:1px solid rgba(99,179,237,.1);border-radius:12px;padding:16px;">
                        <div style="font-size:20px;margin-bottom:8px;">📧</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:12px;font-weight:600;color:#d4ddf0;margin-bottom:4px;">Weekly Email</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:11px;color:#2d4a70;">Scheduled PDF delivery</div>
                    </div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)
        if st.button("Create Blank Dataset In-App"):
            st.session_state.template_df = pd.DataFrame(
                {"month": ["Jan 2026", "Feb 2026", "Mar 2026"], "revenue": [0, 0, 0], "costs": [0, 0, 0]}
            )
            st.rerun()

    # ── DATA LOADED STATE ──────────────────────────────────
    else:
        if uploaded is not None:
            try:
                df = load_financial_file(uploaded)
            except Exception as e:
                st.error(f"Failed to load file: {e}")
                st.stop()
        else:
            df = template_df.copy()
            if "profit" not in df.columns:
                df["profit"] = (pd.to_numeric(df["revenue"], errors="coerce").fillna(0)
                                - pd.to_numeric(df["costs"],   errors="coerce").fillna(0))
            if "margin_pct" not in df.columns:
                denom = pd.to_numeric(df["revenue"], errors="coerce").replace(0, pd.NA)
                df["margin_pct"] = ((pd.to_numeric(df["profit"], errors="coerce") / denom) * 100).fillna(0).round(1)

        st.session_state["_last_df"] = df.copy()

        with st.expander("DATA STUDIO · Edit or Build Your Dataset", expanded=False):
            edited_df = st.data_editor(
                df[["month", "revenue", "costs", "profit", "margin_pct"]].copy(),
                num_rows="dynamic", use_container_width=True, key="engine1_data_editor",
            )
            edited_df["revenue"]    = pd.to_numeric(edited_df["revenue"], errors="coerce").fillna(0)
            edited_df["costs"]      = pd.to_numeric(edited_df["costs"],   errors="coerce").fillna(0)
            edited_df["profit"]     = edited_df["revenue"] - edited_df["costs"]
            denom                   = edited_df["revenue"].replace(0, pd.NA)
            edited_df["margin_pct"] = ((edited_df["profit"] / denom) * 100).fillna(0).round(1)
            df = edited_df
            st.session_state.template_df = df.copy()
            st.session_state["_last_df"] = df.copy()

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown("""
            <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                        letter-spacing:.1em;text-transform:uppercase;margin-bottom:8px;">
                Export Options</div>""", unsafe_allow_html=True)

            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                st.download_button(
                    "⬇ Download CSV",
                    data=df.to_csv(index=False).encode("utf-8"),
                    file_name="aibos_financials.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with dl_col2:
                if st.button("⬇ Download Excel Report", use_container_width=True, key="excel_dl_btn"):
                    with st.spinner("Building formatted workbook…"):
                        try:
                            _pnl_ex = analyse_pnl(df)
                            _al_ex  = _augment_alerts(df, detect_variances(df))
                            _rn_ex  = _cash_runway_months(df)
                            _sc_ex, _lb_ex = _weighted_health_score(_pnl_ex, _al_ex, _rn_ex)
                            _fc_ex  = forecast_revenue(df)
                            _an_ex  = detect_anomalies(df)
                            _be_ex  = calculate_breakeven(df)
                            _xlsx   = export_excel_report(
                                df, _pnl_ex, _sc_ex, _lb_ex, _al_ex, _rn_ex,
                                forecast_data=_fc_ex, anomaly_data=_an_ex, breakeven_data=_be_ex,
                            )
                            st.session_state["_xlsx_bytes"] = _xlsx
                            st.toast("Excel ready — click below to download ✓", icon="✓")
                        except Exception as ex:
                            st.error(f"Excel build failed: {ex}")

                if st.session_state.get("_xlsx_bytes"):
                    st.download_button(
                        "📥 Save Excel File",
                        data=st.session_state["_xlsx_bytes"],
                        file_name="aibos_intelligence_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="excel_save_btn",
                    )

        # ── RUN ENGINE ────────────────────────────────────
        try:
            pnl           = analyse_pnl(df)
            forecast      = forecast_cashflow(df)
            base_alerts   = detect_variances(df)
            alerts        = _augment_alerts(df, base_alerts)
            runway_months = _cash_runway_months(df)
            score, label  = _weighted_health_score(pnl, alerts, runway_months)
        except Exception as e:
            st.error(f"Engine error: {e}. Check your file has month, revenue, and costs columns.")
            st.stop()

        st.session_state.pnl_context = (
            f"Revenue K{pnl['total_revenue']:,}, Profit K{pnl['total_profit']:,}, "
            f"Margin {pnl['avg_margin']}%, Health {score}/100 ({label}), "
            f"Best month {pnl['best_month']}, Worst month {pnl['worst_month']}, "
            f"{len(alerts)} variance alerts."
        )

        if not guest_mode:
            try:
                _db = _get_db()
                if _db:
                    _db.table("analyses").insert({
                        "user_id": current_user["id"], "user_email": current_user["email"],
                        "total_revenue": float(pnl["total_revenue"]), "total_costs": float(pnl["total_costs"]),
                        "total_profit": float(pnl["total_profit"]),   "avg_margin":  float(pnl["avg_margin"]),
                        "health_score": int(score), "health_label": label,
                        "best_month": pnl["best_month"], "worst_month": pnl["worst_month"],
                        "alerts_count": len(alerts),
                    }).execute()
                    st.toast("Intelligence report saved ✓", icon="✓")
            except Exception:
                pass

        # ── HEALTH BANNER ─────────────────────────────────
        score_color = ("#10b981" if label == "Excellent" else "#3b82f6" if label == "Healthy"
                       else "#f59e0b" if label == "At Risk" else "#ef4444")
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#090d1e 0%,#0d1530 100%);
                    border:1px solid {score_color}22;border-left:3px solid {score_color};
                    margin:24px 40px 0;border-radius:14px;padding:20px 28px;
                    display:flex;align-items:center;gap:32px;">
            <div>
                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                            letter-spacing:.12em;text-transform:uppercase;margin-bottom:4px;">
                    Business Health Index</div>
                <div style="font-family:'Outfit',sans-serif;font-size:42px;font-weight:800;
                            color:{score_color};line-height:1;">
                    {score}<span style="font-size:20px;color:#2d4a70;">/100</span></div>
            </div>
            <div style="width:1px;height:48px;background:rgba(99,179,237,.1);"></div>
            <div>
                <div style="font-family:'Outfit',sans-serif;font-size:18px;font-weight:700;
                            color:{score_color};margin-bottom:4px;">{label}</div>
                <div style="font-family:'DM Mono',monospace;font-size:11px;color:#2d4a70;">
                    {len(alerts)} alert{'s' if len(alerts)!=1 else ''} · {len(df)} months analysed</div>
            </div>
            <div style="margin-left:auto;text-align:right;">
                <div style="font-family:'DM Mono',monospace;font-size:10px;color:#2d4a70;margin-bottom:4px;">BEST PERIOD</div>
                <div style="font-family:'Outfit',sans-serif;font-size:16px;font-weight:600;color:#d4ddf0;">{pnl['best_month']}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-family:'DM Mono',monospace;font-size:10px;color:#2d4a70;margin-bottom:4px;">NEEDS ATTENTION</div>
                <div style="font-family:'Outfit',sans-serif;font-size:16px;font-weight:600;color:#d4ddf0;">{pnl['worst_month']}</div>
            </div>
        </div>""", unsafe_allow_html=True)

        # ── KPI ROW ───────────────────────────────────────
        st.markdown("<div style='padding:20px 40px 0;'>", unsafe_allow_html=True)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total Revenue",   f"K{pnl['total_revenue']:,.0f}")
        c2.metric("Total Costs",     f"K{pnl['total_costs']:,.0f}")
        c3.metric("Net Profit",      f"K{pnl['total_profit']:,.0f}")
        c4.metric("Avg Margin",      f"{pnl['avg_margin']}%")
        c5.metric("Variance Alerts", len(alerts), "Detected" if alerts else "Clean")
        c6.metric("Cash Runway",     f"{runway_months:.1f} mo", "Estimated")
        st.markdown("</div>", unsafe_allow_html=True)

        # ══════════════════════════════════════════════════
        # TABS
        # ══════════════════════════════════════════════════
        st.markdown("<div style='padding:24px 40px 0;'>", unsafe_allow_html=True)
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "FINANCIAL OVERVIEW", "CASH INTELLIGENCE", "VARIANCE ANALYSIS",
            "STRATEGIC BRIEF",    "DATA STUDIO",       "REVENUE FORECAST",
            "ANOMALY INTEL",      "BREAKEVEN",
        ])

        with tab1:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            col_left, col_right = st.columns([3, 2])
            with col_left:
                fig_rev = go.Figure()
                fig_rev.add_trace(go.Scatter(x=df["month"], y=df["revenue"], name="Revenue",
                    mode="lines", line=dict(color="#3b82f6", width=2),
                    fill="tozeroy", fillcolor="rgba(59,130,246,.06)"))
                fig_rev.add_trace(go.Scatter(x=df["month"], y=df["costs"], name="Costs",
                    mode="lines", line=dict(color="#ef4444", width=2, dash="dot"),
                    fill="tozeroy", fillcolor="rgba(239,68,68,.04)"))
                fig_rev.update_layout(
                    title=dict(text="REVENUE vs COSTS TREND",
                               font=dict(family="DM Mono", size=10, color="#2d4a70")),
                    legend=dict(font=dict(family="DM Mono", size=10)), **CHART_THEME)
                st.plotly_chart(fig_rev, use_container_width=True)
            with col_right:
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number", value=pnl["avg_margin"],
                    title=dict(text="AVG PROFIT MARGIN %",
                               font=dict(family="DM Mono", size=10, color="#2d4a70")),
                    number=dict(suffix="%", font=dict(family="Outfit", size=36, color="#e2eeff")),
                    gauge=dict(
                        axis=dict(range=[0, 50], tickcolor="#2d4a70",
                                  tickfont=dict(family="DM Mono", size=9)),
                        bar=dict(color=score_color), bgcolor="rgba(0,0,0,0)", borderwidth=0,
                        steps=[dict(range=[0, 10],  color="rgba(239,68,68,.12)"),
                               dict(range=[10, 25], color="rgba(245,158,11,.12)"),
                               dict(range=[25, 50], color="rgba(16,185,129,.12)")],
                        threshold=dict(line=dict(color="#60a5fa", width=2), value=pnl["avg_margin"]),
                    )))
                fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="DM Mono", color="#6b87b0"),
                    margin=dict(l=20, r=20, t=48, b=20), height=220)
                st.plotly_chart(fig_gauge, use_container_width=True)
                bar_colors = ["#10b981" if v >= 0 else "#ef4444" for v in df["profit"]]
                fig_profit = go.Figure(go.Bar(
                    x=df["month"], y=df["profit"], marker_color=bar_colors, name="Net Profit"))
                fig_profit.update_layout(title=dict(text="NET PROFIT BY PERIOD",
                    font=dict(family="DM Mono", size=10, color="#2d4a70")),
                    **CHART_THEME, height=200)
                st.plotly_chart(fig_profit, use_container_width=True)

        with tab2:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            runway_color = "#10b981" if runway_months >= 6 else "#f59e0b" if runway_months >= 3 else "#ef4444"
            st.markdown(f"""
            <div style="background:#090d1e;border:1px solid {runway_color}33;border-radius:12px;
                        padding:14px 18px;margin-bottom:12px;">
                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                            letter-spacing:.1em;">CASH RUNWAY ESTIMATE</div>
                <div style="font-family:'Outfit',sans-serif;font-size:24px;font-weight:700;
                            color:{runway_color};margin-top:4px;">{runway_months:.1f} months</div>
            </div>""", unsafe_allow_html=True)
            forecast_months = [f"Month +{f['month_ahead']}" for f in forecast]
            forecast_values = [f["projected_cash"] for f in forecast]
            forecast_colors = ["#10b981" if f["status"] == "✓ Positive" else "#ef4444" for f in forecast]
            fig_cf = go.Figure()
            fig_cf.add_trace(go.Bar(x=forecast_months, y=forecast_values,
                                    marker_color=forecast_colors, name="Projected Cash"))
            fig_cf.update_layout(title=dict(text="30 / 60 / 90 DAY CASH FLOW PROJECTION",
                font=dict(family="DM Mono", size=10, color="#2d4a70")), **CHART_THEME, height=280)
            st.plotly_chart(fig_cf, use_container_width=True)
            for item in forecast:
                status_color = "#10b981" if item["status"] == "✓ Positive" else "#ef4444"
                st.markdown(f"""
                <div style="background:#090d1e;border:1px solid rgba(99,179,237,.08);border-radius:10px;
                            padding:14px 20px;margin-bottom:8px;display:flex;
                            align-items:center;justify-content:space-between;">
                    <div>
                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                                    letter-spacing:.1em;">MONTH +{item['month_ahead']} PROJECTION</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:20px;font-weight:700;
                                    color:#e2eeff;margin-top:4px;">K{item['projected_cash']:,}</div>
                    </div>
                    <div style="font-family:'DM Mono',monospace;font-size:12px;
                                color:{status_color};font-weight:500;">{item['status']}</div>
                </div>""", unsafe_allow_html=True)

        with tab3:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            if not alerts:
                st.markdown("""
                <div style="background:#090d1e;border:1px solid rgba(16,185,129,.2);
                            border-radius:14px;padding:32px;text-align:center;">
                    <div style="font-size:32px;margin-bottom:12px;">✓</div>
                    <div style="font-family:'Outfit',sans-serif;font-size:16px;font-weight:600;
                                color:#10b981;margin-bottom:6px;">No Significant Variances Detected</div>
                    <div style="font-family:'DM Mono',monospace;font-size:11px;color:#2d4a70;">
                        All periods within normal operating parameters</div>
                </div>""", unsafe_allow_html=True)
            else:
                for alert in alerts:
                    dc = "#ef4444" if alert["direction"] in ("drop", "down") else "#f59e0b"
                    di = "▼" if alert["direction"] in ("drop", "down") else "▲"
                    at = alert.get("type", "revenue_variance").replace("_", " ").upper()
                    st.markdown(f"""
                    <div style="background:#090d1e;border:1px solid {dc}33;
                                border-left:3px solid {dc};border-radius:12px;
                                padding:16px 20px;margin-bottom:10px;">
                        <div style="display:flex;align-items:center;justify-content:space-between;">
                            <div>
                                <div style="font-family:'DM Mono',monospace;font-size:9px;
                                            color:#2d4a70;letter-spacing:.1em;margin-bottom:6px;">
                                    {at} · {str(alert['month']).upper()}</div>
                                <div style="font-family:'Outfit',sans-serif;font-size:15px;
                                            font-weight:600;color:#e2eeff;">
                                    Revenue {alert['direction'].title()} of {abs(alert['change_pct'])}%</div>
                            </div>
                            <div style="font-family:'Outfit',sans-serif;font-size:28px;
                                        font-weight:800;color:{dc};">
                                {di} {abs(alert['change_pct'])}%</div>
                        </div>
                    </div>""", unsafe_allow_html=True)
            if len(df) > 1:
                changes = df["revenue"].diff().fillna(0).tolist()
                colors  = ["#10b981" if c >= 0 else "#ef4444" for c in changes]
                fig_wf  = go.Figure(go.Bar(x=df["month"], y=changes,
                                           marker_color=colors, name="Revenue Change"))
                fig_wf.update_layout(title=dict(text="PERIOD-ON-PERIOD REVENUE CHANGE",
                    font=dict(family="DM Mono", size=10, color="#2d4a70")),
                    **CHART_THEME, height=220)
                st.plotly_chart(fig_wf, use_container_width=True)

        with tab4:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            dl1, dl2 = st.columns(2)
            with dl1:
                pdf_bytes = _build_pdf_report(pnl, score, label, alerts, runway_months)
                st.download_button("📄 Download PDF Report", data=pdf_bytes,
                                   file_name="aibos_executive_report.pdf",
                                   mime="application/pdf", use_container_width=True)
            with dl2:
                if st.button("📊 Build Excel Report", use_container_width=True, key="excel_tab4"):
                    with st.spinner("Generating…"):
                        try:
                            _fc_t4 = forecast_revenue(df)
                            _an_t4 = detect_anomalies(df)
                            _be_t4 = calculate_breakeven(df)
                            _xl_t4 = export_excel_report(
                                df, pnl, score, label, alerts, runway_months,
                                forecast_data=_fc_t4, anomaly_data=_an_t4, breakeven_data=_be_t4,
                            )
                            st.session_state["_xlsx_bytes"] = _xl_t4
                            st.toast("Excel ready ✓", icon="✓")
                        except Exception as ex:
                            st.error(f"Excel error: {ex}")
                if st.session_state.get("_xlsx_bytes"):
                    st.download_button(
                        "📥 Save Excel",
                        data=st.session_state["_xlsx_bytes"],
                        file_name="aibos_intelligence_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True, key="excel_save_tab4",
                    )
            st.markdown("""
            <div style="background:#090d1e;border:1px solid rgba(99,179,237,.1);
                        border-radius:14px;padding:24px 28px;margin:16px 0;">
                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                            letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px;">
                    AI Strategic Intelligence Engine</div>
                <div style="font-family:'Outfit',sans-serif;font-size:14px;color:#6b87b0;line-height:1.7;">
                    Calibrated recommendations from your data — not generic advice.</div>
            </div>""", unsafe_allow_html=True)
            if st.button("⚡ Generate Executive Intelligence Brief", use_container_width=True):
                with st.spinner("Running strategic analysis…"):
                    try:
                        structured   = get_structured_analysis(pnl, alerts)
                        priority_map = {
                            "high":   ("#ef4444", "HIGH PRIORITY",   "IMMEDIATE ACTION"),
                            "medium": ("#f59e0b", "MEDIUM PRIORITY", "THIS QUARTER"),
                            "low":    ("#10b981", "LOW PRIORITY",    "STRATEGIC WATCH"),
                        }
                        for i, rec in enumerate(structured, 1):
                            p = rec.get("priority", "medium").lower()
                            color, p_label, timeline = priority_map.get(p, priority_map["medium"])
                            st.markdown(f"""
                            <div style="background:#090d1e;border:1px solid {color}22;
                                        border-top:2px solid {color};border-radius:14px;
                                        padding:22px 26px;margin-bottom:14px;">
                                <div style="display:flex;align-items:center;
                                            justify-content:space-between;margin-bottom:14px;">
                                    <div style="display:flex;align-items:center;gap:12px;">
                                        <div style="font-family:'DM Mono',monospace;font-size:9px;
                                                    color:{color};letter-spacing:.12em;
                                                    background:{color}15;padding:4px 10px;
                                                    border-radius:20px;">{p_label}</div>
                                        <div style="font-family:'DM Mono',monospace;font-size:9px;
                                                    color:#2d4a70;">{timeline}</div>
                                    </div>
                                    <div style="font-family:'DM Mono',monospace;font-size:9px;
                                                color:#2d4a70;">REC {i:02d} / {len(structured):02d}</div>
                                </div>
                                <div style="font-family:'Outfit',sans-serif;font-size:17px;
                                            font-weight:700;color:#e2eeff;margin-bottom:10px;">
                                    {rec.get('title','')}</div>
                                <div style="font-family:'Outfit',sans-serif;font-size:13px;
                                            color:#6b87b0;line-height:1.7;">
                                    {rec.get('recommendation','')}</div>
                            </div>""", unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")

        with tab5:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            st.markdown("""
            <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                        letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px;">
                Full Period Breakdown</div>""", unsafe_allow_html=True)
            display_cols = [c for c in ["month","revenue","costs","profit","margin_pct"] if c in df.columns]
            st.dataframe(
                df[display_cols].style.format({
                    "revenue": "K{:,.0f}", "costs": "K{:,.0f}",
                    "profit": "K{:,.0f}",  "margin_pct": "{:.1f}%",
                }),
                use_container_width=True, hide_index=True,
            )
            st.caption("Use the DATA STUDIO expander above to edit rows and export.")

        with tab6:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            with st.spinner("Running linear regression forecast…"):
                fc = forecast_revenue(df)
            if "error" in fc:
                st.warning(fc["error"])
            else:
                trend_color = ("#10b981" if fc["trend"] == "upward" else
                               "#ef4444" if fc["trend"] == "downward" else "#f59e0b")
                trend_icon  = "↑" if fc["trend"] == "upward" else "↓" if fc["trend"] == "downward" else "→"
                st.markdown(f"""
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px;">
                    <div style="background:#090d1e;border:1px solid {trend_color}33;
                                border-left:3px solid {trend_color};border-radius:12px;padding:16px 20px;">
                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                                    letter-spacing:.1em;margin-bottom:4px;">TREND</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:22px;font-weight:700;
                                    color:{trend_color};">{trend_icon} {fc['trend'].title()}</div>
                    </div>
                    <div style="background:#090d1e;border:1px solid rgba(99,179,237,.14);
                                border-radius:12px;padding:16px 20px;">
                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                                    letter-spacing:.1em;margin-bottom:4px;">MONTHLY GROWTH</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:22px;font-weight:700;
                                    color:#e2eeff;">{fc['growth_rate']:+.1f}%</div>
                    </div>
                    <div style="background:#090d1e;border:1px solid rgba(99,179,237,.14);
                                border-radius:12px;padding:16px 20px;">
                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                                    letter-spacing:.1em;margin-bottom:4px;">MODEL CONFIDENCE</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:22px;font-weight:700;
                                    color:#e2eeff;">{fc['confidence']}/100</div>
                    </div>
                </div>""", unsafe_allow_html=True)
                hist_months = [str(m) for m in df["month"].tolist()]
                hist_rev    = df["revenue"].tolist()
                fc_months   = [p["month"] for p in fc["forecast"]]
                predicted   = [p["predicted"] for p in fc["forecast"]]
                low         = [p["low"]  for p in fc["forecast"]]
                high        = [p["high"] for p in fc["forecast"]]
                fig_fc = go.Figure()
                fig_fc.add_trace(go.Scatter(x=hist_months, y=hist_rev, name="Historical",
                    mode="lines+markers", line=dict(color="#3b82f6", width=2), marker=dict(size=5)))
                fig_fc.add_trace(go.Scatter(x=fc_months, y=high, name="Best case",
                    mode="lines", line=dict(color="#10b981", width=1, dash="dot")))
                fig_fc.add_trace(go.Scatter(x=fc_months, y=low, name="Worst case",
                    mode="lines", line=dict(color="#ef4444", width=1, dash="dot"),
                    fill="tonexty", fillcolor="rgba(59,130,246,0.06)"))
                fig_fc.add_trace(go.Scatter(x=fc_months, y=predicted, name="Forecast",
                    mode="lines+markers", line=dict(color="#06b6d4", width=2.5),
                    marker=dict(size=6, symbol="diamond")))
                fig_fc.update_layout(
                    title=dict(text="REVENUE FORECAST · LINEAR REGRESSION + CONFIDENCE BAND",
                               font=dict(family="DM Mono", size=10, color="#2d4a70")),
                    legend=dict(font=dict(family="DM Mono", size=10)), **CHART_THEME, height=320)
                st.plotly_chart(fig_fc, use_container_width=True)
                st.markdown(f"""
                <div style="background:#090d1e;border:1px solid rgba(6,182,212,.15);
                            border-left:3px solid #06b6d4;border-radius:12px;
                            padding:16px 20px;margin-top:4px;">
                    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                                letter-spacing:.1em;margin-bottom:8px;">AI FORECAST NARRATIVE</div>
                    <div style="font-family:'Outfit',sans-serif;font-size:14px;color:#9bb0cc;
                                line-height:1.7;">{fc['ai_explanation']}</div>
                </div>""", unsafe_allow_html=True)
                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                for pt in fc["forecast"]:
                    st.markdown(f"""
                    <div style="background:#090d1e;border:1px solid rgba(99,179,237,.08);
                                border-radius:10px;padding:12px 18px;margin-bottom:6px;
                                display:flex;align-items:center;justify-content:space-between;">
                        <div style="font-family:'DM Mono',monospace;font-size:11px;color:#4a6285;">{pt['month']}</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:16px;font-weight:700;color:#e2eeff;">
                            K{pt['predicted']:,}</div>
                        <div style="font-family:'DM Mono',monospace;font-size:11px;color:#2d4a70;">
                            K{pt['low']:,} – K{pt['high']:,}</div>
                    </div>""", unsafe_allow_html=True)

        with tab7:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            z_thresh = st.slider("Detection sensitivity (z-score threshold)",
                                 min_value=1.5, max_value=3.5, value=2.0, step=0.5)
            with st.spinner("Running statistical anomaly scan…"):
                anomalies = detect_anomalies(df, z_threshold=z_thresh)
            if not anomalies:
                st.markdown("""
                <div style="background:#090d1e;border:1px solid rgba(16,185,129,.2);
                            border-radius:14px;padding:32px;text-align:center;">
                    <div style="font-size:28px;margin-bottom:10px;">✓</div>
                    <div style="font-family:'Outfit',sans-serif;font-size:16px;font-weight:600;
                                color:#10b981;">No anomalies at this sensitivity level</div>
                </div>""", unsafe_allow_html=True)
            else:
                critical = sum(1 for a in anomalies if a["severity"] == "critical")
                high_c   = sum(1 for a in anomalies if a["severity"] == "high")
                medium_c = sum(1 for a in anomalies if a["severity"] == "medium")
                st.markdown(f"""
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;
                            gap:10px;margin-bottom:20px;">
                    <div style="background:#090d1e;border:1px solid rgba(99,179,237,.14);
                                border-radius:10px;padding:14px;text-align:center;">
                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;margin-bottom:4px;">TOTAL</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:24px;font-weight:700;color:#e2eeff;">{len(anomalies)}</div>
                    </div>
                    <div style="background:#090d1e;border:1px solid rgba(239,68,68,.2);
                                border-radius:10px;padding:14px;text-align:center;">
                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;margin-bottom:4px;">CRITICAL</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:24px;font-weight:700;color:#ef4444;">{critical}</div>
                    </div>
                    <div style="background:#090d1e;border:1px solid rgba(245,158,11,.2);
                                border-radius:10px;padding:14px;text-align:center;">
                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;margin-bottom:4px;">HIGH</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:24px;font-weight:700;color:#f59e0b;">{high_c}</div>
                    </div>
                    <div style="background:#090d1e;border:1px solid rgba(99,179,237,.2);
                                border-radius:10px;padding:14px;text-align:center;">
                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;margin-bottom:4px;">MEDIUM</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:24px;font-weight:700;color:#60a5fa;">{medium_c}</div>
                    </div>
                </div>""", unsafe_allow_html=True)
                sev_colors = {"critical":"#ef4444","high":"#f59e0b","medium":"#60a5fa","low":"#10b981"}
                for a in anomalies:
                    color = sev_colors.get(a["severity"], "#60a5fa")
                    icon  = "▼" if a["direction"] == "drop" else "▲"
                    st.markdown(f"""
                    <div style="background:#090d1e;border:1px solid {color}22;
                                border-left:3px solid {color};border-radius:12px;
                                padding:16px 20px;margin-bottom:10px;">
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
                            <div style="display:flex;align-items:center;gap:10px;">
                                <div style="font-family:'DM Mono',monospace;font-size:9px;color:{color};
                                            background:{color}15;padding:3px 10px;border-radius:20px;
                                            letter-spacing:.1em;">{a['severity'].upper()}</div>
                                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;">
                                    {a['metric'].upper()} · {a['month'].upper()}</div>
                            </div>
                            <div style="font-family:'Outfit',sans-serif;font-size:22px;
                                        font-weight:800;color:{color};">{icon} {abs(a['change_pct'])}%</div>
                        </div>
                        <div style="font-family:'DM Mono',monospace;font-size:10px;
                                    color:#2d4a70;margin-bottom:6px;">z-score: {a['z_score']}σ</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:13px;
                                    color:#9bb0cc;line-height:1.6;">
                            <span style="color:#4a6285;font-size:11px;font-family:'DM Mono',monospace;">ROOT CAUSE: </span>
                            {a['root_cause']}</div>
                    </div>""", unsafe_allow_html=True)

        with tab8:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            fixed_pct = st.slider("Fixed costs as % of total costs",
                                  min_value=10, max_value=90, value=40, step=5) / 100
            be        = calculate_breakeven(df, fixed_cost_pct=fixed_pct)
            above_be  = be["current_avg_revenue"] >= be["breakeven_revenue"]
            be_color  = "#10b981" if above_be else "#ef4444"
            be_status = "ABOVE BREAKEVEN" if above_be else "BELOW BREAKEVEN"
            st.markdown(f"""
            <div style="background:#090d1e;border:1px solid {be_color}33;
                        border-left:3px solid {be_color};border-radius:14px;
                        padding:20px 28px;margin-bottom:20px;
                        display:flex;align-items:center;gap:32px;">
                <div>
                    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                                letter-spacing:.12em;margin-bottom:4px;">BREAKEVEN REVENUE</div>
                    <div style="font-family:'Outfit',sans-serif;font-size:36px;font-weight:800;
                                color:{be_color};">K{be['breakeven_revenue']:,}</div>
                    <div style="font-family:'DM Mono',monospace;font-size:10px;color:#2d4a70;margin-top:4px;">per month</div>
                </div>
                <div style="width:1px;height:48px;background:rgba(99,179,237,.1);"></div>
                <div>
                    <div style="font-family:'DM Mono',monospace;font-size:9px;color:{be_color};
                                letter-spacing:.1em;margin-bottom:4px;">{be_status}</div>
                    <div style="font-family:'Outfit',sans-serif;font-size:18px;font-weight:700;color:#e2eeff;">
                        Safety margin: {be['margin_of_safety_pct']}%</div>
                </div>
                <div style="margin-left:auto;text-align:right;">
                    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;margin-bottom:4px;">
                        CONTRIBUTION MARGIN</div>
                    <div style="font-family:'Outfit',sans-serif;font-size:18px;font-weight:700;color:#e2eeff;">
                        {be['contribution_margin_ratio']}%</div>
                </div>
            </div>""", unsafe_allow_html=True)
            col_l, col_r = st.columns([3, 2])
            with col_l:
                fig_be = go.Figure()
                fig_be.add_trace(go.Bar(
                    x=["Fixed Costs","Variable Costs","Avg Revenue","Breakeven"],
                    y=[be["fixed_costs"],be["variable_costs"],
                       be["current_avg_revenue"],be["breakeven_revenue"]],
                    marker_color=["#f59e0b","#ef4444","#3b82f6","#10b981"]))
                fig_be.add_hline(y=be["breakeven_revenue"], line_dash="dash",
                                 line_color="#10b981", line_width=1.5,
                                 annotation_text="Breakeven",
                                 annotation_font=dict(family="DM Mono", size=10, color="#10b981"))
                fig_be.update_layout(title=dict(text="COST STRUCTURE vs BREAKEVEN",
                    font=dict(family="DM Mono", size=10, color="#2d4a70")), **CHART_THEME, height=280)
                st.plotly_chart(fig_be, use_container_width=True)
            with col_r:
                st.markdown("""
                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                            letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px;">
                    What-If: Cost Increases</div>""", unsafe_allow_html=True)
                for s in be["scenarios"]:
                    s_color = "#10b981" if s["status"] == "safe" else "#ef4444"
                    st.markdown(f"""
                    <div style="background:#090d1e;border:1px solid {s_color}22;border-radius:10px;
                                padding:10px 14px;margin-bottom:6px;
                                display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;">
                                +{s['cost_increase_pct']}% costs</div>
                            <div style="font-family:'Outfit',sans-serif;font-size:14px;
                                        font-weight:600;color:#e2eeff;">
                                BE: K{s['new_breakeven']:,}</div>
                        </div>
                        <div style="font-family:'DM Mono',monospace;font-size:10px;color:{s_color};">
                            {s['status'].upper()}</div>
                    </div>""", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#090d1e;border:1px solid rgba(6,182,212,.15);
                        border-left:3px solid #06b6d4;border-radius:12px;
                        padding:16px 20px;margin-top:8px;">
                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                            letter-spacing:.1em;margin-bottom:8px;">AI INSIGHT</div>
                <div style="font-family:'Outfit',sans-serif;font-size:14px;color:#9bb0cc;
                            line-height:1.7;">{be['ai_insight']}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # ── RAW DATA ──────────────────────────────────────
        st.markdown("<div style='padding:0 40px 40px;'>", unsafe_allow_html=True)
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        with st.expander("RAW DATA · Full Period Breakdown"):
            display_cols = [c for c in ["month","revenue","costs","profit","margin_pct"] if c in df.columns]
            st.dataframe(
                df[display_cols].style.format({
                    "revenue": "K{:,.0f}", "costs": "K{:,.0f}",
                    "profit": "K{:,.0f}",  "margin_pct": "{:.1f}%",
                }),
                use_container_width=True, hide_index=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
