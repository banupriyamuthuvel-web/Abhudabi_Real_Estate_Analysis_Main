-- =====================================================================
-- Abu Dhabi Real Estate Analysis - SQL queries
-- Dialect: SQLite (also valid in PostgreSQL with minor changes, noted inline)
-- Tables : sales(transaction_id, transaction_date, area, property_type, bedrooms,
--                size_sqm, price_aed, sale_type, price_per_sqm, year, quarter, month,
--                year_quarter, property_group)
--          rentals(contract_id, start_date, area, property_type, size_sqm,
--                  annual_rent_aed, rent_per_sqm, year)
-- Each query is separated by a "-- Q<number>" header so src/run_sql.py can run them.
-- =====================================================================


-- Q1. Which areas are the most and least expensive? (average and median-style spread)
-- Skills: GROUP BY, aggregates, ROUND
SELECT area,
       COUNT(*)                         AS transactions,
       ROUND(AVG(price_per_sqm), 0)     AS avg_price_per_sqm,
       ROUND(MIN(price_per_sqm), 0)     AS min_price_per_sqm,
       ROUND(MAX(price_per_sqm), 0)     AS max_price_per_sqm
FROM sales
GROUP BY area
ORDER BY avg_price_per_sqm DESC;


-- Q2. Year-over-year change in average price per sqm (market-wide)
-- Skills: CTE, LAG window function
-- NOTE: 2026 is a partial year (Jan-Sep), so compare averages, not totals.
WITH yearly AS (
    SELECT year, ROUND(AVG(price_per_sqm), 0) AS avg_ppsqm, COUNT(*) AS transactions
    FROM sales
    GROUP BY year
)
SELECT year,
       avg_ppsqm,
       transactions,
       ROUND(100.0 * (avg_ppsqm - LAG(avg_ppsqm) OVER (ORDER BY year))
             / LAG(avg_ppsqm) OVER (ORDER BY year), 1) AS yoy_price_change_pct
FROM yearly
ORDER BY year;


-- Q3. Year-over-year price growth by area, ranked within each year
-- Skills: CTE, LAG with PARTITION BY, RANK
WITH area_year AS (
    SELECT area, year, AVG(price_per_sqm) AS avg_ppsqm
    FROM sales
    GROUP BY area, year
),
growth AS (
    SELECT area, year, avg_ppsqm,
           100.0 * (avg_ppsqm - LAG(avg_ppsqm) OVER (PARTITION BY area ORDER BY year))
                 / LAG(avg_ppsqm) OVER (PARTITION BY area ORDER BY year) AS yoy_pct
    FROM area_year
)
SELECT year, area, ROUND(yoy_pct, 1) AS yoy_pct,
       RANK() OVER (PARTITION BY year ORDER BY yoy_pct DESC) AS growth_rank
FROM growth
WHERE yoy_pct IS NOT NULL AND year = 2025
ORDER BY growth_rank;


-- Q4. Top 5 areas by transaction volume in the latest full year (2025)
-- Skills: filtering, ORDER BY, LIMIT, share of total via subquery
SELECT area,
       COUNT(*) AS transactions,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM sales WHERE year = 2025), 1) AS pct_of_market,
       ROUND(SUM(price_aed) / 1e6, 0) AS total_value_aed_m
FROM sales
WHERE year = 2025
GROUP BY area
ORDER BY transactions DESC
LIMIT 5;


-- Q5. Which transactions were priced well below their area average? (possible bargains)
-- Skills: CTE, JOIN to a derived table, comparison against group average
WITH area_avg AS (
    SELECT area, year, AVG(price_per_sqm) AS avg_ppsqm
    FROM sales GROUP BY area, year
)
SELECT s.transaction_id, s.transaction_date, s.area, s.property_type,
       s.size_sqm, s.price_aed, s.price_per_sqm,
       ROUND(100.0 * (s.price_per_sqm - a.avg_ppsqm) / a.avg_ppsqm, 1) AS pct_vs_area_avg
FROM sales s
JOIN area_avg a ON a.area = s.area AND a.year = s.year
WHERE s.year = 2025
  AND s.price_per_sqm < 0.7 * a.avg_ppsqm
ORDER BY pct_vs_area_avg ASC
LIMIT 20;


-- Q6. Seasonality: transactions by calendar month (full years 2022-2025 only)
-- Skills: GROUP BY month, index vs average month
WITH monthly AS (
    SELECT month, COUNT(*) AS transactions
    FROM sales
    WHERE year BETWEEN 2022 AND 2025
    GROUP BY month
)
SELECT month,
       transactions,
       ROUND(100.0 * transactions / (SELECT AVG(transactions) FROM monthly), 0) AS seasonality_index
FROM monthly
ORDER BY month;


-- Q7. Off-plan vs ready: price premium by property type
-- Skills: conditional aggregation (CASE WHEN)
SELECT property_type,
       ROUND(AVG(CASE WHEN sale_type = 'Off-Plan' THEN price_per_sqm END), 0) AS offplan_avg_ppsqm,
       ROUND(AVG(CASE WHEN sale_type = 'Ready'    THEN price_per_sqm END), 0) AS ready_avg_ppsqm,
       ROUND(100.0 * (AVG(CASE WHEN sale_type = 'Off-Plan' THEN price_per_sqm END)
                    / AVG(CASE WHEN sale_type = 'Ready'    THEN price_per_sqm END) - 1), 1) AS offplan_premium_pct
FROM sales
WHERE year = 2025
GROUP BY property_type;


-- Q8. Gross rental yield by area (2025): annual rent / purchase price
-- Skills: two CTEs, JOIN across tables, derived KPI
WITH price AS (
    SELECT area, property_type, AVG(price_per_sqm) AS avg_price_sqm
    FROM sales WHERE year = 2025 GROUP BY area, property_type
),
rent AS (
    SELECT area, property_type, AVG(rent_per_sqm) AS avg_rent_sqm
    FROM rentals WHERE year = 2025 GROUP BY area, property_type
)
SELECT p.area,
       ROUND(AVG(100.0 * r.avg_rent_sqm / p.avg_price_sqm), 2) AS gross_yield_pct
FROM price p
JOIN rent r ON r.area = p.area AND r.property_type = p.property_type
GROUP BY p.area
ORDER BY gross_yield_pct DESC;


-- Q9. Value score: combine yield and 2021-2025 price growth into one ranking
-- Skills: multi-CTE pipeline, window function (RANK) over a composite metric
WITH growth AS (
    SELECT area,
           100.0 * (AVG(CASE WHEN year = 2025 THEN price_per_sqm END)
                  / AVG(CASE WHEN year = 2021 THEN price_per_sqm END) - 1) AS growth_pct_21_25
    FROM sales GROUP BY area
),
price25 AS (
    SELECT area, property_type, AVG(price_per_sqm) AS p FROM sales WHERE year = 2025 GROUP BY area, property_type
),
rent25 AS (
    SELECT area, property_type, AVG(rent_per_sqm) AS r FROM rentals WHERE year = 2025 GROUP BY area, property_type
),
yield25 AS (
    SELECT p.area, AVG(100.0 * r.r / p.p) AS yield_pct
    FROM price25 p JOIN rent25 r ON r.area = p.area AND r.property_type = p.property_type
    GROUP BY p.area
)
SELECT g.area,
       ROUND(y.yield_pct, 2)        AS gross_yield_pct,
       ROUND(g.growth_pct_21_25, 1) AS price_growth_pct_21_25,
       ROUND(y.yield_pct + g.growth_pct_21_25 / 4.0, 2) AS annual_total_return_proxy,
       RANK() OVER (ORDER BY y.yield_pct + g.growth_pct_21_25 / 4.0 DESC) AS value_rank
FROM growth g JOIN yield25 y ON y.area = g.area
ORDER BY value_rank;


-- Q10. Rolling 4-quarter average price per sqm (market-wide) to smooth noise
-- Skills: window frame (ROWS BETWEEN), quarterly aggregation
WITH q AS (
    SELECT year_quarter, ROUND(AVG(price_per_sqm), 0) AS avg_ppsqm
    FROM sales GROUP BY year_quarter
)
SELECT year_quarter,
       avg_ppsqm,
       ROUND(AVG(avg_ppsqm) OVER (ORDER BY year_quarter ROWS BETWEEN 3 PRECEDING AND CURRENT ROW), 0) AS rolling_4q_avg
FROM q
ORDER BY year_quarter;
