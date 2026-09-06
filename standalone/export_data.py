"""Export the aid_desert view + simplified county geometry to a JSON file."""
import json
import pathlib

import snowflake.connector
from cryptography.hazmat.primitives import serialization

KEY = r"C:\Users\ncai\AppData\Local\snowflake\keys\aid_desert_rsa_key.p8"
OUT = pathlib.Path(
    r"C:\Users\ncai\AppData\Local\Temp\claude"
    r"\c--Users-ncai-Desktop-Weekend-challanges-WhereNeedMeetsNothing"
    r"\71a68099-9b7d-4442-a9fd-265506df551f\scratchpad\aid_desert_data.json"
)

with open(KEY, "rb") as f:
    pkey = serialization.load_pem_private_key(f.read(), password=None)

conn = snowflake.connector.connect(
    account="BOBHMQB-PUC38478", user="SAIFF", private_key=pkey,
    role="ACCOUNTADMIN", warehouse="AID_DESERT_WH",
    database="AID_DESERT_FINDER", schema="ANALYTICS",
)

cur = conn.cursor()
cur.execute("""
    SELECT
        a.county_geo_id,
        a.county_name,
        a.disaster_count,
        a.poverty_rate_pct,
        a.provider_count,
        a.population,
        a.providers_per_10k,
        a.aid_desert_score,
        TO_VARCHAR(ST_ASGEOJSON(ST_SIMPLIFY(TO_GEOGRAPHY(gc.value), 400))) AS geojson
    FROM AID_DESERT_FINDER.ANALYTICS.AID_DESERT a
    JOIN SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_CHARACTERISTICS gc
        ON gc.geo_id = a.county_geo_id AND gc.relationship_type = 'coordinates_geojson'
    ORDER BY a.aid_desert_score DESC
""")

counties = []
for (gid, name, dis, pov, prov, pop, per10k, score, gj) in cur.fetchall():
    counties.append({
        "id": gid,
        "name": name.replace(" County", ""),
        "disasters": int(dis),
        "poverty": round(float(pov), 1),
        "providers": int(prov),
        "population": int(pop),
        "per10k": round(float(per10k), 1),
        "score": round(float(score), 1),
        "geom": json.loads(gj),
    })

# provenance for the footer
cur.execute("""
    SELECT MAX(date)
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.AMERICAN_COMMUNITY_SURVEY_TIMESERIES
    WHERE variable = 'B01003_001E_5YR' AND geo_id = 'geoId/12001'
""")
acs_date = str(cur.fetchone()[0])

OUT.write_text(json.dumps({"counties": counties, "acs_date": acs_date}), encoding="utf-8")
print(f"wrote {len(counties)} counties, {OUT.stat().st_size/1024:.0f} KB, ACS vintage {acs_date}")
print(f"score range {min(c['score'] for c in counties)} - {max(c['score'] for c in counties)}")
