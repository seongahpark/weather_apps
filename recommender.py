from dataclasses import dataclass, field
from typing import List, Optional
from weather_utils import WeatherObservation
from openai import OpenAI
import os
import json


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------

@dataclass
class Recommendation:
    # --- Existing ---
    outfit: List[str] = field(default_factory=list)
    outfit_rationale: str = ""
    prep: List[str] = field(default_factory=list)
    prep_rationale: str = ""
    lunch: List[str] = field(default_factory=list)
    lunch_rationale: str = ""

    # --- New: Weekend Activity ---
    activity: List[str] = field(default_factory=list)
    activity_rationale: str = ""

    # --- New: Local Attractions (rule-based type + LLM-generated POIs) ---
    travel_type: str = ""          # e.g. "Outdoor Nature Park" — determined by rules
    travel: List[str] = field(default_factory=list)   # specific POI names from LLM
    travel_rationale: str = ""

    # --- New: Beverage & Dessert ---
    beverage: List[str] = field(default_factory=list)
    beverage_rationale: str = ""

    # --- New: Transportation ---
    transport: List[str] = field(default_factory=list)
    transport_rationale: str = ""

    # --- Derived flag ---
    umbrella_needed: bool = False


# ---------------------------------------------------------------------------
# Internal Rule Helpers
# ---------------------------------------------------------------------------

def _is_rainy(condition: str, description: str) -> bool:
    rain_words = ["rain", "drizzle", "thunderstorm", "비", "소나기", "뇌우"]
    return any(w in condition or w in description for w in rain_words)


def _is_snowy(condition: str, description: str) -> bool:
    return "snow" in condition or "눈" in condition or "snow" in description


def _recommend_activity(temp: float, condition: str, description: str, humidity: int) -> dict:
    """Return activity list and rationale based on temp, rain, and humidity."""
    cond = condition.lower()
    desc = description.lower()

    if _is_rainy(cond, desc) or _is_snowy(cond, desc):
        items = ["카페에서 독서·작업", "영화관 관람", "실내 클라이밍", "보드게임 카페", "미술관·박물관"]
        rationale = "비 또는 눈이 예보되어 실외 활동은 권장하지 않습니다. 편안한 실내 활동을 즐겨보세요."
    elif temp >= 28 or humidity >= 80:
        items = ["수영장·워터파크", "쇼핑몰 탐방", "박물관·과학관", "실내 볼링장", "에어컨 카페에서 휴식"]
        rationale = f"기온 {temp}°C / 습도 {humidity}%로 매우 덥고 습합니다. 시원한 실내 공간을 추천합니다."
    elif temp < 5:
        items = ["찜질방·스파", "북카페", "미술관·갤러리", "쇼핑몰", "실내 수영장"]
        rationale = f"기온 {temp}°C로 매우 춥습니다. 따뜻한 실내에서 여유로운 시간을 보내세요."
    elif 17 <= temp < 28:
        items = ["공원 산책·피크닉", "자전거 라이딩", "등산·하이킹", "야외 카페", "한강 공원"]
        rationale = f"기온 {temp}°C, 야외 활동 최적 조건입니다. 자연 속에서 활기찬 하루를 즐겨보세요!"
    else:  # 5 <= temp < 17
        items = ["가벼운 도심 산책", "카페 투어", "독서실·스터디카페", "미술관", "재래시장 탐방"]
        rationale = f"기온 {temp}°C로 다소 쌀쌀합니다. 가볍게 움직이되 따뜻한 곳을 중간중간 활용하세요."

    return {"items": items, "rationale": rationale}


def get_local_attraction_type(temp_c: float, condition: str, description: str) -> tuple[str, str]:
    """
    Rule-based function: derives the *type* of local attraction to visit
    based on weather parameters. Returns (attraction_type_ko, rationale_ko).

    attraction_type_ko is a Korean descriptor passed to the LLM so it can
    resolve actual venue names for any city worldwide, and also displayed to the user.
    """
    cond = condition.lower()
    desc = description.lower()

    if _is_rainy(cond, desc) or _is_snowy(cond, desc):
        return (
            "실내 박물관 및 미술관",
            "비 또는 눈이 내려 실외 방문은 권장하지 않습니다. 실내 박물관이나 미술관에서 문화생활을 즐겨보세요.",
        )
    elif temp_c >= 33:
        return (
            "대형 복합 쇼핑몰 및 아쿠아리움",
            f"기온 {temp_c}°C의 폭염입니다. 에어컨이 잘 가동되는 대형 쇼핑몰이나 실내 아쿠아리움을 추천합니다.",
        )
    elif temp_c >= 25:
        return (
            "수변 공원 및 해변",
            f"기온 {temp_c}°C의 더운 날씨입니다. 강변 공원이나 물가처럼 시원한 야외를 즐겨보세요.",
        )
    elif 15 <= temp_c < 25:
        return (
            "야외 역사 유적지 및 문화 명소",
            f"기온 {temp_c}°C의 쾌적한 날씨입니다. 유적지나 문화 명소를 여유롭게 탐방하기에 최적인 날입니다.",
        )
    elif 5 <= temp_c < 15:
        return (
            "자연 경관이 아름다운 공원 및 산책로",
            f"기온 {temp_c}°C의 선선한 날씨입니다. 자연 공원이나 산책로를 거닐며 도심을 벗어나 보세요.",
        )
    else:  # temp_c < 5
        return (
            "실내 문화 공간 및 핫플레이스 카페, 온천",
            f"기온 {temp_c}°C의 추운 날씨입니다. 따뜻한 실내 문화시설이나 온천을 추천합니다.",
        )


def get_local_pois(city: str, attraction_type: str, weather_summary: str, api_key: str) -> dict:
    """
    Dedicated LLM call: given a city and the rule-determined attraction type,
    returns 3 specific, real-world POI names that exist in that city,
    plus a 1-sentence Korean reason tied to the current weather.

    Uses response_format=json_object for reliable parsing and temperature=0.3
    to reduce hallucination risk on factual venue names.
    """
    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You are a local travel expert with encyclopedic, up-to-date knowledge of "
        "tourist attractions and points of interest worldwide.\n\n"
        "Rules:\n"
        "1. Identify if the 'City' is in South Korea (Republic of Korea).\n"
        "2. If the city is in South Korea, return 'is_korea': true. Otherwise, false.\n"
        "3. Provide exactly 3 real attractions for the city matching the 'Attraction Type'.\n"
        "4. Language Format:\n"
        "   - If is_korea is true: Return the common Korean name in BOTH 'name_primary' and 'name_secondary'.\n"
        "   - If is_korea is false: Return a well-known English name in 'name_primary', and the native local language script (e.g., Japanese Kanji, French, etc.) in 'name_secondary'.\n"
        "5. Respond ONLY in valid JSON using this exact schema:\n"
        '{\n'
        '  "is_korea": boolean,\n'
        '  "spots": [\n'
        '    {"name_primary": "...", "name_secondary": "..."},\n'
        '    {"name_primary": "...", "name_secondary": "..."},\n'
        '    {"name_primary": "...", "name_secondary": "..."}\n'
        '  ],\n'
        '  "reason": "One sentence in Korean explaining why these suit the weather"\n'
        '}\n'
    )

    user_prompt = (
        f"City: {city}\n"
        f"Attraction Type: {attraction_type}\n"
        f"Current Weather: {weather_summary}\n\n"
        f"Return 3 real, well-known attractions in {city} matching the criteria."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,  # factual accuracy over creativity
        )
        data = json.loads(response.choices[0].message.content)
        return {
            "is_korea": data.get("is_korea", False),
            "spots": data.get("spots", []),
            "reason": data.get("reason", ""),
        }
    except Exception as e:
        return {"spots": [], "reason": f"명소 조회 중 오류가 발생했습니다: {e}"}


def _recommend_beverage(temp: float, humidity: int) -> dict:
    """Recommend café drinks and desserts based on temp and humidity."""
    if temp >= 28 and humidity >= 70:
        items = ["아이스 아메리카노", "콜드브루", "냉 말차 라떼", "팥빙수", "수박 주스"]
        rationale = f"기온 {temp}°C + 습도 {humidity}%로 매우 덥고 후텁지근합니다. 시원하고 청량한 음료·빙과류를 추천합니다."
    elif temp >= 28:
        items = ["아이스 라떼", "젤라또", "스무디 (망고·딸기)", "에이드 (레몬·자몽)", "셔벗"]
        rationale = f"기온 {temp}°C의 더운 날씨입니다. 달달하고 시원한 음료가 기분을 살려줄 거예요."
    elif 20 <= temp < 28:
        items = ["아이스 아메리카노", "아이스 라떼", "과일 에이드", "아이스크림", "크로플"]
        rationale = f"기온 {temp}°C의 따뜻한 날씨입니다. 아이스 음료 한 잔으로 활력을 더해보세요."
    elif 10 <= temp < 20:
        items = ["따뜻한 카페 라떼", "바닐라 라떼", "캐모마일 티", "크로플", "마들렌"]
        rationale = f"기온 {temp}°C로 선선합니다. 따뜻한 음료와 고소한 디저트로 힐링하세요."
    else:  # temp < 10
        items = ["핫 초코", "따뜻한 아메리카노", "생강차·유자차", "호두파이", "붕어빵"]
        rationale = f"기온 {temp}°C의 추운 날씨입니다. 따뜻한 음료 한 잔이 몸과 마음을 녹여줄 거예요."

    return {"items": items, "rationale": rationale}


def _recommend_transport(wind_speed: float, condition: str, description: str, temp: float) -> dict:
    """Recommend transportation based on wind, rain, and temperature."""
    cond = condition.lower()
    desc = description.lower()

    if _is_rainy(cond, desc) or _is_snowy(cond, desc):
        items = ["지하철 (가장 안전)", "버스", "택시·카풀"]
        rationale = "비 또는 눈이 내립니다. 대중교통을 적극 이용하고 자전거·킥보드는 피해주세요."
        umbrella = True
    elif wind_speed >= 10:
        items = ["지하철", "버스", "자가용"]
        rationale = f"풍속 {wind_speed}m/s로 매우 강한 바람입니다. 자전거·오토바이는 위험할 수 있으니 대중교통을 권장합니다."
        umbrella = False
    elif wind_speed >= 5 and temp < 5:
        items = ["지하철·버스", "자가용 (방한 필수)", "핫팩 챙기기"]
        rationale = f"풍속 {wind_speed}m/s + 기온 {temp}°C로 체감온도가 매우 낮습니다. 노출을 최소화하세요."
        umbrella = False
    elif 5 <= wind_speed < 10:
        items = ["자전거 (바람 주의)", "도보", "버스·지하철"]
        rationale = f"풍속 {wind_speed}m/s의 적당한 바람입니다. 자전거도 가능하지만 맞바람 구간은 주의하세요."
        umbrella = False
    else:  # ideal
        items = ["도보", "자전거·전동킥보드", "버스·지하철"]
        rationale = f"풍속 {wind_speed}m/s의 쾌적한 날씨입니다. 도보나 자전거로 가볍게 이동해보세요."
        umbrella = False

    return {"items": items, "rationale": rationale, "umbrella": umbrella}


# ---------------------------------------------------------------------------
# Main Rule-based Engine
# ---------------------------------------------------------------------------

def get_rule_based_recommendation(weather: WeatherObservation) -> Recommendation:
    rec = Recommendation()

    temp = weather.temp_c
    humidity = weather.humidity
    wind_speed = weather.wind_speed
    condition = weather.condition.lower()
    description = weather.description.lower()

    # ── Outfit (existing logic) ──────────────────────────────────────────────
    if temp >= 28:
        rec.outfit = ["민소매", "반팔", "반바지", "린넨 소재 옷"]
        rec.outfit_rationale = "매우 더운 날씨입니다. 통풍이 잘 되는 시원한 소재의 옷을 추천합니다."
        rec.lunch = ["냉면", "콩국수", "모밀", "아이스크림", "샐러드"]
        rec.lunch_rationale = "무더운 날씨에 열을 식혀줄 시원한 메뉴를 추천합니다."
    elif 23 <= temp < 28:
        rec.outfit = ["반팔", "얇은 셔츠", "면바지", "반바지"]
        rec.outfit_rationale = "활동하기 좋은 날씨입니다. 가벼운 차림을 추천합니다."
        rec.lunch = ["비빔국수", "샌드위치", "덮밥", "스시"]
        rec.lunch_rationale = "산뜻하게 즐길 수 있는 메뉴를 추천합니다."
    elif 17 <= temp < 23:
        rec.outfit = ["긴팔 티셔츠", "가디건", "후드티", "면바지", "청바지"]
        rec.outfit_rationale = "약간 선선할 수 있는 날씨입니다. 얇은 겉옷을 챙기세요."
        rec.lunch = ["파스타", "돈가스", "비빔밥", "백반"]
        rec.lunch_rationale = "기분 좋게 배를 채울 수 있는 대중적인 메뉴를 추천합니다."
    elif 10 <= temp < 17:
        rec.outfit = ["자켓", "트렌치코트", "셔츠 레이어드", "청바지"]
        rec.outfit_rationale = "쌀쌀한 날씨입니다. 자켓이나 얇은 코트로 체온을 유지하세요."
        rec.lunch = ["칼국수", "찌개류", "육개장", "돈부리"]
        rec.lunch_rationale = "체온을 올려줄 따뜻한 국물이 있는 음식을 추천합니다."
    elif 0 <= temp < 10:
        rec.outfit = ["코트", "가벼운 패딩", "니트", "청바지", "스타킹"]
        rec.outfit_rationale = "추운 날씨입니다. 코디에 보온성이 있는 코트나 패딩을 포함하세요."
        rec.lunch = ["국밥", "부대찌개", "수제비", "짬뽕"]
        rec.lunch_rationale = "속을 따뜻하게 달래줄 뜨끈한 국물 요리를 추천합니다."
    else:  # temp < 0
        rec.outfit = ["롱패딩", "두꺼운 코트", "내복", "기모 바지", "목도리", "장갑"]
        rec.outfit_rationale = "혹한의 날씨입니다. 방한에 각별히 신경 쓰세요."
        rec.lunch = ["만두전골", "곰탕", "순대국", "어묵탕"]
        rec.lunch_rationale = "추위를 녹여줄 뜨거운 전골이나 탕 요리를 추천합니다."

    # ── Wind (outfit add-on) ─────────────────────────────────────────────────
    if wind_speed > 5:
        rec.outfit.append("바람막이/방풍 아우터")
        rec.outfit_rationale += " 바람이 강하게 불어 체감 온도가 낮아질 수 있으니 바람막이를 추천합니다."

    # ── Prep (enhanced) ─────────────────────────────────────────────────────
    if _is_rainy(condition, description):
        rec.prep.extend(["☂️ 우산", "방수 신발/장화"])
        rec.prep_rationale += "비 예보가 있습니다. 우산을 꼭 챙기시고 비에 젖지 않는 신발을 신으세요. "
        rec.umbrella_needed = True
    elif _is_snowy(condition, description):
        rec.prep.extend(["☂️ 우산", "미끄럼 방지 신발", "장갑"])
        rec.prep_rationale += "눈 예보가 있습니다. 길이 미끄러울 수 있으니 주의하시고 체온 유지에 신경 쓰세요. "
        rec.umbrella_needed = True

    if humidity > 80:
        rec.prep.append("통풍 소재 의류")
        rec.prep_rationale += "습도가 높아 불쾌지수가 높을 수 있습니다. 통풍이 잘 되는 옷을 입으세요."
    elif humidity < 30:
        rec.prep.extend(["💋 립밤", "핸드크림"])
        rec.prep_rationale += "공기가 건조하므로 보습에 신경 쓰세요."

    if not rec.prep:
        rec.prep = ["✅ 특별한 준비물 없음"]
        rec.prep_rationale = "평소대로 준비하셔도 좋습니다."

    # ── Activity (new) ───────────────────────────────────────────────────────
    act = _recommend_activity(temp, condition, description, humidity)
    rec.activity = act["items"]
    rec.activity_rationale = act["rationale"]

    # ── Local Attractions (rule determines type; LLM resolves specific POIs) ──
    attraction_type, travel_rationale = get_local_attraction_type(temp, condition, description)
    rec.travel_type = attraction_type
    rec.travel_rationale = travel_rationale
    rec.travel = []  # populated on-demand by get_local_pois() in the UI layer

    # ── Beverage (new) ───────────────────────────────────────────────────────
    bev = _recommend_beverage(temp, humidity)
    rec.beverage = bev["items"]
    rec.beverage_rationale = bev["rationale"]

    # ── Transport (new) ──────────────────────────────────────────────────────
    trp = _recommend_transport(wind_speed, condition, description, temp)
    rec.transport = trp["items"]
    rec.transport_rationale = trp["rationale"]
    if trp["umbrella"]:
        rec.umbrella_needed = True

    return rec


# ---------------------------------------------------------------------------
# LLM-based Enrichment
# ---------------------------------------------------------------------------

def get_llm_recommendation(weather: WeatherObservation, base_rec: Recommendation, api_key: str) -> str:
    client = OpenAI(api_key=api_key)

    system_prompt = (
        "너는 날씨 기반 라이프스타일 큐레이터야. "
        "아래에 주어진 [날씨 데이터]와 [규칙 기반 추천 가이드]를 참고해서, "
        "각 섹션별로 친절하고 세련된 자연어 문장을 생성해줘. "
        "반드시 아래 7개 섹션을 모두 포함하고, "
        "각 섹션은 적절한 이모지로 시작하는 소제목 + 2~3문장의 자연스러운 한국어 추천으로 구성해. "
        "날씨 수치(기온, 풍속 등)를 직접 언급해서 신뢰감을 줘. "
        "각 섹션 사이는 한 줄 띄워서 구분해줘.\n\n"
        "섹션 순서: "
        "1) 👕 오늘의 옷차림  "
        "2) 🎒 준비물 & 교통수단  "
        "3) 🍱 점심 메뉴  "
        "4) 🎯 주말 활동 추천  "
        "5) ✈️ 여행지 추천  "
        "6) ☕ 음료 & 디저트  "
        "7) 🚇 교통수단 추천"
    )

    user_prompt = f"""
[날씨 데이터]
- 지역: {weather.city}
- 기온: {weather.temp_c}°C (체감: {weather.feels_like_c}°C)
- 습도: {weather.humidity}%
- 풍속: {weather.wind_speed} m/s
- 날씨 상태: {weather.description}

[규칙 기반 추천 가이드]
- 👕 옷차림: {', '.join(base_rec.outfit)}
  근거: {base_rec.outfit_rationale}
- 🎒 준비물: {', '.join(base_rec.prep)}
  근거: {base_rec.prep_rationale}
- 🍱 점심: {', '.join(base_rec.lunch)}
  근거: {base_rec.lunch_rationale}
- 🎯 주말 활동: {', '.join(base_rec.activity)}
  근거: {base_rec.activity_rationale}
- ✈️ 현지 추천 명소 유형: {base_rec.travel_type}
  근거: {base_rec.travel_rationale}
  (구체적인 명소 이름은 별도 LLM 호출로 제공됩니다)
- ☕ 음료·디저트: {', '.join(base_rec.beverage)}
  근거: {base_rec.beverage_rationale}
- 🚇 교통수단: {', '.join(base_rec.transport)}
  근거: {base_rec.transport_rationale}

위 가이드를 바탕으로 7개 섹션을 자연스럽고 따뜻한 한국어로 작성해줘.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ LLM 추천 생성 중 오류가 발생했습니다: {e}"
