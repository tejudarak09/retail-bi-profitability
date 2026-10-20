-- ============================================================================
-- Retail BI & Profitability Analysis - KPI Queries (SQLite dialect)
--
-- Every query in this file is executed by python/prep_and_verify.py against
-- retail_bi.db and its result is written to outputs/<query_name>.csv.
-- A query only counts as "in the project" if it runs here - no decorative SQL.
--
-- Convention: each query starts with a marker line:  -- @query: <name>
-- ============================================================================

-- @query: headline_kpis
-- The numbers that go on page 1 of the Power BI report and in the README.
SELECT
    ROUND(SUM(f.sales), 2)                                   AS total_sales,
    ROUND(SUM(f.profit), 2)                                  AS total_profit,
    ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2)           AS profit_margin_pct,
    COUNT(DISTINCT f.order_id)                               AS order_count,
    COUNT(*)                                                 AS order_lines,
    COUNT(DISTINCT f.customer_key)                           AS customer_count,
    COUNT(DISTINCT f.product_key)                            AS product_count,
    SUM(f.quantity)                                          AS units_sold,
    ROUND(SUM(f.sales) / COUNT(DISTINCT f.order_id), 2)      AS avg_order_value,
    ROUND(AVG(f.discount), 4)                                AS avg_discount,
    MIN(d.full_date)                                         AS first_order_date,
    MAX(d.full_date)                                         AS last_order_date
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.order_date_key;

-- @query: sales_by_category
SELECT
    p.category,
    COUNT(*)                                       AS order_lines,
    ROUND(SUM(f.sales), 2)                         AS total_sales,
    ROUND(SUM(f.profit), 2)                        AS total_profit,
    ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS profit_margin_pct
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.category
ORDER BY total_sales DESC;

-- @query: sales_by_subcategory
SELECT
    p.category,
    p.sub_category,
    COUNT(*)                                       AS order_lines,
    ROUND(SUM(f.sales), 2)                         AS total_sales,
    ROUND(SUM(f.profit), 2)                        AS total_profit,
    ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS profit_margin_pct
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.category, p.sub_category
ORDER BY total_profit DESC;

-- @query: discount_band_profit
-- The core profitability story: margin collapses as the discount band rises.
SELECT
    CASE
        WHEN f.discount = 0        THEN '0% (no discount)'
        WHEN f.discount <= 0.10    THEN '1-10%'
        WHEN f.discount <= 0.20    THEN '11-20%'
        WHEN f.discount <= 0.30    THEN '21-30%'
        WHEN f.discount <= 0.50    THEN '31-50%'
        ELSE 'Over 50%'
    END                                            AS discount_band,
    COUNT(*)                                       AS order_lines,
    ROUND(SUM(f.sales), 2)                         AS total_sales,
    ROUND(SUM(f.profit), 2)                        AS total_profit,
    ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS profit_margin_pct,
    ROUND(AVG(f.discount), 4)                      AS avg_discount
FROM fact_sales f
GROUP BY discount_band
ORDER BY MIN(f.discount);

-- @query: region_profitability
SELECT
    r.region,
    COUNT(DISTINCT f.order_id)                     AS orders,
    COUNT(*)                                       AS order_lines,
    ROUND(SUM(f.sales), 2)                         AS total_sales,
    ROUND(SUM(f.profit), 2)                        AS total_profit,
    ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS profit_margin_pct
FROM fact_sales f
JOIN dim_region r ON r.region_key = f.region_key
GROUP BY r.region
ORDER BY total_profit DESC;

-- @query: monthly_trend
SELECT
    d.year_month,
    d.year,
    d.month,
    COUNT(DISTINCT f.order_id)                     AS orders,
    ROUND(SUM(f.sales), 2)                         AS total_sales,
    ROUND(SUM(f.profit), 2)                        AS total_profit,
    ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS profit_margin_pct
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.order_date_key
GROUP BY d.year_month, d.year, d.month
ORDER BY d.year, d.month;

-- @query: yearly_summary
SELECT
    d.year,
    COUNT(DISTINCT f.order_id)                     AS orders,
    ROUND(SUM(f.sales), 2)                         AS total_sales,
    ROUND(SUM(f.profit), 2)                        AS total_profit,
    ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS profit_margin_pct
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.order_date_key
GROUP BY d.year
ORDER BY d.year;

-- @query: top_products_by_profit
SELECT
    p.product_name,
    p.category,
    p.sub_category,
    SUM(f.quantity)                                AS units_sold,
    ROUND(SUM(f.sales), 2)                         AS total_sales,
    ROUND(SUM(f.profit), 2)                        AS total_profit,
    ROUND(AVG(f.discount), 4)                      AS avg_discount
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.product_name, p.category, p.sub_category
ORDER BY total_profit DESC
LIMIT 10;

-- @query: bottom_products_by_profit
SELECT
    p.product_name,
    p.category,
    p.sub_category,
    SUM(f.quantity)                                AS units_sold,
    ROUND(SUM(f.sales), 2)                         AS total_sales,
    ROUND(SUM(f.profit), 2)                        AS total_profit,
    ROUND(AVG(f.discount), 4)                      AS avg_discount
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.product_name, p.category, p.sub_category
HAVING SUM(f.profit) < 0
ORDER BY total_profit ASC
LIMIT 10;

-- @query: top_customers
SELECT
    c.customer_name,
    c.segment,
    COUNT(DISTINCT f.order_id)                     AS orders,
    ROUND(SUM(f.sales), 2)                         AS total_sales,
    ROUND(SUM(f.profit), 2)                        AS total_profit,
    ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS profit_margin_pct
FROM fact_sales f
JOIN dim_customer c ON c.customer_key = f.customer_key
GROUP BY c.customer_name, c.segment
ORDER BY total_sales DESC
LIMIT 10;

-- @query: segment_profitability
SELECT
    c.segment,
    COUNT(DISTINCT f.customer_key)                 AS customers,
    COUNT(DISTINCT f.order_id)                     AS orders,
    ROUND(SUM(f.sales), 2)                         AS total_sales,
    ROUND(SUM(f.profit), 2)                        AS total_profit,
    ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS profit_margin_pct
FROM fact_sales f
JOIN dim_customer c ON c.customer_key = f.customer_key
GROUP BY c.segment
ORDER BY total_sales DESC;
