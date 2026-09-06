# Setup Guide

Target for the weekend MVP: **Florida**, one state, three joined datasets, a natural-language
query box, a choropleth map.

## 1. Create a Snowflake account

1. Go to https://signup.snowflake.com/ and create a free trial account (30 days, $400 credit).
   Pick any cloud/region close to you — it doesn't matter for this project.
2. Log in to Snowsight (the web UI) once the account is provisioned.
3. Cortex Analyst (used for the natural-language query box) requires your account to be in a
   region where Cortex is supported (most commercial AWS/Azure US regions qualify). If Cortex
   Analyst isn't available, pick a supported region when creating the trial — see
   https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst for the current list.

## 2. Add the free public data share

1. In Snowsight, go to **Data Products → Marketplace**.
2. Search for **"Snowflake Public Data (Free)"** (listing by Snowflake Public Data Products).
3. Click **Get**, and give the resulting database a name — this guide assumes you name it
   `PUBLIC_DATA` (adjust the scripts in `sql/` if you pick something else).
4. No warehouse credits are consumed by adding the share itself — you only pay compute when you
   query it.

This single share includes FEMA disaster data, Census Bureau (incl. ACS) data, and NPPES
healthcare-provider data — the three datasets this project joins. No ETL, no pipelines.

## 3. Discover the real schema

Documentation table/column names drift and the exact schema can vary by account. Before writing
any real queries, run [sql/02_explore_schema.sql](sql/02_explore_schema.sql) in Snowsight. It
runs `SHOW SCHEMAS` / `SHOW TABLES` / `DESCRIBE TABLE` against the share so you can confirm the
actual object names, then fill in the `TODO` placeholders in
[sql/03_build_aid_desert_view.sql](sql/03_build_aid_desert_view.sql).

## 4. Build the joined view

Run [sql/01_setup_share.sql](sql/01_setup_share.sql) to create a working database/schema/warehouse
for this project, then [sql/03_build_aid_desert_view.sql](sql/03_build_aid_desert_view.sql) to
build the Florida county-level `aid_desert` view joining FEMA + Census + NPPES.

## 5. Create the Cortex Analyst semantic model

1. Upload [semantic_model/aid_desert.yaml](semantic_model/aid_desert.yaml) to a Snowflake stage
   (a `PUT` command or drag-and-drop in Snowsight's stage browser both work).
2. In Snowsight, go to **AI & ML → Cortex Analyst**, point it at the staged YAML file.
3. Test it with a question like *"Which counties had disasters but the fewest doctors?"*

## 6. Deploy the Streamlit app

1. In Snowsight, go to **Projects → Streamlit → + Streamlit App**.
2. Name it (e.g. `aid_desert_finder`), pick your warehouse.
3. Replace the generated `streamlit_app.py` with
   [streamlit_app/streamlit_app.py](streamlit_app/streamlit_app.py), and add the packages listed
   in [streamlit_app/environment.yml](streamlit_app/environment.yml) via the app's package picker
   (`pydeck` and `snowflake-ml-python` are not preinstalled).
4. Run the app. Ask it: *"Which counties had disasters but fewest doctors?"* and confirm the map
   and table populate.

## Notes on data-source specifics

- **FEMA**: `fema_disaster_declaration_index` (one row per declared disaster) joins to
  `fema_disaster_declaration_areas_index` (one row per county/area hit by a disaster) — a single
  disaster can span many counties, so aggregate at the county level before joining further.
- **Census/ACS**: values live in a long/timeseries table (one row per geography × variable ×
  year) rather than a wide table — you'll need to pivot or filter to the specific poverty-rate
  variable ID for Florida counties. `sql/02_explore_schema.sql` includes a query to find that
  variable ID.
- **NPPES**: provider records carry practice-location ZIP code, not county FIPS directly. You'll
  need a ZIP→county crosswalk to roll providers up to the county level Census and FEMA use — the
  free share includes a geography/ZIP crosswalk table; `sql/02_explore_schema.sql` checks for it.
