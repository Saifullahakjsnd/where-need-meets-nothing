# WhereNeedMeetsNothing — Aid Desert Finder

**Category:** Best Use of Snowflake

## The Hook
It fuses disaster, poverty, and health-access data into a single equity map that nobody has assembled
for donors, using a massive, free Snowflake dataset.

## What It Does
Overlays FEMA disaster declarations, Census/ACS poverty and demographics, and NPPES health-provider
density to surface "aid deserts" — high-need counties with the fewest resources. It allows for
plain-English querying.

## Architecture
Snowflake Public Data (Free) share
→ Cortex Analyst over a small semantic YAML model
→ Streamlit in Snowflake map (pydeck)
Zero ETL required.

## Weekend MVP
- One state
- Three joined datasets
- A natural language query box
- A choropleth map

## Key Challenge & Fix
**Challenge:** Building the semantic YAML.
**Fix:** Start from Snowflake's Cortex Analyst quickstart repo and keep the model tiny.

## The Demo
Ask "Which counties had disasters but fewest doctors?" and show the resulting map and table.

## Weekend MVP target
**Florida.** See [SETUP.md](SETUP.md) for step-by-step account creation, data-share setup, and
deployment instructions.

## Project layout
- `sql/01_setup_share.sql` — creates the warehouse/database/schema/stage for this project.
- `sql/02_explore_schema.sql` — discovers the real FEMA/Census/NPPES table & column names in your
  account (run this first; documentation names drift).
- `sql/03_build_aid_desert_view.sql` — builds the Florida county-level `aid_desert` view joining
  all three datasets.
- `semantic_model/aid_desert.yaml` — the Cortex Analyst semantic model over that view.
- `streamlit_app/` — the Streamlit in Snowflake app (NL query box + pydeck choropleth map).
