# 네이버 데이터랩 - 통합 검색어 트렌드 API 가이드

통합 검색어 트렌드 API는 네이버 데이터랩의 검색어 트렌드 서비스를 제공하는 RESTful API입니다. 설정한 주제어 및 하위 검색어 묶음에 대한 네이버 통합검색 내 검색 추이 데이터를 상댓값(최대 100) 비율로 반환합니다.

---

## 1. 기본 정보

* **요청 URL**: `https://openapi.naver.com/v1/datalab/search`
* **HTTP 메서드**: `POST`
* **프로토콜**: `HTTPS`
* **인증 방식**: 비로그인 방식 (HTTP 헤더에 `X-Naver-Client-Id`, `X-Naver-Client-Secret` 전송)
* **일일 호출 한도**: 1,000회 (클라이언트 ID 기준)

---

## 2. 요청 파라미터 (JSON 포맷)

요청 본문(Body)에 JSON 형식의 데이터를 실어 전송해야 합니다.

| 파라미터 | 타입 | 필수 여부 | 설명 |
| :--- | :--- | :---: | :--- |
| `startDate` | string | Y | 조회 기간의 시작 날짜 (`yyyy-mm-dd`). 2016년 1월 1일부터 조회 가능합니다. |
| `endDate` | string | Y | 조회 기간의 종료 날짜 (`yyyy-mm-dd`). |
| `timeUnit` | string | Y | 구간 단위 설정 (`date`: 일간, `week`: 주간, `month`: 월간) |
| `keywordGroups` | array | Y | 주제어와 주제어에 매핑할 하위 검색어 목록 쌍의 배열 (최대 5개 그룹 등록 가능) |
| `keywordGroups[].groupName` | string | Y | 주제어 명칭. 그룹을 대표하는 이름입니다. |
| `keywordGroups[].keywords` | array(string) | Y | 주제어에 속하는 하위 검색어 배열 (그룹당 최대 20개 검색어 설정 가능) |
| `device` | string | N | 검색 기기 필터 (`설정 안 함`: 전체 기기, `pc`: PC 검색량, `mo`: 모바일 검색량) |
| `gender` | string | N | 검색자 성별 필터 (`설정 안 함`: 전체, `m`: 남성, `f`: 여성) |
| `ages` | array(string) | N | 검색자 연령대 필터 배열. (`설정 안 함`: 전체 연령) 아래 코드를 배열로 지정합니다.<br>`1`: 0~12세, `2`: 13~18세, `3`: 19~24세, `4`: 25~29세, `5`: 30~34세, `6`: 35~39세, `7`: 40~44세, `8`: 45~49세, `9`: 50~54세, `10`: 55~59세, `11`: 60세 이상 |

---

## 3. 응답 필드 (JSON 포맷)

요청이 성공하면 결과 데이터를 JSON 형식으로 반환합니다.

| 속성명 | 타입 | 설명 |
| :--- | :--- | :--- |
| `startDate` | string | 조회 시작 날짜 (`yyyy-mm-dd`) |
| `endDate` | string | 조회 종료 날짜 (`yyyy-mm-dd`) |
| `timeUnit` | string | 결과 구간 단위 (`date`, `week`, `month`) |
| `results` | array | 주제어별 결과 목록 |
| `results[].title` | string | 설정했던 주제어 명칭 (`groupName`) |
| `results[].keywords` | array(string) | 설정했던 검색어 배열 |
| `results[].data` | array | 날짜별 상대적 검색 비율 데이터 |
| `results[].data[].period` | string | 해당 구간의 시작 날짜 (`yyyy-mm-dd`) |
| `results[].data[].ratio` | number | 검색량의 상대적 비율. 조회 기간 내 전체 그룹 중 최고 일일 검색량을 100으로 기준 삼아 환산한 상댓값입니다. |

---

## 4. 파이썬(Python) 호출 예시

```python
import json
import urllib.request

client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"
url = "https://openapi.naver.com/v1/datalab/search"

# 요청 파라미터 구성
body = {
    "startDate": "2023-01-01",
    "endDate": "2023-06-30",
    "timeUnit": "month",
    "keywordGroups": [
        {
            "groupName": "스마트폰",
            "keywords": ["아이폰", "갤럭시", "iphone", "galaxy"]
        },
        {
            "groupName": "노트북",
            "keywords": ["맥북", "그램", "macbook", "gram"]
        }
    ],
    "device": "pc",
    "gender": "f"
}

# 파라미터 인코딩
json_data = json.dumps(body).encode("utf-8")

request = urllib.request.Request(url)
request.add_header("X-Naver-Client-Id", client_id)
request.add_header("X-Naver-Client-Secret", client_secret)
request.add_header("Content-Type", "application/json")

try:
    response = urllib.request.urlopen(request, data=json_data)
    res_code = response.getcode()
    if res_code == 200:
        response_body = response.read().decode('utf-8')
        print(json.loads(response_body))
    else:
        print("Error Code:", res_code)
except Exception as e:
    print("API 호출 오류:", e)
```

---

## 5. 주요 오류 코드

| HTTP 상태 코드 | 에러 메시지 | 설명 / 원인 |
| :---: | :--- | :--- |
| **400** | 잘못된 요청 (Bad Request) | 파라미터 포맷(날짜 형식 등)이나 필수 속성이 누락되었는지 확인합니다. |
| **403** | API 권한 없음 (Forbidden) | 개발자 센터 애플리케이션 설정에서 `데이터랩 (검색어트렌드)` API 권한을 부여받았는지 체크합니다. |
| **500** | 서버 내부 오류 (Internal Server Error) | 네이버 서버 장애입니다. 오류가 지속되면 네이버 개발자 포럼에 문의합니다. |
