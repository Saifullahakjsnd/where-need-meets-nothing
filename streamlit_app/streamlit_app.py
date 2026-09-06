"""
Aid Desert Finder -- Streamlit in Snowflake app.

Natural-language query box (Cortex Analyst) + choropleth map (pydeck) over the
AID_DESERT_FINDER.ANALYTICS.AID_DESERT view built by sql/03_build_aid_desert_view.sql.

Deploy: Snowsight -> Projects -> Streamlit -> + Streamlit App -> paste this file's contents,
add packages from environment.yml. See SETUP.md step 6.
"""

import json

import _snowflake
import pandas as pd
import pydeck as pdk
import streamlit as st
from snowflake.snowpark.context import get_active_session

SEMANTIC_MODEL_PATH = "AID_DESERT_FINDER.ANALYTICS.SEMANTIC_MODELS/aid_desert.yaml"
ANALYST_API_ENDPOINT = "/api/v2/cortex/analyst/message"
ANALYST_API_TIMEOUT_MS = 50000

# TODO: confirm this table/schema exists (see sql/02_explore_schema.sql step 5). If your account's
# free share doesn't expose Florida county boundary polygons under this name, adjust the query in
# load_county_boundaries() below -- the rest of the app only needs county_fips + geometry.
COUNTY_BOUNDARY_QUERY = """
    SELECT
        county_fips,
        ST_ASGEOJSON(county_boundary) AS geojson
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.GEOGRAPHY.COUNTY_INDEX
    WHERE state = 'FL'
"""

session = get_active_session()

st.set_page_config(page_title="Aid Desert Finder", layout="wide")
st.title("Aid Desert Finder — Florida")
st.caption(
    "Where FEMA disasters, poverty, and thin healthcare access overlap. "
    "Ask a question below or explore the map directly."
)


@st.cache_data(show_spinner=False)
def load_aid_desert_data() -> pd.DataFrame:
    return session.table("AID_DESERT_FINDER.ANALYTICS.AID_DESERT").to_pandas()


@st.cache_data(show_spinner=False)
def load_county_boundaries() -> pd.DataFrame:
    try:
        return session.sql(COUNTY_BOUNDARY_QUERY).to_pandas()
    except Exception:
        return pd.DataFrame(columns=["COUNTY_FIPS", "GEOJSON"])


def score_to_color(score: float, min_score: float, max_score: float) -> list:
    if max_score == min_score:
        t = 0.5
    else:
        t = (score - min_score) / (max_score - min_score)
    # low need -> pale yellow, high need -> dark red
    r = 255
    g = int(255 * (1 - t))
    b = int(180 * (1 - t))
    return [r, g, b, 160]


def render_map(df: pd.DataFrame, boundaries: pd.DataFrame):
    if boundaries.empty:
        st.info(
            "No county boundary polygons found — showing county need scores as a table only. "
            "Fill in COUNTY_BOUNDARY_QUERY in streamlit_app.py once you've confirmed the "
            "boundary table name (see sql/02_explore_schema.sql)."
        )
        return

    merged = boundaries.merge(df, left_on="COUNTY_FIPS", right_on="COUNTY_FIPS", how="inner")
    min_score, max_score = df["AID_DESERT_SCORE"].min(), df["AID_DESERT_SCORE"].max()

    features = []
    for _, row in merged.iterrows():
        geometry = json.loads(row["GEOJSON"])
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "county_name": row["COUNTY_NAME"],
                    "aid_desert_score": row["AID_DESERT_SCORE"],
                    "disaster_count": int(row["DISASTER_COUNT"]),
                    "poverty_rate_pct": float(row["POVERTY_RATE_PCT"]),
                    "provider_count": int(row["PROVIDER_COUNT"]),
                    "fill_color": score_to_color(row["AID_DESERT_SCORE"], min_score, max_score),
                },
            }
        )
    geojson = {"type": "FeatureCollection", "features": features}

    layer = pdk.Layer(
        "GeoJsonLayer",
        geojson,
        opacity=0.7,
        stroked=True,
        filled=True,
        get_fill_color="properties.fill_color",
        get_line_color=[80, 80, 80],
        pickable=True,
    )
    view_state = pdk.ViewState(latitude=27.8, longitude=-81.7, zoom=5.5)
    tooltip = {
        "html": (
            "<b>{county_name}</b><br/>"
            "Need score: {aid_desert_score}<br/>"
            "Disasters: {disaster_count}<br/>"
            "Poverty rate: {poverty_rate_pct}%<br/>"
            "Doctors: {provider_count}"
        )
    }
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))


def ask_cortex_analyst(question: str) -> dict:
    request_body = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": question}]}],
        "semantic_model_file": f"@{SEMANTIC_MODEL_PATH}",
    }
    resp = _snowflake.send_snow_api_request(
        "POST", ANALYST_API_ENDPOINT, {}, {}, request_body, None, ANALYST_API_TIMEOUT_MS
    )
    parsed = json.loads(resp["content"])
    if resp["status"] >= 400:
        raise RuntimeError(parsed.get("message", "Cortex Analyst request failed"))
    return parsed


# --- Natural-language query box ---
question = st.text_input(
    "Ask a question", placeholder="Which counties had disasters but fewest doctors?"
)
if question:
    with st.spinner("Asking Cortex Analyst..."):
        try:
            response = ask_cortex_analyst(question)
            sql_statement = next(
                (item["statement"] for item in response["message"]["content"] if item["type"] == "sql"),
                None,
            )
            text_reply = next(
                (item["text"] for item in response["message"]["content"] if item["type"] == "text"),
                None,
            )
            if text_reply:
                st.markdown(text_reply)
            if sql_statement:
                st.code(sql_statement, language="sql")
                result_df = session.sql(sql_statement).to_pandas()
                st.dataframe(result_df, use_container_width=True)
        except Exception as exc:
            st.error(f"Cortex Analyst error: {exc}")

st.divider()

# --- Choropleth map + table over the full aid-desert view ---
aid_desert_df = load_aid_desert_data()
boundary_df = load_county_boundaries()

col_map, col_table = st.columns([2, 1])
with col_map:
    st.subheader("Aid desert map")
    render_map(aid_desert_df, boundary_df)
with col_table:
    st.subheader("Top need counties")
    st.dataframe(
        aid_desert_df.sort_values("AID_DESERT_SCORE", ascending=False).head(10),
        use_container_width=True,
        hide_index=True,
    )
