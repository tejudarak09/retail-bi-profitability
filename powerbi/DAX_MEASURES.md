# DAX Measure Library — Retail BI & Profitability Analysis

Create a dedicated **measure table** in Power BI (Home → Enter data → name it `_Measures`,
one dummy column) and add every measure below to it. Measures are used instead of
calculated columns on purpose: they are evaluated in filter context, cost no storage,
and keep the fact table lean.

All measures assume the star schema from this repo:
`fact_sales` related to `dim_customer`, `dim_product`, `dim_date`, `dim_region`.

---

## Core KPIs

### Total Sales
```dax
Total Sales = SUM ( fact_sales[sales] )
```
Sum of the Sales column over whatever the user has filtered (category, region, month…).

### Total Profit
```dax
Total Profit = SUM ( fact_sales[profit] )
```
Same idea for Profit — the second headline number of the report.

### Profit Margin %
```dax
Profit Margin % =
DIVIDE ( [Total Profit], [Total Sales] ) * 100
```
DIVIDE is used instead of `/` so a filter combination with zero sales returns BLANK
instead of an error. Format as a number with 2 decimals (values are already ×100).

### Order Count
```dax
Order Count = DISTINCTCOUNT ( fact_sales[order_id] )
```
Counts orders, not order lines — the fact grain is one row per order line, so a plain
COUNTROWS would overstate orders (9,994 lines vs 5,009 real orders in this dataset).

### Order Lines
```dax
Order Lines = COUNTROWS ( fact_sales )
```
The raw grain count; useful on the data-quality / audit page.

### Units Sold
```dax
Units Sold = SUM ( fact_sales[quantity] )
```

### AOV (Average Order Value)
```dax
AOV = DIVIDE ( [Total Sales], [Order Count] )
```
Sales per distinct order — $458.61 across the full dataset.

### Avg Discount
```dax
Avg Discount = AVERAGE ( fact_sales[discount] )
```
Mean discount per order line (15.62% overall). Format as Percentage.

### Avg Profit per Order
```dax
Avg Profit per Order = DIVIDE ( [Total Profit], [Order Count] )
```

---

## Time Intelligence (uses dim_date)

> For these to work, mark `dim_date` as the date table in Power BI
> (right-click the table → "Mark as date table" → `full_date`), and make sure
> `dim_date[full_date]` is related to `fact_sales[order_date_key]` via a real
> date column — see the build guide for the exact relationship setup.

### Sales YTD
```dax
Sales YTD = TOTALYTD ( [Total Sales], dim_date[full_date] )
```

### Sales PY (Prior Year)
```dax
Sales PY =
CALCULATE ( [Total Sales], SAMEPERIODLASTYEAR ( dim_date[full_date] ) )
```

### YoY Sales Growth %
```dax
YoY Sales Growth % =
DIVIDE ( [Total Sales] - [Sales PY], [Sales PY] ) * 100
```
The dataset spans 2014-2017, so YoY is meaningful: sales went
$484,248 (2014) → $470,533 (2015) → $609,206 (2016) → $733,215 (2017).

### Sales Rolling 3M
```dax
Sales Rolling 3M =
CALCULATE (
    [Total Sales],
    DATESINPERIOD ( dim_date[full_date], MAX ( dim_date[full_date] ), -3, MONTH )
)
```
Smooths the monthly trend line on the Executive Overview page.

---

## Profitability Analysis

### Top Category Profit
```dax
Top Category Profit =
MAXX ( VALUES ( dim_product[category] ), [Total Profit] )
```
Returns the profit of the single best category in context
(Technology, $145,454.95 on the full dataset). Pair with:

### Top Category Name
```dax
Top Category Name =
VAR Ranked =
    ADDCOLUMNS (
        VALUES ( dim_product[category] ),
        "@p", [Total Profit]
    )
RETURN
    MAXX ( TOPN ( 1, Ranked, [@p] ), dim_product[category] )
```
Lets a card visual show "Technology" next to its profit without hardcoding.

### Loss-Making Sales
```dax
Loss-Making Sales =
CALCULATE ( [Total Sales], FILTER ( fact_sales, fact_sales[profit] < 0 ) )
```
Sales value sitting in order lines that lost money — the discount problem in one number.

### Loss-Making Lines %
```dax
Loss-Making Lines % =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_sales ), fact_sales[profit] < 0 ),
    [Order Lines]
) * 100
```

### Profit at No Discount
```dax
Profit at No Discount =
CALCULATE ( [Total Profit], fact_sales[discount] = 0 )
```
$320,987.60 across 4,798 undiscounted lines (29.51% margin) — the benchmark that
makes the discount-band chart on page 3 hit home.

### Deep-Discount Profit (over 20%)
```dax
Deep-Discount Profit =
CALCULATE ( [Total Profit], fact_sales[discount] > 0.20 )
```
Negative on this dataset: discounts above 20% destroy $135,376.06 of profit in total.

### High-Value Customer Sales (>$10k lifetime)
```dax
High-Value Customer Sales =
SUMX (
    FILTER (
        VALUES ( dim_customer[customer_name] ),
        CALCULATE ( [Total Sales] ) > 10000
    ),
    [Total Sales]
)
```
Iterates customers, keeps only those above the threshold, then sums their sales —
a classic SUMX + FILTER pattern for interviews.

---

## Formatting notes
- Currency measures (Total Sales, Total Profit, AOV): format `$#,##0` — the source
  data is USD and is deliberately **not** converted.
- Margin and growth measures: 2-decimal numbers with a "%" suffix in the visual,
  because the measures already multiply by 100.
- Avg Discount: Percentage format (the raw value is a 0-1 fraction).
