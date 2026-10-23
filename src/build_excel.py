"""
Build excel/summary_pivot.xlsx: a formula-driven summary (AVERAGEIFS / COUNTIFS / SUMIFS)
on top of the cleaned data, with charts. Change the selected year in Summary!B3 and
everything recalculates.

Run from the project root:  python src/build_excel.py
"""
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
sales = pd.read_csv(ROOT / "data/clean/sales_clean.csv")
rent = pd.read_csv(ROOT / "data/clean/rentals_clean.csv")

FONT = "Arial"
HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(name=FONT, bold=True, color="FFFFFF")
INPUT_FONT = Font(name=FONT, bold=True, color="0000FF")
INPUT_FILL = PatternFill("solid", fgColor="FFFF00")
BASE = Font(name=FONT)
thin = Side(style="thin", color="BFBFBF")
BORDER = Border(top=thin, bottom=thin, left=thin, right=thin)

wb = Workbook()

# ------------------------------------------------------------------ data sheets
ws_s = wb.active
ws_s.title = "Sales_Data"
cols_s = ["transaction_id", "transaction_date", "year", "area", "property_type", "size_sqm", "price_aed", "price_per_sqm"]
ws_s.append(cols_s)
for r in sales[cols_s].itertuples(index=False):
    ws_s.append(list(r))
n_s = len(sales) + 1

ws_r = wb.create_sheet("Rentals_Data")
cols_r = ["contract_id", "start_date", "year", "area", "property_type", "size_sqm", "annual_rent_aed", "rent_per_sqm"]
ws_r.append(cols_r)
for r in rent[cols_r].itertuples(index=False):
    ws_r.append(list(r))
n_r = len(rent) + 1

for ws in (ws_s, ws_r):
    for c in ws[1]:
        c.font, c.fill = HDR_FONT, HDR_FILL
    ws.freeze_panes = "A2"
    for i, w in enumerate([14, 16, 8, 26, 16, 10, 14, 14], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = BASE
    ws.auto_filter.ref = ws.dimensions

# Named ranges as absolute strings for readability
S = lambda col: f"Sales_Data!${col}$2:${col}${n_s}"
R = lambda col: f"Rentals_Data!${col}$2:${col}${n_r}"

areas = sorted(sales["area"].unique())
years = sorted(sales["year"].unique())

# ------------------------------------------------------------------ Summary
ws = wb.create_sheet("Summary", 0)
ws["A1"] = "Abu Dhabi Real Estate - Area Summary"
ws["A1"].font = Font(name=FONT, size=14, bold=True)
ws["A2"] = "SAMPLE (synthetic) data - illustrative only. Blue/yellow cell is the input; all other numbers are formulas."
ws["A2"].font = Font(name=FONT, italic=True, color="7F7F7F")
ws["A3"], ws["B3"] = "Select year:", 2025
ws["A3"].font = BASE
ws["B3"].font, ws["B3"].fill, ws["B3"].border = INPUT_FONT, INPUT_FILL, BORDER

hdr = ["Area", "Transactions", "Avg price (AED/sqm)", "Total value (AED m)", "Avg rent (AED/sqm/yr)",
       "Gross yield %", "Price rank (1 = most expensive)", "Yield rank (1 = highest)"]
hr = 5
for j, h in enumerate(hdr, 1):
    c = ws.cell(hr, j, h)
    c.font, c.fill, c.border = HDR_FONT, HDR_FILL, BORDER
    c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
ws.row_dimensions[hr].height = 42

first, last = hr + 1, hr + len(areas)
for i, a in enumerate(areas):
    r = first + i
    ws.cell(r, 1, a)
    ws.cell(r, 2, f'=COUNTIFS({S("D")},$A{r},{S("C")},$B$3)')
    ws.cell(r, 3, f'=IFERROR(AVERAGEIFS({S("H")},{S("D")},$A{r},{S("C")},$B$3),0)')
    ws.cell(r, 4, f'=SUMIFS({S("G")},{S("D")},$A{r},{S("C")},$B$3)/1000000')
    ws.cell(r, 5, f'=IFERROR(AVERAGEIFS({R("H")},{R("D")},$A{r},{R("C")},$B$3),0)')
    ws.cell(r, 6, f'=IF(C{r}=0,0,E{r}/C{r})')
    ws.cell(r, 7, f'=RANK(C{r},$C${first}:$C${last},0)')
    ws.cell(r, 8, f'=RANK(F{r},$F${first}:$F${last},0)')
    for j in range(1, 9):
        c = ws.cell(r, j)
        c.font, c.border = BASE, BORDER
    ws.cell(r, 2).number_format = "#,##0"
    ws.cell(r, 3).number_format = "#,##0"
    ws.cell(r, 4).number_format = "#,##0"
    ws.cell(r, 5).number_format = "#,##0"
    ws.cell(r, 6).number_format = "0.0%"

tr = last + 1
ws.cell(tr, 1, "Total / market")
ws.cell(tr, 2, f"=SUM(B{first}:B{last})")
ws.cell(tr, 3, f'=AVERAGEIFS({S("H")},{S("C")},$B$3)')
ws.cell(tr, 4, f"=SUM(D{first}:D{last})")
ws.cell(tr, 5, f'=AVERAGEIFS({R("H")},{R("C")},$B$3)')
ws.cell(tr, 6, f"=IF(C{tr}=0,0,E{tr}/C{tr})")
for j in range(1, 9):
    c = ws.cell(tr, j)
    c.font, c.border = Font(name=FONT, bold=True), BORDER
    c.fill = PatternFill("solid", fgColor="D9E1F2")
for j, fmt in zip(range(2, 7), ["#,##0", "#,##0", "#,##0", "#,##0", "0.0%"]):
    ws.cell(tr, j).number_format = fmt

ws.cell(tr + 2, 1, "Notes").font = Font(name=FONT, bold=True)
notes = [
    "Gross yield = average annual rent per sqm / average sale price per sqm (same year, area-level averages).",
    "Averages are simple means of cleaned transactions; they are affected by property mix (apartments vs villas).",
    "2026 contains Jan-Sep only. Prefer 2025 for full-year comparisons.",
    "Source: synthetic data from src/generate_sample_data.py, cleaned by src/clean_data.py.",
]
for k, t in enumerate(notes):
    ws.cell(tr + 3 + k, 1, t).font = BASE

ws.column_dimensions["A"].width = 28
for col in "BCDEFGH":
    ws.column_dimensions[col].width = 16
ws.freeze_panes = "B6"

bar = BarChart()
bar.type, bar.style = "bar", 10
bar.title = "Average price per sqm by area (selected year)"
bar.y_axis.title = "AED per sqm"
bar.add_data(Reference(ws, min_col=3, min_row=hr, max_row=last), titles_from_data=True)
bar.set_categories(Reference(ws, min_col=1, min_row=first, max_row=last))
bar.legend = None
bar.height, bar.width = 10, 18
ws.add_chart(bar, "J5")

bar2 = BarChart()
bar2.type, bar2.style = "bar", 12
bar2.title = "Gross rental yield by area (selected year)"
bar2.add_data(Reference(ws, min_col=6, min_row=hr, max_row=last), titles_from_data=True)
bar2.set_categories(Reference(ws, min_col=1, min_row=first, max_row=last))
bar2.legend = None
bar2.height, bar2.width = 10, 18
ws.add_chart(bar2, "J26")

# ------------------------------------------------------------------ Trend
wt = wb.create_sheet("Price_Trend", 1)
wt["A1"] = "Average price per sqm by area and year (AED) - formulas"
wt["A1"].font = Font(name=FONT, size=14, bold=True)
wt["A3"] = "Area"
for j, y in enumerate(years, 2):
    wt.cell(3, j, int(y))
wt.cell(3, len(years) + 2, "Growth first year to 2025")
for j in range(1, len(years) + 3):
    c = wt.cell(3, j)
    c.font, c.fill, c.border = HDR_FONT, HDR_FILL, BORDER
    c.alignment = Alignment(horizontal="center", wrap_text=True)
col2025 = 2 + years.index(2025)
for i, a in enumerate(areas):
    r = 4 + i
    wt.cell(r, 1, a)
    for j, y in enumerate(years, 2):
        L = get_column_letter(j)
        wt.cell(r, j, f'=IFERROR(AVERAGEIFS({S("H")},{S("D")},$A{r},{S("C")},{L}$3),0)')
        wt.cell(r, j).number_format = "#,##0"
    wt.cell(r, len(years) + 2, f"={get_column_letter(col2025)}{r}/B{r}-1")
    wt.cell(r, len(years) + 2).number_format = "0.0%"
    for j in range(1, len(years) + 3):
        wt.cell(r, j).font, wt.cell(r, j).border = BASE, BORDER
mr = 4 + len(areas)
wt.cell(mr, 1, "Market average")
for j, y in enumerate(years, 2):
    L = get_column_letter(j)
    wt.cell(mr, j, f'=AVERAGEIFS({S("H")},{S("C")},{L}$3)')
    wt.cell(mr, j).number_format = "#,##0"
wt.cell(mr, len(years) + 2, f"={get_column_letter(col2025)}{mr}/B{mr}-1")
wt.cell(mr, len(years) + 2).number_format = "0.0%"
yr = mr + 1
wt.cell(yr, 1, "Market YoY change")
for j in range(3, len(years) + 2):
    L, P = get_column_letter(j), get_column_letter(j - 1)
    wt.cell(yr, j, f"={L}{mr}/{P}{mr}-1")
    wt.cell(yr, j).number_format = "0.0%"
for rr in (mr, yr):
    for j in range(1, len(years) + 3):
        wt.cell(rr, j).font = Font(name=FONT, bold=True)
        wt.cell(rr, j).border = BORDER
        wt.cell(rr, j).fill = PatternFill("solid", fgColor="D9E1F2")
wt.cell(yr + 2, 1, "2026 is a partial year (Jan-Sep); growth to 2025 is computed on full years.").font = BASE
wt.column_dimensions["A"].width = 28
for j in range(2, len(years) + 3):
    wt.column_dimensions[get_column_letter(j)].width = 14
wt.freeze_panes = "B4"

line = LineChart()
line.title = "Market average price per sqm"
line.y_axis.title = "AED per sqm"
line.add_data(Reference(wt, min_col=1, max_col=len(years) + 1, min_row=mr), titles_from_data=True, from_rows=True)
line.set_categories(Reference(wt, min_col=2, max_col=len(years) + 1, min_row=3))
line.legend = None
line.height, line.width = 9, 18
wt.add_chart(line, "A" + str(yr + 5))

# ------------------------------------------------------------------ order sheets & save
wb.move_sheet("Summary", offset=-wb.index(wb["Summary"]))
out = ROOT / "excel" / "summary_pivot.xlsx"
out.parent.mkdir(exist_ok=True)
wb.save(out)
print("saved", out)
