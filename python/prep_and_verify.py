"""
prep_and_verify.py - Retail BI & Profitability Analysis pipeline.

What it does (deterministic + idempotent: safe to run any number of times,
the outputs are byte-identical on every run):

  1. Loads the raw Tableau Sample Superstore CSV (data/raw/superstore.csv).
  2. Cleans it: parses order/ship dates, drops exact duplicate rows,
     enforces the source row grain (one row per Row ID).
  3. Builds a star schema - fact_sales + dim_customer, dim_product,
     dim_date, dim_region - and loads it into SQLite (retail_bi.db)
     using the DDL in sql/schema.sql.
  4. Exports the star-schema tables as CSVs to data/processed/
     (these are the files Power BI Desktop imports).
  5. Executes EVERY query in sql/kpi_queries.sql against the SQLite DB
     and writes each result set to outputs/<query_name>.csv.
  6. Writes the headline KPIs + key findings to outputs/kpi_summary.json.

Run:  python python/prep_and_verify.py
"""

import json
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = ROOT / "data" / "raw" / "superstore.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUTS_DIR = ROOT / "outputs"
DB_PATH = ROOT / "retail_bi.db"
SCHEMA_SQL = ROOT / "sql" / "schema.sql"
KPI_SQL = ROOT / "sql" / "kpi_queries.sql"


# --------------------------------------------------------------------------
# 1-2. Load + clean
# --------------------------------------------------------------------------
def load_and_clean() -> pd.DataFrame:
    # Source file is latin-1 encoded (Tableau Sample Superstore export)
    df = pd.read_csv(RAW_CSV, encoding="latin-1")
    raw_rows = len(df)

    # Parse dates explicitly (source format is M/D/YYYY)
    df["Order Date"] = pd.to_datetime(df["Order Date"], format="%m/%d/%Y")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], format="%m/%d/%Y")

    # No exact duplicates
    df = df.drop_duplicates()

    # The grain is one row per Row ID - enforce it
    assert df["Row ID"].is_unique, "Row ID is not unique after cleaning"
    assert df["Order Date"].notna().all() and df["Ship Date"].notna().all()

    print(f"[clean] raw rows: {raw_rows} -> cleaned rows: {len(df)}")
    return df.sort_values("Row ID").reset_index(drop=True)


# --------------------------------------------------------------------------
# 3. Star schema
# --------------------------------------------------------------------------
def build_star_schema(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    # --- dim_customer: one row per Customer ID ---
    # (the source repeats a customer ID with identical attributes; sort first
    #  so the surviving row is deterministic)
    dim_customer = (
        df[["Customer ID", "Customer Name", "Segment"]]
        .drop_duplicates()
        .sort_values(["Customer ID", "Customer Name", "Segment"])
        .drop_duplicates(subset="Customer ID", keep="first")
        .reset_index(drop=True)
    )
    dim_customer.insert(0, "customer_key", range(1, len(dim_customer) + 1))
    dim_customer.columns = ["customer_key", "customer_id", "customer_name", "segment"]

    # --- dim_product: one row per Product ID ---
    # NOTE: the raw Superstore file lists a few Product IDs under slightly
    # different product names. The dimension keeps the first name variant
    # (sorted, so deterministic) per Product ID - the ID is the grain.
    dim_product = (
        df[["Product ID", "Product Name", "Category", "Sub-Category"]]
        .drop_duplicates()
        .sort_values(["Product ID", "Product Name"])
        .drop_duplicates(subset="Product ID", keep="first")
        .reset_index(drop=True)
    )
    dim_product.insert(0, "product_key", range(1, len(dim_product) + 1))
    dim_product.columns = [
        "product_key", "product_id", "product_name", "category", "sub_category",
    ]

    # --- dim_region: one row per distinct shipping location ---
    dim_region = (
        df[["Country", "Region", "State", "City", "Postal Code"]]
        .drop_duplicates()
        .sort_values(["Region", "State", "City", "Postal Code"])
        .reset_index(drop=True)
    )
    dim_region.insert(0, "region_key", range(1, len(dim_region) + 1))
    dim_region.columns = ["region_key", "country", "region", "state", "city", "postal_code"]
    dim_region["postal_code"] = dim_region["postal_code"].astype("Int64").astype(str)

    # --- dim_date: every date that appears as an order or ship date ---
    all_dates = pd.Series(
        pd.concat([df["Order Date"], df["Ship Date"]]).unique()
    ).sort_values()
    dim_date = pd.DataFrame({"full_date_dt": all_dates})
    dim_date["date_key"] = dim_date["full_date_dt"].dt.strftime("%Y%m%d").astype(int)
    dim_date["full_date"] = dim_date["full_date_dt"].dt.strftime("%Y-%m-%d")
    dim_date["year"] = dim_date["full_date_dt"].dt.year
    dim_date["quarter"] = dim_date["full_date_dt"].dt.quarter
    dim_date["month"] = dim_date["full_date_dt"].dt.month
    dim_date["month_name"] = dim_date["full_date_dt"].dt.strftime("%B")
    dim_date["year_month"] = dim_date["full_date_dt"].dt.strftime("%Y-%m")
    dim_date = dim_date[
        ["date_key", "full_date", "year", "quarter", "month", "month_name", "year_month"]
    ].reset_index(drop=True)

    # --- fact_sales at the order-line grain ---
    cust_map = dict(zip(dim_customer["customer_id"], dim_customer["customer_key"]))
    prod_map = dict(zip(dim_product["product_id"], dim_product["product_key"]))
    region_map = {
        (r.country, r.region, r.state, r.city, str(r.postal_code)): r.region_key
        for r in dim_region.itertuples()
    }

    fact = pd.DataFrame(
        {
            "row_id": df["Row ID"].astype(int),
            "order_id": df["Order ID"],
            "order_date_key": df["Order Date"].dt.strftime("%Y%m%d").astype(int),
            "ship_date_key": df["Ship Date"].dt.strftime("%Y%m%d").astype(int),
            "customer_key": df["Customer ID"].map(cust_map).astype(int),
            "product_key": df["Product ID"].map(prod_map).astype(int),
            "region_key": [
                region_map[(c, r, s, ci, str(int(p)))]
                for c, r, s, ci, p in zip(
                    df["Country"], df["Region"], df["State"], df["City"], df["Postal Code"]
                )
            ],
            "ship_mode": df["Ship Mode"],
            "sales": df["Sales"].round(4),
            "quantity": df["Quantity"].astype(int),
            "discount": df["Discount"].round(4),
            "profit": df["Profit"].round(4),
        }
    )
    assert len(fact) == len(df), "fact row count must equal cleaned source rows"

    return {
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_date": dim_date,
        "dim_region": dim_region,
        "fact_sales": fact,
    }


def load_to_sqlite(tables: dict[str, pd.DataFrame]) -> sqlite3.Connection:
    if DB_PATH.exists():
        DB_PATH.unlink()  # rebuild from scratch -> idempotent
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_SQL.read_text())
    for name in ["dim_customer", "dim_product", "dim_date", "dim_region", "fact_sales"]:
        tables[name].to_sql(name, conn, if_exists="append", index=False)
    conn.commit()
    counts = {
        name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        for name in tables
    }
    print(f"[load] sqlite row counts: {counts}")
    return conn


def export_processed(tables: dict[str, pd.DataFrame]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)
    print(f"[export] star-schema CSVs written to {PROCESSED_DIR}")


# --------------------------------------------------------------------------
# 5-6. Run the KPI queries (parsed from the .sql file - the SQL is the spec)
# --------------------------------------------------------------------------
def parse_queries(sql_text: str) -> list[tuple[str, str]]:
    parts = re.split(r"--\s*@query:\s*(\w+)", sql_text)
    # parts = [preamble, name1, body1, name2, body2, ...]
    queries = []
    for i in range(1, len(parts), 2):
        name, body = parts[i], parts[i + 1]
        # strip comment lines, keep only the SQL statement
        lines = [ln for ln in body.splitlines() if not ln.strip().startswith("--")]
        sql = "\n".join(lines).strip().rstrip(";")
        if sql:
            queries.append((name, sql))
    return queries


def run_queries(conn: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, sql in parse_queries(KPI_SQL.read_text()):
        result = pd.read_sql_query(sql, conn)
        result.to_csv(OUTPUTS_DIR / f"{name}.csv", index=False)
        results[name] = result
        print(f"[query] {name}: {len(result)} rows")
    return results


def write_summary(results: dict[str, pd.DataFrame]) -> dict:
    h = results["headline_kpis"].iloc[0]
    cat = results["sales_by_category"]
    sub = results["sales_by_subcategory"]
    reg = results["region_profitability"]
    bands = results["discount_band_profit"]
    top_prod = results["top_products_by_profit"].iloc[0]
    worst_prod = results["bottom_products_by_profit"].iloc[0]
    top_cust = results["top_customers"].iloc[0]
    years = results["yearly_summary"]

    def band_row(label):
        row = bands[bands["discount_band"] == label].iloc[0]
        return {
            "order_lines": int(row["order_lines"]),
            "total_sales": float(row["total_sales"]),
            "total_profit": float(row["total_profit"]),
            "profit_margin_pct": float(row["profit_margin_pct"]),
        }

    summary = {
        "headline_kpis": {
            "total_sales": float(h["total_sales"]),
            "total_profit": float(h["total_profit"]),
            "profit_margin_pct": float(h["profit_margin_pct"]),
            "order_count": int(h["order_count"]),
            "order_lines": int(h["order_lines"]),
            "customer_count": int(h["customer_count"]),
            "product_count": int(h["product_count"]),
            "units_sold": int(h["units_sold"]),
            "avg_order_value": float(h["avg_order_value"]),
            "avg_discount": float(h["avg_discount"]),
            "first_order_date": str(h["first_order_date"]),
            "last_order_date": str(h["last_order_date"]),
        },
        "best_category_by_profit": {
            "category": str(cat.loc[cat["total_profit"].idxmax(), "category"]),
            "total_profit": float(cat["total_profit"].max()),
            "total_sales": float(cat.loc[cat["total_profit"].idxmax(), "total_sales"]),
        },
        "worst_subcategory_by_profit": {
            "sub_category": str(sub.iloc[-1]["sub_category"]),
            "category": str(sub.iloc[-1]["category"]),
            "total_profit": float(sub.iloc[-1]["total_profit"]),
            "total_sales": float(sub.iloc[-1]["total_sales"]),
            "profit_margin_pct": float(sub.iloc[-1]["profit_margin_pct"]),
        },
        "best_region_by_profit": {
            "region": str(reg.iloc[0]["region"]),
            "total_profit": float(reg.iloc[0]["total_profit"]),
            "total_sales": float(reg.iloc[0]["total_sales"]),
            "profit_margin_pct": float(reg.iloc[0]["profit_margin_pct"]),
        },
        "worst_region_by_margin": {
            "region": str(reg.loc[reg["profit_margin_pct"].idxmin(), "region"]),
            "profit_margin_pct": float(reg["profit_margin_pct"].min()),
            "total_profit": float(reg.loc[reg["profit_margin_pct"].idxmin(), "total_profit"]),
        },
        "discount_impact": {
            "no_discount": band_row("0% (no discount)"),
            "over_50pct": band_row("Over 50%"),
        },
        "top_product_by_profit": {
            "product_name": str(top_prod["product_name"]),
            "total_profit": float(top_prod["total_profit"]),
            "total_sales": float(top_prod["total_sales"]),
        },
        "biggest_loss_making_product": {
            "product_name": str(worst_prod["product_name"]),
            "total_profit": float(worst_prod["total_profit"]),
            "total_sales": float(worst_prod["total_sales"]),
        },
        "top_customer_by_sales": {
            "customer_name": str(top_cust["customer_name"]),
            "total_sales": float(top_cust["total_sales"]),
            "total_profit": float(top_cust["total_profit"]),
        },
        "yearly_sales": {
            str(int(r.year)): float(r.total_sales) for r in years.itertuples()
        },
    }
    (OUTPUTS_DIR / "kpi_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(f"[summary] kpi_summary.json written")
    return summary


def main() -> None:
    df = load_and_clean()
    tables = build_star_schema(df)
    conn = load_to_sqlite(tables)
    export_processed(tables)
    results = run_queries(conn)
    summary = write_summary(results)
    conn.close()
    print("\nHEADLINE KPIs")
    for k, v in summary["headline_kpis"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
