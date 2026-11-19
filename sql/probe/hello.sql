-- Phase 00 probe: proves a bundle-deployed serverless SQL pipeline runs on Databricks Free Edition.
CREATE OR REFRESH MATERIALIZED VIEW probe_hello AS SELECT 1 AS ok;
