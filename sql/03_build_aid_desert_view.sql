-- Builds AID_DESERT_FINDER.ANALYTICS.AID_DESERT: one row per Florida county with disaster
-- count, poverty rate, and doctor density.
--
-- All object and column names below are CONFIRMED against a live account (see
-- 02_explore_schema.sql). The three datasets join through the share's unified GEO_ID spine
-- rather than raw FIPS codes.
--
-- Florida is resolved by name through GEOGRAPHY_HIERARCHY rather than a hardcoded geo_id, so
-- switching states later is a one-line change in the fl_state CTE.

USE WAREHOUSE aid_desert_wh;
USE DATABASE aid_desert_finder;
USE SCHEMA analytics;

CREATE OR REPLACE VIEW aid_desert AS
WITH fl_state AS (
    SELECT geo_id
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX
    WHERE level = 'State' AND geo_name ILIKE 'Florida'
),

fl_counties AS (
    SELECT gi.geo_id AS county_geo_id, gi.geo_name AS county_name
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_HIERARCHY h
    JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX gi
        ON gi.geo_id = h.geo_id
    WHERE gi.level = 'County'
      AND h.parent_geo_id IN (SELECT geo_id FROM fl_state)
),

-- FEMA: distinct declared disasters touching each county in the last 10 years.
disasters AS (
    SELECT a.county_geo_id, COUNT(DISTINCT a.disaster_id) AS disaster_count
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FEMA_DISASTER_DECLARATION_AREAS_INDEX a
    JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.FEMA_DISASTER_DECLARATION_INDEX d
        ON d.disaster_id = a.disaster_id
    WHERE a.county_geo_id IN (SELECT county_geo_id FROM fl_counties)
      AND d.disaster_declaration_date >= DATEADD(year, -10, CURRENT_DATE())
    GROUP BY 1
),

-- ACS: latest 5-year estimate per county for the two poverty counts.
-- 5YR (not 1YR) because 1-year estimates only cover counties above ~65k population, which
-- would drop most rural Florida counties -- exactly the ones this project is looking for.
poverty_latest AS (
    SELECT geo_id, variable, value
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.AMERICAN_COMMUNITY_SURVEY_TIMESERIES
    WHERE variable IN ('B17001_001E_5YR', 'B17001_002E_5YR')
      AND geo_id IN (SELECT county_geo_id FROM fl_counties)
    QUALIFY ROW_NUMBER() OVER (PARTITION BY geo_id, variable ORDER BY date DESC) = 1
),

poverty AS (
    SELECT
        geo_id AS county_geo_id,
        MAX(CASE WHEN variable = 'B17001_001E_5YR' THEN value END) AS poverty_universe,
        MAX(CASE WHEN variable = 'B17001_002E_5YR' THEN value END) AS below_poverty
    FROM poverty_latest
    GROUP BY 1
),

-- NPPES has only a ZIP-level geo id, so providers roll up to county via the hierarchy.
-- A ZIP can straddle county lines; pick one county per ZIP deterministically so a provider
-- is never counted in two counties.
zip_to_county AS (
    SELECT h.geo_id AS zip_geo_id, h.parent_geo_id AS county_geo_id
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_HIERARCHY h
    JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX z
        ON z.geo_id = h.geo_id AND z.level = 'CensusZipCodeTabulationArea'
    JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX c
        ON c.geo_id = h.parent_geo_id AND c.level = 'County'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY h.geo_id ORDER BY h.parent_geo_id) = 1
),

providers AS (
    SELECT z.county_geo_id, COUNT(DISTINCT addr.npi) AS provider_count
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.NPPES_PROVIDER_ADDRESSES addr
    JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.NPPES_NPI_INDEX npi
        ON npi.npi = addr.npi AND npi.active
    -- restrict to individual practitioners ("doctors"), excluding organizations
    JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.NPPES_PRACTITIONER_ATTRIBUTES prac
        ON prac.npi = addr.npi
    JOIN zip_to_county z
        ON z.zip_geo_id = addr.geo_id_zip
    WHERE addr.state = 'FL'
      AND z.county_geo_id IN (SELECT county_geo_id FROM fl_counties)
    GROUP BY 1
)

SELECT
    c.county_geo_id,
    c.county_name,
    COALESCE(d.disaster_count, 0) AS disaster_count,
    ROUND(100.0 * p.below_poverty / NULLIF(p.poverty_universe, 0), 2) AS poverty_rate_pct,
    COALESCE(pr.provider_count, 0) AS provider_count,
    p.poverty_universe AS population,
    -- doctors per 10k residents: the actual access measure
    ROUND(
        COALESCE(pr.provider_count, 0) * 10000.0 / NULLIF(p.poverty_universe, 0)
    , 2) AS providers_per_10k,
    -- Composite need score, 0-100ish: high disaster exposure + high poverty + thin provider
    -- coverage. Each term is normalized across Florida counties so no single input dominates.
    ROUND(
        40 * COALESCE(d.disaster_count, 0)
             / NULLIF(MAX(COALESCE(d.disaster_count, 0)) OVER (), 0)
      + 40 * (100.0 * p.below_poverty / NULLIF(p.poverty_universe, 0))
             / NULLIF(MAX(100.0 * p.below_poverty / NULLIF(p.poverty_universe, 0)) OVER (), 0)
      + 20 * (1 - COALESCE(
                    (COALESCE(pr.provider_count, 0) * 10000.0 / NULLIF(p.poverty_universe, 0))
                    / NULLIF(MAX(COALESCE(pr.provider_count, 0) * 10000.0
                                 / NULLIF(p.poverty_universe, 0)) OVER (), 0)
                  , 0))
    , 2) AS aid_desert_score
FROM fl_counties c
LEFT JOIN disasters d ON d.county_geo_id = c.county_geo_id
LEFT JOIN poverty   p ON p.county_geo_id = c.county_geo_id
LEFT JOIN providers pr ON pr.county_geo_id = c.county_geo_id;

-- Sanity checks -- expect ~67 rows (Florida county count), non-null poverty, sane scores.
SELECT COUNT(*) AS county_count FROM aid_desert;

SELECT county_name, disaster_count, poverty_rate_pct, provider_count,
       providers_per_10k, aid_desert_score
FROM aid_desert
ORDER BY aid_desert_score DESC NULLS LAST
LIMIT 15;
