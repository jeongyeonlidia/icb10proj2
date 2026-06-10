# 네이버 검색 > 카페글 API 가이드

카페글 검색 API는 네이버 카페의 공개 게시판 글 중 설정한 키워드와 일치하는 검색 결과를 반환하는 RESTful API입니다. XML 또는 JSON 형식으로 제공됩니다.

---

## 1. 기본 정보

* **요청 URL**: 
  * **JSON 응답**: `https://openapi.naver.com/v1/search/cafearticle.json`
  * **XML 응답**: `https://openapi.naver.com/v1/search/cafearticle.xml`
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
| `sort` | string | N | `sim` | 정렬 방식 옵션<br>- `sim`: 검색 결과의 정확도순 내림차순 정렬<br>- `date`: 카페글 작성 시간 기준 내림차순 정렬 |

---

## 3. 응답 필드 (JSON 포맷 기준)

요청 성공 시 JSON 오브젝트 형식으로 반환되는 필드 사양입니다.

| 속성명 | 타입 | 설명 |
| :--- | :--- | :--- |
| `lastBuildDate` | string | 검색 결과가 생성된 시각 (RFC 822 포맷) |
| `total` | integer | 검색 키워드에 매칭되는 전체 카페 게시글 개수 |
| `start` | integer | 검색 시작 번호 |
| `display` | integer | 출력 결과 건수 |
| `items` | array | 개별 카페글 검색 결과 배열 |
| `items[].title` | string | 카페 게시글의 제목. 검색어 일치 부분은 `<b>` 태그 처리됩니다. |
| `items[].link` | string | 카페 게시글의 본문 주소 URL |
| `items[].description` | string | 카페 게시글의 본문 일부 요약. 검색어 일치 부분은 `<b>` 태그 처리됩니다. |
| `items[].cafename` | string | 해당 게시글이 게시된 카페의 명칭 |
| `items[].cafeurl` | string | 해당 게시글이 게시된 카페의 주소 URL |

---

## 4. 파이썬(Python) 호출 예시

```python
import urllib.request
import urllib.parse
import json

client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"

enc_text = urllib.parse.quote("주식 초보")
url = f"https://openapi.naver.com/v1/search/cafearticle.json?query={enc_text}&display=5"

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
            print("글 제목:", item['title'])
            print("카페 이름:", item['cafename'])
            print("카페 URL:", item['cafeurl'])
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
