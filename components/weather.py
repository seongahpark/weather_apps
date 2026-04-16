import streamlit as st

def render_weather_summary(weather):
    st.divider()
    w_col1, w_col2, w_col3, w_col4 = st.columns(4)
    with w_col1:
        st.image(f"http://openweathermap.org/img/wn/{weather.icon}@2x.png")
        st.metric("현재 기온", f"{weather.temp_c}°C", f"체감 {weather.feels_like_c}°C")
    with w_col2:
        st.metric("습도", f"{weather.humidity}%")
    with w_col3:
        st.metric("풍속", f"{weather.wind_speed} m/s")
    with w_col4:
        st.subheader(weather.description)
        st.caption(f"관측 시간: {weather.observed_at.strftime('%Y-%m-%d %H:%M:%S')}")
