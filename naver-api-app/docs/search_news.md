# 네이버 검색 > 뉴스 API 가이드

뉴스 검색 API는 네이버 검색 서비스에 색인된 최신 언론 기사 중 설정한 키워드와 일치하는 결과를 반환하는 RESTful API입니다. XML 또는 JSON 형식으로 제공됩니다.

---

## 1. 기본 정보

* **요청 URL**: 
  * **JSON 응답**: `https://openapi.naver.com/v1/search/news.json`
  * **XML 응답**: `https://openapi.naver.com/v1/search/news.xml`
* **HTTP 메서드**: `GET`
* **프로토콜**: `HTTPS`
* **인증 방식**: 비로그인 방식 (HTTP 헤더에 `X-Naver-Client-Id`, `X-Naver-Client-Secret` 전송)
* **일일 호출 한도**: 25,000회 (전체 검색 API 호출 횟수 합산 기준)

---

## 2. 요청 파라미터 (Query String)

| 파라미터 | 타입 | 필수 여부 | 기본값 | 설명 |
| :--- | :--- | :---: | :---: | :--- |
| `query` | string | Y | - | 검색어. UTF-8 형식의 URL 인코딩 적용 필수. |
| `display` | integer | N | 10 | 한 번에 출력할 검색 결과의 개수 (허용 범위: 1 ~ 100) |
| `start` | integer | N | 1 | 검색 시작 위치 (허용 범위: 1 ~ 1000) |
| `sort` | string | N | `sim` | 정렬 방식 옵션<br>- `sim`: 검색 결과의 정확도순 내림차순 정렬<br>- `date`: 뉴스 기사 제공/작성 시간 기준 내림차순 정렬 |

---

## 3. 응답 필드 (JSON 포맷 기준)

요청 성공 시 JSON 오브젝트 형식으로 반환되는 필드 사양입니다.

| 속성명 | 타입 | 설명 |
| :--- | :--- | :--- |
| `lastBuildDate` | string | 검색 결과가 생성된 시각 (RFC 822 포맷) |
| `total` | integer | 검색 키워드에 매칭되는 전체 뉴스 기사 개수 |
| `start` | integer | 검색 시작 번호 |
| `display` | integer | 출력 결과 건수 |
| `items` | array | 개별 뉴스 검색 결과 배열 |
| `items[].title` | string | 뉴스 기사 제목. 검색어 일치 부분은 `<b>` 태그 처리됩니다. |
| `items[].originallink` | string | 언론사 웹사이트 원본 기사 주소 URL |
| `items[].link` | string | 네이버 뉴스 기사 주소 URL. (네이버 뉴스에 미제공된 기사는 원본 기사 주소와 동일) |
| `items[].description` | string | 뉴스 기사 요약 정보. 검색어 일치 부분은 `<b>` 태그 처리됩니다. |
| `items[].pubDate` | string | 기사가 등록된 시각 (RFC 822 포맷. 예: `Mon, 26 Sep 2016 07:50:00 +0900`) |

---

## 4. 파이썬(Python) 호출 예시

```python
import urllib.request
import urllib.parse
import json

client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"

enc_text = urllib.parse.quote("주식 시장")
url = f"https://openapi.naver.com/v1/search/news.json?query={enc_text}&display=5"

request = urllib.request.Request(url)
request.add_header("X-Naver-Client-Id", client_id)
request.add_header("X-Naver-Client-Secret", client_secret)

try:
    response = urllib.request.urlopen(request)
    res_code = response.getcode()
    if res_code == 200:
        response_body = response.read().decode('utf-8')
        data = json.loads(response_body)
        print("총 검색 개수:", data['total'])
        for item in data['items']:
            print("기사제목:", item['title'])
            print("원본링크:", item['originallink'])
            print("작성시간:", item['pubDate'])
            print("-" * 30)
    else:
        print("Error Code:", res_code)
except Exception as e:
    print("API 호출 오류:", e)
```

---

## 5. 주요 오류 코드 (검색 API 공통)

| 에러 코드 (errorCode) | HTTP 상태 코드 | 메시지 / 설명 |
| :---: | :---: | :--- |
| **SE01** | 400 | Incorrect query request (잘못된 쿼리요청입니다.) |
| **SE02** | 400 | Invalid display value (출력 개수 범위 1~100 초과) |
| **SE03** | 400 | Invalid start value (시작 인덱스 범위 1~1000 초과) |
| **SE04** | 400 | Invalid sort value (부적절한 sort 파라미터 값 지정) |
| **SE06** | 400 | Malformed encoding (인코딩 형식 오류) |
| **SE05** | 404 | Invalid search api (엔드포인트 경로 오류) |
| **SE99** | 500 | System Error (네이버 내부 시스템 장애) |
