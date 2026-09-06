"""
Aid Desert Finder -- Streamlit in Snowflake app.

Natural-language query box (Cortex Analyst) + choropleth map (pydeck) over the
AID_DESERT_FINDER.ANALYTICS.AID_DESERT view built by sql/03_build_aid_desert_view.sql.

Deploy: Snowsight -> Projects -> Streamlit -> + Streamlit App -> paste this file's contents,
add packages from environment.yml. See SETUP.md step 6.
"""

import json

import pandas as pd
import pydeck as pdk
import streamlit as st
from snowflake.snowpark.context import get_active_session

SEMANTIC_MODEL_PATH = "AID_DESERT_FINDER.ANALYTICS.SEMANTIC_MODELS/aid_desert.yaml"
ANALYST_API_ENDPOINT = "/api/v2/cortex/analyst/message"
ANALYST_API_TIMEOUT_MS = 50000

# County polygons come from the same free share as everything else -- no external geo data.
# Raw geometry is 4.5MB across 67 counties; simplifying to a 300m tolerance cuts that to
# ~190KB with no visible difference at state zoom.
COUNTY_BOUNDARY_QUERY = """
    SELECT
        gc.geo_id AS county_geo_id,
        TO_VARCHAR(ST_ASGEOJSON(ST_SIMPLIFY(TO_GEOGRAPHY(gc.value), 300))) AS geojson
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_CHARACTERISTICS gc
    JOIN AID_DESERT_FINDER.ANALYTICS.AID_DESERT a ON a.county_geo_id = gc.geo_id
    WHERE gc.relationship_type = 'coordinates_geojson'
"""

session = get_active_session()

st.set_page_config(page_title="Aid Desert Finder", layout="wide")
st.title("Aid Desert Finder — Florida")
st.caption(
    "Where FEMA disasters, poverty, and thin healthcare access overlap. "
    "Every number below comes from the free Snowflake Public Data share — zero ETL."
)


@st.cache_data(show_spinner=False)
def load_aid_desert_data() -> pd.DataFrame:
    return session.table("AID_DESERT_FINDER.ANALYTICS.AID_DESERT").to_pandas()


@st.cache_data(show_spinner=False)
def load_county_boundaries() -> pd.DataFrame:
    return session.sql(COUNTY_BOUNDARY_QUERY).to_pandas()


def score_to_color(score: float, lo: float, hi: float) -> list:
    """Pale sand (low need) -> deep red (high need)."""
    t = 0.5 if hi == lo else (score - lo) / (hi - lo)
    return [int(253 - 20 * t), int(231 - 186 * t), int(190 - 150 * t), 200]


def render_map(df: pd.DataFrame, boundaries: pd.DataFrame):
    if boundaries.empty:
        st.warning("No county boundaries returned — showing the table only.")
        return

    merged = boundaries.merge(df, on="COUNTY_GEO_ID", how="inner")
    lo, hi = df["AID_DESERT_SCORE"].min(), df["AID_DESERT_SCORE"].max()

    features = [
        {
            "type": "Feature",
            "geometry": json.loads(row["GEOJSON"]),
            "properties": {
                "county_name": row["COUNTY_NAME"],
                "aid_desert_score": float(row["AID_DESERT_SCORE"]),
                "disaster_count": int(row["DISASTER_COUNT"]),
                "poverty_rate_pct": float(row["POVERTY_RATE_PCT"]),
                "provider_count": int(row["PROVIDER_COUNT"]),
                "providers_per_10k": float(row["PROVIDERS_PER_10K"]),
                "fill_color": score_to_color(row["AID_DESERT_SCORE"], lo, hi),
            },
        }
        for _, row in merged.iterrows()
    ]

    layer = pdk.Layer(
        "GeoJsonLayer",
        {"type": "FeatureCollection", "features": features},
        opacity=0.85,
        stroked=True,
        filled=True,
        get_fill_color="properties.fill_color",
        get_line_color=[255, 255, 255],
        line_width_min_pixels=1,
        pickable=True,
    )
    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=pdk.ViewState(latitude=27.9, longitude=-83.4, zoom=5.6),
            tooltip={
                "html": (
                    "<b>{county_name}</b><br/>"
                    "Need score: <b>{aid_desert_score}</b><br/>"
                    "Disasters (10yr): {disaster_count}<br/>"
                    "Poverty: {poverty_rate_pct}%<br/>"
                    "Doctors: {provider_count} ({providers_per_10k} per 10k)"
                )
            },
        )
    )


def ask_cortex_analyst(question: str) -> dict:
    import _snowflake

    resp = _snowflake.send_snow_api_request(
        "POST",
        ANALYST_API_ENDPOINT,
        {},
        {},
        {
            "messages": [{"role": "user", "content": [{"type": "text", "text": question}]}],
            "semantic_model_file": f"@{SEMANTIC_MODEL_PATH}",
        },
        None,
        ANALYST_API_TIMEOUT_MS,
    )
    parsed = json.loads(resp["content"])
    if resp["status"] >= 400:
        raise RuntimeError(parsed.get("message", "Cortex Analyst request failed"))
    return parsed


aid_desert_df = load_aid_desert_data()

# --- Headline numbers ---
worst = aid_desert_df.sort_values("AID_DESERT_SCORE", ascending=False).iloc[0]
thinnest = aid_desert_df.sort_values("PROVIDERS_PER_10K").iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("Counties analyzed", len(aid_desert_df))
c2.metric("Highest need", worst["COUNTY_NAME"], f"score {worst['AID_DESERT_SCORE']:.0f}")
c3.metric(
    "Thinnest coverage",
    thinnest["COUNTY_NAME"],
    f"{thinnest['PROVIDERS_PER_10K']:.0f} doctors / 10k",
)

st.divider()

# --- Natural-language query box ---
st.subheader("Ask the data")
question = st.text_input(
    "Question",
    placeholder="Which counties had disasters but fewest doctors?",
    label_visibility="collapsed",
)
if question:
    with st.spinner("Asking Cortex Analyst..."):
        try:
            content = ask_cortex_analyst(question)["message"]["content"]
            text_reply = next((i["text"] for i in content if i["type"] == "text"), None)
            sql_statement = next((i["statement"] for i in content if i["type"] == "sql"), None)

            if text_reply:
                st.markdown(text_reply)
            if sql_statement:
                with st.expander("Generated SQL"):
                    st.code(sql_statement, language="sql")
                st.dataframe(
                    session.sql(sql_statement).to_pandas(),
                    use_container_width=True,
                    hide_index=True,
                )
        except Exception as exc:
            st.error(f"Cortex Analyst error: {exc}")

st.divider()

# --- Choropleth map + ranked table ---
col_map, col_table = st.columns([3, 2])
with col_map:
    st.subheader("Aid desert map")
    render_map(aid_desert_df, load_county_boundaries())
with col_table:
    st.subheader("Highest need counties")
    st.dataframe(
        aid_desert_df.sort_values("AID_DESERT_SCORE", ascending=False)[
            ["COUNTY_NAME", "DISASTER_COUNT", "POVERTY_RATE_PCT",
             "PROVIDERS_PER_10K", "AID_DESERT_SCORE"]
        ].head(15),
        use_container_width=True,
        hide_index=True,
        column_config={
            "COUNTY_NAME": "County",
            "DISASTER_COUNT": st.column_config.NumberColumn("Disasters", width="small"),
            "POVERTY_RATE_PCT": st.column_config.NumberColumn("Poverty %", format="%.1f"),
            "PROVIDERS_PER_10K": st.column_config.NumberColumn("Docs/10k", format="%.0f"),
            "AID_DESERT_SCORE": st.column_config.ProgressColumn(
                "Need", min_value=0, max_value=100, format="%.0f"
            ),
        },
    )
