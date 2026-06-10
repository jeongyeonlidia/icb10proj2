# 네이버 검색 > 쇼핑 API 가이드

쇼핑 검색 API는 네이버 쇼핑 서비스에 등록된 상품 데이터 중 설정한 키워드와 일치하는 상품 정보를 반환하는 RESTful API입니다. XML 또는 JSON 형식으로 제공됩니다.

---

## 1. 기본 정보

* **요청 URL**: 
  * **JSON 응답**: `https://openapi.naver.com/v1/search/shop.json`
  * **XML 응답**: `https://openapi.naver.com/v1/search/shop.xml`
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
| `sort` | string | N | `sim` | 정렬 방식 옵션<br>- `sim`: 검색 결과의 정확도순 내림차순 정렬<br>- `date`: 상품 등록일 기준 내림차순 정렬<br>- `asc`: 상품 가격 오름차순 정렬 (최저가 순)<br>- `dsc`: 상품 가격 내림차순 정렬 (최고가 순) |
| `filter` | string | N | - | 상품 유형 필터<br>- `naverpay`: 네이버페이 연동 상품만 필터링 |
| `exclude` | string | N | - | 검색 결과에서 제외할 상품 유형 지정. 콜론(`:`)으로 구분하여 다중 지정 가능 (예: `used:rental`) <br>- `used`: 중고 상품 제외<br>- `rental`: 대여(렌탈) 상품 제외<br>- `cbshop`: 해외직구 및 구매대행 상품 제외 |

---

## 3. 응답 필드 (JSON 포맷 기준)

요청 성공 시 JSON 오브젝트 형식으로 반환되는 필드 사양입니다.

| 속성명 | 타입 | 설명 |
| :--- | :--- | :--- |
| `lastBuildDate` | string | 검색 결과가 생성된 시각 (RFC 822 포맷) |
| `total` | integer | 검색 키워드에 매칭되는 전체 상품 개수 |
| `start` | integer | 검색 시작 번호 |
| `display` | integer | 출력 결과 건수 |
| `items` | array | 개별 상품 검색 결과 배열 |
| `items[].title` | string | 상품명. 검색어 일치 부분은 `<b>` 태그 처리됩니다. |
| `items[].link` | string | 상품 상세 정보 및 구매 페이지 URL |
| `items[].image` | string | 상품 썸네일 이미지 주소 URL |
| `items[].lprice` | string(int) | 최저가 정보. 최저가가 없을 경우 `0` 반환. (가격 비교 데이터가 없는 경우 본래 상품 가격) |
| `items[].hprice` | string(int) | 최고가 정보. 최고가 정보가 없거나 가격 비교가 불가능한 단일 상품일 경우 `0` 반환. |
| `items[].mallName` | string | 상품 판매 쇼핑몰의 이름. 쇼핑몰명이 존재하지 않으면 '네이버' 반환. |
| `items[].productId` | string(int) | 네이버 쇼핑 서비스 내의 상품 ID |
| `items[].productType` | string(int) | 상품군 및 상품 분류 종류 코드 (1 ~ 12). 아래 상세 매핑 참고. |
| `items[].brand` | string | 상품 브랜드 명칭 |
| `items[].maker` | string | 상품 제조사 명칭 |
| `items[].category1` | string | 대분류 카테고리 |
| `items[].category2` | string | 중분류 카테고리 |
| `items[].category3` | string | 소분류 카테고리 |
| `items[].category4` | string | 세분류 카테고리 |

### 상품군 타입 (`productType`) 코드 매핑 상세

| 상품군 | 가격비교 상품 (코드) | 가격비교 비매칭 일반상품 (코드) | 가격비교 매칭 일반상품 (코드) |
| :--- | :---: | :---: | :---: |
| **일반 상품** | 1 | 2 | 3 |
| **중고 상품** | 4 | 5 | 6 |
| **단종 상품** | 7 | 8 | 9 |
| **판매 예정** | 10 | 11 | 12 |

---

## 4. 파이썬(Python) 호출 예시

```python
import urllib.request
import urllib.parse
import json

client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"

enc_text = urllib.parse.quote("노이즈캔슬링 헤드폰")
url = f"https://openapi.naver.com/v1/search/shop.json?query={enc_text}&display=5&sort=asc&exclude=used"

request = urllib.request.Request(url)
request.add_header("X-Naver-Client-Id", client_id)
request.add_header("X-Naver-Client-Secret", client_secret)

try:
    response = urllib.request.urlopen(request)
    res_code = response.getcode()
    if res_code == 200:
        response_body = response.read().decode('utf-8')
        data = json.loads(response_body)
        print("총 상품 개수:", data['total'])
        for item in data['items']:
            print("상품명:", item['title'])
            print("최저가:", item['lprice'])
            print("판매처:", item['mallName'])
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
