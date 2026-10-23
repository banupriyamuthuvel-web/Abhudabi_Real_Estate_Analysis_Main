"""
Load the clean CSVs into a SQLite database and run every query in sql/analysis_queries.sql.
Results are saved to data/clean/sql_results/Q<n>.csv and printed.

Run from the project root:  python src/run_sql.py
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
DB = CLEAN / "real_estate.db"
OUT = CLEAN / "sql_results"
OUT.mkdir(exist_ok=True)

con = sqlite3.connect(DB)
pd.read_csv(CLEAN / "sales_clean.csv").to_sql("sales", con, if_exists="replace", index=False)
pd.read_csv(CLEAN / "rentals_clean.csv").to_sql("rentals", con, if_exists="replace", index=False)
con.execute("CREATE INDEX IF NOT EXISTS idx_sales_area_year ON sales(area, year)")
con.execute("CREATE INDEX IF NOT EXISTS idx_rentals_area_year ON rentals(area, year)")

sql_text = (ROOT / "sql" / "analysis_queries.sql").read_text()
blocks = re.split(r"(?m)^-- (Q\d+)\.", sql_text)
# blocks = [preamble, 'Q1', body1, 'Q2', body2, ...]
for qid, body in zip(blocks[1::2], blocks[2::2]):
    lines = body.strip().splitlines()
    title = lines[0].strip()                 # rest of the "-- Q<n>." header line
    statement = "\n".join(lines[1:]).strip()  # remaining comments + the SQL itself
    df = pd.read_sql_query(statement, con)
    df.to_csv(OUT / f"{qid}.csv", index=False)
    print(f"\n=== {qid}. {title}")
    print(df.head(12).to_string(index=False))

con.close()
