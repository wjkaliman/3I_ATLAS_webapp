
import pandas as pd
import plotly.express as px
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="3I/ATLAS Satellite Observer Set", page_icon="🛰️", layout="wide")

@st.cache_data
def load_data(csv_path: Path):
    df = pd.read_csv(csv_path)
    if "Earth_TLE_Available" in df.columns:
        df["Earth_TLE_Available"] = df["Earth_TLE_Available"].astype(str)
    if "Launch_Date_UTC" in df.columns:
        df["Launch_Date_UTC"] = pd.to_datetime(df["Launch_Date_UTC"], errors="coerce")
    return df

st.title("🛰️ 3I/ATLAS — Satellite Observer Set")
st.markdown(
    """This app explores spacecraft that could observe **3I/ATLAS**, with NORAD/SatCat and COSPAR IDs.
Use the sidebar to filter; click column headers to sort. Export the filtered results as CSV."""
)

default_csv = Path("data/3I_ATLAS_satellites_with_NORAD.csv")
csv_file = st.sidebar.file_uploader("Upload a CSV (optional)", type=["csv"])
if csv_file is not None:
    df = pd.read_csv(csv_file)
else:
    df = load_data(default_csv)

st.sidebar.header("Filters")
q = st.sidebar.text_input("Search by name/operator/notes", "")

def uniques(col):
    return sorted([x for x in df[col].dropna().unique().tolist()])

col_filters = {}
for col in ["Mission_Type", "Operator", "Current_Location", "Earth_TLE_Available", "3I_ATLAS_View_Utility"]:
    if col in df.columns:
        opts = uniques(col)
        sel = st.sidebar.multiselect(col, opts, default=opts)
        col_filters[col] = set(sel)

mask = pd.Series([True]*len(df))
if q:
    ql = q.lower()
    def row_match(row):
        hay = " ".join([str(row.get(c, "")) for c in ["Name","Operator","Notes"]]).lower()
        return ql in hay
    mask = mask & df.apply(row_match, axis=1)

for col, allowed in col_filters.items():
    if col in df.columns:
        mask = mask & df[col].fillna("Unknown").isin(list(allowed))

fdf = df[mask].copy()

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Spacecraft (filtered)", len(fdf))
with c2:
    st.metric("Mission types", fdf["Mission_Type"].nunique() if "Mission_Type" in fdf.columns else "—")
with c3:
    st.metric("Operators", fdf["Operator"].nunique() if "Operator" in fdf.columns else "—")

st.subheader("Filtered Table")
st.dataframe(fdf, use_container_width=True)

chart_cols = st.multiselect(
    "Pick a categorical column for a bar chart (optional)",
    [c for c in ["Mission_Type", "Operator", "Current_Location", "3I_ATLAS_View_Utility"] if c in fdf.columns],
    default=[c for c in ["Mission_Type", "3I_ATLAS_View_Utility"] if c in fdf.columns],
)
for c in chart_cols:
    counts = fdf[c].value_counts().reset_index()
    counts.columns = [c, "count"]
    fig = px.bar(counts, x=c, y="count", title=f"Count by {c}")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Export")
st.download_button(
    "Download filtered CSV",
    fdf.to_csv(index=False).encode("utf-8"),
    file_name="3I_ATLAS_satellites_filtered.csv",
    mime="text/csv",
)

st.caption("Built with Streamlit • Data: NORAD & COSPAR IDs compiled for 3I/ATLAS observers")
