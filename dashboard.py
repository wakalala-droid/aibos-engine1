import streamlit as st
import pandas as pd
import plotly.express as px
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
)
from utils import load_financial_file
from auth import (
    get_supabase_client,
    get_current_user,
    get_profile_role,
    login_with_email_password,
    logout_current_user,
    signup_with_email_password,
)

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
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════
# DESIGN SYSTEM
# ══════════════════════════════════════════════════════════════
_APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,400;0,500;1,400&family=Outfit:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stApp"] {
    background:#03060d !important;
    color: #d4ddf0 !important;
    font-family: 'Outfit', sans-serif !important;
}

#MainMenu { display: none !important; }
footer { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

[data-testid="stHeader"] {
    background: #050810 !important;
    background-image: none !important;
    pointer-events: auto !important;
}

section[data-testid="stMain"], section.main { padding-top: 0.9rem !important; }
.block-container {
    padding-left: 0 !important;
    padding-right: 0 !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}

[data-testid="stSidebar"] {
    background: #07091a !important;
    border-right: 1px solid rgba(99,179,237,.12) !important;
    pointer-events: auto !important;
}

[data-testid="stHeader"] button,
[data-testid="stSidebarCollapseButton"] button,
[data-testid="collapsedControl"] button,
[data-testid="stExpandSidebarButton"] button {
    background: transparent !important;
    background-image: none !important;
    border: none !important;
    box-shadow: none !important;
    color: #d4ddf0 !important;
    transform: none !important;
}
[data-testid="stHeader"] button:hover,
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="collapsedControl"] button:hover,
[data-testid="stExpandSidebarButton"] button:hover {
    transform: none !important;
    background: rgba(99,179,237,0.14) !important;
    box-shadow: none !important;
}

.js-plotly-plot .plotly, .plot-container { background: transparent !important; }

[data-testid="stMetric"] {
    background: #090d1e;
    border: 1px solid rgba(99,179,237,.14);
    border-radius: 14px;
    padding: 18px 20px !important;
    position: relative;
    overflow: hidden;
}
[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #3b82f6, #06b6d4);
}
[data-testid="stMetricLabel"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: .1em !important;
    color: #4a6285 !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Outfit', sans-serif !important;
    font-size: 26px !important;
    font-weight: 700 !important;
    color: #e2eeff !important;
}
[data-testid="stMetricDelta"] { font-family: 'DM Mono', monospace !important; font-size: 11px !important; }

section.main .stButton > button,
[data-testid="stMain"] .stButton > button,
[data-testid="stSidebarUserContent"] .stButton > button,
[data-baseweb="modal"] .stButton > button,
div[role="dialog"] .stButton > button {
    background: linear-gradient(135deg, #1d4ed8, #0891b2) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 10px 24px !important;
    transition: all .2s !important;
    letter-spacing: .02em !important;
}
section.main .stButton > button:hover,
[data-testid="stMain"] .stButton > button:hover,
[data-testid="stSidebarUserContent"] .stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(6,182,212,.25) !important;
}

[data-testid="stFileUploader"] {
    background: #090d1e !important;
    border: 1px dashed rgba(99,179,237,.25) !important;
    border-radius: 14px !important;
    padding: 8px !important;
}
[data-testid="stFileUploadDropzone"] { background: transparent !important; }

[data-testid="stChatInput"] textarea {
    background: #090d1e !important;
    border: 1px solid rgba(99,179,237,.2) !important;
    border-radius: 12px !important;
    color: #d4ddf0 !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 14px !important;
}
[data-testid="stChatMessage"] {
    background: #090d1e !important;
    border: 1px solid rgba(99,179,237,.1) !important;
    border-radius: 12px !important;
    margin-bottom: 8px !important;
}

[data-testid="stTabs"] [role="tablist"] {
    background: transparent !important;
    border-bottom: 1px solid rgba(99,179,237,.12) !important;
    gap: 0 !important;
}
[data-testid="stTabs"] [role="tab"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    letter-spacing: .06em !important;
    color: #4a6285 !important;
    padding: 10px 20px !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
    text-transform: uppercase !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #60a5fa !important;
    border-bottom-color: #60a5fa !important;
    background: transparent !important;
}

[data-testid="stAlert"] {
    border-radius: 10px !important;
    border: none !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 12px !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid rgba(99,179,237,.12) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}
hr { border-color: rgba(99,179,237,.1) !important; }
[data-testid="stSpinner"] { color: #60a5fa !important; }
[data-testid="toastContainer"] { font-family: 'DM Mono', monospace !important; }
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
db = get_supabase_client()

# ══════════════════════════════════════════════════════════════
# CHART THEME
# ══════════════════════════════════════════════════════════════
CHART_THEME = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='DM Mono', color='#6b87b0', size=11),
    xaxis=dict(gridcolor='rgba(99,179,237,.06)', linecolor='rgba(99,179,237,.1)'),
    yaxis=dict(gridcolor='rgba(99,179,237,.06)', linecolor='rgba(99,179,237,.1)'),
    margin=dict(l=0, r=0, t=32, b=0),
)

# ══════════════════════════════════════════════════════════════
# HELPERS (unchanged from your original)
# ══════════════════════════════════════════════════════════════
def _auth_error_text(error):
    msg = str(error).lower()
    if "invalid login credentials" in msg:
        return "Invalid email/password. Check email confirmation is disabled in Supabase Auth settings."
    if "email not confirmed" in msg:
        return "Email not confirmed. Confirm from your inbox or disable confirmation in Supabase."
    return str(error)


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
    burn = (df["costs"] - df["revenue"]).clip(lower=0)
    avg_monthly_burn  = float(burn.mean()) if len(burn) else 0.0
    latest_cash_proxy = float(df["profit"].tail(3).sum()) if "profit" in df.columns else 0.0
    if avg_monthly_burn <= 0:
        return 99.0
    return max(0.0, latest_cash_proxy / avg_monthly_burn)


def _weighted_health_score(pnl, alerts, runway_months):
    margin_score       = max(0.0, min(100.0, float(pnl.get("avg_margin", 0)) * 3.2))
    alerts_penalty     = min(45.0, len(alerts) * 4.0)
    runway_score       = max(0.0, min(100.0, runway_months * 10.0))
    profitability_score = 100.0 if float(pnl.get("total_profit", 0)) > 0 else 35.0
    weighted = (
        (margin_score * 0.35) + (runway_score * 0.25)
        + (profitability_score * 0.20) + ((100.0 - alerts_penalty) * 0.20)
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


def _ensure_auth_state():
    if "auth_user"        not in st.session_state: st.session_state.auth_user        = None
    if "is_authenticated" not in st.session_state: st.session_state.is_authenticated = False


def _render_login_screen():
    st.markdown("""
    <div style="padding:64px 32px 24px;text-align:center;">
        <div style="font-family:'Outfit',sans-serif;font-size:36px;font-weight:800;
                    background:linear-gradient(90deg,#60a5fa,#06b6d4);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    margin-bottom:10px;">AI-BOS</div>
        <div style="font-family:'DM Mono',monospace;font-size:10px;color:#2d4a70;
                    letter-spacing:.14em;text-transform:uppercase;">Secure Command Centre Access</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        mode     = st.radio("Mode", ["Sign In", "Create Account"], horizontal=True, label_visibility="collapsed")
        email    = st.text_input("Email", placeholder="you@company.com")
        password = st.text_input("Password", type="password")

        if mode == "Sign In":
            if st.button("Enter Command Centre", use_container_width=True):
                try:
                    result = login_with_email_password(email.strip(), password)
                    user   = result.user
                    role   = get_profile_role(user.id, user.email)
                    st.session_state.auth_user = {"id": user.id, "email": user.email,
                                                   "role": role, "is_admin": role == "admin"}
                    st.session_state.is_authenticated = True
                    try:
                        db.table("profiles").upsert({"id": user.id, "email": user.email,
                                                      "role": role,
                                                      "last_seen_at": pd.Timestamp.utcnow().isoformat()}).execute()
                    except Exception:
                        pass
                    st.success("Signed in successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {_auth_error_text(e)}")
        else:
            if st.button("Create Account", use_container_width=True):
                try:
                    signup_with_email_password(email.strip(), password)
                    try:
                        result = login_with_email_password(email.strip(), password)
                        user   = result.user
                        role   = get_profile_role(user.id, user.email)
                        st.session_state.auth_user = {"id": user.id, "email": user.email,
                                                       "role": role, "is_admin": role == "admin"}
                        st.session_state.is_authenticated = True
                        st.success("Account created. Welcome to the dashboard.")
                        st.rerun()
                    except Exception as login_error:
                        st.success("Account created.")
                        st.warning(_auth_error_text(login_error))
                except Exception as e:
                    st.error(f"Signup failed: {_auth_error_text(e)}")


# ══════════════════════════════════════════════════════════════
# AUTH GATE
# ══════════════════════════════════════════════════════════════
_ensure_auth_state()
current_user = get_current_user()
if not st.session_state.is_authenticated or not current_user:
    _render_login_screen()
    st.stop()

latest_role = get_profile_role(current_user["id"], current_user.get("email"))
st.session_state.auth_user["role"]     = latest_role
st.session_state.auth_user["is_admin"] = latest_role == "admin"
current_user = st.session_state.auth_user

try:
    db.table("profiles").upsert({"id": current_user["id"], "email": current_user["email"],
                                  "role": current_user.get("role", "user"),
                                  "last_seen_at": pd.Timestamp.utcnow().isoformat()}).execute()
except Exception:
    pass

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
                    letter-spacing:.12em;text-transform:uppercase;">Intelligence Platform · v2.0</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
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
        st.rerun()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                letter-spacing:.12em;text-transform:uppercase;padding:0 8px;margin-bottom:10px;">
        Data Source
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload financial data", type=["csv", "xlsx"],
                                 label_visibility="collapsed")

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                letter-spacing:.12em;text-transform:uppercase;padding:0 8px;margin-bottom:10px;">
        Intelligence Query
    </div>
    <div style="font-family:'Outfit',sans-serif;font-size:12px;color:#3d5a80;
                padding:0 8px;margin-bottom:12px;line-height:1.6;">
        Ask your business data anything.
    </div>
    """, unsafe_allow_html=True)

    if "chat"        not in st.session_state: st.session_state.chat        = []
    if "pnl_context" not in st.session_state: st.session_state.pnl_context = None

    with st.container():
        for msg in st.session_state.chat[-6:]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    if question := st.chat_input("e.g. Why did March outperform?"):
        st.session_state.chat.append({"role": "user", "content": question})
        context = st.session_state.pnl_context or "No financial data loaded yet."
        with st.spinner("Analysing..."):
            try:
                response = client_ai.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are an expert CFO and business intelligence analyst. Be concise, precise, and cite specific numbers."},
                        {"role": "user",   "content": f"Context: {context}\n\nQuestion: {question}"}
                    ], timeout=30)
                answer = response.choices[0].message.content
                st.session_state.chat.append({"role": "assistant", "content": answer})
                st.rerun()
            except Exception as e:
                st.error(f"Query failed: {e}")

    if st.session_state.chat:
        if st.button("Clear Conversation", use_container_width=True):
            st.session_state.chat = []
            st.rerun()

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                letter-spacing:.12em;text-transform:uppercase;padding:0 8px;margin-bottom:10px;">
        Analysis History
    </div>
    """, unsafe_allow_html=True)

    if st.button("Load Past Analyses", use_container_width=True):
        try:
            query = db.table("analyses").select("*").order("created_at", desc=True).limit(8)
            if not current_user["is_admin"]:
                query = query.eq("user_id", current_user["id"])
            history = query.execute()
            if history.data:
                for record in history.data:
                    date_str = record['created_at'][:10]
                    color    = ("#10b981" if record['health_label'] == "Excellent"
                                else "#60a5fa" if record['health_label'] == "Healthy" else "#f59e0b")
                    st.markdown(f"""
                    <div style="background:#090d1e;border:1px solid rgba(99,179,237,.1);
                                border-radius:10px;padding:10px 12px;margin-bottom:8px;">
                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;">{date_str}</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:13px;font-weight:600;
                                    color:#d4ddf0;margin:3px 0;">K{record['total_revenue']:,.0f} revenue</div>
                        <div style="font-family:'DM Mono',monospace;font-size:11px;color:{color};">
                            {record['health_score']}/100 · {record['health_label']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No history yet.")
        except Exception as e:
            st.error(f"Error: {e}")

    if current_user["is_admin"]:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                    letter-spacing:.12em;text-transform:uppercase;padding:0 8px;margin-bottom:8px;">
            Admin Control
        </div>
        """, unsafe_allow_html=True)
        if st.button("View User Activity", use_container_width=True):
            try:
                users = db.table("profiles").select("id,email,last_seen_at").order("last_seen_at", desc=True).limit(20).execute()
                if users.data:
                    for item in users.data:
                        st.caption(f"{item.get('email','No email')} · last seen: {item.get('last_seen_at','N/A')}")
                else:
                    st.info("No user activity records found.")
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
    </a>
    """, unsafe_allow_html=True)

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
                Financial Intelligence Command Centre
            </div>
            <div style="font-family:'DM Mono',monospace;font-size:10px;color:#2d4a70;
                        letter-spacing:.1em;text-transform:uppercase;">
                AI-BOS · Engine 1 · Real-Time Business Intelligence
            </div>
        </div>
        <div style="font-family:'DM Mono',monospace;font-size:10px;color:#2d4a70;
                    text-align:right;letter-spacing:.08em;">
            SYSTEM STATUS<br><span style="color:#10b981;">● OPERATIONAL</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    template_df    = st.session_state.get("template_df")
    data_available = uploaded is not None or template_df is not None

    # ── NO DATA STATE ──────────────────────────────────────
    if not data_available:
        st.markdown("""
        <div style="display:flex;align-items:center;justify-content:center;min-height:60vh;padding:40px;">
            <div style="text-align:center;max-width:480px;">
                <div style="font-size:56px;margin-bottom:24px;opacity:.25;">⚡</div>
                <div style="font-family:'Outfit',sans-serif;font-size:22px;font-weight:700;
                            color:#e2eeff;margin-bottom:12px;">Upload your financial data to begin</div>
                <div style="font-family:'Outfit',sans-serif;font-size:14px;color:#2d4a70;
                            line-height:1.7;margin-bottom:32px;">
                    Upload a CSV or Excel file with
                    <span style="color:#60a5fa;font-family:'DM Mono',monospace;font-size:12px;">month</span>,
                    <span style="color:#60a5fa;font-family:'DM Mono',monospace;font-size:12px;">revenue</span>, and
                    <span style="color:#60a5fa;font-family:'DM Mono',monospace;font-size:12px;">costs</span> columns.
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;text-align:left;">
                    <div style="background:#090d1e;border:1px solid rgba(99,179,237,.1);border-radius:12px;padding:16px;">
                        <div style="font-size:20px;margin-bottom:8px;">📊</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:12px;font-weight:600;color:#d4ddf0;margin-bottom:4px;">P&L Analysis</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:11px;color:#2d4a70;">Profit, margin, variance</div>
                    </div>
                    <div style="background:#090d1e;border:1px solid rgba(99,179,237,.1);border-radius:12px;padding:16px;">
                        <div style="font-size:20px;margin-bottom:8px;">🔮</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:12px;font-weight:600;color:#d4ddf0;margin-bottom:4px;">Revenue Forecast</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:11px;color:#2d4a70;">Linear regression model</div>
                    </div>
                    <div style="background:#090d1e;border:1px solid rgba(99,179,237,.1);border-radius:12px;padding:16px;">
                        <div style="font-size:20px;margin-bottom:8px;">🤖</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:12px;font-weight:600;color:#d4ddf0;margin-bottom:4px;">AI Strategy</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:11px;color:#2d4a70;">Executive recommendations</div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
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
                df["profit"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0) - pd.to_numeric(df["costs"], errors="coerce").fillna(0)
            if "margin_pct" not in df.columns:
                denom = pd.to_numeric(df["revenue"], errors="coerce").replace(0, pd.NA)
                df["margin_pct"] = ((pd.to_numeric(df["profit"], errors="coerce") / denom) * 100).fillna(0).round(1)

        with st.expander("DATA STUDIO · Edit or Build Your Dataset", expanded=False):
            edited_df = st.data_editor(
                df[["month", "revenue", "costs", "profit", "margin_pct"]].copy(),
                num_rows="dynamic", use_container_width=True, key="engine1_data_editor"
            )
            edited_df["revenue"]    = pd.to_numeric(edited_df["revenue"], errors="coerce").fillna(0)
            edited_df["costs"]      = pd.to_numeric(edited_df["costs"],   errors="coerce").fillna(0)
            edited_df["profit"]     = edited_df["revenue"] - edited_df["costs"]
            denom                   = edited_df["revenue"].replace(0, pd.NA)
            edited_df["margin_pct"] = ((edited_df["profit"] / denom) * 100).fillna(0).round(1)
            df = edited_df
            st.session_state.template_df = df.copy()
            st.download_button("Download Edited CSV", data=df.to_csv(index=False).encode("utf-8"),
                               file_name="engine1_edited_financials.csv", mime="text/csv")

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

        try:
            db.table("analyses").insert({
                "user_id": current_user["id"], "user_email": current_user["email"],
                "total_revenue": float(pnl["total_revenue"]), "total_costs": float(pnl["total_costs"]),
                "total_profit": float(pnl["total_profit"]),   "avg_margin":  float(pnl["avg_margin"]),
                "health_score": int(score), "health_label": label,
                "best_month": pnl["best_month"], "worst_month": pnl["worst_month"],
                "alerts_count": len(alerts)
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
        </div>
        """, unsafe_allow_html=True)

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
        # TABS — 5 original + 3 new
        # ══════════════════════════════════════════════════
        st.markdown("<div style='padding:24px 40px 0;'>", unsafe_allow_html=True)

        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "FINANCIAL OVERVIEW",
            "CASH INTELLIGENCE",
            "VARIANCE ANALYSIS",
            "STRATEGIC BRIEF",
            "DATA STUDIO",
            "REVENUE FORECAST",   # ← NEW
            "ANOMALY INTEL",      # ← NEW
            "BREAKEVEN",          # ← NEW
        ])

        # ── TAB 1: FINANCIAL OVERVIEW (unchanged) ──────────
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
                    title=dict(text="REVENUE vs COSTS TREND", font=dict(family="DM Mono", size=10, color="#2d4a70")),
                    legend=dict(font=dict(family="DM Mono", size=10)), **CHART_THEME)
                st.plotly_chart(fig_rev, use_container_width=True)
            with col_right:
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number", value=pnl['avg_margin'],
                    title=dict(text="AVG PROFIT MARGIN %", font=dict(family="DM Mono", size=10, color="#2d4a70")),
                    number=dict(suffix="%", font=dict(family="Outfit", size=36, color="#e2eeff")),
                    gauge=dict(axis=dict(range=[0, 50], tickcolor="#2d4a70", tickfont=dict(family="DM Mono", size=9)),
                               bar=dict(color=score_color), bgcolor="rgba(0,0,0,0)", borderwidth=0,
                               steps=[dict(range=[0,10], color="rgba(239,68,68,.12)"),
                                      dict(range=[10,25], color="rgba(245,158,11,.12)"),
                                      dict(range=[25,50], color="rgba(16,185,129,.12)")],
                               threshold=dict(line=dict(color="#60a5fa", width=2), value=pnl['avg_margin']))))
                fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(family="DM Mono", color="#6b87b0"),
                                        margin=dict(l=20, r=20, t=48, b=20), height=220)
                st.plotly_chart(fig_gauge, use_container_width=True)
                bar_colors = ["#10b981" if v >= 0 else "#ef4444" for v in df["profit"]]
                fig_profit = go.Figure(go.Bar(x=df["month"], y=df["profit"], marker_color=bar_colors, name="Net Profit"))
                fig_profit.update_layout(title=dict(text="NET PROFIT BY PERIOD",
                    font=dict(family="DM Mono", size=10, color="#2d4a70")), **CHART_THEME, height=200)
                st.plotly_chart(fig_profit, use_container_width=True)

        # ── TAB 2: CASH INTELLIGENCE (unchanged) ──────────
        with tab2:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            runway_color = "#10b981" if runway_months >= 6 else "#f59e0b" if runway_months >= 3 else "#ef4444"
            st.markdown(f"""
            <div style="background:#090d1e;border:1px solid {runway_color}33;border-radius:12px;
                        padding:14px 18px;margin-bottom:12px;">
                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;letter-spacing:.1em;">CASH RUNWAY ESTIMATE</div>
                <div style="font-family:'Outfit',sans-serif;font-size:24px;font-weight:700;color:{runway_color};margin-top:4px;">{runway_months:.1f} months</div>
            </div>
            """, unsafe_allow_html=True)
            forecast_months = [f"Month +{f['month_ahead']}" for f in forecast]
            forecast_values = [f['projected_cash'] for f in forecast]
            forecast_colors = ["#10b981" if f['status'] == "✓ Positive" else "#ef4444" for f in forecast]
            fig_cf = go.Figure()
            fig_cf.add_trace(go.Bar(x=forecast_months, y=forecast_values, marker_color=forecast_colors, name="Projected Cash"))
            fig_cf.update_layout(title=dict(text="30 / 60 / 90 DAY CASH FLOW PROJECTION",
                font=dict(family="DM Mono", size=10, color="#2d4a70")), **CHART_THEME, height=280)
            st.plotly_chart(fig_cf, use_container_width=True)
            for item in forecast:
                status_color = "#10b981" if item['status'] == "✓ Positive" else "#ef4444"
                st.markdown(f"""
                <div style="background:#090d1e;border:1px solid rgba(99,179,237,.08);border-radius:10px;
                            padding:14px 20px;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;">
                    <div>
                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;letter-spacing:.1em;">
                            MONTH +{item['month_ahead']} PROJECTION</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:20px;font-weight:700;color:#e2eeff;margin-top:4px;">
                            K{item['projected_cash']:,}</div>
                    </div>
                    <div style="font-family:'DM Mono',monospace;font-size:12px;color:{status_color};font-weight:500;">
                        {item['status']}</div>
                </div>
                """, unsafe_allow_html=True)

        # ── TAB 3: VARIANCE ANALYSIS (unchanged) ──────────
        with tab3:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            if not alerts:
                st.markdown("""
                <div style="background:#090d1e;border:1px solid rgba(16,185,129,.2);border-radius:14px;
                            padding:32px;text-align:center;">
                    <div style="font-size:32px;margin-bottom:12px;">✓</div>
                    <div style="font-family:'Outfit',sans-serif;font-size:16px;font-weight:600;color:#10b981;margin-bottom:6px;">
                        No Significant Variances Detected</div>
                    <div style="font-family:'DM Mono',monospace;font-size:11px;color:#2d4a70;">
                        All periods within normal operating parameters</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                for alert in alerts:
                    direction_color = "#ef4444" if alert['direction'] == "drop" else "#f59e0b"
                    direction_icon  = "▼" if alert['direction'] == "drop" else "▲"
                    alert_type = alert.get("type", "revenue_variance").replace("_", " ").upper()
                    st.markdown(f"""
                    <div style="background:#090d1e;border:1px solid {direction_color}33;
                                border-left:3px solid {direction_color};border-radius:12px;
                                padding:16px 20px;margin-bottom:10px;">
                        <div style="display:flex;align-items:center;justify-content:space-between;">
                            <div>
                                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                                            letter-spacing:.1em;margin-bottom:6px;">{alert_type} · {alert['month'].upper()}</div>
                                <div style="font-family:'Outfit',sans-serif;font-size:15px;font-weight:600;color:#e2eeff;">
                                    Revenue {alert['direction'].title()} of {abs(alert['change_pct'])}%</div>
                            </div>
                            <div style="font-family:'Outfit',sans-serif;font-size:28px;font-weight:800;color:{direction_color};">
                                {direction_icon} {abs(alert['change_pct'])}%</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            if len(df) > 1:
                changes = df["revenue"].diff().fillna(0).tolist()
                colors  = ["#10b981" if c >= 0 else "#ef4444" for c in changes]
                fig_wf  = go.Figure(go.Bar(x=df["month"], y=changes, marker_color=colors, name="Revenue Change"))
                fig_wf.update_layout(title=dict(text="PERIOD-ON-PERIOD REVENUE CHANGE",
                    font=dict(family="DM Mono", size=10, color="#2d4a70")), **CHART_THEME, height=220)
                st.plotly_chart(fig_wf, use_container_width=True)

        # ── TAB 4: STRATEGIC BRIEF (unchanged) ────────────
        with tab4:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            pdf_bytes = _build_pdf_report(pnl, score, label, alerts, runway_months)
            st.download_button("Download Executive PDF", data=pdf_bytes,
                               file_name="engine1_executive_report.pdf", mime="application/pdf",
                               use_container_width=True)
            st.markdown("""
            <div style="background:#090d1e;border:1px solid rgba(99,179,237,.1);border-radius:14px;
                        padding:24px 28px;margin-bottom:20px;">
                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                            letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px;">AI Strategic Intelligence Engine</div>
                <div style="font-family:'Outfit',sans-serif;font-size:14px;color:#6b87b0;line-height:1.7;">
                    Generate a comprehensive strategic intelligence brief derived from your financial data.
                    Each recommendation is calibrated to your specific metrics — not generic advice.</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("⚡ Generate Executive Intelligence Brief", use_container_width=True):
                with st.spinner("Running strategic analysis..."):
                    try:
                        structured   = get_structured_analysis(pnl, alerts)
                        priority_map = {
                            "high":   ("#ef4444", "HIGH PRIORITY",   "IMMEDIATE ACTION"),
                            "medium": ("#f59e0b", "MEDIUM PRIORITY", "THIS QUARTER"),
                            "low":    ("#10b981", "LOW PRIORITY",    "STRATEGIC WATCH"),
                        }
                        for i, rec in enumerate(structured, 1):
                            p = rec.get('priority', 'medium').lower()
                            color, p_label, timeline = priority_map.get(p, priority_map['medium'])
                            st.markdown(f"""
                            <div style="background:#090d1e;border:1px solid {color}22;border-top:2px solid {color};
                                        border-radius:14px;padding:22px 26px;margin-bottom:14px;">
                                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
                                    <div style="display:flex;align-items:center;gap:12px;">
                                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:{color};
                                                    letter-spacing:.12em;background:{color}15;padding:4px 10px;
                                                    border-radius:20px;">{p_label}</div>
                                        <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;">{timeline}</div>
                                    </div>
                                    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;">REC {i:02d} / {len(structured):02d}</div>
                                </div>
                                <div style="font-family:'Outfit',sans-serif;font-size:17px;font-weight:700;color:#e2eeff;margin-bottom:10px;">
                                    {rec.get('title', '')}</div>
                                <div style="font-family:'Outfit',sans-serif;font-size:13px;color:#6b87b0;line-height:1.7;">
                                    {rec.get('recommendation', '')}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")

        # ── TAB 5: DATA STUDIO (unchanged) ────────────────
        with tab5:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            st.markdown("""
            <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                        letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px;">In-App Data Editing</div>
            """, unsafe_allow_html=True)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption("Use the DATA STUDIO expander above to edit rows and download a clean CSV.")

        # ══════════════════════════════════════════════════
        # TAB 6 — REVENUE FORECAST (NEW)
        # ══════════════════════════════════════════════════
        with tab6:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

            with st.spinner("Running linear regression forecast..."):
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
                </div>
                """, unsafe_allow_html=True)

                # Chart: historical + forecast with bands
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
                            border-left:3px solid #06b6d4;border-radius:12px;padding:16px 20px;margin-top:4px;">
                    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                                letter-spacing:.1em;margin-bottom:8px;">AI FORECAST NARRATIVE</div>
                    <div style="font-family:'Outfit',sans-serif;font-size:14px;color:#9bb0cc;
                                line-height:1.7;">{fc['ai_explanation']}</div>
                </div>
                """, unsafe_allow_html=True)

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
                    </div>
                    """, unsafe_allow_html=True)

        # ══════════════════════════════════════════════════
        # TAB 7 — ANOMALY INTELLIGENCE (NEW)
        # ══════════════════════════════════════════════════
        with tab7:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

            z_thresh = st.slider("Detection sensitivity (z-score threshold)",
                                 min_value=1.5, max_value=3.5, value=2.0, step=0.5,
                                 help="Lower = more sensitive. 2.0 is standard. 3.0 = major anomalies only.")

            with st.spinner("Running statistical anomaly scan..."):
                anomalies = detect_anomalies(df, z_threshold=z_thresh)

            if not anomalies:
                st.markdown("""
                <div style="background:#090d1e;border:1px solid rgba(16,185,129,.2);
                            border-radius:14px;padding:32px;text-align:center;">
                    <div style="font-size:28px;margin-bottom:10px;">✓</div>
                    <div style="font-family:'Outfit',sans-serif;font-size:16px;font-weight:600;color:#10b981;">
                        No anomalies at this sensitivity level</div>
                    <div style="font-family:'DM Mono',monospace;font-size:11px;color:#2d4a70;margin-top:6px;">
                        Try lowering the threshold to surface subtler patterns</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                critical = sum(1 for a in anomalies if a["severity"] == "critical")
                high_c   = sum(1 for a in anomalies if a["severity"] == "high")
                medium_c = sum(1 for a in anomalies if a["severity"] == "medium")

                st.markdown(f"""
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;margin-bottom:20px;">
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
                </div>
                """, unsafe_allow_html=True)

                severity_colors = {"critical": "#ef4444", "high": "#f59e0b", "medium": "#60a5fa", "low": "#10b981"}
                for a in anomalies:
                    color = severity_colors.get(a["severity"], "#60a5fa")
                    icon  = "▼" if a["direction"] == "drop" else "▲"
                    st.markdown(f"""
                    <div style="background:#090d1e;border:1px solid {color}22;border-left:3px solid {color};
                                border-radius:12px;padding:16px 20px;margin-bottom:10px;">
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
                            <div style="display:flex;align-items:center;gap:10px;">
                                <div style="font-family:'DM Mono',monospace;font-size:9px;color:{color};
                                            background:{color}15;padding:3px 10px;border-radius:20px;
                                            letter-spacing:.1em;">{a['severity'].upper()}</div>
                                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;">
                                    {a['metric'].upper()} · {a['month'].upper()}</div>
                            </div>
                            <div style="font-family:'Outfit',sans-serif;font-size:22px;font-weight:800;color:{color};">
                                {icon} {abs(a['change_pct'])}%</div>
                        </div>
                        <div style="font-family:'DM Mono',monospace;font-size:10px;color:#2d4a70;margin-bottom:6px;">
                            z-score: {a['z_score']}σ</div>
                        <div style="font-family:'Outfit',sans-serif;font-size:13px;color:#9bb0cc;line-height:1.6;">
                            <span style="color:#4a6285;font-size:11px;font-family:'DM Mono',monospace;">ROOT CAUSE: </span>
                            {a['root_cause']}</div>
                    </div>
                    """, unsafe_allow_html=True)

        # ══════════════════════════════════════════════════
        # TAB 8 — BREAKEVEN ANALYSIS (NEW)
        # ══════════════════════════════════════════════════
        with tab8:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

            fixed_pct = st.slider("Fixed costs as % of total costs",
                                  min_value=10, max_value=90, value=40, step=5,
                                  help="Rent, salaries, subscriptions = fixed. Stock, commissions = variable.") / 100

            be         = calculate_breakeven(df, fixed_cost_pct=fixed_pct)
            above_be   = be["current_avg_revenue"] >= be["breakeven_revenue"]
            be_color   = "#10b981" if above_be else "#ef4444"
            be_status  = "ABOVE BREAKEVEN" if above_be else "BELOW BREAKEVEN"

            st.markdown(f"""
            <div style="background:#090d1e;border:1px solid {be_color}33;border-left:3px solid {be_color};
                        border-radius:14px;padding:20px 28px;margin-bottom:20px;
                        display:flex;align-items:center;gap:32px;">
                <div>
                    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                                letter-spacing:.12em;margin-bottom:4px;">BREAKEVEN REVENUE</div>
                    <div style="font-family:'Outfit',sans-serif;font-size:36px;font-weight:800;color:{be_color};">
                        K{be['breakeven_revenue']:,}</div>
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
            </div>
            """, unsafe_allow_html=True)

            col_l, col_r = st.columns([3, 2])
            with col_l:
                fig_be = go.Figure()
                fig_be.add_trace(go.Bar(
                    x=["Fixed Costs", "Variable Costs", "Avg Revenue", "Breakeven"],
                    y=[be["fixed_costs"], be["variable_costs"], be["current_avg_revenue"], be["breakeven_revenue"]],
                    marker_color=["#f59e0b", "#ef4444", "#3b82f6", "#10b981"]))
                fig_be.add_hline(y=be["breakeven_revenue"], line_dash="dash", line_color="#10b981", line_width=1.5,
                                 annotation_text="Breakeven", annotation_font=dict(family="DM Mono", size=10, color="#10b981"))
                fig_be.update_layout(title=dict(text="COST STRUCTURE vs BREAKEVEN",
                    font=dict(family="DM Mono", size=10, color="#2d4a70")), **CHART_THEME, height=280)
                st.plotly_chart(fig_be, use_container_width=True)

            with col_r:
                st.markdown("""
                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                            letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px;">
                    What-If: Cost Increases</div>
                """, unsafe_allow_html=True)
                for s in be["scenarios"]:
                    s_color = "#10b981" if s["status"] == "safe" else "#ef4444"
                    st.markdown(f"""
                    <div style="background:#090d1e;border:1px solid {s_color}22;border-radius:10px;
                                padding:10px 14px;margin-bottom:6px;
                                display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;">
                                +{s['cost_increase_pct']}% costs</div>
                            <div style="font-family:'Outfit',sans-serif;font-size:14px;font-weight:600;color:#e2eeff;">
                                BE: K{s['new_breakeven']:,}</div>
                        </div>
                        <div style="font-family:'DM Mono',monospace;font-size:10px;color:{s_color};">
                            {s['status'].upper()}</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="background:#090d1e;border:1px solid rgba(6,182,212,.15);border-left:3px solid #06b6d4;
                        border-radius:12px;padding:16px 20px;margin-top:8px;">
                <div style="font-family:'DM Mono',monospace;font-size:9px;color:#2d4a70;
                            letter-spacing:.1em;margin-bottom:8px;">AI INSIGHT</div>
                <div style="font-family:'Outfit',sans-serif;font-size:14px;color:#9bb0cc;line-height:1.7;">
                    {be['ai_insight']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # ── RAW DATA (unchanged) ───────────────────────────
        st.markdown("<div style='padding:0 40px 40px;'>", unsafe_allow_html=True)
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        with st.expander("RAW DATA · Full Period Breakdown"):
            display_cols = [c for c in ["month", "revenue", "costs", "profit", "margin_pct"] if c in df.columns]
            st.dataframe(
                df[display_cols].style.format({"revenue": "K{:,.0f}", "costs": "K{:,.0f}",
                                               "profit": "K{:,.0f}", "margin_pct": "{:.1f}%"}),
                use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
