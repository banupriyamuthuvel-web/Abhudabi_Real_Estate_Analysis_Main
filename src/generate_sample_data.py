"""
Generate a SYNTHETIC, intentionally messy Abu Dhabi real estate dataset.

WHY: Real transaction-level data is not always freely downloadable. This script lets the
project run end to end out of the box. Replace the files in data/raw/ with real data
(Bayanat, Abu Dhabi Open Data, SCAD, Kaggle) and adjust the column names in
src/clean_data.py.

The numbers are INVENTED but follow realistic patterns (area price tiers, yearly growth,
seasonality, rent-to-price ratios). Do NOT present findings as real market facts.
"""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# area: (base AED/sqm in 2021, relative volume weight, gross yield tier)
AREAS = {
    "Al Reem Island": (10500, 0.18, 0.068),
    "Saadiyat Island": (15000, 0.10, 0.052),
    "Yas Island": (11800, 0.12, 0.060),
    "Al Raha Beach": (10000, 0.08, 0.063),
    "Al Maryah Island": (16500, 0.04, 0.050),
    "Corniche Area": (12000, 0.05, 0.058),
    "Masdar City": (8200, 0.04, 0.070),
    "Khalifa City": (6600, 0.10, 0.072),
    "Mohammed Bin Zayed City": (5700, 0.09, 0.078),
    "Al Reef": (6100, 0.08, 0.076),
    "Al Ghadeer": (5200, 0.07, 0.082),
    "Al Raha Gardens": (7000, 0.05, 0.071),
}
AREA_NAMES = list(AREAS)
AREA_P = np.array([v[1] for v in AREAS.values()])
AREA_P = AREA_P / AREA_P.sum()

# type: (avg sqm, sd, price multiplier, share)
TYPES = {
    "Apartment": (95, 35, 1.00, 0.62),
    "Townhouse": (210, 45, 0.88, 0.14),
    "Villa": (360, 110, 0.80, 0.24),
}
TYPE_NAMES = list(TYPES)
TYPE_P = [v[3] for v in TYPES.values()]

YEAR_GROWTH = {2021: 1.00, 2022: 1.07, 2023: 1.17, 2024: 1.30, 2025: 1.41, 2026: 1.47}
# Monthly seasonality of transaction volume (Q4/Q1 stronger, summer weaker)
SEASON = np.array([1.15, 1.10, 1.05, 0.95, 0.90, 0.80, 0.75, 0.78, 0.95, 1.10, 1.20, 1.25])
YEAR_VOL = {2021: 0.7, 2022: 1.0, 2023: 1.25, 2024: 1.5, 2025: 1.65, 2026: 1.2}

# ---------------------------------------------------------------- sales
rows = []
tid = 100000
for year, yv in YEAR_VOL.items():
    last_month = 9 if year == 2026 else 12
    for month in range(1, last_month + 1):
        n = int(rng.normal(520, 25) * yv * SEASON[month - 1])
        areas = rng.choice(AREA_NAMES, size=n, p=AREA_P)
        types = rng.choice(TYPE_NAMES, size=n, p=TYPE_P)
        for area, ptype in zip(areas, types):
            base = AREAS[area][0]
            avg, sd, mult, _ = TYPES[ptype]
            size = max(30, rng.normal(avg, sd))
            ppsqm = base * YEAR_GROWTH[year] * mult * rng.lognormal(0, 0.12)
            tid += 1
            if ptype == "Apartment":
                beds = int(np.clip(round(size / 55), 0, 6))
            else:
                beds = int(rng.choice([3, 4, 5, 6]))
            rows.append({
                "transaction_id": tid,
                "transaction_date": f"{year}-{month:02d}-{int(rng.integers(1, 28)):02d}",
                "area": area,
                "property_type": ptype,
                "bedrooms": beds,
                "size_sqm": round(size, 1),
                "price_aed": round(ppsqm * size, -3),
                "sale_type": rng.choice(["Off-Plan", "Ready"], p=[0.45, 0.55]),
            })
sales = pd.DataFrame(rows)

# ---- inject realistic mess so the cleaning step is meaningful
variants = {
    "Al Reem Island": ["Reem Island", "AL REEM ISLAND", "al reem island "],
    "Saadiyat Island": ["Saadiyat", "SAADIYAT ISLAND"],
    "Yas Island": ["Yas", "yas island"],
    "Khalifa City": ["Khalifa City A", "KHALIFA CITY"],
    "Mohammed Bin Zayed City": ["MBZ City", "Mohamed Bin Zayed City", "M.B.Z City"],
    "Al Raha Beach": ["Raha Beach", "Al Raha  Beach"],
}
for i in sales.sample(frac=0.06, random_state=1).index:
    a = sales.at[i, "area"]
    if a in variants:
        sales.at[i, "area"] = rng.choice(variants[a])
sales.loc[sales.sample(frac=0.03, random_state=2).index, "size_sqm"] = np.nan
sales.loc[sales.sample(frac=0.01, random_state=3).index, "price_aed"] = np.nan
sales.loc[sales.sample(frac=0.005, random_state=4).index, "price_aed"] *= 40   # obvious outliers
sales.loc[sales.sample(frac=0.004, random_state=5).index, "size_sqm"] = 5      # impossible sizes
dd = sales.sample(frac=0.04, random_state=6).index                              # dd/mm/yyyy dates
sales.loc[dd, "transaction_date"] = (
    pd.to_datetime(sales.loc[dd, "transaction_date"]).dt.strftime("%d/%m/%Y")
)
sales = pd.concat([sales, sales.sample(frac=0.015, random_state=7)], ignore_index=True)  # duplicates
sales = sales.sample(frac=1, random_state=8).reset_index(drop=True)
sales.to_csv(RAW / "ad_sales_transactions_SAMPLE.csv", index=False)

# ---------------------------------------------------------------- rentals
rrows = []
cid = 500000
for year in range(2021, 2027):
    n_year = 2600 if year < 2026 else 1900
    for _ in range(n_year):
        area = rng.choice(AREA_NAMES, p=AREA_P)
        ptype = rng.choice(TYPE_NAMES, p=TYPE_P)
        base, _, yld = AREAS[area]
        avg, sd, mult, _ = TYPES[ptype]
        size = max(30, rng.normal(avg, sd))
        price_equiv = base * YEAR_GROWTH[year] * mult * size
        rent_growth = 1 + (YEAR_GROWTH[year] - 1) * 1.15
        rent = price_equiv * (yld / YEAR_GROWTH[year]) * rent_growth * rng.lognormal(0, 0.10)
        cid += 1
        rrows.append({
            "contract_id": cid,
            "start_date": f"{year}-{int(rng.integers(1, 13)):02d}-{int(rng.integers(1, 28)):02d}",
            "area": area,
            "property_type": ptype,
            "size_sqm": round(size, 1),
            "annual_rent_aed": round(rent, -2),
        })
rent = pd.DataFrame(rrows)
rent.to_csv(RAW / "ad_rental_contracts_SAMPLE.csv", index=False)

print(f"sales rows: {len(sales):,} | rental rows: {len(rent):,}")
