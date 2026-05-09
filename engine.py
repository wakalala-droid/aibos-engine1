# ════════════════════════════════════════════════════════
# AI-BOS — Financial Intelligence Engine v1 (upgraded)
# ════════════════════════════════════════════════════════

import pandas as pd
import numpy as np
import os
import json
from groq import Groq

# ── AI CLIENT SETUP ──────────────────────────────────────
client_ai = Groq(api_key=os.environ.get("GROQ_API_KEY") or "placeholder")
print("AI Client ready ✓")

# ── LOAD DATA ────────────────────────────────────────────
df = pd.read_csv("test_data.csv")
df["profit"]     = df["revenue"] - df["costs"]
df["margin_pct"] = (df["profit"] / df["revenue"]) * 100
df["margin_pct"] = df["margin_pct"].round(1)


# ── FUNCTION 1 — P&L (unchanged) ─────────────────────────
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


# ── FUNCTION 2 — CASH FLOW FORECAST (unchanged) ──────────
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


# ── FUNCTION 3 — VARIANCE DETECTION (unchanged, kept for compatibility) ──
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


# ── FUNCTION 4 — HEALTH SCORE (unchanged) ────────────────
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


# ── FUNCTION 5 — AI ANALYSIS (unchanged) ─────────────────
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


# ── FUNCTION 6 — STRUCTURED JSON ANALYSIS (unchanged) ────
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
        return json.loads(raw)
    except Exception:
        return [{"title": "Analysis", "recommendation": raw, "priority": "medium"}]


# ════════════════════════════════════════════════════════
# UPGRADE 1 — REVENUE FORECAST (replaces naive rolling avg)
# Linear regression + confidence bands + AI narrative
# ════════════════════════════════════════════════════════

def forecast_revenue(df: pd.DataFrame, months_ahead: int = 6) -> dict:
    """
    Linear regression forecast with best/worst case bands.
    Works with as few as 3 months of data.

    Returns:
        forecast        list of {month, predicted, low, high}
        trend           "upward" | "downward" | "flat"
        growth_rate     % per month
        confidence      0–100
        r_squared       model fit score
        ai_explanation  plain-English narrative
    """
    revenue = pd.to_numeric(df["revenue"], errors="coerce").fillna(0).values
    n       = len(revenue)

    if n < 3:
        return {"error": "Need at least 3 months of data"}

    x = np.arange(n, dtype=float)

    # Linear regression
    slope, intercept = np.polyfit(x, revenue, 1)
    y_hat     = slope * x + intercept
    residuals = revenue - y_hat
    std_err   = float(np.std(residuals))

    # R² (confidence proxy)
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((revenue - np.mean(revenue)) ** 2))
    r2     = max(0.0, 1 - ss_res / ss_tot) if ss_tot > 0 else 0.0
    confidence = int(min(100, round(r2 * 100)))

    # Monthly growth rate as % of last known revenue
    last_rev    = float(revenue[-1]) if revenue[-1] > 0 else 1.0
    growth_rate = round((slope / last_rev) * 100, 2)

    # Trend label
    if   slope >  last_rev * 0.01:  trend = "upward"
    elif slope < -last_rev * 0.01:  trend = "downward"
    else:                            trend = "flat"

    # Build forecast points
    forecast_pts = []
    for i in range(1, months_ahead + 1):
        predicted = max(0.0, slope * (n - 1 + i) + intercept)
        low       = max(0.0, predicted - std_err)
        high      = predicted + std_err
        forecast_pts.append({
            "month":     f"Month +{i}",
            "predicted": round(predicted),
            "low":       round(low),
            "high":      round(high),
        })

    # AI narrative
    ai_explanation = _get_forecast_narrative(
        trend, growth_rate, confidence, forecast_pts, pnl_context=df
    )

    return {
        "forecast":        forecast_pts,
        "trend":           trend,
        "growth_rate":     growth_rate,
        "confidence":      confidence,
        "r_squared":       round(r2, 3),
        "ai_explanation":  ai_explanation,
        "std_err":         round(std_err),
    }


def _get_forecast_narrative(trend, growth_rate, confidence, forecast_pts, pnl_context) -> str:
    next_month = forecast_pts[0]["predicted"] if forecast_pts else 0
    last_month = forecast_pts[-1]["predicted"] if forecast_pts else 0
    try:
        prompt = f"""
You are a CFO advisor. Give a 2-sentence plain-English explanation of this revenue forecast.
Reference specific numbers. No jargon.

Trend: {trend}
Monthly growth rate: {growth_rate}%
Model confidence: {confidence}/100
Next month predicted revenue: K{next_month:,}
End of forecast period revenue: K{last_month:,}
"""
        response = client_ai.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            timeout=20
        )
        return response.choices[0].message.content.strip()
    except Exception:
        direction = "grow" if trend == "upward" else "decline" if trend == "downward" else "remain stable"
        return (
            f"Revenue is projected to {direction} at {abs(growth_rate)}% per month "
            f"(confidence: {confidence}/100). "
            f"Next month forecast: K{next_month:,}."
        )


# ════════════════════════════════════════════════════════
# UPGRADE 2 — ANOMALY DETECTION (replaces % threshold)
# Z-score statistical detection + AI root cause per alert
# ════════════════════════════════════════════════════════

def detect_anomalies(df: pd.DataFrame, z_threshold: float = 2.0) -> list[dict]:
    """
    Z-score based anomaly detection across revenue, costs, and margin.
    Each detected anomaly gets an AI-generated root cause explanation.

    Severity:
        |z| >= 3.0  → Critical
        |z| >= 2.5  → High
        |z| >= 2.0  → Medium
        |z| >= 1.5  → Low  (only if z_threshold <= 1.5)

    Returns list of:
        month, metric, direction, change_pct, z_score,
        severity, root_cause, type
    """
    if len(df) < 4:
        return []

    anomalies = []

    metrics = {
        "revenue":    ("revenue",    "Revenue"),
        "costs":      ("costs",      "Costs"),
        "margin_pct": ("margin_pct", "Profit Margin"),
    }

    for col, (_, label) in metrics.items():
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce").fillna(0)
        mean   = series.mean()
        std    = series.std()

        if std == 0:
            continue

        for i in range(1, len(df)):
            val   = series.iloc[i]
            z     = (val - mean) / std
            if abs(z) < z_threshold:
                continue

            prev       = series.iloc[i - 1]
            pct_change = ((val - prev) / prev * 100) if prev != 0 else 0.0
            direction  = "drop" if z < 0 else "spike"

            severity = (
                "critical" if abs(z) >= 3.0 else
                "high"     if abs(z) >= 2.5 else
                "medium"   if abs(z) >= 2.0 else
                "low"
            )

            root_cause = _get_anomaly_root_cause(
                month=str(df.iloc[i]["month"]),
                metric=label,
                direction=direction,
                pct_change=round(pct_change, 1),
                z_score=round(z, 2),
                severity=severity,
                df=df,
            )

            anomalies.append({
                "month":      str(df.iloc[i]["month"]),
                "metric":     label,
                "type":       f"{col}_{direction}",
                "direction":  direction,
                "change_pct": round(pct_change, 1),
                "z_score":    round(abs(z), 2),
                "severity":   severity,
                "root_cause": root_cause,
            })

    # Sort: critical first
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    anomalies.sort(key=lambda a: order.get(a["severity"], 4))
    return anomalies


def _get_anomaly_root_cause(
    month, metric, direction, pct_change, z_score, severity, df
) -> str:
    try:
        prompt = f"""
You are a CFO analyst. In 1–2 sentences, explain the likely root cause of this financial anomaly.
Be specific and practical. Reference the metric and numbers.

Month: {month}
Metric: {metric}
Direction: {direction} of {abs(pct_change)}%
Statistical deviation: {z_score} standard deviations from normal
Severity: {severity}

Give only the root cause explanation. No preamble.
"""
        response = client_ai.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            timeout=20
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return (
            f"{metric} {direction} of {abs(pct_change)}% in {month} "
            f"({z_score}σ deviation). Manual review recommended."
        )


# ════════════════════════════════════════════════════════
# UPGRADE 3 — BREAKEVEN ANALYSIS (new function)
# Fixed vs variable cost model with what-if scenarios
# ════════════════════════════════════════════════════════

def calculate_breakeven(
    df: pd.DataFrame,
    fixed_cost_pct: float = 0.40,
) -> dict:
    """
    Calculates breakeven revenue using a fixed/variable cost split.

    fixed_cost_pct: what fraction of total costs are fixed (default 40%).
    Clients can adjust this in the UI.

    Returns:
        breakeven_revenue       monthly revenue needed to cover all costs
        breakeven_units         breakeven as % of current avg revenue
        contribution_margin     revenue minus variable costs
        margin_of_safety        how far above breakeven you currently are
        months_to_profit        if currently below breakeven
        scenarios               list of what-if cost increase scenarios
        ai_insight              plain-English recommendation
    """
    avg_revenue  = float(df["revenue"].mean())
    avg_costs    = float(df["costs"].mean())
    avg_profit   = float(df["profit"].mean()) if "profit" in df.columns else avg_revenue - avg_costs

    fixed_costs    = avg_costs * fixed_cost_pct
    variable_costs = avg_costs * (1 - fixed_cost_pct)

    # Contribution margin ratio
    variable_cost_ratio = variable_costs / avg_revenue if avg_revenue > 0 else 0
    contribution_margin_ratio = 1 - variable_cost_ratio

    # Breakeven = Fixed Costs / Contribution Margin Ratio
    if contribution_margin_ratio > 0:
        breakeven_revenue = fixed_costs / contribution_margin_ratio
    else:
        breakeven_revenue = avg_costs

    # Margin of safety
    margin_of_safety     = avg_revenue - breakeven_revenue
    margin_of_safety_pct = (margin_of_safety / avg_revenue * 100) if avg_revenue > 0 else 0

    # Breakeven as % of current avg revenue (so clients understand scale)
    breakeven_pct = (breakeven_revenue / avg_revenue * 100) if avg_revenue > 0 else 100

    # Months to profit if currently loss-making
    months_to_profit = None
    if avg_profit < 0 and avg_revenue > 0:
        monthly_improvement_needed = breakeven_revenue - avg_revenue
        months_to_profit = round(monthly_improvement_needed / (avg_revenue * 0.05), 1)

    # What-if scenarios: cost increases of 5%, 10%, 15%
    scenarios = []
    for increase_pct in [5, 10, 15, 20]:
        new_fixed   = fixed_costs * (1 + increase_pct / 100)
        new_be      = new_fixed / contribution_margin_ratio if contribution_margin_ratio > 0 else avg_costs
        new_safety  = avg_revenue - new_be
        scenarios.append({
            "cost_increase_pct":  increase_pct,
            "new_breakeven":      round(new_be),
            "margin_of_safety":   round(new_safety),
            "status":             "safe" if new_safety > 0 else "at risk",
        })

    # AI insight
    ai_insight = _get_breakeven_insight(
        breakeven_revenue, avg_revenue, margin_of_safety_pct,
        fixed_cost_pct, avg_costs
    )

    return {
        "breakeven_revenue":      round(breakeven_revenue),
        "current_avg_revenue":    round(avg_revenue),
        "breakeven_pct":          round(breakeven_pct, 1),
        "contribution_margin_ratio": round(contribution_margin_ratio * 100, 1),
        "fixed_costs":            round(fixed_costs),
        "variable_costs":         round(variable_costs),
        "margin_of_safety":       round(margin_of_safety),
        "margin_of_safety_pct":   round(margin_of_safety_pct, 1),
        "months_to_profit":       months_to_profit,
        "scenarios":              scenarios,
        "ai_insight":             ai_insight,
    }


def _get_breakeven_insight(
    breakeven_revenue, avg_revenue, margin_of_safety_pct,
    fixed_cost_pct, avg_costs
) -> str:
    try:
        status = "above" if avg_revenue >= breakeven_revenue else "below"
        prompt = f"""
You are a CFO advisor. Give 2 sentences of practical advice on this breakeven situation.
Reference the specific numbers. Plain English only.

Current average monthly revenue: K{avg_revenue:,.0f}
Breakeven revenue needed: K{breakeven_revenue:,.0f}
Business is {status} breakeven
Margin of safety: {margin_of_safety_pct:.1f}%
Fixed costs are {fixed_cost_pct*100:.0f}% of total costs
"""
        response = client_ai.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            timeout=20
        )
        return response.choices[0].message.content.strip()
    except Exception:
        status = "above" if avg_revenue >= breakeven_revenue else "below"
        return (
            f"Your business is {status} the breakeven point of K{breakeven_revenue:,.0f}/month. "
            f"Margin of safety is {margin_of_safety_pct:.1f}%."
        )


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

    print("\n── REVENUE FORECAST (upgraded) ─────────────────")
    fc = forecast_revenue(df)
    print(f"Trend: {fc['trend']} | Growth: {fc['growth_rate']}%/mo | Confidence: {fc['confidence']}/100")
    for pt in fc["forecast"]:
        print(f"  {pt['month']}: K{pt['predicted']:,}  (K{pt['low']:,} – K{pt['high']:,})")
    print(f"AI: {fc['ai_explanation']}")

    print("\n── ANOMALY DETECTION (upgraded) ────────────────")
    anomalies = detect_anomalies(df)
    if not anomalies:
        print("No anomalies detected")
    for a in anomalies:
        print(f"[{a['severity'].upper()}] {a['month']} · {a['metric']} {a['direction']} {a['change_pct']}% (z={a['z_score']})")
        print(f"  Root cause: {a['root_cause']}")

    print("\n── BREAKEVEN ANALYSIS (new) ────────────────────")
    be = calculate_breakeven(df)
    print(f"Breakeven revenue: K{be['breakeven_revenue']:,}/month")
    print(f"Current avg revenue: K{be['current_avg_revenue']:,}/month")
    print(f"Margin of safety: {be['margin_of_safety_pct']}%")
    print(f"AI insight: {be['ai_insight']}")
