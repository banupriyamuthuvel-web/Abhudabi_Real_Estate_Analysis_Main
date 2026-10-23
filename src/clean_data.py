"""
Clean raw sales and rental data and write analysis-ready CSVs to data/clean/.

Run from the project root:  python src/clean_data.py
Every step prints how many rows it affected, so the cleaning log is reproducible.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)

# Map every spelling variant to one standard area name (lowercase key)
AREA_MAP = {
    "reem island": "Al Reem Island", "al reem island": "Al Reem Island",
    "saadiyat": "Saadiyat Island", "saadiyat island": "Saadiyat Island",
    "yas": "Yas Island", "yas island": "Yas Island",
    "khalifa city": "Khalifa City", "khalifa city a": "Khalifa City",
    "mbz city": "Mohammed Bin Zayed City", "m.b.z city": "Mohammed Bin Zayed City",
    "mohamed bin zayed city": "Mohammed Bin Zayed City",
    "mohammed bin zayed city": "Mohammed Bin Zayed City",
    "raha beach": "Al Raha Beach", "al raha beach": "Al Raha Beach",
    "al maryah island": "Al Maryah Island", "corniche area": "Corniche Area",
    "masdar city": "Masdar City", "al reef": "Al Reef",
    "al ghadeer": "Al Ghadeer", "al raha gardens": "Al Raha Gardens",
}


def standardise_area(s: pd.Series) -> pd.Series:
    key = s.astype(str).str.strip().str.lower().apply(lambda x: re.sub(r"\s+", " ", x))
    out = key.map(AREA_MAP)
    unmapped = key[out.isna()].unique()
    if len(unmapped):
        print(f"  WARNING unmapped area names: {list(unmapped)}")
    return out.fillna(s.str.strip().str.title())


def parse_dates(s: pd.Series) -> pd.Series:
    iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    dmy = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    return iso.fillna(dmy)


def clean_sales() -> pd.DataFrame:
    df = pd.read_csv(RAW / "ad_sales_transactions_SAMPLE.csv")
    print(f"SALES raw rows: {len(df):,}")

    n = len(df)
    df = df.drop_duplicates(subset="transaction_id")
    print(f"  duplicates removed: {n - len(df):,}")

    df["area"] = standardise_area(df["area"])
    df["transaction_date"] = parse_dates(df["transaction_date"])
    print(f"  unparseable dates: {df['transaction_date'].isna().sum():,}")

    n = len(df)
    df = df.dropna(subset=["transaction_date", "price_aed", "size_sqm"])
    print(f"  rows dropped for missing date/price/size: {n - len(df):,}")

    n = len(df)
    df = df[df["size_sqm"] >= 20]  # impossible sizes
    print(f"  rows dropped for size < 20 sqm: {n - len(df):,}")

    df["price_per_sqm"] = df["price_aed"] / df["size_sqm"]

    # Outliers: flag anything beyond 3 IQR of price/sqm within its area (robust to skew)
    q1 = df.groupby("area")["price_per_sqm"].transform(lambda x: x.quantile(0.25))
    q3 = df.groupby("area")["price_per_sqm"].transform(lambda x: x.quantile(0.75))
    iqr = q3 - q1
    mask = (df["price_per_sqm"] < q1 - 3 * iqr) | (df["price_per_sqm"] > q3 + 3 * iqr)
    print(f"  price/sqm outliers removed: {mask.sum():,}")
    df = df[~mask]

    df["year"] = df["transaction_date"].dt.year
    df["quarter"] = df["transaction_date"].dt.quarter
    df["month"] = df["transaction_date"].dt.month
    df["year_quarter"] = df["year"].astype(str) + "-Q" + df["quarter"].astype(str)
    df["property_group"] = np.where(df["property_type"] == "Apartment", "Apartment", "Villa/Townhouse")
    df["price_per_sqm"] = df["price_per_sqm"].round(0)

    df = df.sort_values("transaction_date").reset_index(drop=True)
    df.to_csv(CLEAN / "sales_clean.csv", index=False, date_format="%Y-%m-%d")
    print(f"SALES clean rows: {len(df):,}\n")
    return df


def clean_rentals() -> pd.DataFrame:
    df = pd.read_csv(RAW / "ad_rental_contracts_SAMPLE.csv")
    print(f"RENTALS raw rows: {len(df):,}")
    df = df.drop_duplicates(subset="contract_id")
    df["area"] = standardise_area(df["area"])
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df = df.dropna(subset=["start_date", "annual_rent_aed", "size_sqm"])
    df = df[df["size_sqm"] >= 20]
    df["rent_per_sqm"] = (df["annual_rent_aed"] / df["size_sqm"]).round(0)
    df["year"] = df["start_date"].dt.year
    df.to_csv(CLEAN / "rentals_clean.csv", index=False, date_format="%Y-%m-%d")
    print(f"RENTALS clean rows: {len(df):,}")
    return df


if __name__ == "__main__":
    clean_sales()
    clean_rentals()
