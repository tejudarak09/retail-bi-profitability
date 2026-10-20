-- ============================================================================
-- Retail BI & Profitability Analysis - Star Schema DDL (SQLite)
-- Database file: retail_bi.db  (created by python/prep_and_verify.py)
--
-- Design: one fact table (fact_sales) at the order-line grain, surrounded by
-- conformed dimensions for customer, product, date and region. Surrogate
-- integer keys keep joins fast and stable even if source IDs change.
-- ============================================================================

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_region;

-- ----------------------------------------------------------------------------
-- Dimension: Customer (one row per Customer ID in the source)
-- ----------------------------------------------------------------------------
CREATE TABLE dim_customer (
    customer_key  INTEGER PRIMARY KEY,
    customer_id   TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    segment       TEXT NOT NULL
);

-- ----------------------------------------------------------------------------
-- Dimension: Product (one row per Product ID; Category/Sub-Category roll up
-- from here, which is what the Power BI hierarchy uses)
-- ----------------------------------------------------------------------------
CREATE TABLE dim_product (
    product_key   INTEGER PRIMARY KEY,
    product_id    TEXT NOT NULL UNIQUE,
    product_name  TEXT NOT NULL,
    category      TEXT NOT NULL,
    sub_category  TEXT NOT NULL
);

-- ----------------------------------------------------------------------------
-- Dimension: Date (one row per calendar date in the fact range; enables
-- time-intelligence in DAX: YoY, rolling totals, monthly trend)
-- ----------------------------------------------------------------------------
CREATE TABLE dim_date (
    date_key    INTEGER PRIMARY KEY,          -- YYYYMMDD, e.g. 20161108
    full_date   TEXT NOT NULL,                -- ISO date, e.g. 2016-11-08
    year        INTEGER NOT NULL,
    quarter     INTEGER NOT NULL,             -- 1..4
    month       INTEGER NOT NULL,             -- 1..12
    month_name  TEXT NOT NULL,                -- January..December
    year_month  TEXT NOT NULL                 -- 2016-11 (sortable label)
);

-- ----------------------------------------------------------------------------
-- Dimension: Region / Geography (one row per distinct shipping location
-- combination: country + region + state + city + postal code)
-- ----------------------------------------------------------------------------
CREATE TABLE dim_region (
    region_key  INTEGER PRIMARY KEY,
    country     TEXT NOT NULL,
    region      TEXT NOT NULL,
    state       TEXT NOT NULL,
    city        TEXT NOT NULL,
    postal_code TEXT
);

-- ----------------------------------------------------------------------------
-- Fact: Sales (grain = one row per order line in the source file)
-- Measures: sales, profit, quantity, discount
-- ----------------------------------------------------------------------------
CREATE TABLE fact_sales (
    row_id         INTEGER PRIMARY KEY,       -- source Row ID
    order_id       TEXT NOT NULL,
    order_date_key INTEGER NOT NULL REFERENCES dim_date (date_key),
    ship_date_key  INTEGER NOT NULL REFERENCES dim_date (date_key),
    customer_key   INTEGER NOT NULL REFERENCES dim_customer (customer_key),
    product_key    INTEGER NOT NULL REFERENCES dim_product (product_key),
    region_key     INTEGER NOT NULL REFERENCES dim_region (region_key),
    ship_mode      TEXT NOT NULL,
    sales          REAL NOT NULL,
    quantity       INTEGER NOT NULL,
    discount       REAL NOT NULL,
    profit         REAL NOT NULL
);

CREATE INDEX idx_fact_customer ON fact_sales (customer_key);
CREATE INDEX idx_fact_product  ON fact_sales (product_key);
CREATE INDEX idx_fact_region   ON fact_sales (region_key);
CREATE INDEX idx_fact_order_dt ON fact_sales (order_date_key);
