1) HTTP 요청정보
Request URL
https://store.kyobobook.co.kr/api/gw/best/v2/best-seller/online?page=1&per=20&saleCmdtClstCode=33&soldOutExcludeYn=N&saleCmdtDsplDvsnCode=KOR&period=002&dsplDvsnCode=001&dsplTrgtDvsnCode=004
Request Method
GET
Status Code
200 OK
Remote Address
103.182.126.2:443
Referrer Policy
strict-origin-when-cross-origin

2) HTTP 헤더정보

host
store.kyobobook.co.kr
referer
https://store.kyobobook.co.kr/category/domestic/33/best?page=1
sec-ch-ua
"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"Windows"
sec-ch-ua-platform-version
"19.0.0"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-origin
user-agent
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36
x-api-gw-key
eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..wReN9X_PbI3TvMjY.m_lP6O5LrobKahX4AuNRW9ZkFTSeJhLvRI6SDbXAU98Vnr1ZucS4vqV1xwGLeMPMTHxyYEH7p14WVMwDsCMyMdqL0yfJ66gzTzVOqT_K6eMIbEKmmJk1ugjC3CtZvBmpJw8wKJo8.xrUuSdZZke9D8rVT1H-MYA

3) Payload 정보

page=1&per=20&saleCmdtClstCode=33&soldOutExcludeYn=N&saleCmdtDsplDvsnCode=KOR&period=002&dsplDvsnCode=001&dsplTrgtDvsnCode=004

4) 응답의 일부를 Response 에서 일부를 복사해서 넣어주기 (전체는 토큰 수 제한으로 어렵습니다.)
```
{
    "data": {
        "bestSeller": [
            {
                "prstRnkn": 1,
                "frmrRnkn": 1,
                "ymw": "2026061320260619",
                "total": 0,
                "rowNum": 1,
                "product": {
                    "productInfo": {
```
5) 한페이지가 성공적으로 수집되는지 확인하고 csv 파일로 저장할 것