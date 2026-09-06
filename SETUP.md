# Setup Guide

Weekend MVP target: **Florida**, three joined datasets, a natural-language query box, a
choropleth map. All of this is already built and deployed — this document covers how to
reproduce it in a fresh account, and how to keep working on it.

## Current state

| Piece | Where it lives |
|---|---|
| Joined county view | `AID_DESERT_FINDER.ANALYTICS.AID_DESERT` (67 Florida counties) |
| Semantic model | `@AID_DESERT_FINDER.ANALYTICS.SEMANTIC_MODELS/aid_desert.yaml` |
| Streamlit app | `AID_DESERT_FINDER.ANALYTICS.AID_DESERT_FINDER` |

App URL: https://app.snowflake.com/us-east-1/ipc20383/#/streamlit-apps/AID_DESERT_FINDER.ANALYTICS.AID_DESERT_FINDER

> **Note the account identifier in that URL.** Snowsight routes by account **locator**
> (`IPC20383`), but `snow streamlit deploy` prints a URL built from the account **name**
> (`PUC38478`) — that URL does not resolve and fails with "Unable to connect to the Snowflake
> backend", which looks like a firewall problem but isn't. Get the locator with
> `SELECT CURRENT_ACCOUNT();` and ignore the URL the CLI prints.

## 1. Snowflake account

1. https://signup.snowflake.com/ — free trial, 30 days, $400 credit. Enterprise edition.
2. Any commercial AWS/Azure region works. Accounts created after March 2026 default to
   `ANY_REGION` cross-region inference, so Cortex Analyst works regardless of region.

## 2. Add the free public data share

**Data Products → Marketplace → "Snowflake Public Data (Free)" → Get.**

Name the database `SNOWFLAKE_PUBLIC_DATA_FREE` (the default). All three datasets this project
joins live in that one share — FEMA, Census/ACS, and NPPES — so there is no ETL, no pipeline,
and no external data of any kind, including the map geometry.

## 3. Build it

```sh
snow sql -c <your-connection> -f sql/01_setup_share.sql
snow sql -c <your-connection> -f sql/03_build_aid_desert_view.sql
snow stage copy semantic_model/aid_desert.yaml @AID_DESERT_FINDER.ANALYTICS.SEMANTIC_MODELS \
    -c <your-connection> --overwrite
cd streamlit_app && snow streamlit deploy -c <your-connection> --replace
```

`sql/02_explore_schema.sql` is not part of the build — it is the schema-discovery scratchpad,
kept because it documents what the share actually contains and how the pieces connect.

## 4. Connecting the CLI

This project was built through key-pair auth, because `externalbrowser` fails on a trial
account with no SAML IdP configured (error 390190).

```sh
pip install snowflake-cli
snow connection add --connection-name aid_desert --account <ORG-ACCOUNT> --user <USER> \
    --authenticator SNOWFLAKE_JWT --role ACCOUNTADMIN --warehouse COMPUTE_WH
# then register the public half:
#   ALTER USER <USER> SET RSA_PUBLIC_KEY='<base64 body, no PEM header/footer lines>';
snow connection test -c aid_desert
```

Two gotchas that cost time here: `config.toml` must be written **without a UTF-8 BOM** (Windows
PowerShell's `Set-Content -Encoding utf8` adds one, and the TOML parser rejects it), and the
`RSA_PUBLIC_KEY` value is the base64 body only, with the `-----BEGIN/END-----` lines stripped.

To revoke the key: `ALTER USER <USER> UNSET RSA_PUBLIC_KEY;`

## How the data actually connects

Everything in the share sits in a single schema, `SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE`,
and every object is a view. Views suffixed `_PIT` are point-in-time variants — use the plain ones.

The three datasets join through a shared **`GEO_ID` spine** (Data Commons style — Florida is
`geoId/12`, Alachua County is `geoId/12001`), not through FIPS codes or ZIP crosswalks:

- **FEMA** — `FEMA_DISASTER_DECLARATION_AREAS_INDEX` carries `COUNTY_GEO_ID` directly, joined to
  `FEMA_DISASTER_DECLARATION_INDEX` on `DISASTER_ID` for declaration dates.
- **Census/ACS** — `AMERICAN_COMMUNITY_SURVEY_TIMESERIES` is long format (`GEO_ID`, `VARIABLE`,
  `DATE`, `VALUE`). Poverty is `B17001_002E_5YR / B17001_001E_5YR`; population is
  `B01003_001E_5YR`. Use 5-year estimates — 1-year only covers counties above ~65k population,
  which drops most of rural Florida.
- **NPPES** — has **no county geo id**, only `GEO_ID_ZIP` and `GEO_ID_CITY`, so providers roll up
  through `GEOGRAPHY_HIERARCHY`.
- **Map geometry** — `GEOGRAPHY_CHARACTERISTICS` holds `coordinates_geojson` rows: real county
  polygons, no external GeoJSON needed.

## Three traps in this data

These each produced plausible-looking but wrong numbers before being caught:

1. **`ADDRESS_TYPE` has three values** — `Mailing`, `Primary Practice`, `Secondary Practice`.
   Counting all of them credits a provider to both their mailing county and their practice
   county. Filter to `Primary Practice`.
2. **Two of Florida's 67 counties have no ZIP children** in the hierarchy (Union among them), so
   a ZIP-only rollup can never assign them a provider — they report 0 doctors and rank as
   perfect aid deserts. All 67 do have city children, hence the city fallback.
3. **A view cannot be built over `TEMPORARY` tables** — it compiles fine and then breaks as soon
   as the session ends. The view is one CTE chain for this reason.

Sanity check after any change: county count should be 67 and `SUM(population)` should land near
22.4M against Florida's actual ~22.6M.
