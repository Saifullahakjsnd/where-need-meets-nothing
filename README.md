# Where Need Meets Nothing — Aid Desert Finder

**Live map → https://aid-desert-finder.vercel.app**

Finds the Florida counties where disaster exposure and poverty are high *and* healthcare
resources are thinnest — the places most likely to be overlooked by donors, because attention
follows cameras rather than need.

Built for the DEV Weekend Challenge: Generosity Edition. Category: **Best Use of Snowflake**.

| County | FEMA disasters (10yr) | Poverty | Doctors per 10k |
|---|---|---|---|
| Alachua | 21 | 21.2% | 351.0 |
| Glades | 14 | 17.2% | 20.7 |

Alachua has more disasters and more poverty than Glades, and 17× the doctor density. That gap
is invisible in any one dataset. This joins three of them.

## What it does

Ranks all 67 Florida counties on a composite need score — 35% disaster frequency, 35% poverty
rate, 30% scarcity of doctors per capita, each as a percentile rank across the state. The result
is an interactive choropleth plus a natural-language query box.

Headline finding: **9 counties, ~258,000 people** averaging 22 disaster declarations in ten years,
one in five below the poverty line, at roughly half the state's median doctor density.

## Architecture

Everything comes from the **Snowflake Public Data (Free)** Marketplace share — no ETL, no external
data, not even the map geometry.

```
SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE
  ├── FEMA_DISASTER_DECLARATION_{INDEX,AREAS_INDEX}   disasters per county
  ├── AMERICAN_COMMUNITY_SURVEY_TIMESERIES            poverty + population (ACS 5yr)
  ├── NPPES_{NPI_INDEX,PROVIDER_ADDRESSES,...}        practitioners per county
  └── GEOGRAPHY_{INDEX,HIERARCHY,CHARACTERISTICS}     geo spine + county polygons
                        │
                        ▼
        AID_DESERT_FINDER.ANALYTICS.AID_DESERT        one view, 67 rows
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
  Cortex Analyst   Streamlit in    standalone page
  (NL querying)     Snowflake       (static, no runtime)
```

All three datasets share one `GEO_ID` spine (Data Commons style — Florida is `geoId/12`), so the
join runs on that rather than FIPS codes or a ZIP crosswalk.

## Layout

| Path | What it is |
|---|---|
| `sql/01_setup_share.sql` | Warehouse, database, schema, stage |
| `sql/02_explore_schema.sql` | Schema discovery — documents what the share contains |
| `sql/03_build_aid_desert_view.sql` | **The core** — builds the joined county view |
| `semantic_model/aid_desert.yaml` | Cortex Analyst semantic model (108 lines) |
| `streamlit_app/` | Streamlit in Snowflake app |
| `standalone/` | Generator for the static page — `export_data.py` then `build_html.py` |
| `SETUP.md` | Reproduce from scratch, plus the traps worth knowing |
| `SUBMISSION.md` | The challenge write-up |

## Three traps in this data

Each produced plausible-looking wrong numbers before being caught:

1. **NPPES stores three address types** (`Mailing`, `Primary Practice`, `Secondary Practice`).
   Counting all of them credits a doctor to both where they live and where they work.
2. **Two of the 67 counties have no ZIP children** in the geography hierarchy, so a ZIP-only
   rollup reports them as having zero doctors — they rank as perfect aid deserts by being
   invisible. Union County actually has 70.
3. **A view can't be built over `TEMPORARY` tables.** It compiles, then breaks when the session
   ends.

Sanity check after any change: 67 counties, and `SUM(population)` ≈ 22.4M against Florida's
actual ~22.6M.

## Credits

The Cortex Analyst REST call pattern (`send_snow_api_request`) is adapted from Snowflake's
[Cortex Analyst quickstart](https://github.com/Snowflake-Labs/sfguide-getting-started-with-cortex-analyst).
Everything else was written for this challenge, within the challenge window.
