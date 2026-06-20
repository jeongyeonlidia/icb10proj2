"""
이 모듈은 curl-cffi를 이용하여 iHerb 스포츠 카테고리의 상품 데이터를 페이지별로 수집하고,
매 페이지를 수집할 때마다 SQLite 데이터베이스에 즉시 저장하는 스크립트입니다.
주요 기능:
- kr.iherb.com AJAX 요청을 통해 스포츠 카테고리 1~10페이지 순회 수집
- SQLite 데이터베이스(iherb/data/sports_products.db) 연결 및 테이블 생성
- 수집된 상품 정보를 매 페이지마다 DB에 INSERT OR REPLACE 처리하여 적재
- 수집 완료 후 전체 데이터를 CSV 및 JSON 파일로도 백업 저장
"""

from curl_cffi import requests
from bs4 import BeautifulSoup
import os
import time
import pandas as pd
import json
import sqlite3
from datetime import datetime

# 데이터베이스 초기화 함수
def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sports_products (
            productId TEXT PRIMARY KEY,
            displayName TEXT,
            url TEXT,
            brandName TEXT,
            partNumber TEXT,
            price TEXT,
            rating TEXT,
            reviewCount TEXT,
            recentActivity TEXT,
            collectedAt TEXT
        )
    """)
    conn.commit()
    return conn

# 매 페이지의 상품 데이터를 DB에 저장하는 함수
def save_page_to_db(conn, products_data):
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    inserted_count = 0
    for prod in products_data:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO sports_products (
                    productId, displayName, url, brandName, partNumber, price, rating, reviewCount, recentActivity, collectedAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prod["productId"],
                prod["displayName"],
                prod["url"],
                prod["brandName"],
                prod["partNumber"],
                prod["price"],
                prod["rating"],
                prod["reviewCount"],
                prod["recentActivity"],
                now_str
            ))
            inserted_count += 1
        except Exception as ex:
            print(f"DB 저장 중 개별 오류 발생 (productId: {prod.get('productId')}): {ex}")
            
    conn.commit()
    return inserted_count

# HTML 파싱 함수
def parse_product_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    product_blocks = soup.find_all("div", class_="product-inner")
    
    if not product_blocks:
        product_blocks = soup.find_all(class_="product-cell-container")
        
    products_data = []
    
    for block in product_blocks:
        try:
            link_tag = block.find("a", class_="product-link")
            if not link_tag:
                continue
                
            product_id = link_tag.get("data-product-id") or link_tag.get("data-ga-product-id")
            display_name = link_tag.get("title") or link_tag.get("aria-label")
            url = link_tag.get("href")
            brand_name = link_tag.get("data-ga-brand-name")
            part_number = link_tag.get("data-part-number") or link_tag.get("data-ga-part-number")
            
            price_tag = block.find("span", class_="price")
            price = ""
            if price_tag:
                bdi_tag = price_tag.find("bdi")
                price = bdi_tag.text.strip() if bdi_tag else price_tag.text.strip()
            if not price:
                meta_price = block.find("meta", itemprop="price")
                if meta_price:
                    price = meta_price.get("content")
                    
            rating_tag = block.find("div", class_="rating")
            rating = ""
            review_count = ""
            if rating_tag:
                stars_tag = rating_tag.find("a", class_="stars")
                if stars_tag and stars_tag.get("title"):
                    title_text = stars_tag.get("title")
                    if " - " in title_text:
                        parts = title_text.split(" - ")
                        rating = parts[0].strip()
                        review_count = parts[1].replace("구매후기", "").replace("Reviews", "").strip()
                
                count_tag = rating_tag.find("a", class_="rating-count")
                if count_tag:
                    span_tag = count_tag.find("span")
                    if span_tag:
                        review_count = span_tag.text.strip()
            
            recent_activity = ""
            activity_tag = block.find("div", class_="recent-activity-message-wrapper")
            if activity_tag:
                recent_activity = activity_tag.text.strip()
                
            products_data.append({
                "productId": product_id,
                "displayName": display_name,
                "url": url,
                "brandName": brand_name,
                "partNumber": part_number,
                "price": price,
                "rating": rating,
                "reviewCount": review_count,
                "recentActivity": recent_activity
            })
            
        except Exception as ex:
            print(f"상품 파싱 중 오류 발생: {ex}")
            continue
            
    return products_data

# 전체 수집 실행 함수 (최대 10페이지 제한 및 SQLite 적재)
def fetch_and_save_sqlite(max_pages=10):
    url = "https://kr.iherb.com/c/sports"
    db_path = "iherb/data/sports_products.db"
    
    headers = {
        "referer": "https://kr.iherb.com/c/sports",
        "x-requested-with": "XMLHttpRequest",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "cookie": "ih-pref=lc=ko-KR; cc=KR; cr=KRW;"
    }
    
    # 1. DB 초기화 및 커넥션 오픈
    os.makedirs("iherb/data", exist_ok=True)
    conn = init_db(db_path)
    print(f"SQLite DB 초기화 완료: {db_path}")
    
    all_products = []
    
    print(f"1페이지부터 {max_pages}페이지까지 순회 수집 및 SQLite 적재를 시작합니다...")
    
    for page in range(1, max_pages + 1):
        params = {
            "p": page,
            "isAjax": "true"
        }
        
        print(f"페이지 {page} 요청 중...")
        try:
            response = requests.get(url, headers=headers, params=params, impersonate="chrome")
            if response.status_code != 200:
                print(f"페이지 {page} 요청 실패 (상태 코드: {response.status_code})")
                break
                
            html_content = response.text
            products = parse_product_html(html_content)
            
            if not products:
                print(f"페이지 {page}에 상품이 존재하지 않거나 파싱되지 않습니다. 수집을 중단합니다.")
                break
                
            # 매 페이지 수집 직후 DB에 즉시 적재
            saved_count = save_page_to_db(conn, products)
            print(f"페이지 {page}: {len(products)}개 상품 파싱 완료 -> {saved_count}개 상품 DB 적재 완료.")
            
            all_products.extend(products)
            
            # 부하 방지용 딜레이
            time.sleep(1.5)
            
        except Exception as e:
            print(f"페이지 {page} 처리 중 에러 발생: {e}")
            break
            
    # DB 커넥션 종료
    conn.close()
    print("SQLite DB 커넥션이 무사히 종료되었습니다.")
    
    # 수집 완료 후 백업 파일 저장
    if all_products:
        # JSON 백업
        json_path = "iherb/data/sports_products_all.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_products, f, indent=4, ensure_ascii=False)
        # CSV 백업
        csv_path = "iherb/data/sports_products_all.csv"
        df_all = pd.DataFrame(all_products)
        df_all.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"백업 데이터 저장 완료! 총 {len(all_products)}개 상품 (JSON 및 CSV)")
    else:
        print("수집된 상품 데이터가 없습니다.")

if __name__ == "__main__":
    fetch_and_save_sqlite(max_pages=10)
