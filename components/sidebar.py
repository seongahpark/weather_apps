import streamlit as st
from security import save_keys_encrypted

def render_sidebar():
    st.sidebar.title("⚙️ 설정")
    api_key_owm = st.sidebar.text_input(
        "OpenWeatherMap API Key",
        value=st.session_state.get('owm_key', ''),
        type="password"
    )
    api_key_openai = st.sidebar.text_input(
        "OpenAI API Key",
        value=st.session_state.get('openai_key', ''),
        type="password"
    )

    # Save keys button
    if st.sidebar.button("🔐 보안 저장 (새로고침 시 유지)"):
        if api_key_owm or api_key_openai:
            save_keys_encrypted(api_key_owm, api_key_openai)
            st.session_state.owm_key = api_key_owm
            st.session_state.openai_key = api_key_openai
            st.sidebar.success("키가 암호화되어 저장되었습니다! ✓")
        else:
            st.sidebar.warning("저장할 키를 입력해주세요.")

    mode = st.sidebar.radio("추천 모드", ["규칙 기반 (기본)", "LLM 기반 (자연어 강화)"])
    st.sidebar.divider()
    st.sidebar.caption("v2.1 | Powered by OpenWeatherMap + GPT-4o-mini")
    
    return api_key_owm, api_key_openai, mode
