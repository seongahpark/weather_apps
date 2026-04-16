# 날씨 기반 라이프스타일 추천 서비스

실시간 날씨 정보를 기반으로 오늘의 **옷차림**, **준비물**, **점심 메뉴**를 추천해주는 Streamlit 웹 서비스입니다.

## 주요 기능
- **실시간 날씨 정보**: OpenWeatherMap API를 사용하여 현재 날씨 정보(기온, 습도, 풍속 등) 제공
- **규칙 기반 추천**: 기온대별/날씨 상태별 최적의 옷차림 및 메뉴 추천
- **LLM 기반 추천**: OpenAI GPT-4o-mini를 활용하여 친절하고 자연스러운 추천 문백 생성
- **사용자 맞춤 UI**: Streamlit을 활용한 직관적인 대시보드 인터페이스

## 설치 및 실행 방법

### 1. 환경 설정
`.env.template` 파일을 복사하여 `.env` 파일을 생성하고 API 키를 입력합니다.
```bash
cp .env.template .env
```
또는 앱 실행 후 사이드바에서 직접 API 키를 입력할 수도 있습니다.

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 앱 실행
```bash
streamlit run app.py
```

## 기술 스택
- **Frontend/Backend**: Streamlit
- **API**: OpenWeatherMap API, OpenAI API
- **Language**: Python 3.x
