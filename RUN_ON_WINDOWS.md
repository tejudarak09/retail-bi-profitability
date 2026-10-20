# Run on Windows — Retail BI & Profitability Analysis

Click-by-click from a fresh folder to a pushed GitHub repo.
Budget: ~20 minutes for the Python + Excel part, ~45-60 minutes for the
Power BI build.

## Prerequisites

- **Python 3.12** (check: open PowerShell and run `python --version`)
- **Power BI Desktop** (free — Microsoft Store → search "Power BI Desktop")
- **Git** (check: `git --version`)
- The project folder `retail-bi-profitability` extracted on your PC,
  e.g. at `C:\CV_projects\retail-bi-profitability`

## Step 1 — Run the Python verifier

Open PowerShell **inside the project folder** (in File Explorer, click the
address bar, type `powershell`, press Enter — or Shift+Right-click the folder
→ "Open PowerShell window here").

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python python\prep_and_verify.py
python python\build_workbook.py
```

What you should see:
- `[clean] raw rows: 9994 -> cleaned rows: 9994`
- `[load] sqlite row counts: {'dim_customer': 793, 'dim_product': 1862, 'dim_date': 1434, 'dim_region': 632, 'fact_sales': 9994}`
- 11 `[query] ...` lines, one per KPI query
- Headline KPIs ending with `total_sales: 2297200.86` and
  `total_profit: 286397.02`
- `[excel] workbook written to ... retail_bi_kpi_workbook.xlsx`

Run `python python\prep_and_verify.py` a second time — the outputs must be
identical (the pipeline is deterministic; that's the verification).

Open `excel\retail_bi_kpi_workbook.xlsx` and check the KPI Summary sheet:
Total Sales 2,297,200.86, Total Profit 286,397.02, Margin 12.47%.

## Step 2 — Build the Power BI file

Follow `powerbi\PBIX_BUILD_GUIDE.md` exactly. Short version:

1. Power BI Desktop → Get data → Text/CSV → import the 5 CSVs from
   `data\processed\`.
2. Model view → create the 4 relationships (dim keys → fact keys).
3. Mark `dim_date` as the date table on `full_date`.
4. Create the `_Measures` table and paste the measures from
   `powerbi\DAX_MEASURES.md`.
5. Build the 3 pages: **Executive Overview**, **Profitability Deep-Dive**,
   **Discount & Region Analysis** (visual list is in the guide).
6. With all slicers cleared, check the cards against
   `outputs\kpi_summary.json` — they must match exactly.
7. Save As → `retail_bi_profitability.pbix` in the project folder.
   (The .pbix is in .gitignore — it stays on your PC, that's fine.)

## Step 3 — Push to GitHub

On github.com, create a **new public repository**:
- Name: `retail-bi-profitability-analysis`
- Do **NOT** tick "Add a README file" (the repo already has one) — leave
  README, .gitignore and license all unticked.

Then, in the **same PowerShell window inside the project folder**:

```powershell
cd C:\CV_projects\retail-bi-profitability
git init
git add .
git status
git commit -m "Retail BI & Profitability Analysis: star schema, SQL KPIs, Power BI + Excel"
git branch -M main
git remote add origin https://github.com/tejudarak09/retail-bi-profitability-analysis.git
git push -u origin main
```

> ⚠️ **STOP RULE (from a past accident):** after `git add .`, read
> `git status` carefully. It must list only this project's files
> (README.md, sql\, python\, data\, outputs\, excel\, powerbi\...).
> If it ever shows **AppData**, **Desktop**, or thousands of files from
> `C:\Users\tejud`, you are in the WRONG folder — close PowerShell, do not
> commit, and reopen it inside `C:\CV_projects\retail-bi-profitability`.
> Only ever run `git init` inside the project folder itself.

If Git asks you to sign in, use the browser popup — never paste a password
or token into chat or into any file.

## Step 4 — Verify the push

1. Open https://github.com/tejudarak09/retail-bi-profitability-analysis
2. Check the README renders with the KPI table.
3. Check `outputs\kpi_summary.json` and
   `excel\retail_bi_kpi_workbook.xlsx` are visible in the file list.
4. Send the repo link to Rio for a final check.
