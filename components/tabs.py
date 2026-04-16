import streamlit as st
import streamlit.components.v1 as components
from recommender import get_local_pois

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_local_pois(city: str, attraction_type: str, weather_summary: str, api_key: str) -> dict:
    """Thin cached wrapper around get_local_pois so repeated renders don't re-call the LLM."""
    return get_local_pois(city, attraction_type, weather_summary, api_key)

def render_tabs(weather, base_rec, api_key_openai):
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👕 기본 추천",
        "🎯 주말 활동",
        "✈️ 여행지",
        "☕ 음료 & 디저트",
        "🚇 교통수단"
    ])

    # ── Tab 1: 기본 추천 (Outfit / Prep / Lunch) ─────────────────
    with tab1:
        r_col1, r_col2, r_col3 = st.columns(3)

        with r_col1:
            st.info("### 👕 옷차림 추천")
            for item in base_rec.outfit:
                st.markdown(f"- {item}")
            with st.expander("추천 근거"):
                st.write(base_rec.outfit_rationale)

        with r_col2:
            # Umbrella badge at the top of prep column
            if base_rec.umbrella_needed:
                st.markdown(
                    '<div class="umbrella-alert">☂️ 오늘은 우산이 필요합니다!</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div class="no-umbrella-alert">☀️ 오늘은 우산이 필요 없어요</div>',
                    unsafe_allow_html=True
                )
            st.success("### 🎒 대비 / 준비물")
            for item in base_rec.prep:
                st.markdown(f"- {item}")
            with st.expander("추천 근거"):
                st.write(base_rec.prep_rationale)

        with r_col3:
            st.warning("### 🍱 점심 메뉴")
            for item in base_rec.lunch:
                st.markdown(f"- {item}")
            with st.expander("추천 근거"):
                st.write(base_rec.lunch_rationale)

    # ── Tab 2: 주말 활동 ──────────────────────────────────────────
    with tab2:
        st.subheader("🎯 주말 활동 추천")
        st.caption(base_rec.activity_rationale)
        act_cols = st.columns(min(len(base_rec.activity), 3))
        for i, item in enumerate(base_rec.activity):
            with act_cols[i % 3]:
                st.markdown(
                    f'<div class="rec-card"><h4>{"🏠" if "실내" in base_rec.activity_rationale or "카페" in item else "🌿"} {item}</h4></div>',
                    unsafe_allow_html=True
                )
        with st.expander("추천 근거 자세히 보기"):
            st.write(base_rec.activity_rationale)

    # ── Tab 3: 현지 관광명소 ─────────────────────────────────────
    with tab3:
        st.subheader(f"✈️ {weather.city} 현지 관광명소")

        # ① Rule-based: always show the weather-derived attraction type
        st.markdown(
            f"""
            <div class="rec-card">
              <p style="color:#94a3b8;margin:0;font-size:0.8rem">현재 날씨를 바탕으로 추천되는 명소 유형</p>
              <h4 style="color:#e2e8f0;margin:0.3rem 0">🏛️ {base_rec.travel_type}</h4>
              <p style="color:#cbd5e1;margin:0;font-size:0.9rem">{base_rec.travel_rationale}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # ② LLM: resolve 3 specific, real POIs in the user's exact city
        if api_key_openai:
            weather_summary = (
                f"{weather.description}, {weather.temp_c}°C, "
                f"humidity {weather.humidity}%, wind {weather.wind_speed} m/s"
            )
            with st.spinner(f"{weather.city}의 실제 명소를 검색하는 중..."):
                poi_result = fetch_local_pois(
                    weather.city,
                    base_rec.travel_type,
                    weather_summary,
                    api_key_openai,
                )

            spots = poi_result.get("spots", [])
            is_korea = poi_result.get("is_korea", False)
            reason = poi_result.get("reason", "")

            if spots:
                st.markdown("##### 📍 오늘 가볼 만한 명소 3곳")
                poi_cols = st.columns(3)
                
                for i, spot in enumerate(spots[:3]):
                    if isinstance(spot, str):
                        p_name = spot
                        s_name = ""
                    else:
                        p_name = spot.get("name_primary", "")
                        s_name = spot.get("name_secondary", "")
                    
                    # Use p_name (first line) text for copying, as requested
                    copy_text = p_name
                    
                    with poi_cols[i]:
                        # Create individual card with copy button inside
                        card_id = f"spot-{i}"
                        
                        display_html = f"""
                        <div class="rec-card" id="{card_id}">
                            <button class="copy-btn" data-copy="{copy_text}" title="복사">📋</button>
                            <div style="margin-top: 5px;">
                        """
                        
                        if is_korea:
                            # Korea: Just show primary name in Korean
                            display_html += f'<p style="color:#e2e8f0;font-size:1.1rem;font-weight:600;margin:0">{p_name}</p>'
                        else:
                            # Abroad: English (Big) + Local (Small)
                            display_html += f'<p style="color:#e2e8f0;font-size:1.1rem;font-weight:600;margin:0">{p_name}</p><p style="color:#94a3b8;font-size:0.85rem;margin:0.2rem 0 0 0">{s_name}</p>'
                        
                        display_html += "</div></div>"
                        st.markdown(display_html, unsafe_allow_html=True)

                # Inject the JS helper via components.html so it bypasses markdown sanitisation reliably
                components.html("""
                    <script>
                        const parentDoc = window.parent.document;
                        
                        function showToast(text) {
                            const existing = parentDoc.getElementById('custom-toast');
                            if (existing) parentDoc.body.removeChild(existing);
                            
                            const toast = parentDoc.createElement('div');
                            toast.id = 'custom-toast';
                            toast.textContent = '✅ "' + text + '" 복사되었습니다!';
                            toast.style.position = 'fixed';
                            toast.style.bottom = '24px';
                            toast.style.right = '24px';
                            toast.style.backgroundColor = 'rgba(16, 185, 129, 0.9)';
                            toast.style.color = 'white';
                            toast.style.padding = '12px 24px';
                            toast.style.borderRadius = '8px';
                            toast.style.fontSize = '0.9rem';
                            toast.style.fontWeight = '600';
                            toast.style.boxShadow = '0 10px 15px -3px rgba(0,0,0,0.1)';
                            toast.style.zIndex = '99999';
                            toast.style.opacity = '0';
                            toast.style.transform = 'translateY(20px)';
                            toast.style.transition = 'all 0.3s ease';
                            
                            parentDoc.body.appendChild(toast);
                            
                            setTimeout(() => {
                                toast.style.opacity = '1';
                                toast.style.transform = 'translateY(0)';
                            }, 10);
                            
                            setTimeout(() => {
                                toast.style.opacity = '0';
                                toast.style.transform = 'translateY(20px)';
                                setTimeout(() => {
                                    if (toast.parentNode) toast.parentNode.removeChild(toast);
                                }, 300);
                            }, 2000);
                        }

                        setInterval(() => {
                            const btns = parentDoc.querySelectorAll('.copy-btn:not(.bound)');
                            btns.forEach(btn => {
                                btn.classList.add('bound');
                                btn.addEventListener('click', function(e) {
                                    e.preventDefault();
                                    const text = this.getAttribute('data-copy');
                                    
                                    const ta = parentDoc.createElement('textarea');
                                    ta.value = text;
                                    ta.style.position = 'fixed';
                                    ta.style.opacity = '0';
                                    parentDoc.body.appendChild(ta);
                                    ta.select();
                                    try {
                                        parentDoc.execCommand('copy');
                                        const displayTxt = text.length > 15 ? text.substring(0, 15) + '...' : text;
                                        showToast(displayTxt);
                                    } catch (err) {
                                        console.error('Fallback copy failed', err);
                                    }
                                    parentDoc.body.removeChild(ta);
                                });
                            });
                        }, 1000);
                    </script>
                """, height=0, width=0)

                if reason:
                    st.caption(f"💬 {reason}")
            else:
                st.info("명소 정보를 가져오는 중 오류가 발생했습니다. 다시 시도해주세요.")
        else:
            st.info(
                "🔑 OpenAI API 키를 사이드바에 입력하면 "
                f"{weather.city}의 실제 명소 3곳을 구체적으로 추천해 드립니다."
            )

    # ── Tab 4: 음료 & 디저트 ──────────────────────────────────────
    with tab4:
        st.subheader("☕ 오늘의 음료 & 디저트")
        st.caption(base_rec.beverage_rationale)
        bev_cols = st.columns(min(len(base_rec.beverage), 5))
        icons = ["☕", "🧊", "🍵", "🍰", "🧃"]
        for i, item in enumerate(base_rec.beverage):
            with bev_cols[i % 5]:
                icon = icons[i % len(icons)]
                st.markdown(
                    f'<div class="rec-card" style="text-align:center"><h4>{icon}</h4><p style="color:#cbd5e1;margin:0">{item}</p></div>',
                    unsafe_allow_html=True
                )
        with st.expander("추천 근거 자세히 보기"):
            st.write(base_rec.beverage_rationale)

    # ── Tab 5: 교통수단 ───────────────────────────────────────────
    with tab5:
        st.subheader("🚇 오늘의 교통수단 추천")

        # Umbrella status badge
        if base_rec.umbrella_needed:
            st.error("☂️ 우산을 챙기세요! 오늘은 우산이 필요한 날씨입니다.")
        else:
            st.success("☀️ 우산 없이도 괜찮은 날씨입니다.")

        st.caption(base_rec.transport_rationale)
        trp_cols = st.columns(min(len(base_rec.transport), 3))
        transport_icons = {"지하철": "🚇", "버스": "🚌", "자전거": "🚴", "도보": "🚶",
                           "킥보드": "🛴", "택시": "🚖", "자가용": "🚗", "핫팩": "🔥"}
        for i, item in enumerate(base_rec.transport):
            icon = next((v for k, v in transport_icons.items() if k in item), "🚍")
            with trp_cols[i % 3]:
                st.markdown(
                    f'<div class="rec-card" style="text-align:center"><h4>{icon}</h4><p style="color:#cbd5e1;margin:0">{item}</p></div>',
                    unsafe_allow_html=True
                )
        with st.expander("추천 근거 자세히 보기"):
            st.write(base_rec.transport_rationale)
