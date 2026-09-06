-- Builds AID_DESERT_FINDER.ANALYTICS.AID_DESERT: one row per Florida county with disaster count,
-- poverty rate, and doctor density. Fill in the TODO markers using the object/column names you
-- confirmed with 02_explore_schema.sql -- the names below are best-guess starting points based
-- on Snowflake's public documentation, not verified against a live account.

USE WAREHOUSE aid_desert_wh;
USE DATABASE aid_desert_finder;
USE SCHEMA analytics;

-- TODO: replace PUBLIC_DATA and schema names below if yours differ.

-- Step 1: disaster count per Florida county since 2015.
CREATE OR REPLACE TEMPORARY TABLE fl_disaster_counts AS
SELECT
    areas.fips_state_code || areas.fips_county_code AS county_fips,  -- TODO: confirm column names
    areas.county_name,                                               -- TODO: confirm column name
    COUNT(DISTINCT decl.disaster_number) AS disaster_count
FROM PUBLIC_DATA.FEMA.FEMA_DISASTER_DECLARATION_AREAS_INDEX areas     -- TODO: confirm schema/table
JOIN PUBLIC_DATA.FEMA.FEMA_DISASTER_DECLARATION_INDEX decl            -- TODO: confirm schema/table
    ON areas.disaster_number = decl.disaster_number                  -- TODO: confirm join key
WHERE areas.state = 'FL'                                             -- TODO: confirm column name
  AND decl.declaration_date >= '2015-01-01'                          -- TODO: confirm column name
GROUP BY 1, 2;

-- Step 2: poverty rate per Florida county from the latest available ACS year.
-- ACS data ships as a long table (one row per geography x variable x year), so filter to the
-- specific poverty-percent variable_id found via 02_explore_schema.sql's step 3a query.
CREATE OR REPLACE TEMPORARY TABLE fl_poverty AS
SELECT
    geo_id AS county_fips,               -- TODO: confirm column name (may be `geo_id` or `fips`)
    value AS poverty_rate_pct            -- TODO: confirm column name
FROM PUBLIC_DATA.CENSUS.AMERICAN_COMMUNITY_SURVEY_TIMESERIES   -- TODO: confirm schema/table
WHERE variable_id = 'TODO_POVERTY_VARIABLE_ID'                 -- TODO: fill in from step 3a
  AND geo_id LIKE '12%'                                        -- 12 = Florida state FIPS prefix
  AND date_value = (
        SELECT MAX(date_value)
        FROM PUBLIC_DATA.CENSUS.AMERICAN_COMMUNITY_SURVEY_TIMESERIES
        WHERE variable_id = 'TODO_POVERTY_VARIABLE_ID'
  );

-- Step 3: doctor (individual healthcare provider) count per Florida county.
-- NPPES only has ZIP code, not county FIPS, so join through a ZIP->county crosswalk found in
-- 02_explore_schema.sql's step 5 (name/schema TBD -- adjust join below once known).
CREATE OR REPLACE TEMPORARY TABLE fl_provider_counts AS
SELECT
    zc.county_fips,                                          -- TODO: confirm crosswalk column
    COUNT(DISTINCT npi.npi) AS provider_count
FROM PUBLIC_DATA.NPPES.NPIDATA_PFILE npi                     -- TODO: confirm schema/table
JOIN PUBLIC_DATA.CENSUS.ZIP_COUNTY_CROSSWALK zc               -- TODO: confirm schema/table/columns
    ON npi.provider_business_practice_location_zip5 = zc.zip -- TODO: confirm column names
WHERE npi.provider_business_practice_location_state = 'FL'   -- TODO: confirm column name
  AND npi.entity_type_code = '1'                             -- 1 = individual provider (not org)
GROUP BY 1;

-- Step 4: join the three into the aid-desert view Cortex Analyst and Streamlit will read.
CREATE OR REPLACE VIEW aid_desert AS
SELECT
    d.county_fips,
    d.county_name,
    d.disaster_count,
    p.poverty_rate_pct,
    COALESCE(pr.provider_count, 0) AS provider_count,
    -- simple composite score: more disasters + higher poverty + fewer doctors = higher need
    ROUND(
        d.disaster_count * 10
        + p.poverty_rate_pct
        - COALESCE(pr.provider_count, 0) * 0.1
    , 2) AS aid_desert_score
FROM fl_disaster_counts d
JOIN fl_poverty p ON p.county_fips = d.county_fips
LEFT JOIN fl_provider_counts pr ON pr.county_fips = d.county_fips
ORDER BY aid_desert_score DESC;

SELECT * FROM aid_desert;
