# app.py
# ------------------------------------------------------------
# 3I/ATLAS — Satellite Observer Set (Local Streamlit App)
#
# What this app does:
# • Loads a CSV (default: data/3I_ATLAS_satellites_with_NORAD.csv)
# • Lets you search (case-insensitive) across chosen text columns
# • Filters by mission, operator, location, TLE availability, utility
# • Shows KPIs, a sortable table, and simple bar charts (Plotly)
# • Exports the filtered results to CSV
#
# Notes:
# • We deliberately keep `use_container_width=True` (works across versions).
# • The Quick Charts section is hardened to avoid Plotly dataframe naming issues.
# • If you upload a CSV in the sidebar, it replaces the default one for the session.
# ------------------------------------------------------------

from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st


# -----------------------------
# Page config & light styling
# -----------------------------
st.set_page_config(
    page_title="3I/ATLAS Satellite Observer Set",
    page_icon="🛰️",
    layout="wide",
)

# Optional: tighten page padding a bit
st.markdown(
    """
    <style>
      .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Cached CSV loader
# -----------------------------
@st.cache_data
def load_csv(csv_path: Path) -> pd.DataFrame:
    """Load CSV with light normalization to avoid common dtype/text issues."""
    df = pd.read_csv(csv_path)

    # Normalize booleans as strings for consistent filtering
    if "Earth_TLE_Available" in df.columns:
        df["Earth_TLE_Available"] = (
            df["Earth_TLE_Available"]
            .astype(str)
            .replace({"True": "True", "False": "False", "true": "True", "false": "False"})
        )

    # Parse dates if present
    if "Launch_Date_UTC" in df.columns:
        df["Launch_Date_UTC"] = pd.to_datetime(df["Launch_Date_UTC"], errors="coerce")

    # Ensure common text columns are strings (avoids .str errors)
    for c in ["Name", "Operator", "Notes", "Mission_Type", "Current_Location", "3I_ATLAS_View_Utility"]:
        if c in df.columns:
            df[c] = df[c].astype(str)

    return df


# -----------------------------
# Title & description
# -----------------------------
st.title("🛰️ 3I/ATLAS — Satellite Observer Set")
st.markdown(
    """
This app explores spacecraft that could observe **3I/ATLAS**, including their NORAD/SatCat and COSPAR IDs.
Use the sidebar to search and filter; export your filtered results as CSV.
"""
)


# -----------------------------
# Data source (default or upload)
# -----------------------------
default_csv = Path("data/3I_ATLAS_satellites_with_NORAD.csv")

st.sidebar.header("Data Source")
uploaded = st.sidebar.file_uploader("Upload a CSV (optional)", type=["csv"])

if uploaded is not None:
    df = pd.read_csv(uploaded)
else:
    df = load_csv(default_csv)

# Warn gently if the common search fields are missing
expected_like = ["Name", "Operator", "Notes"]
present_like = [c for c in expected_like if c in df.columns]
if not present_like:
    st.warning(
        "Heads up: columns **Name**, **Operator**, **Notes** were not found. "
        "Search will still work, but over fewer fields."
    )


# -----------------------------
# Sidebar: Search & Filters
# -----------------------------
st.sidebar.header("Filters")

# (1) Choose which columns to search (default to Name/Operator/Notes if present)
searchable_defaults = [c for c in ["Name", "Operator", "Notes"] if c in df.columns]
searchable_all = [c for c in df.columns if df[c].dtype == "object"]  # text-like columns only

search_cols = st.sidebar.multiselect(
    "Columns to search",
    options=searchable_all,
    default=searchable_defaults or searchable_all[:3],  # fallback to first few text cols
    help="Choose which text columns the search box will scan.",
)

# Build a single lowercase haystack column for fast search
if search_cols:
    df["_hay"] = (
        df[search_cols].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
    )
else:
    df["_hay"] = ""

# (2) Text search (case-insensitive substring over _hay)
q = st.sidebar.text_input("Search by selected columns", value="", help="Case-insensitive substring match.")
ql = q.strip().lower()

# (3) Categorical multi-select filters
def unique_sorted(col: str):
    return sorted([x for x in df[col].dropna().unique().tolist()])

multi_filter_cols = [
    "Mission_Type",
    "Operator",
    "Current_Location",
    "Earth_TLE_Available",
    "3I_ATLAS_View_Utility",
]

selected_values = {}
for col in multi_filter_cols:
    if col in df.columns:
        options = unique_sorted(col)
        # default selects "all" so the filter only constrains if you narrow it
        selected_values[col] = st.sidebar.multiselect(col, options=options, default=options)

# (4) Reset filters button: clears search & resets multiselects by rerunning
if st.sidebar.button("Reset filters"):
    st.rerun()


# -----------------------------
# Apply filters to dataframe
# -----------------------------
mask = pd.Series(True, index=df.index)

# Text search
if ql:
    mask &= df["_hay"].str.contains(ql, na=False, regex=False)

# Categorical filters
for col, allowed in selected_values.items():
    if col in df.columns and allowed:
        mask &= df[col].fillna("Unknown").isin(allowed)

# Final filtered frame
fdf = df[mask].copy()


# -----------------------------
# KPIs (quick glance)
# -----------------------------
k1, k2, k3 = st.columns(3)
with k1:
    st.metric("Spacecraft (filtered)", len(fdf))
with k2:
    st.metric("Mission types", fdf["Mission_Type"].nunique() if "Mission_Type" in fdf.columns else "—")
with k3:
    st.metric("Operators", fdf["Operator"].nunique() if "Operator" in fdf.columns else "—")

if ql and search_cols:
    st.caption(f"Searching for **{q}** in: {', '.join(search_cols)}")


# -----------------------------
# Results table
# -----------------------------
st.subheader("Filtered Table")
# Keep container width for compatibility with current versions
st.dataframe(fdf, use_container_width=True)

# Optional: summarize active filters below the table
if any(selected_values.values()) or ql:
    with st.expander("Active filters (summary)"):
        if ql:
            st.write(f"Text search: `{q}` over {', '.join(search_cols)}")
        for col, allowed in selected_values.items():
            if col in fdf.columns:
                all_vals = unique_sorted(col)
                if len(allowed) != len(all_vals):  # only show if not "all"
                    st.write(f"**{col}**: {', '.join(map(str, allowed))}")


# -----------------------------
# Quick Charts (hardened)
# -----------------------------
st.subheader("Quick Charts")
chart_cols = st.multiselect(
    "Pick one or more categorical columns to chart",
    [c for c in ["Mission_Type", "Operator", "Current_Location", "3I_ATLAS_View_Utility"] if c in fdf.columns],
    default=[c for c in ["Mission_Type", "3I_ATLAS_View_Utility"] if c in fdf.columns],
)

for c in chart_cols:
    if c in fdf.columns and not fdf.empty:
        # Build counts in a way that is robust across Pandas versions
        vc = fdf[c].fillna("Unknown").value_counts(dropna=False)
        counts = vc.reset_index()

        # Normalize to exactly two columns: [c, 'count']
        # Depending on Pandas version, reset_index() can produce different column names.
        if "index" in counts.columns:
            # Typical case: columns like ['index', c] or ['index', 0]
            other_col = [col for col in counts.columns if col != "index"][0]
            counts = counts.rename(columns={"index": c, other_col: "count"})
        else:
            # Already something like [c, 'count'] or [c, 0]
            second = counts.columns[1]
            if second != "count":
                counts = counts.rename(columns={second: "count"})

        # Now Plotly sees x=<category column>, y='count'
        fig = px.bar(counts, x=c, y="count", title=f"Count by {c}")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"No data to chart for '{c}' with current filters.")


# -----------------------------
# Export filtered results
# -----------------------------
st.subheader("Export")
# Drop helper columns like _hay so exports are clean
export_df = fdf.drop(columns=[col for col in ["_hay"] if col in fdf.columns])
st.download_button(
    label="Download filtered CSV",
    data=export_df.to_csv(index=False).encode("utf-8"),
    file_name="3I_ATLAS_satellites_filtered.csv",
    mime="text/csv",
)

# -----------------------------
# Footer
# -----------------------------
st.caption("Built with Streamlit • Data: NORAD & COSPAR IDs compiled for 3I/ATLAS observers")


