import io
import os
import re
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
from groq import Groq


CANONICAL_COLUMN_ALIASES: Dict[str, Tuple[str, ...]] = {
    "revenue": (
        "revenue",
        "sales",
        "turnover",
        "net_sales",
        "income",
        "total_revenue",
    ),
    "costs": (
        "costs",
        "cost",
        "expense",
        "expenses",
        "total_expenses",
        "operating_expenses",
        "cogs",
        "cost_of_goods_sold",
        "overheads",
        "opex",
    ),
    "month": (
        "month",
        "period",
        "date",
        "month_year",
        "reporting_period",
        "time_period",
    ),
    "profit": ("profit", "net_profit", "gross_profit"),
    "margin_pct": ("margin_pct", "margin_percent", "profit_margin", "margin"),
    "product_id": ("product_id", "sku", "item_id", "stock_code"),
}

# ── ADDITION 1 ─────────────────────────────────────────────────────────────────
# Product-group model constants.
# Triggered when the first column is a product/type label (not a date/period)
# AND the sheet has no column whose name suggests a month/period.
_PRODUCT_GROUP_SIZE = 3          # rows per month in the flower model
_MONTH_LABEL_PREFIX = [          # first-column values that signal a product-group layout
    "flower", "wreath", "bouquet", "arrangement", "product", "item", "type",
]
_MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _is_product_group_layout(df: pd.DataFrame) -> bool:
    """
    Return True when the sheet looks like the flower-business model:
      - No column whose normalised name IS a time/period label.
        We match only columns that START WITH the keyword so that
        'monthly_savings_zmw' does NOT falsely trigger this guard.
      - First column contains repeating product-type strings (not numbers/dates)
    """
    _TIME_EXACT  = {"month", "period", "date", "time", "month_year",
                    "reporting_period", "time_period"}
    _TIME_STARTS = ("month_", "period_", "date_", "report_period")

    norm_cols = [normalize_col_name(c) for c in df.columns]
    has_month_col = any(
        c in _TIME_EXACT or any(c.startswith(p) for p in _TIME_STARTS)
        for c in norm_cols
    )
    if has_month_col:
        return False

    first_col_values = df.iloc[:, 0].dropna().astype(str).str.lower()
    return first_col_values.apply(
        lambda v: any(kw in v for kw in _MONTH_LABEL_PREFIX)
    ).any()


def _aggregate_product_groups(df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse every _PRODUCT_GROUP_SIZE rows into one month row by summing
    revenue, costs and profit columns, then derive margin_pct.
    Month labels are generated as 'Jan 2025', 'Feb 2025', ...
    """
    norm_cols = [normalize_col_name(c) for c in df.columns]
    df = df.copy()
    df.columns = norm_cols

    # Map normalised column names to canonical targets.
    # Use a priority order so "total_expenses" beats "cost_per_unit" etc.
    rev_col  = _pick_column(norm_cols, (
        "sales_revenue_zmw", "total_revenue", "revenue", "sales", "turnover", "income",
    ))
    cost_col = _pick_column(norm_cols, (
        "total_expenses_zmw", "total_expenses", "total_costs", "operating_expenses_zmw",
        "operating_expenses", "cogs_zmw", "cogs", "expenses", "costs", "cost",
    ))
    prof_col = _pick_column(norm_cols, (
        "profit_zmw", "profit", "net_profit", "gross_profit",
    ))

    if not rev_col or not cost_col:
        raise ValueError(
            "Product-group layout detected but could not find Revenue / Costs columns.\n"
            f"Columns present: {norm_cols}"
        )

    for col in (rev_col, cost_col, prof_col):
        if col:
            df[col] = to_number(df[col])

    records = []
    num_months = len(df) // _PRODUCT_GROUP_SIZE

    for m in range(num_months):
        chunk = df.iloc[m * _PRODUCT_GROUP_SIZE : (m + 1) * _PRODUCT_GROUP_SIZE]
        revenue = float(chunk[rev_col].sum())
        costs   = float(chunk[cost_col].sum())
        profit  = float(chunk[prof_col].sum()) if prof_col else revenue - costs
        margin_pct = round((profit / revenue * 100) if revenue else 0.0, 1)
        records.append({
            "month":      f"{_MONTH_NAMES[m % 12]} {2025 + m // 12}",
            "revenue":    round(revenue, 2),
            "costs":      round(costs,   2),
            "profit":     round(profit,  2),
            "margin_pct": margin_pct,
        })

    return pd.DataFrame(records)
# ── END ADDITION 1 ─────────────────────────────────────────────────────────────


def normalize_col_name(name: str) -> str:
    value = str(name).replace("\ufeff", "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def to_number(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace("\u00a0", "", regex=False).str.replace(",", "", regex=False)
    s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    s = s.str.replace(r"[^0-9.\-]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def _pick_column(columns: Iterable[str], aliases: Iterable[str]) -> Optional[str]:
    col_set = set(columns)
    for alias in aliases:
        if alias in col_set:
            return alias
    for column in columns:
        if any(token in column for token in aliases):
            return column
    return None


def _sample_values(df: pd.DataFrame, column: str, max_values: int = 5) -> List[str]:
    values = df[column].dropna().astype(str).head(max_values).tolist()
    return values


def classify_unknown_column_with_groq(df: pd.DataFrame, column: str) -> Optional[str]:
    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        return None

    samples = _sample_values(df, column)
    if not samples:
        return None

    prompt = (
        "Classify this dataset column into exactly one canonical label from this list: "
        "revenue, costs, month, profit, margin_pct, product_id, ignore. "
        "Reply with only one label.\n\n"
        f"Column name: {column}\n"
        f"Sample values: {samples}\n"
    )

    try:
        client = Groq(api_key=groq_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an accounting data schema classifier. "
                        "Return only one label."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            timeout=20,
        )
        label = (response.choices[0].message.content or "").strip().lower()
        return label if label in CANONICAL_COLUMN_ALIASES or label == "ignore" else None
    except Exception:
        return None


def _apply_ai_column_mapping(df: pd.DataFrame, mapped: Dict[str, str]) -> Dict[str, str]:
    rename_map = dict(mapped)
    taken_targets = set(rename_map.values())

    for col in df.columns:
        if col in rename_map:
            continue
        label = classify_unknown_column_with_groq(df, col)
        if label and label != "ignore" and label not in taken_targets:
            rename_map[col] = label
            taken_targets.add(label)
    return rename_map


def load_financial_file(uploaded_file) -> pd.DataFrame:
    ext = os.path.splitext(uploaded_file.name.lower())[1]
    if ext in {".xlsx", ".xls", ".xlsm", ".xlsb"}:
        # ── ADDITION 2 ─────────────────────────────────────────────────────────
        # Re-read xlsx/xlsm with openpyxl data_only=True so formula cells return
        # their last-calculated numeric value instead of the raw formula string
        # (e.g. "=B2*C2").  Falls back to pd.read_excel on any error.
        uploaded_file.seek(0)
        raw_bytes = uploaded_file.read()
        df = None
        if ext in {".xlsx", ".xlsm"}:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(
                    io.BytesIO(raw_bytes), data_only=True, read_only=True
                )
                ws = wb.active
                rows = list(ws.iter_rows(values_only=True))
                if rows:
                    df = pd.DataFrame(rows[1:], columns=rows[0])
                    df = df.dropna(how="all").dropna(axis=1, how="all")
            except Exception:
                df = None
        if df is None or df.empty:
            df = pd.read_excel(io.BytesIO(raw_bytes))
        # ── END ADDITION 2 ───────────────────────────────────────────────────────
    else:
        csv_errors = []
        for enc in ("utf-8", "utf-8-sig", "latin1"):
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding=enc)
                break
            except Exception as error:
                csv_errors.append(f"{enc}: {error}")
        else:
            raise ValueError(f"Could not read CSV. Attempts: {' | '.join(csv_errors)}")

    if df.empty:
        raise ValueError("File loaded but has no rows.")

    # ── ADDITION 3 ─────────────────────────────────────────────────────────────
    # Detect product-group layout (e.g. flower business model where every N rows
    # are product types for the same month) and aggregate before any column
    # mapping runs.  Returns early with a ready-to-use tidy DataFrame.
    if _is_product_group_layout(df):
        return _aggregate_product_groups(df)
    # ── END ADDITION 3 ───────────────────────────────────────────────────────────

    df.columns = [normalize_col_name(c) for c in df.columns]

    mapped: Dict[str, str] = {}
    for target, aliases in CANONICAL_COLUMN_ALIASES.items():
        picked = _pick_column(df.columns, aliases)
        if picked:
            mapped[picked] = target

    mapped = _apply_ai_column_mapping(df, mapped)
    df = df.rename(columns=mapped)

    if "revenue" not in df.columns:
        raise ValueError(
            "Could not detect a revenue column. "
            f"Found columns: {', '.join(df.columns)}"
        )

    df["revenue"] = to_number(df["revenue"])
    for numeric in ("costs", "profit", "margin_pct"):
        if numeric in df.columns:
            df[numeric] = to_number(df[numeric])

    if "costs" not in df.columns:
        if "profit" in df.columns:
            df["costs"] = df["revenue"] - df["profit"]
        elif "margin_pct" in df.columns:
            margin_fraction = df["margin_pct"] / 100.0
            df["profit"] = df["revenue"] * margin_fraction
            df["costs"] = df["revenue"] - df["profit"]
        else:
            raise ValueError(
                "Could not detect costs/expenses column and no profit/margin column to derive costs."
            )

    df = df.dropna(subset=["revenue", "costs"], how="all").copy()
    if df.empty:
        raise ValueError("No usable revenue/cost values found after cleaning.")

    if "month" in df.columns:
        parsed_month = pd.to_datetime(df["month"], errors="coerce")
        if parsed_month.notna().any():
            df.loc[parsed_month.notna(), "month"] = parsed_month.dt.strftime("%b %Y")
        df["month"] = df["month"].astype(str).str.strip().replace({"": None})
    else:
        df["month"] = [f"Period {i + 1}" for i in range(len(df))]

    if "profit" not in df.columns:
        df["profit"] = df["revenue"] - df["costs"]

    if "margin_pct" not in df.columns:
        denom = df["revenue"].replace(0, pd.NA)
        df["margin_pct"] = (df["profit"] / denom) * 100
    df["margin_pct"] = df["margin_pct"].fillna(0).round(1)

    return df