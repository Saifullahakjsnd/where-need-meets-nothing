-- Run once, as ACCOUNTADMIN or a role with CREATE DATABASE/WAREHOUSE privileges.
-- Prerequisite: you've already added the "Snowflake Public Data (Free)" listing from the
-- Marketplace as a database named SNOWFLAKE_PUBLIC_DATA_FREE (Data Products -> Marketplace -> Get). See SETUP.md.

CREATE WAREHOUSE IF NOT EXISTS aid_desert_wh
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

CREATE DATABASE IF NOT EXISTS aid_desert_finder;
CREATE SCHEMA IF NOT EXISTS aid_desert_finder.analytics;

-- Stage for the Cortex Analyst semantic model YAML.
CREATE STAGE IF NOT EXISTS aid_desert_finder.analytics.semantic_models
    DIRECTORY = (ENABLE = TRUE);

USE WAREHOUSE aid_desert_wh;
USE DATABASE aid_desert_finder;
USE SCHEMA analytics;
