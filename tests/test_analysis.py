import pandas as pd
from analysis import run_full_analysis, compute_beneish, benford_first_digit_test


def load_sample():
    return pd.read_csv("sample_data.csv")


def test_run_full_analysis_returns_keys():
    df = load_sample()
    res = run_full_analysis(df, amount_cols_for_benford=["revenue", "cfo"]) 
    assert isinstance(res, dict)
    assert "beneish_table" in res
    assert "ratios_table" in res


def test_beneish_computes_mscore():
    df = load_sample()
    out = compute_beneish(df)
    assert "beneish_Mscore" in out.columns


def test_benford_runs():
    df = load_sample()
    b = benford_first_digit_test(df, ["revenue", "cfo"]) 
    assert "observed_counts" in b and "pvalue" in b
