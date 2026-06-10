# 네이버 검색 > 블로그 API 가이드

블로그 검색 API는 네이버 검색 서비스에 등록된 블로그 글 중 설정한 키워드와 일치하는 검색 결과를 반환하는 RESTful API입니다. XML 또는 JSON 형식으로 데이터를 수신할 수 있습니다.

---

## 1. 기본 정보

* **요청 URL**: 
  * **JSON 응답**: `https://openapi.naver.com/v1/search/blog.json`
  * **XML 응답**: `https://openapi.naver.com/v1/search/blog.xml`
* **HTTP 메서드**: `GET`
* **프로토콜**: `HTTPS`
* **인증 방식**: 비로그인 방식 (HTTP 헤더에 `X-Naver-Client-Id`, `X-Naver-Client-Secret` 전송)
* **일일 호출 한도**: 25,000회 (전체 검색 API 호출 횟수 합산 기준)

---

## 2. 요청 파라미터 (Query String)

URL 뒤에 쿼리 스트링 파라미터 형태로 실어 호출합니다.

| 파라미터 | 타입 | 필수 여부 | 기본값 | 설명 |
| :--- | :--- | :---: | :---: | :--- |
| `query` | string | Y | - | 검색어. UTF-8 형식으로 URL 인코딩을 반드시 적용해야 합니다. |
| `display` | integer | N | 10 | 한 번에 출력할 검색 결과의 개수 (허용 범위: 1 ~ 100) |
| `start` | integer | N | 1 | 검색 시작 위치 (허용 범위: 1 ~ 1000) |
| `sort` | string | N | `sim` | 정렬 방식 옵션<br>- `sim`: 검색 결과의 정확도순 내림차순 정렬<br>- `date`: 블로그 글 작성일 기준 내림차순 정렬 |

---

## 3. 응답 필드 (JSON 포맷 기준)

요청에 성공하면 다음과 같은 정보가 JSON 오브젝트로 반환됩니다.

| 속성명 | 타입 | 설명 |
| :--- | :--- | :--- |
| `lastBuildDate` | string | 검색 결과가 생성된 시각 (RFC 822 포맷) |
| `total` | integer | 검색 키워드에 매칭되는 전체 결과 건수 |
| `start` | integer | 검색 시작 번호 |
| `display` | integer | 출력 결과 건수 |
| `items` | array | 검색 결과 개별 아이템 배열 |
| `items[].title` | string | 블로그 포스트의 제목. 검색어와 일치하는 부분은 `<b>` 태그로 둘러싸여 반환됩니다. |
| `items[].link` | string | 블로그 포스트의 하이퍼링크 URL |
| `items[].description` | string | 블로그 포스트 요약 내용. 검색어 일치부는 `<b>` 태그 처리됩니다. |
| `items[].bloggername` | string | 해당 블로그 포스트가 게재된 블로그의 명칭 |
| `items[].bloggerlink` | string | 해당 블로그의 메인 주소 URL |
| `items[].postdate` | string | 블로그 포스트 작성일 (`YYYYMMDD` 형식) |

---

## 4. 파이썬(Python) 호출 예시

```python
import urllib.request
import urllib.parse
import json

client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"

# 검색어 URL 인코딩 적용
enc_text = urllib.parse.quote("네이버 오픈API")
url = f"https://openapi.naver.com/v1/search/blog.json?query={enc_text}&display=5"

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
            print("제목:", item['title'])
            print("작성일:", item['postdate'])
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
| **SE02** | 400 | Invalid display value (부적절한 display 값입니다. 1~100 범위를 초과했는지 확인합니다.) |
| **SE03** | 400 | Invalid start value (부적절한 start 값입니다. 1~1000 범위를 초과했는지 확인합니다.) |
| **SE04** | 400 | Invalid sort value (부적절한 sort 값입니다. 정렬 매개변수 오타 확인.) |
| **SE06** | 400 | Malformed encoding (검색어가 UTF-8 인코딩이 아닌 경우 발생합니다.) |
| **SE05** | 404 | Invalid search api (요청 URL 경로의 오타를 확인합니다.) |
| **SE99** | 500 | System Error (네이버 내부 서버 장애입니다.) |
