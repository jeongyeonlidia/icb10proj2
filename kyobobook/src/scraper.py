"""
이 모듈은 교보문고 베스트셀러 API를 호출하여 전체 데이터를 수집하고 CSV 파일로 저장하는 스크립트입니다.
주요 기능:
- 교보문고 베스트셀러 API에 HTTP GET 요청을 보내며 1페이지부터 마지막 페이지까지 데이터를 순차적으로 수집
- 수집된 JSON 데이터에서 도서명, 저자, 출판사, 가격, 평점 등의 주요 정보를 추출하여 파싱
- 파싱된 데이터를 Pandas DataFrame으로 변환 후 UTF-8-SIG 인코딩의 CSV 파일로 저장
"""
import os
import sys
import time
import pandas as pd
import requests

def collect_best_sellers():
    # Windows 콘솔 등에서 유니코드(이모지 등) 출력 시 에러 방지
    if sys.stdout and sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    # API 요청 URL
    url = "https://store.kyobobook.co.kr/api/gw/best/v2/best-seller/online"
    
    # HTTP 요청 헤더 설정 (최초 page=1 기준)
    headers = {
        "host": "store.kyobobook.co.kr",
        "referer": "https://store.kyobobook.co.kr/category/domestic/33/best?page=1",
        "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-platform-version": '"19.0.0"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "x-api-gw-key": "eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..wReN9X_PbI3TvMjY.m_lP6O5LrobKahX4AuNRW9ZkFTSeJhLvRI6SDbXAU98Vnr1ZucS4vqV1xwGLeMPMTHxyYEH7p14WVMwDsCMyMdqL0yfJ66gzTzVOqT_K6eMIbEKmmJk1ugjC3CtZvBmpJw8wKJo8.xrUuSdZZke9D8rVT1H-MYA"
    }

    parsed_books = []
    page = 1
    max_pages = 50  # 안전을 위한 최대 페이지 제한
    
    print("교보문고 베스트셀러 전체 데이터 수집 시작...")

    while page <= max_pages:
        print(f"페이지 {page} 수집 중...")
        
        # Referer 업데이트 (페이지 번호 매칭)
        headers["referer"] = f"https://store.kyobobook.co.kr/category/domestic/33/best?page={page}"
        
        # API 쿼리 파라미터
        params = {
            "page": str(page),
            "per": "20",
            "saleCmdtClstCode": "33",
            "soldOutExcludeYn": "N",
            "saleCmdtDsplDvsnCode": "KOR",
            "period": "002",
            "dsplDvsnCode": "001",
            "dsplTrgtDvsnCode": "004"
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            response_data = response.json()
            
            if "data" in response_data and "bestSeller" in response_data["data"]:
                best_sellers = response_data["data"]["bestSeller"]
                
                # 수집할 데이터가 더 없으면 중단
                if not best_sellers:
                    print(f"페이지 {page}에 데이터가 존재하지 않아 수집을 종료합니다.")
                    break
                
                print(f"페이지 {page}: {len(best_sellers)}개의 도서 정보를 성공적으로 가져왔습니다.")
                
                for item in best_sellers:
                    product = item.get("product", {})
                    product_info = product.get("productInfo", {})
                    price_info = product.get("priceInfo", {})
                    review_info = product.get("reviewInfo", {})
                    event_info = product.get("eventInfo", {}) or {}

                    book_data = {
                        "순위": item.get("prstRnkn", ""),
                        "이전순위": item.get("frmrRnkn", ""),
                        "도서ID": product_info.get("saleCmdtid", ""),
                        "도서명": product_info.get("cmdtName", ""),
                        "저자": product_info.get("chrcName", ""),
                        "출판사": product_info.get("pbcmName", ""),
                        "출판일": product_info.get("rlseDate", ""),
                        "정가": price_info.get("saleCmdtPrce", ""),
                        "판매가": price_info.get("saleCmdtSapr", ""),
                        "할인율": price_info.get("saleCmdtPrceDscnRate", ""),
                        "평점": review_info.get("score", ""),
                        "리뷰수": review_info.get("count", ""),
                        "이벤트": event_info.get("eventTitle", ""),
                        "분류명": product_info.get("saleCmdtClstName", "")
                    }
                    parsed_books.append(book_data)
                
            else:
                print(f"페이지 {page}에서 데이터를 가져오는 데 오류가 발생했습니다.")
                break
                
        except Exception as e:
            print(f"페이지 {page} 수집 중 오류 발생: {e}")
            break
            
        # 페이지 증가 및 지연 시간 부여
        page += 1
        time.sleep(1.0)
        
    # DataFrame 변환 및 저장
    if parsed_books:
        df = pd.DataFrame(parsed_books)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(os.path.dirname(current_dir), "data")
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, "best_sellers.csv")
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"\n데이터 수집 및 CSV 저장 완료! 총 {len(parsed_books)}개 도서 저장됨: {output_path}")
        
        print("\n--- 수집 데이터 샘플 (상위 5개) ---")
        print(df.head())
    else:
        print("수집된 데이터가 없습니다.")

if __name__ == "__main__":
    collect_best_sellers()
