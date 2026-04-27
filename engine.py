# ════════════════════════════════════════════════════════
# AI-BOS — Financial Intelligence Engine v1
# ════════════════════════════════════════════════════════

import pandas as pd
import os
import json
from groq import Groq

# ── AI CLIENT SETUP ──────────────────────────────────────
client_ai = Groq(api_key=os.environ.get("GROQ_API_KEY"))
print("AI Client ready ✓")

# ── LOAD DATA ────────────────────────────────────────────
df = pd.read_csv("test_data.csv")
df["profit"]     = df["revenue"] - df["costs"]
df["margin_pct"] = (df["profit"] / df["revenue"]) * 100
df["margin_pct"] = df["margin_pct"].round(1)

# ── FUNCTION 1 — P&L ─────────────────────────────────────
def analyse_pnl(df):
    total_rev    = df["revenue"].sum()
    total_cost   = df["costs"].sum()
    total_profit = total_rev - total_cost
    avg_margin   = round(df["margin_pct"].mean(), 1)
    best_idx     = df["profit"].idxmax()
    return {
        "total_revenue": total_rev,
        "total_costs":   total_cost,
        "total_profit":  total_profit,
        "avg_margin":    avg_margin,
        "best_month":    df.loc[best_idx, "month"],
        "worst_month":   df.loc[df["profit"].idxmin(), "month"]
    }

# ── FUNCTION 2 — CASH FLOW FORECAST ──────────────────────
def forecast_cashflow(df, current_cash=50000, months_ahead=3):
    recent_profit = df.tail(3)["profit"].mean()
    running_cash  = current_cash
    forecast      = []
    for m in range(1, months_ahead + 1):
        running_cash += recent_profit
        forecast.append({
            "month_ahead":    m,
            "projected_cash": round(running_cash),
            "status": "⚠ NEGATIVE" if running_cash < 0 else "✓ Positive"
        })
    return forecast

# ── FUNCTION 3 — VARIANCE DETECTION ──────────────────────
def detect_variances(df, threshold=0.10):
    alerts = []
    for i in range(1, len(df)):
        prev_rev = df.iloc[i-1]["revenue"]
        curr_rev = df.iloc[i]["revenue"]
        pct_chg  = ((curr_rev - prev_rev) / prev_rev) * 100
        if abs(pct_chg) > threshold * 100:
            alerts.append({
                "month":      df.iloc[i]["month"],
                "change_pct": round(pct_chg, 1),
                "direction":  "drop" if pct_chg < 0 else "spike"
            })
    return alerts

# ── FUNCTION 4 — HEALTH SCORE ─────────────────────────────
def health_score(pnl, alerts):
    margin_pts = min(pnl["avg_margin"] * 1.5, 50)
    trend      = pnl["total_revenue"] - pnl["total_costs"]
    trend_pts  = 30 if trend > 0 else 0
    alert_pen  = len(alerts) * 8
    score      = max(0, min(100, margin_pts + trend_pts - alert_pen))
    label      = ("Critical" if score < 30 else
                  "At Risk"  if score < 55 else
                  "Healthy"  if score < 80 else "Excellent")
    return round(score), label

# ── FUNCTION 5 — AI ANALYSIS ──────────────────────────────
def get_ai_analysis(pnl, alerts):
    prompt = f"""
You are an expert CFO advising a small African business.

Business financial data:
- Total Revenue:  K{pnl['total_revenue']:,}
- Total Costs:    K{pnl['total_costs']:,}
- Total Profit:   K{pnl['total_profit']:,}
- Average Margin: {pnl['avg_margin']}%
- Best Month:     {pnl['best_month']}
- Worst Month:    {pnl['worst_month']}
- Alerts:         {len(alerts)} variance detected

Give exactly 3 specific actionable recommendations.
Reference the actual numbers above.
Plain English only. No jargon.
Maximum 2 sentences each.
"""
    response = client_ai.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        timeout=30
    )
    return response.choices[0].message.content

# ── FUNCTION 6- STRUCTURED JSON ANALYSIS ──────────────────────────────

import json

def get_structured_analysis(pnl, alerts):
    prompt = f"""
You are an expert CFO advising a small African business.

Business financial data:
- Total Revenue:  K{pnl['total_revenue']:,}
- Total Costs:    K{pnl['total_costs']:,}
- Total Profit:   K{pnl['total_profit']:,}
- Average Margin: {pnl['avg_margin']}%
- Best Month:     {pnl['best_month']}
- Worst Month:    {pnl['worst_month']}
- Alerts:         {len(alerts)} variance detected

Return ONLY a valid JSON array. No other text before or after it.
Exactly 3 recommendations in this format:
[
  {{"title": "short title", "recommendation": "specific advice referencing the numbers", "priority": "high/medium/low"}},
  {{"title": "short title", "recommendation": "specific advice referencing the numbers", "priority": "high/medium/low"}},
  {{"title": "short title", "recommendation": "specific advice referencing the numbers", "priority": "high/medium/low"}}
]
"""
    response = client_ai.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        timeout=30
    )
    raw = response.choices[0].message.content

    try:
        recommendations = json.loads(raw)
        return recommendations
    except:
        return [{"title": "Analysis", "recommendation": raw, "priority": "medium"}]

# ════════════════════════════════════════════════════════
# RUN THE ENGINE — only runs when called directly
# ════════════════════════════════════════════════════════
if __name__ == "__main__":
    pnl          = analyse_pnl(df)
    forecast     = forecast_cashflow(df)
    alerts       = detect_variances(df)
    score, label = health_score(pnl, alerts)

    print("\n── AI-BOS FINANCIAL REPORT ──────────────────────")
    print(f"Health Score:  {score}/100 — {label}")
    print(f"Total Revenue: K{pnl['total_revenue']:,}")
    print(f"Total Profit:  K{pnl['total_profit']:,}")
    print(f"Avg Margin:    {pnl['avg_margin']}%")
    print(f"Best Month:    {pnl['best_month']}")
    print(f"Worst Month:   {pnl['worst_month']}")

    print("\n── CASH FLOW FORECAST ───────────────────────────")
    for item in forecast:
        print(f"Month {item['month_ahead']}: K{item['projected_cash']:,} {item['status']}")

    print("\n── VARIANCE ALERTS ──────────────────────────────")
    if len(alerts) == 0:
        print("No significant variances detected")
    else:
        for alert in alerts:
            print(f"{alert['month']}: {alert['direction']} of {alert['change_pct']}%")

    print("\n── AI CFO RECOMMENDATIONS ───────────────────────")
    analysis = get_ai_analysis(pnl, alerts)
    print(analysis)

    print("\n── STRUCTURED AI RECOMMENDATIONS ───────────────")
    structured = get_structured_analysis(pnl, alerts)
    for i, rec in enumerate(structured, 1):
        print(f"\n[{rec['priority'].upper()}] Recommendation {i}: {rec['title']}")
        print(f"→ {rec['recommendation']}")