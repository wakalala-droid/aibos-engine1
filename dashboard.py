import streamlit as st
import pandas as pd
import plotly.express as px
import os
from groq import Groq
from supabase import create_client
from engine import (
    analyse_pnl,
    forecast_cashflow,
    detect_variances,
    health_score,
    get_structured_analysis
)

# ── CLIENTS ───────────────────────────────────────────────
client_ai = Groq(api_key=os.environ.get("GROQ_API_KEY"))
db = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)

# ── PAGE HEADER ───────────────────────────────────────────
st.title("AI-BOS Financial Engine")
st.write("Your AI-powered CFO")

# ── FILE UPLOAD ───────────────────────────────────────────
uploaded = st.file_uploader(
    "Upload your business data",
    type=["csv", "xlsx"]
)

if uploaded:
    # ── LOAD DATA ─────────────────────────────────────────
    if uploaded.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded)
    else:
        df = pd.read_csv(uploaded)

    df["profit"]     = df["revenue"] - df["costs"]
    df["margin_pct"] = (df["profit"] / df["revenue"]) * 100
    df["margin_pct"] = df["margin_pct"].round(1)

    st.success(f"Loaded {len(df)} rows successfully")

    # ── RUN ENGINE ────────────────────────────────────────
    pnl          = analyse_pnl(df)
    forecast     = forecast_cashflow(df)
    alerts       = detect_variances(df)
    score, label = health_score(pnl, alerts)

    # ── SAVE TO SUPABASE ──────────────────────────────────
    try:
        db.table("analyses").insert({
            "total_revenue": float(pnl["total_revenue"]),
            "total_costs":   float(pnl["total_costs"]),
            "total_profit":  float(pnl["total_profit"]),
            "avg_margin":    float(pnl["avg_margin"]),
            "health_score":  int(score),
            "health_label":  label,
            "best_month":    pnl["best_month"],
            "worst_month":   pnl["worst_month"],
            "alerts_count":  len(alerts)
        }).execute()
        st.toast("Analysis saved ✓")
    except Exception as e:
        st.error(f"Save failed: {e}")

    # ── METRIC CARDS ──────────────────────────────────────
    st.subheader("Financial Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue",      f"K{pnl['total_revenue']:,}")
    c2.metric("Profit",       f"K{pnl['total_profit']:,}")
    c3.metric("Avg Margin",   f"{pnl['avg_margin']}%")
    c4.metric("Health Score", f"{score}/100", label)

    # ── CHARTS ────────────────────────────────────────────
    st.subheader("Revenue Trend")
    fig = px.line(df, x="month", y="revenue",
                  title="Monthly Revenue",
                  labels={"revenue": "Revenue (K)"})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly Profit")
    fig2 = px.bar(df, x="month", y="profit",
                  color="profit", title="Profit by Month")
    st.plotly_chart(fig2, use_container_width=True)

    # ── VARIANCE ALERTS ───────────────────────────────────
    st.subheader("Variance Alerts")
    if len(alerts) == 0:
        st.success("No significant variances detected")
    else:
        for alert in alerts:
            st.warning(f"{alert['month']}: {alert['direction']} of {alert['change_pct']}%")

    # ── CASH FLOW FORECAST ────────────────────────────────
    st.subheader("Cash Flow Forecast")
    for item in forecast:
        st.write(f"Month {item['month_ahead']}: K{item['projected_cash']:,} {item['status']}")

    # ── AI RECOMMENDATIONS ────────────────────────────────
    st.subheader("AI CFO Recommendations")
    if st.button("Generate AI Analysis"):
        with st.spinner("Analysing your business data..."):
            structured = get_structured_analysis(pnl, alerts)
            for rec in structured:
                priority_color = {
                    "high":   "🔴",
                    "medium": "🟡",
                    "low":    "🟢"
                }.get(rec['priority'].lower(), "⚪")
                st.markdown(f"### {priority_color} {rec['title']}")
                st.write(rec['recommendation'])
                st.divider()

    # ── ASK ANYTHING ──────────────────────────────────────
    st.subheader("Ask Your Business Anything")
    if "chat" not in st.session_state:
        st.session_state.chat = []

    for msg in st.session_state.chat:
        st.chat_message(msg["role"]).write(msg["content"])

    if question := st.chat_input("e.g. Why did my worst month underperform?"):
        st.session_state.chat.append({"role": "user", "content": question})
        context = f"Business data: {pnl}. User asks: {question}"
        response = client_ai.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": context}],
            timeout=30
        )
        answer = response.choices[0].message.content
        st.session_state.chat.append({"role": "assistant", "content": answer})
        st.rerun()

# ── ANALYSIS HISTORY ──────────────────────────────────────
st.divider()
st.subheader("Past Analyses")
if st.button("Load History"):
    try:
        history = db.table("analyses").select("*").order("created_at", desc=True).limit(10).execute()
        if history.data:
            for record in history.data:
                st.write(f"**{record['created_at'][:10]}** — Revenue: K{record['total_revenue']:,} | Health: {record['health_score']}/100 — {record['health_label']}")
        else:
            st.info("No analyses saved yet.")
    except Exception as e:
        st.error(f"Could not load history: {e}")


# ── GET STARTED ───────────────────────────────────────────
st.divider()
st.subheader("Want Full Access?")
st.write("Contact us directly to get started with AI-BOS for your business.")
st.link_button(
    "💬 WhatsApp Us — Get Started",
    "https://wa.me/260973759352"
)