-- Schema discovery against the Snowflake Public Data (Free) share.
-- CONFIRMED against a live account: everything lives in a single schema,
--   SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.*
-- and every object is a VIEW. Views ending in _PIT are point-in-time variants -- use the
-- non-PIT ones for this project.
--
-- Relevant views for the Aid Desert Finder:
--   FEMA       FEMA_DISASTER_DECLARATION_INDEX        one row per declared disaster
--              FEMA_DISASTER_DECLARATION_AREAS_INDEX  one row per area (county) per disaster
--   Census     AMERICAN_COMMUNITY_SURVEY_ATTRIBUTES   variable id -> human-readable label
--              AMERICAN_COMMUNITY_SURVEY_TIMESERIES   geography x variable x date values
--   NPPES      NPPES_NPI_INDEX                        provider master index
--              NPPES_PROVIDER_ADDRESSES               provider practice locations
--              NPPES_PRACTITIONER_ATTRIBUTES          individual practitioner detail
--              NPPES_NUCC_TAXONOMY                    specialty/taxonomy codes
--   Geography  GEOGRAPHY_INDEX                        geo entities (county, zip, state) + ids
--              GEOGRAPHY_HIERARCHY                    parent/child (zip -> county -> state)
--              GEOGRAPHY_RELATIONSHIPS                cross-geography mappings
--   Catalogs   PUBLIC_DATA_CATALOG / PUBLIC_DATA_DICTIONARY / PUBLIC_DATA_VARIABLE_CATALOG

-- 1. Full object list (how the above was discovered).
SELECT table_schema, table_name, table_type
FROM SNOWFLAKE_PUBLIC_DATA_FREE.INFORMATION_SCHEMA.TABLES
ORDER BY table_schema, table_name;

-- 2. Columns of the views this project joins.
SELECT table_name, column_name, data_type
FROM SNOWFLAKE_PUBLIC_DATA_FREE.INFORMATION_SCHEMA.COLUMNS
WHERE table_schema = 'PUBLIC_DATA_FREE'
  AND table_name IN (
      'FEMA_DISASTER_DECLARATION_INDEX',
      'FEMA_DISASTER_DECLARATION_AREAS_INDEX',
      'AMERICAN_COMMUNITY_SURVEY_ATTRIBUTES',
      'AMERICAN_COMMUNITY_SURVEY_TIMESERIES',
      'NPPES_NPI_INDEX',
      'NPPES_PROVIDER_ADDRESSES',
      'GEOGRAPHY_INDEX',
      'GEOGRAPHY_HIERARCHY'
  )
ORDER BY table_name, ordinal_position;

-- CONFIRMED COLUMNS (from step 2 against a live account):
--
--   FEMA_DISASTER_DECLARATION_INDEX
--     DISASTER_ID, DISASTER_DECLARATION_NAME, DISASTER_DECLARATION_TYPE,
--     DISASTER_DECLARATION_DATE, DISASTER_TYPE, DISASTER_BEGIN_DATE, DISASTER_END_DATE,
--     APPROVED_INDIVIDUAL_AND_HOUSEHOLDS_PROGRAM_AMOUNT, ... (funding amounts)
--
--   FEMA_DISASTER_DECLARATION_AREAS_INDEX
--     DISASTER_ID, FEMA_DESIGNATED_AREA, STATE_GEO_ID, COUNTY_GEO_ID, DESIGNATED_DATE, ...
--
--   AMERICAN_COMMUNITY_SURVEY_TIMESERIES
--     GEO_ID, VARIABLE, VARIABLE_NAME, DATE, VALUE, UNIT      <- long format
--   AMERICAN_COMMUNITY_SURVEY_ATTRIBUTES
--     VARIABLE, VARIABLE_NAME, CENSUS_SUBJECT, MEASURE, UNIT, SERIES_LEVEL_1..6, ...
--
--   NPPES_NPI_INDEX            NPI, NPI_CREATION_DATE, NPI_DEACTIVATION_DATE, ACTIVE
--   NPPES_PROVIDER_ADDRESSES   NPI, ADDRESS_TYPE, CITY, STATE, ZIP_CODE,
--                              GEO_ID_ZIP, GEO_ID_CITY, GEO_ID_STATE   <- note: NO county geo id
--
--   GEOGRAPHY_INDEX            GEO_ID, GEO_NAME, LEVEL, ISO_* codes
--   GEOGRAPHY_HIERARCHY        PARENT_GEO_ID, GEO_ID                   <- walk zip -> county
--
-- KEY INSIGHT: all three datasets share one GEO_ID spine, so joins go through GEO_ID rather
-- than raw FIPS codes or ZIP-to-county crosswalks. NPPES has only a ZIP-level geo id, so
-- provider counts roll up to county via GEOGRAPHY_HIERARCHY.

-- 3. Remaining unknowns to resolve before building the view:

-- 3a. What LEVEL vocabulary does the geography spine use ('County'? 'CensusCounty'?)
SELECT level, COUNT(*) AS n
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX
GROUP BY 1 ORDER BY 2 DESC;

-- 3b. Florida's own geo_id, and what its counties look like.
SELECT geo_id, geo_name, level
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX
WHERE geo_name ILIKE 'Florida' OR geo_name ILIKE 'Miami-Dade%'
LIMIT 20;

-- 3c. Which ACS variable holds county-level poverty rate.
SELECT variable, variable_name, unit, measure
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.AMERICAN_COMMUNITY_SURVEY_ATTRIBUTES
WHERE variable_name ILIKE '%poverty%'
LIMIT 50;

-- 3d. Does GEOGRAPHY_HIERARCHY link zip -> county directly, or zip -> state?
SELECT c.level AS child_level, p.level AS parent_level, COUNT(*) AS n
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_HIERARCHY h
JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX c ON c.geo_id = h.geo_id
JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX p ON p.geo_id = h.parent_geo_id
GROUP BY 1, 2 ORDER BY 3 DESC
LIMIT 30;
