# 3I/ATLAS — Satellite Observer Web App (Local)

A lightweight Streamlit app to browse and filter spacecraft relevant to observing 3I/ATLAS.
Loads a CSV with NORAD & COSPAR IDs, operators, mission types, and quick-view utility notes.

## Quickstart (Windows)
```powershell
cd 3I_ATLAS_webapp
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL printed in the terminal (usually http://localhost:8501).

## Data
- `data/3I_ATLAS_satellites_with_NORAD.csv` (included)

## Notes
- You can upload an updated CSV via the sidebar.
- The app is offline by default; future enhancements can add live queries for TLEs on trackable assets.
