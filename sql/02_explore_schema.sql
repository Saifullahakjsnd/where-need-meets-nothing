-- Run these interactively in Snowsight, one block at a time, and read the results.
-- Goal: confirm the real object names in your account's PUBLIC_DATA share before writing joins
-- in 03_build_aid_desert_view.sql. Docs drift; your account is the source of truth.
--
-- Adjust the database name below if you named the share something other than PUBLIC_DATA.
SET share_db = 'PUBLIC_DATA';

-- 1. What schemas (data sources) does the share expose?
SHOW SCHEMAS IN DATABASE identifier($share_db);

-- 2. FEMA disaster tables. Expected (per Snowflake's public docs, verify against your output):
--      fema_disaster_declaration_index        -- one row per declared disaster
--      fema_disaster_declaration_areas_index  -- one row per county/area hit by a disaster
SHOW TABLES LIKE '%fema%' IN DATABASE identifier($share_db);
-- Once you find the right schema name, e.g.:
-- DESCRIBE TABLE PUBLIC_DATA.FEMA.FEMA_DISASTER_DECLARATION_INDEX;
-- DESCRIBE TABLE PUBLIC_DATA.FEMA.FEMA_DISASTER_DECLARATION_AREAS_INDEX;

-- 3. Census / ACS tables. Expected:
--      american_community_survey_attributes   -- variable ID -> human-readable label
--      american_community_survey_timeseries   -- geography x variable x year, long format
SHOW TABLES LIKE '%census%' IN DATABASE identifier($share_db);
SHOW TABLES LIKE '%community_survey%' IN DATABASE identifier($share_db);
-- DESCRIBE TABLE PUBLIC_DATA.CENSUS.AMERICAN_COMMUNITY_SURVEY_TIMESERIES;

-- 3a. Find the exact variable_id for county-level poverty rate once you can query the attributes
-- table (replace schema name once known):
-- SELECT variable_id, variable_name
-- FROM PUBLIC_DATA.CENSUS.AMERICAN_COMMUNITY_SURVEY_ATTRIBUTES
-- WHERE variable_name ILIKE '%poverty%' AND variable_name ILIKE '%percent%';

-- 4. NPPES healthcare-provider tables. Expected:
--      npidata_pfile   -- master provider table (address incl. ZIP, NUCC taxonomy code)
--      pl_pfile        -- secondary practice-location table
SHOW TABLES LIKE '%npi%' IN DATABASE identifier($share_db);
-- DESCRIBE TABLE PUBLIC_DATA.NPPES.NPIDATA_PFILE;

-- 5. Geography reference / ZIP-to-county crosswalk (needed to roll NPPES ZIPs up to counties).
SHOW TABLES LIKE '%geograph%' IN DATABASE identifier($share_db);
SHOW TABLES LIKE '%fips%' IN DATABASE identifier($share_db);
SHOW TABLES LIKE '%zip%' IN DATABASE identifier($share_db);
