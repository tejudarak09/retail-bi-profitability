# Retail Business Intelligence & Profitability Analysis

A retail BI project built on a **star schema**: raw sales data is cleaned and
modelled in Python + SQLite, every KPI is proven by executable SQL, and the
same model powers a Power BI report (DAX measures + a click-by-click build
guide) and an Excel KPI workbook.

**Stack:** SQL (SQLite) · Power BI / DAX · Excel (openpyxl) · Python (pandas)

---

## Headline KPIs (verified by SQL — see `outputs/kpi_summary.json`)

| KPI | Value |
|---|---|
| Total Sales | **$2,297,200.86** |
| Total Profit | **$286,397.02** |
| Profit Margin | **12.47%** |
| Orders | **5,009** |
| Order Lines | **9,994** |
| Customers | **793** |
| Products | **1,862** |
| Units Sold | **37,873** |
| Average Order Value | **$458.61** |
| Average Discount | **15.62%** |
| Date Range | **2014-01-03 → 2017-12-30** |

Currency is **USD**, exactly as in the source data — no conversion.

## Key findings (all computed from the data, not assumed)

1. **Discounts above 20% lose money — a lot of it.** Undiscounted lines earn a
   29.51% margin (+$320,987.60). The 21-30% band loses $10,369.28, the 31-50%
   band loses $48,447.73, and lines discounted over 50% lose $76,559.05 at a
   **-119.20% margin**. Combined, discounts above 20% destroy **$135,376.06**
   of profit.
2. **Furniture is the weak category.** It is #2 in sales ($741,999.80) but
   keeps only a 2.49% margin ($18,451.27 profit). Technology leads on profit
   ($145,454.95, 17.40% margin); Office Supplies is close behind on margin
   (17.04%).
3. **Tables are the single biggest problem sub-category:** $206,965.53 of
   sales produced a **-$17,725.48 loss** (-8.56% margin). Bookcases also lose
   money (-$3,472.56). At the other end, Copiers are the profit engine:
   $55,617.82 profit at a 37.20% margin.
4. **West is the best region** ($108,418.45 profit, 14.94% margin);
   **Central is the weakest** (7.92% margin despite $501,239.89 of sales).
5. **The biggest customer is not a good customer.** Sean Miller is #1 by
   sales ($25,043.05) but generated **-$1,980.74** of profit — heavy discounting
   on his orders ate the margin.
6. **The biggest loss-making product** is the Cubify CubeX 3D Printer Double
   Head Print: -$8,879.97 on $11,099.96 of sales (average discount 53%).
   The most profitable product is the Canon imageCLASS 2200 Advanced Copier:
   +$25,199.93.
7. **Sales grew over the period** despite a soft 2015: $484,247.50 (2014) →
   $470,532.51 (2015) → $609,205.60 (2016) → $733,215.26 (2017).

## Architecture

```
data/raw/superstore.csv          (Tableau Sample Superstore, 9,994 order lines)
        │
        ▼  python/prep_and_verify.py  (pandas: clean, dedupe, model)
┌─────────────────────────────────────────────────────────────┐
│ STAR SCHEMA in SQLite (retail_bi.db, DDL in sql/schema.sql) │
│   fact_sales ── dim_customer / dim_product / dim_date /     │
│                 dim_region                                  │
└─────────────────────────────────────────────────────────────┘
        │                                    │
        ▼  sql/kpi_queries.sql               ▼  data/processed/*.csv
outputs/*.csv + kpi_summary.json      Power BI Desktop (DAX measures,
(every query executed + verified)     guide in powerbi/) + Excel workbook
                                      (python/build_workbook.py)
```

## Repo structure

```
retail-bi-profitability/
├── data/
│   ├── raw/superstore.csv          # source dataset (see Data source)
│   └── processed/                  # star-schema CSVs (Power BI imports these)
│       ├── fact_sales.csv
│       ├── dim_customer.csv
│       ├── dim_product.csv
│       ├── dim_date.csv
│       └── dim_region.csv
├── sql/
│   ├── schema.sql                  # star-schema DDL
│   └── kpi_queries.sql             # 11 named KPI queries (all executed)
├── python/
│   ├── prep_and_verify.py          # cleaning -> star schema -> SQL -> outputs
│   └── build_workbook.py           # outputs -> Excel workbook
├── outputs/                        # verified query results (CSV + JSON)
├── excel/
│   └── retail_bi_kpi_workbook.xlsx # KPI summary + category/region/trend sheets
├── powerbi/
│   ├── DAX_MEASURES.md             # full DAX measure library
│   └── PBIX_BUILD_GUIDE.md         # click-by-click .pbix build guide
├── INTERVIEW_QA.md
├── RUN_ON_WINDOWS.md
└── requirements.txt
```

## How to run

```bash
pip install -r requirements.txt
python python/prep_and_verify.py   # builds retail_bi.db, processed CSVs, outputs/
python python/build_workbook.py    # builds excel/retail_bi_kpi_workbook.xlsx
```

The pipeline is deterministic and idempotent — run it twice and the outputs
are identical (verified). Then follow `powerbi/PBIX_BUILD_GUIDE.md` to build
`retail_bi_profitability.pbix` in Power BI Desktop, and `RUN_ON_WINDOWS.md`
for the full Windows walkthrough including the GitHub push steps.

## Data source

The **Tableau Sample Superstore** dataset (9,994 order lines, 2014-2017, US
retail orders) — the same file already used in my
[SQL Business Insights Portfolio](https://github.com/tejudarak09/sql-business-insights),
reused here so the SQL findings and the BI findings cross-check each other
(and they do: the >20%-discount loss of $135,376 appears in both projects,
computed independently).

## 30-second interview pitch

> "I took 9,994 raw retail order lines and modelled them into a star schema —
> a fact_sales table with customer, product, date and region dimensions — in
> SQLite. Every KPI in the report is a SQL query I can show you; the same
> model feeds Power BI, where I wrote the KPIs as DAX measures instead of
> calculated columns. The headline insight is that discounting above 20%
> flips the business from a 29.5% margin to losses totalling $135K, and the
> Furniture category — especially Tables — is where the money leaks. I also
> packaged the KPIs into an Excel workbook so the numbers exist in three
> tools, all generated from one verified pipeline."
