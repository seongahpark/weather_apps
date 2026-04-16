import streamlit as st
import os
from dotenv import load_dotenv

from weather_utils import get_weather
from recommender import get_rule_based_recommendation, get_llm_recommendation
from security import load_keys_encrypted

# UI Components
from components.sidebar import render_sidebar
from components.search import render_search
from components.weather import render_weather_summary
from components.tabs import render_tabs

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="오늘의 날씨 & 라이프 추천",
    page_icon="🌤️",
    layout="wide"
)

# Initialize API Keys from encrypted storage
if 'owm_key' not in st.session_state or 'openai_key' not in st.session_state:
    stored_keys = load_keys_encrypted()
    if stored_keys:
        st.session_state.owm_key = stored_keys.get('owm', '')
        st.session_state.openai_key = stored_keys.get('openai', '')
    else:
        st.session_state.owm_key = os.getenv("OPENWEATHER_API_KEY", "")
        st.session_state.openai_key = os.getenv("OPENAI_API_KEY", "")

# ── Custom CSS ────────────────────────────────────────────────────────────────
try:
    with open(os.path.join(os.path.dirname(__file__), "assets", "style.css"), "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass # fallback if css is missing

# ── Orchestrate Components ────────────────────────────────────────────────────

# 1. Setup Sidebar
api_key_owm, api_key_openai, mode = render_sidebar()

# 2. Setup Main Search Area
city_input, search_btn = render_search()

# 3. Main Logic
if search_btn or city_input:
    if not api_key_owm:
        st.error("OpenWeatherMap API 키가 필요합니다. 사이드바에서 입력해주세요.")
    else:
        with st.spinner("날씨 정보를 가져오는 중..."):
            weather = get_weather(city_input, api_key_owm)

        if weather:
            # Render Weather Summary
            render_weather_summary(weather)

            # Build Recommendations
            base_rec = get_rule_based_recommendation(weather)

            st.divider()
            st.header("💡 오늘의 맞춤 추천")

            # ── LLM Mode vs Rule Mode logic
            if mode == "LLM 기반 (자연어 강화)":
                if not api_key_openai:
                    st.warning("OpenAI API 키가 없습니다. 규칙 기반 추천을 표시합니다.")
                    display_mode = "rule"
                else:
                    with st.spinner("AI가 7개 섹션의 추천 문구를 생성하고 있습니다..."):
                        llm_text = get_llm_recommendation(weather, base_rec, api_key_openai)
                    with st.container():
                        st.markdown(llm_text)
                    display_mode = "llm"
            else:
                display_mode = "rule"

            # Render Rule-based Tabs
            if display_mode == "rule":
                render_tabs(weather, base_rec, api_key_openai)

            # Footer
            st.divider()
            st.caption("OpenWeatherMap 데이터를 기반으로 생성된 추천입니다. 상황에 따라 유동적으로 결정하세요.")

        else:
            st.error(f"'{city_input}' 도시 정보를 가져올 수 없습니다. 도시 이름을 확인해주세요.")
