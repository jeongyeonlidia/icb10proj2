"""
이 모듈은 YES24 베스트셀러 페이지의 모든 페이지 데이터를 수집하여 CSV 파일로 저장하는 스크립트입니다.
주요 기능:
- YES24 베스트셀러 API/컨텐츠 URL에 HTTP GET 요청을 페이지 번호를 올려가며 순차적으로 전송
- BeautifulSoup을 이용해 도서 번호, 순위, 제목, 저자, 출판사, 가격, 평점, 태그, 혜택 등 상세 정보 파싱
- 수집된 전체 데이터를 Pandas DataFrame으로 변환 후 UTF-8-SIG 인코딩의 CSV 파일로 저장
"""
import os
import re
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd

def main():
    base_url = "https://www.yes24.com/product/category/BestSellerContents"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "Referer": "https://www.yes24.com/product/category/bestseller?pageNumber=1&pageSize=24&categoryNumber=001001003",
        "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-requested-with": "XMLHttpRequest"
    }

    books_data = []
    page = 1
    max_pages = 50  # 무한루프 방지를 위한 최대 페이지 제한

    print("전체 페이지 데이터 수집 시작...")

    while page <= max_pages:
        # 쿼리 파라미터 빌드
        params = {
            "categoryNumber": "001001003",
            "sumGb": "06",
            "sex": "A",
            "age": "255",
            "goodsTp": "0",
            "addOptionTp": "0",
            "excludeTp": "2",
            "pageNumber": str(page),
            "pageSize": "24",
            "goodsStatGb": "06",
            "eBookTp": "0",
            "bestType": "YES24_BESTSELLER",
            "type": "",
            "saleYear": "0",
            "saleMonth": "0",
            "weekNo": "0",
            "saleDts": "",
            "viewMode": "",
            "freeYn": ""
        }

        print(f"페이지 {page} 수집 중...")
        
        try:
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
        except Exception as e:
            print(f"페이지 {page} HTTP 요청 실패: {e}")
            break

        soup = BeautifulSoup(response.text, "lxml")
        best_list = soup.select("#yesBestList > li")
        
        # 데이터가 없으면 중단
        if not best_list:
            print(f"페이지 {page}에 상품 데이터가 없어 수집을 종료합니다.")
            break

        print(f"페이지 {page} 수집된 상품 수: {len(best_list)}")
        
        for li in best_list:
            try:
                # 상품 번호
                goods_no = li.get("data-goods-no", "")
                
                # 순위
                rank_el = li.select_one(".ico.rank")
                rank = rank_el.text.strip() if rank_el else ""
                
                # 도서명
                name_el = li.select_one(".gd_name")
                title = name_el.text.strip() if name_el else ""
                
                # 부도서명
                name_e_el = li.select_one(".gd_nameE")
                subtitle = name_e_el.text.strip() if name_e_el else ""
                
                # 저자
                auth_el = li.select_one(".info_auth")
                author = ""
                if auth_el:
                    author = auth_el.text.strip()
                    author = re.sub(r'\s*저$', '', author).strip()
                
                # 출판사
                pub_el = li.select_one(".info_pub")
                publisher = pub_el.text.strip() if pub_el else ""
                
                # 출판일
                date_el = li.select_one(".info_date")
                pub_date = date_el.text.strip() if date_el else ""
                
                # 판매가
                price_el = li.select_one(".info_price strong.txt_num .yes_b")
                price = price_el.text.strip() if price_el else ""
                
                # 할인율
                sale_rate_el = li.select_one(".info_price .txt_sale .num")
                sale_rate = sale_rate_el.text.strip() if sale_rate_el else ""
                
                # 원래 가격 (정가)
                original_price_el = li.select_one(".info_price .txt_num.dash .yes_m")
                original_price = original_price_el.text.strip() if original_price_el else ""
                
                # 판매지수
                sale_num_el = li.select_one(".saleNum")
                sale_index = ""
                if sale_num_el:
                    sale_index_text = sale_num_el.text.strip()
                    sale_index = sale_index_text.replace("판매지수", "").strip()
                
                # 평점
                rating_el = li.select_one(".rating_grade .yes_b")
                rating = rating_el.text.strip() if rating_el else ""
                
                # 리뷰 건수
                review_el = li.select_one(".rating_rvCount .txC_blue")
                review_count = review_el.text.strip() if review_el else ""
                
                # 추가 정보 1: 분철 서비스 여부
                spring_el = li.select_one(".info_spring")
                spring_option = "Y" if spring_el else "N"
                
                # 추가 정보 2: 태그 정보
                tag_els = li.select(".info_tag .tag a")
                tags = ", ".join([tag.text.strip() for tag in tag_els]) if tag_els else ""
                
                # 추가 정보 3: 구매혜택 / 이벤트
                benefit_els = li.select(".info_present dd a, .info_event .event .txt a")
                benefits = ", ".join([b.text.strip() for b in benefit_els]) if benefit_els else ""
                
                # 추가 정보 4: 관련상품
                rel_els = li.select(".info_relG .relG a")
                related_goods = ", ".join([r.text.strip() for r in rel_els]) if rel_els else ""
                
                # 추가 정보 5: 배송 정보
                deli_el = li.select_one(".info_deli")
                delivery_info = ""
                if deli_el:
                    delivery_info = " ".join([span.text.strip() for span in deli_el.find_all("span") if span.text.strip()])
                
                book_info = {
                    "순위": rank,
                    "도서번호": goods_no,
                    "도서명": title,
                    "부제목": subtitle,
                    "저자": author,
                    "출판사": publisher,
                    "출판일": pub_date,
                    "판매가": price,
                    "할인율": sale_rate,
                    "정가": original_price,
                    "판매지수": sale_index,
                    "평점": rating,
                    "리뷰수": review_count,
                    "분철가능여부": spring_option,
                    "태그": tags,
                    "구매혜택및이벤트": benefits,
                    "관련상품": related_goods,
                    "배송정보": delivery_info
                }
                
                books_data.append(book_info)
            except Exception as e:
                print(f"항목 파싱 중 오류 발생: {e}")
                continue
        
        # 페이지 증가 및 대기
        page += 1
        time.sleep(1.0)

    # 4. 데이터 저장
    if books_data:
        df = pd.DataFrame(books_data)
        
        # 저장 디렉토리 생성
        output_dir = os.path.join("yes24", "data")
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, "best_sellers.csv")
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"데이터 수집 완료! 총 {len(books_data)}개 상품 저장됨: {output_path}")
        
        print("\n--- 수집 데이터 샘플 (상위 5개) ---")
        print(df.head())
    else:
        print("수집된 데이터가 없습니다.")

if __name__ == "__main__":
    main()
