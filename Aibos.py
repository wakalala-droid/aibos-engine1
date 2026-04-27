import pandas as pd

# ── LOAD AND PREPARE DATA ──────────────────────────────
df = pd.read_csv("test_data.csv")
df["profit"]     = df["revenue"] - df["costs"]
df["margin_pct"] = (df["profit"] / df["revenue"]) * 100
df["margin_pct"] = df["margin_pct"].round(1)

# ── FUNCTION 1 ─────────────────────────────────────────
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

# ── FUNCTION 2 ─────────────────────────────────────────
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

# ── FUNCTION 3 ─────────────────────────────────────────
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

# ── RUN ────────────────────────────────────────────────
pnl          = analyse_pnl(df)
alerts       = detect_variances(df)
score, label = health_score(pnl, alerts)

print(f"Business Health: {score}/100 — {label}")
print(f"Best Month:      {pnl['best_month']}")
print(f"Worst Month:     {pnl['worst_month']}")
print(f"Avg Margin:      {pnl['avg_margin']}%")
print(f"Alerts Found:    {len(alerts)}")