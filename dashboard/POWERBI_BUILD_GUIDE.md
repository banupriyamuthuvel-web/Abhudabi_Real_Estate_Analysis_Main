# Power BI Build Guide


```DAX
Create 2 tables -
DimArea = DISTINCT ( UNION ( VALUES ( sales_clean[area] ), VALUES ( rentals_clean[area] ) ) )

DimDate =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2021, 1, 1 ), DATE ( 2026, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Quarter", "Q" & QUARTER ( [Date] ),
    "YearQuarter", YEAR ( [Date] ) & "-Q" & QUARTER ( [Date] ),
    "MonthNo", MONTH ( [Date] ),
    "Month", FORMAT ( [Date], "MMM" )
)
```
**Model view relationships** (many-to-one, single direction):
   - `sales_clean[area]` -> `DimArea[area]`; `rentals_clean[area]` -> `DimArea[area]`
   - `sales_clean[transaction_date]` -> `DimDate[Date]`; `rentals_clean[start_date]` -> `DimDate[Date]`
   - Mark `DimDate` as the date table.

##  DAX measures
Create a table called `_Measures` (Enter Data, empty) and add these:

```DAX
Transactions = COUNTROWS ( sales_clean )

Total Sales Value (AED m) = DIVIDE ( SUM ( sales_clean[price_aed] ), 1000000 )

Avg Price per sqm = AVERAGE ( sales_clean[price_per_sqm] )

Median Price per sqm = MEDIAN ( sales_clean[price_per_sqm] )

Avg Rent per sqm = AVERAGE ( rentals_clean[rent_per_sqm] )

Gross Yield % = DIVIDE ( [Avg Rent per sqm], [Avg Price per sqm] )

Avg Price per sqm PY =
CALCULATE ( [Avg Price per sqm], SAMEPERIODLASTYEAR ( DimDate[Date] ) )

YoY Price Change % =
DIVIDE ( [Avg Price per sqm] - [Avg Price per sqm PY], [Avg Price per sqm PY] )

Rolling 12M Avg Price =
CALCULATE (
    [Avg Price per sqm],
    DATESINPERIOD ( DimDate[Date], MAX ( DimDate[Date] ), -12, MONTH )
)

Transactions PY =
CALCULATE ( [Transactions], SAMEPERIODLASTYEAR ( DimDate[Date] ) )

Transactions YoY % = DIVIDE ( [Transactions] - [Transactions PY], [Transactions PY] )

Market Share % =
DIVIDE ( [Transactions], CALCULATE ( [Transactions], ALL ( DimArea ) ) )

Price Rank =
RANKX ( ALL ( DimArea[area] ), [Avg Price per sqm], , DESC, Dense )

Seasonality Index =
VAR AvgMonth =
    AVERAGEX ( ALLSELECTED ( DimDate[Month] ), [Transactions] )
RETURN DIVIDE ( [Transactions], AvgMonth ) * 100
```
