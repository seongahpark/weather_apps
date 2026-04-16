import streamlit as st
import os

def render_search():
    st.title("🌦️ 날씨 기반 오늘의 라이프 추천")
    st.markdown("날씨에 딱 맞는 **옷차림**, **준비물**, **점심**, **주말 활동**, **여행지**, **음료** 까지 한눈에!")

    st.markdown("🔍 **도시 이름을 영어로 입력하세요 (예: Seoul, Busan, Tokyo)**")
    
    input_col, btn_col = st.columns([3.2, 1])
    with input_col:
        city_input = st.text_input(
            "City Input",
            value=os.getenv("DEFAULT_CITY", "Seoul"),
            label_visibility="collapsed"
        )
    with btn_col:
        search_btn = st.button("날씨 가져오기", use_container_width=True)
        
    return city_input, search_btn
