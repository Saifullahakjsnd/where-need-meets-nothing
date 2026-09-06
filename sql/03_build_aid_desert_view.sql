-- Builds AID_DESERT_FINDER.ANALYTICS.AID_DESERT: one row per Florida county with disaster
-- count, poverty rate, and doctor density.
--
-- All object and column names below are CONFIRMED against a live account (see
-- 02_explore_schema.sql). The three datasets join through the share's unified GEO_ID spine
-- (Data Commons style, e.g. Florida = 'geoId/12') rather than raw FIPS codes.
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

-- ACS: latest 5-year estimate per county.
-- 5YR (not 1YR) because 1-year estimates only cover counties above ~65k population, which
-- would drop most rural Florida counties -- exactly the ones this project is looking for.
--   B17001_001E = population for whom poverty status is determined (poverty denominator)
--   B17001_002E = population below poverty level (poverty numerator)
--   B01003_001E = total population (used for provider density)
acs_latest AS (
    SELECT geo_id, variable, value
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.AMERICAN_COMMUNITY_SURVEY_TIMESERIES
    WHERE variable IN ('B17001_001E_5YR', 'B17001_002E_5YR', 'B01003_001E_5YR')
      AND geo_id IN (SELECT county_geo_id FROM fl_counties)
    QUALIFY ROW_NUMBER() OVER (PARTITION BY geo_id, variable ORDER BY date DESC) = 1
),

census AS (
    SELECT
        geo_id AS county_geo_id,
        MAX(CASE WHEN variable = 'B17001_001E_5YR' THEN value END) AS poverty_universe,
        MAX(CASE WHEN variable = 'B17001_002E_5YR' THEN value END) AS below_poverty,
        MAX(CASE WHEN variable = 'B01003_001E_5YR' THEN value END) AS population
    FROM acs_latest
    GROUP BY 1
),

-- NPPES carries no county geo id -- only ZIP and city -- so providers roll up to county via
-- the geography hierarchy. Both a ZIP and a city can straddle county lines, so each mapping
-- picks one county deterministically and a provider is never counted twice.
zip_to_county AS (
    SELECT h.geo_id AS zip_geo_id, h.parent_geo_id AS county_geo_id
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_HIERARCHY h
    JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX z
        ON z.geo_id = h.geo_id AND z.level = 'CensusZipCodeTabulationArea'
    JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX c
        ON c.geo_id = h.parent_geo_id AND c.level = 'County'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY h.geo_id ORDER BY h.parent_geo_id) = 1
),

-- Fallback for the 2 of 67 Florida counties that have NO zip children in the hierarchy
-- (Union among them). Without this they can never be assigned a provider and show up as
-- fake perfect aid deserts with 0 doctors. All 67 counties do have city children.
city_to_county AS (
    SELECT h.geo_id AS city_geo_id, h.parent_geo_id AS county_geo_id
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_HIERARCHY h
    JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX ci
        ON ci.geo_id = h.geo_id AND ci.level = 'City'
    JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX c
        ON c.geo_id = h.parent_geo_id AND c.level = 'County'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY h.geo_id ORDER BY h.parent_geo_id) = 1
),

-- ADDRESS_TYPE matters: the table holds 'Mailing', 'Primary Practice' and 'Secondary Practice'
-- rows per provider. Counting all of them double-counts anyone whose mailing address sits in a
-- different county than where they practice. Only the primary practice location represents
-- where care is actually delivered.
providers AS (
    SELECT
        COALESCE(z.county_geo_id, cty.county_geo_id) AS county_geo_id,
        COUNT(DISTINCT addr.npi) AS provider_count
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.NPPES_PROVIDER_ADDRESSES addr
    JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.NPPES_NPI_INDEX npi
        ON npi.npi = addr.npi AND npi.active
    -- restrict to individual practitioners ("doctors"), excluding organizations
    JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.NPPES_PRACTITIONER_ATTRIBUTES prac
        ON prac.npi = addr.npi
    LEFT JOIN zip_to_county z   ON z.zip_geo_id   = addr.geo_id_zip
    LEFT JOIN city_to_county cty ON cty.city_geo_id = addr.geo_id_city
    WHERE addr.state = 'FL'
      AND addr.address_type = 'Primary Practice'
      AND COALESCE(z.county_geo_id, cty.county_geo_id)
          IN (SELECT county_geo_id FROM fl_counties)
    GROUP BY 1
),

metrics AS (
    SELECT
        c.county_geo_id,
        c.county_name,
        COALESCE(d.disaster_count, 0) AS disaster_count,
        ROUND(100.0 * ce.below_poverty / NULLIF(ce.poverty_universe, 0), 2) AS poverty_rate_pct,
        COALESCE(pr.provider_count, 0) AS provider_count,
        ce.population,
        ROUND(COALESCE(pr.provider_count, 0) * 10000.0 / NULLIF(ce.population, 0), 2)
            AS providers_per_10k
    FROM fl_counties c
    LEFT JOIN disasters d  ON d.county_geo_id  = c.county_geo_id
    LEFT JOIN census    ce ON ce.county_geo_id = c.county_geo_id
    LEFT JOIN providers pr ON pr.county_geo_id = c.county_geo_id
)

-- Composite need score, 0-100. Each input is converted to a percentile rank across Florida
-- counties before weighting, so one extreme county can't dominate the scale the way a
-- divide-by-max normalization would. Provider scarcity is ranked ascending-inverted: the
-- county with the fewest doctors per capita scores 1.0 on that term.
SELECT
    *,
    ROUND(100 * (
          0.35 * PERCENT_RANK() OVER (ORDER BY disaster_count)
        + 0.35 * PERCENT_RANK() OVER (ORDER BY poverty_rate_pct)
        + 0.30 * PERCENT_RANK() OVER (ORDER BY providers_per_10k DESC)
    ), 1) AS aid_desert_score
FROM metrics;

-- Sanity checks.
SELECT COUNT(*) AS county_count FROM aid_desert;

SELECT county_name, disaster_count, poverty_rate_pct, provider_count,
       providers_per_10k, aid_desert_score
FROM aid_desert
ORDER BY aid_desert_score DESC NULLS LAST
LIMIT 15;
