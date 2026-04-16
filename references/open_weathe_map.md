## OpenWeathermap API

https://openweathermap.org/

```python
import requests
import json

city = "Seoul"
api_key = "cae9c532caea0c33c93547a70879e455"
lang = 'kr'
units = 'metric'

url = f'https://api.openweathermap.org/data/2.5/weather?lat=37.411&lon=127.099397&appid={api_key}'
result = requests.get(url)
jo = json.loads(result.text)
jo
```


```python
import requests

# API 키와 날씨를 확인할 지역의 이름을 지정합니다.
api_key = "cae9c532caea0c33c93547a70879e455"
city = 'Bundang-gu, Seongnam-si, Gyeonggi-do'

# API 엔드포인트 URL을 생성합니다.
url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}'

# API를 호출하여 JSON 형식으로 날씨 정보를 가져옵니다.
response = requests.get(url)
data = response.json()

# 날씨 정보를 출력합니다.
weather = data['weather'][0]['description']
temp = data['main']['temp'] - 273.15  # K to C
humidity = data['main']['humidity']

print(f'현재 {city} 날씨: {weather}')
print(f'현재 {city} 기온: {temp:.1f}°C')
print(f'현재 {city} 습도: {humidity:.1f}%')
```


## 함수로 정리하기

```python
import requests
import json

api_key = "cae9c532caea0c33c93547a70879e455"

def weather_info(city):
    lang = 'kr'
    units = 'metric'

    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}'
    response = requests.get(url)
    data = response.json()

    weather = data['weather'][0]['description']
    temp = data['main']['temp'] - 273.15  # K to C
    humidity = data['main']['humidity']
    return weather, temp, humidity
```


## 날씨 어플리케이션

```python
from openai import OpenAI

client = OpenAI()

def recommand_clothes(weather, temp, humidity):
    prompt=f'''다음 날씨에 어울리는 옷차림을 추천해줘
    날씨: {weather}
    온도: {temp}
    습도: {humidity}
    '''

    messages = [
        {"role": "system", "content": "너는 친절한 어시스턴트야"},
        {"role": "user", "content": prompt}
    ]

    response = client.responses.create(
        model="gpt-4o-mini",
        input=messages
    )
    return response.output_text

```