# Interview Q&A — Retail BI & Profitability Analysis

Sample answers grounded in this project's actual build and numbers.
Dataset: Tableau Sample Superstore — 9,994 order lines, $2,297,200.86 sales,
$286,397.02 profit, 12.47% margin, 2014-2017.

---

**Q1. Walk me through this project in one minute.**
I took a flat retail orders file and turned it into a BI system. Python cleans
the data and builds a star schema in SQLite — one fact table at the order-line
grain with customer, product, date and region dimensions. Every KPI is a SQL
query stored in the repo and executed by the pipeline, so the numbers are
provable. The same star schema is imported into Power BI, where KPIs are DAX
measures, and into an Excel workbook generated from the verified outputs.
Headline finding: discounts above 20% turn a 29.5% margin into $135,376 of
losses.

**Q2. Why a star schema instead of one flat table?**
Three reasons: query simplicity (business users drag dimension attributes
instead of writing joins against a 21-column flat file), performance (narrow
fact table, small dimensions, single-direction filters), and correctness —
measures like profit margin are defined once and every visual inherits them.
The grain is declared once: one fact row per order line, and every dimension
conforms to it.

**Q3. What's the grain of your fact table, and why does it matter?**
One row per order line (9,994 rows), not per order (5,009 orders). If you get
the grain wrong, every aggregate is wrong: for example, Order Count must be
`DISTINCTCOUNT(order_id)` — a COUNTROWS would report 9,994 "orders", almost
double the truth.

**Q4. Measures vs calculated columns in DAX — which did you use and why?**
Measures, almost everywhere. A calculated column is stored row-by-row and
evaluated at refresh; a measure is evaluated at query time in the current
filter context and stores nothing. KPIs like Total Profit or Margin % must
respond to slicers, so they are measures. I used exactly one calculated
column — Discount Band — because it is a row-level category I want to use as
an axis/slicer, which is the legitimate use case for a column.

**Q5. How is Profit Margin % defined, and how did you avoid divide-by-zero?**
Margin = Total Profit / Total Sales × 100, written with `DIVIDE()` so a
filter combination with zero sales returns blank instead of an error. Overall
margin is 12.47%, but it swings from +29.51% on undiscounted lines to
-119.20% on lines discounted over 50%.

**Q6. What is the discount-profitability story in this data?**
Discounting works until 20%, then it doesn't. The 11-20% band is still
profitable (+$91,756.30, 11.58% margin). Above 20% every band loses money:
21-30% loses $10,369.28, 31-50% loses $48,447.73, over-50% loses $76,559.05 —
$135,376.06 lost in total. My recommendation: cap routine discounts at 20%
and require approval above that.

**Q7. Which category would you investigate first, and why?**
Furniture. It is the #2 category by sales ($741,999.80) but converts at only
a 2.49% margin ($18,451.27 profit), while Technology makes $145,454.95 at
17.40%. Inside Furniture, Tables lose $17,725.48 on $206,965.53 of sales and
Bookcases lose $3,472.56 — both heavily discounted sub-categories, so the
fix is pricing/discount policy, not more marketing.

**Q8. How did you do year-over-year growth in DAX?**
I marked dim_date as the date table, then `Sales PY = CALCULATE([Total
Sales], SAMEPERIODLASTYEAR(dim_date[full_date]))` and YoY % = (Sales − PY) /
PY. The data supports it — four full years, 2014-2017. Sales dipped in 2015
($470,532.51 vs $484,247.50) then grew to $609,205.60 and $733,215.26.

**Q9. Your top customer by sales — is he your best customer?**
No, and that's one of my favourite findings. Sean Miller is #1 by sales at
$25,043.05 but his orders lost $1,980.74. Ranking customers by profit instead
of sales changes the conversation completely — Tamara Chand spent less
($19,052.22) but generated $8,981.32 of profit at a 47.14% margin.

**Q10. How do drill-through and drill-down work in your report?**
Drill-down is inside one visual: the matrix goes Category → Sub-Category.
Drill-through jumps to a dedicated Product Detail page filtered to the
sub-category you right-clicked — the page carries a drill-through filter on
sub_category, so from the profitability bar chart you can jump straight to
the product list behind Tables' -$17,725.48.

**Q11. How do you know the Power BI numbers are right?**
They're reconciled against SQL. The pipeline executes every KPI query in
sql/kpi_queries.sql against the same star schema and writes CSVs + a JSON
summary. I built the report so that with all slicers cleared, every card
must equal the SQL output exactly ($2,297,200.86 sales, $286,397.02 profit).
The Excel workbook is a third surface generated from the same outputs.

**Q12. Why keep ship_date_key if there's no relationship on it?**
Because order date and ship date are two different business questions
(demand vs fulfilment). I kept the key in the fact so the model can grow —
the clean options are a second role-playing dim_date or activating the
relationship with USERELATIONSHIP in specific measures. I left it inactive
deliberately rather than having two active paths, which creates ambiguous
filter propagation.

**Q13. What data-quality issues did you find in the raw file?**
Three: the file is latin-1 encoded, so a naive UTF-8 read crashes; a few
Product IDs appear under slightly different product names, so the product
dimension must dedupe on Product ID deterministically or the unique key
breaks; and "Postal Code" needs care because it is location data, not a
measure. The cleaning step also asserts the grain: Row ID must be unique and
dates must parse 100%.

**Q14. AOV is $458.61 — how is it calculated and why not just average the
Sales column?**
AOV = Total Sales / distinct Order Count (5,009 orders). Averaging the
Sales column averages over 9,994 order *lines*, which answers a different
question (average line value, ~$229.86). Confusing lines with orders is the
most common beginner mistake with this dataset.

**Q15. If you had one more week, what would you add?**
Two things: a discount-approval simulation — a what-if parameter in Power
BI that caps discounts at 20% and shows recovered profit (roughly the
$135K) — and row-level security by region so a West region manager only
sees West data. Both build directly on the existing star schema.
