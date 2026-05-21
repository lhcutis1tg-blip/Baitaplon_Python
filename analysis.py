"""analysis.py

Utility functions for financial red-flag detection:
- Beneish M-Score calculation
- Benford's Law first-digit test
- Common financial ratios and CFO vs Net Income checks

Designed to be robust to missing columns and vectorized with pandas.
"""
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from scipy.stats import chisquare


def compute_beneish(df: pd.DataFrame, revenue_col: str = "revenue",
                    receivables_col: str = "receivables",
                    gross_profit_col: Optional[str] = None,
                    total_assets_col: str = "total_assets",
                    cfo_col: str = "cfo",
                    net_income_col: str = "net_income",
                    sga_col: Optional[str] = None,
                    long_term_debt_col: Optional[str] = None,
                    period_col: Optional[str] = None) -> pd.DataFrame:
    """Compute Beneish M-Score per period using available proxies.

    The function expects a DataFrame sorted by time with latest period last.
    It returns the DataFrame augmented with M-score and component columns where calculable.
    Missing inputs will produce NaN for the corresponding components.
    """
    df = df.copy()
    # Ensure numeric
    for col in [revenue_col, receivables_col, total_assets_col, cfo_col, net_income_col]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # shift previous period
    prev = df.shift(1)

    # DSRI = (Receivables_t / Sales_t) / (Receivables_t-1 / Sales_t-1)
    def safe_div(a, b):
        return a.div(b).replace([np.inf, -np.inf], np.nan)

    dsri = safe_div(safe_div(df.get(receivables_col), df.get(revenue_col)),
                    safe_div(prev.get(receivables_col), prev.get(revenue_col)))

    # GMI = (GrossMargin_{t-1}/Sales_{t-1}) / (GrossMargin_t/Sales_t)
    if gross_profit_col and gross_profit_col in df.columns:
        gmi = safe_div(safe_div(prev[gross_profit_col], prev[revenue_col]),
                       safe_div(df[gross_profit_col], df[revenue_col]))
    else:
        # fallback: use revenue growth inverse
        gmi = safe_div(prev.get(revenue_col), df.get(revenue_col))

    # AQI: asset quality index -- proxy using non-current assets share
    if total_assets_col in df.columns:
        prev_noncurrent_share = safe_div(prev.get(total_assets_col) - prev.get(receivables_col, 0), prev.get(total_assets_col))
        curr_noncurrent_share = safe_div(df.get(total_assets_col) - df.get(receivables_col, 0), df.get(total_assets_col))
        aqi = safe_div(curr_noncurrent_share, prev_noncurrent_share)
    else:
        aqi = pd.Series(np.nan, index=df.index)

    # SGI: sales growth index
    sgi = safe_div(df.get(revenue_col), prev.get(revenue_col))

    # DEPI: depreciation index - approximate with change in accumulated depreciation ratio if available
    depi = pd.Series(np.nan, index=df.index)
    # SGAI: selling, general & admin expense index
    if sga_col and sga_col in df.columns:
        sgai = safe_div(safe_div(df[sga_col], df.get(revenue_col)), safe_div(prev.get(sga_col), prev.get(revenue_col)))
    else:
        sgai = pd.Series(np.nan, index=df.index)

    # LVGI: leverage growth index - proxy using long-term debt share
    if long_term_debt_col and long_term_debt_col in df.columns:
        lvgi = safe_div(safe_div(df[long_term_debt_col], df.get(total_assets_col)), safe_div(prev.get(long_term_debt_col), prev.get(total_assets_col)))
    else:
        lvgi = pd.Series(np.nan, index=df.index)

    # TATA: total accruals to total assets = (Net income - CFO)/Total assets
    tata = safe_div(df.get(net_income_col) - df.get(cfo_col), df.get(total_assets_col))

    # Compose M-Score using Beneish coefficients (original model)
    # M = -4.84 + 0.92*DSRI + 0.528*GMI +0.404*AQI +0.892*SGI +0.115*DEPI -0.172*SGAI +4.679*TATA -0.327*LVGI
    m = -4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi

    df["beneish_DSRI"] = dsri
    df["beneish_GMI"] = gmi
    df["beneish_AQI"] = aqi
    df["beneish_SGI"] = sgi
    df["beneish_DEPI"] = depi
    df["beneish_SGAI"] = sgai
    df["beneish_LVGI"] = lvgi
    df["beneish_TATA"] = tata
    df["beneish_Mscore"] = m
    df["beneish_flag"] = df["beneish_Mscore"] > -1.78  # standard threshold: > -1.78 indicates likely manipulator

    return df


def benford_first_digit_test(df: pd.DataFrame, amount_cols: List[str]) -> Dict:
    """Run Benford first-digit test on specified numeric columns.

    Returns a dict with observed frequencies, expected frequencies and chi-square p-value.
    """
    # gather concatenated absolute positive numeric values
    vals = []
    for c in amount_cols:
        if c in df.columns:
            series = pd.to_numeric(df[c], errors="coerce").dropna().abs()
            vals.append(series)
    if not vals:
        raise ValueError("No valid amount columns found for Benford test")
    allv = pd.concat(vals)
    # Extract first non-zero digit
    first = allv.map(lambda x: int(str(x).lstrip('0.')[0]) if x > 0 else np.nan).dropna()
    obs_counts = first.value_counts().reindex(range(1, 10), fill_value=0).astype(int)
    total = obs_counts.sum()
    obs_freq = obs_counts / total
    expected = np.array([np.log10(1 + 1 / d) for d in range(1, 10)])
    expected_counts = expected * total
    chi, p = chisquare(f_obs=obs_counts.values, f_exp=expected_counts)
    return {
        "observed_counts": obs_counts.to_dict(),
        "observed_freq": obs_freq.to_dict(),
        "expected_freq": {i + 1: float(expected[i]) for i in range(9)},
        "chi2": float(chi),
        "pvalue": float(p),
    }


def compute_ratios(df: pd.DataFrame, revenue_col: str = "revenue", cogs_col: str = "cogs",
                   total_liabilities_col: str = "total_liabilities", total_assets_col: str = "total_assets",
                   gross_profit_col: Optional[str] = None) -> pd.DataFrame:
    """Compute standard ratios: gross margin, debt ratio, current ratio proxy if available."""
    df = df.copy()
    df["gross_margin"] = np.nan
    if gross_profit_col and gross_profit_col in df.columns:
        df["gross_margin"] = safe_div_col(df, gross_profit_col, revenue_col)
    elif revenue_col in df.columns and cogs_col in df.columns:
        df["gross_margin"] = safe_div_col(df, revenue_col, revenue_col) - safe_div_col(df, cogs_col, revenue_col)

    if total_assets_col in df.columns:
        df["debt_ratio"] = safe_div_col(df, total_liabilities_col, total_assets_col)
    else:
        df["debt_ratio"] = np.nan

    return df


def safe_div_col(df: pd.DataFrame, num_col: str, den_col: str) -> pd.Series:
    return df.get(num_col) / df.get(den_col)


def cfo_vs_net_income_check(df: pd.DataFrame, cfo_col: str = "cfo", net_income_col: str = "net_income") -> pd.DataFrame:
    """Flag odd CFO vs Net Income situations.

    Flags:
    - `cfo_negative_net_positive`: CFO < 0 and Net Income > 0
    - `cfo_less_half_net`: CFO < 0.5 * Net Income when Net Income > 0
    """
    df = df.copy()
    df[cfo_col] = pd.to_numeric(df.get(cfo_col), errors="coerce")
    df[net_income_col] = pd.to_numeric(df.get(net_income_col), errors="coerce")
    df["cfo_negative_net_positive"] = (df[cfo_col] < 0) & (df[net_income_col] > 0)
    df["cfo_less_half_net"] = (df[cfo_col] < 0.5 * df[net_income_col]) & (df[net_income_col] > 0)
    return df


def run_full_analysis(df: pd.DataFrame, amount_cols_for_benford: Optional[List[str]] = None) -> Dict:
    """Run a collection of analyses and return structured results."""
    results = {}
    # Beneish
    bene = compute_beneish(df)
    results["beneish_table"] = bene[[c for c in bene.columns if c.startswith("beneish_")]].tail(10)

    # Ratios
    ratios = compute_ratios(df)
    results["ratios_table"] = ratios[["gross_margin", "debt_ratio"]].tail(10)

    # CFO checks
    cfo_checks = cfo_vs_net_income_check(df)
    results["cfo_checks"] = cfo_checks[["cfo_negative_net_positive", "cfo_less_half_net"]].tail(10)

    # Benford
    if amount_cols_for_benford:
        try:
            benf = benford_first_digit_test(df, amount_cols_for_benford)
            results["benford"] = benf
        except Exception as e:
            results["benford_error"] = str(e)

    return results
