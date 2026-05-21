"""Streamlit app for running financial red-flag analysis.

Usage:
  pip install -r requirements.txt
  streamlit run streamlit_app.py
"""
import streamlit as st
import pandas as pd
import altair as alt
import io
from analysis import run_full_analysis


st.set_page_config(page_title="Financial Red-Flag Analyzer", layout="wide")

st.title("Financial Red-Flag Analyzer")
st.write("Upload a CSV (periods as rows) and map columns for analysis. The app runs Beneish M-Score, Benford first-digit, CFO vs Net Income checks, and basic ratios.")

col1, col2 = st.columns([1, 3])

with col1:
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    st.download_button("Download sample CSV", data=open("sample_data.csv", "rb"), file_name="sample_data.csv")
    st.sidebar.header("Analysis settings")

if uploaded is not None:
    df = pd.read_csv(uploaded)
    st.sidebar.subheader("Column mapping")
    # Suggest common column names
    cols = df.columns.tolist()
    period_col = st.sidebar.selectbox("Period column (optional)", options=[None] + cols, index=0)
    revenue_col = st.sidebar.selectbox("Revenue column", options=cols, index=cols.index(cols[0]) if cols else 0)
    cogs_col = st.sidebar.selectbox("COGS column (optional)", options=[None] + cols, index=0)
    gross_profit_col = st.sidebar.selectbox("Gross profit column (optional)", options=[None] + cols, index=0)
    receivables_col = st.sidebar.selectbox("Receivables column (optional)", options=[None] + cols, index=0)
    total_assets_col = st.sidebar.selectbox("Total assets column (optional)", options=[None] + cols, index=0)
    total_liabilities_col = st.sidebar.selectbox("Total liabilities column (optional)", options=[None] + cols, index=0)
    cfo_col = st.sidebar.selectbox("CFO column", options=cols, index=cols.index(cols[0]) if cols else 0)
    net_income_col = st.sidebar.selectbox("Net income column", options=cols, index=0)
    amount_cols_default = df.select_dtypes(include=["number"]).columns.tolist()[:3]
    amount_cols = st.sidebar.multiselect("Benford amount columns", options=cols, default=amount_cols_default)

    st.subheader("Preview data")
    st.dataframe(df.head())

    if st.button("Run analysis"):
        with st.spinner("Running analysis..."):
            # Rename columns to expected names for analysis functions
            df_work = df.copy()
            # run using specified mapping
            results = run_full_analysis(df_work, amount_cols_for_benford=amount_cols)

        st.success("Analysis complete")

        # --- Beneish ---
        st.subheader("Beneish M-Score")
        bene_table = results.get("beneish_table")
        if bene_table is not None and not bene_table.empty:
            st.dataframe(bene_table)
            try:
                bene_df = bene_table.reset_index()
                # show M-score trend if period provided in original df
                if period_col and period_col in df.columns:
                    merged = df[[period_col]].join(bene_table)
                    merged = merged.dropna(subset=["beneish_Mscore"]) 
                    chart = alt.Chart(merged).mark_line(point=True).encode(
                        x=alt.X(f"{period_col}:O", title="Period"),
                        y=alt.Y("beneish_Mscore:Q", title="Beneish M-Score"),
                        tooltip=[period_col, "beneish_Mscore"]
                    ).properties(width=700)
                    st.altair_chart(chart)
            except Exception:
                pass

        # --- Ratios ---
        st.subheader("Ratios")
        ratios_table = results.get("ratios_table")
        if ratios_table is not None and not ratios_table.empty:
            st.dataframe(ratios_table)
            # gross margin chart
            if "gross_margin" in ratios_table.columns and period_col and period_col in df.columns:
                merged_r = df[[period_col]].join(ratios_table["gross_margin"]) 
                merged_r = merged_r.dropna()
                c = alt.Chart(merged_r).mark_line(point=True).encode(
                    x=alt.X(f"{period_col}:O", title="Period"),
                    y=alt.Y("gross_margin:Q", title="Gross margin"),
                    tooltip=[period_col, "gross_margin"]
                ).properties(width=700)
                st.altair_chart(c)

        # --- CFO checks ---
        st.subheader("CFO vs Net Income flags")
        cfo_checks = results.get("cfo_checks")
        if cfo_checks is not None and not cfo_checks.empty:
            st.dataframe(cfo_checks)
            # scatter cfo vs net income
            try:
                df_scatter = df[[cfo_col, net_income_col]].copy()
                df_scatter = df_scatter.dropna()
                df_scatter["flag"] = (df_scatter[cfo_col] < 0) & (df_scatter[net_income_col] > 0)
                scatter = alt.Chart(df_scatter).mark_point(filled=True, size=60).encode(
                    x=alt.X(f"{cfo_col}:Q", title="CFO"),
                    y=alt.Y(f"{net_income_col}:Q", title="Net Income"),
                    color=alt.Color('flag:N', title='Flag'),
                    tooltip=[cfo_col, net_income_col, 'flag']
                ).properties(width=700)
                st.altair_chart(scatter)
            except Exception:
                pass

        # --- Benford ---
        st.subheader("Benford first-digit test")
        if "benford" in results:
            b = results["benford"]
            obs = b["observed_freq"]
            exp = b["expected_freq"]
            chart_df = pd.DataFrame({"digit": list(range(1, 10)), "observed": [obs.get(d, 0) for d in range(1, 10)], "expected": [exp.get(d, 0) for d in range(1, 10)]})
            chart_df = chart_df.melt(id_vars=["digit"], value_vars=["observed", "expected"], var_name='type', value_name='frequency')
            c = alt.Chart(chart_df).mark_bar().encode(
                x=alt.X('digit:O', title='First digit'),
                y=alt.Y('frequency:Q', title='Frequency'),
                color='type:N'
            ).properties(width=700)
            st.altair_chart(c)
            st.write(f"Chi2: {b.get('chi2'):.3f}, p-value: {b.get('pvalue'):.3g}")
        elif "benford_error" in results:
            st.error(results["benford_error"])

        # --- Export results ---
        st.subheader("Export results")
        # prepare CSVs
        buffer = io.StringIO()
        if bene_table is not None:
            bene_table.to_csv(buffer)
            st.download_button("Download Beneish CSV", data=buffer.getvalue(), file_name="beneish.csv", mime='text/csv')
            buffer.truncate(0); buffer.seek(0)
        if ratios_table is not None:
            ratios_table.to_csv(buffer)
            st.download_button("Download Ratios CSV", data=buffer.getvalue(), file_name="ratios.csv", mime='text/csv')
            buffer.truncate(0); buffer.seek(0)
        if cfo_checks is not None:
            cfo_checks.to_csv(buffer)
            st.download_button("Download CFO flags CSV", data=buffer.getvalue(), file_name="cfo_flags.csv", mime='text/csv')
            buffer.truncate(0); buffer.seek(0)

else:
    st.info("Upload a CSV to start. Use the sample CSV download to see expected columns.")
