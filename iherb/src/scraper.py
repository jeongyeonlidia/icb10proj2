"""
이 모듈은 iHerb의 스포츠 카테고리 내 특가(Specials) 상품 전체 데이터를 수집하는 스크립트입니다.
주요 기능:
- iHerb API(https://catalog.app.iherb.com/category/sports/specials)를 호출하며 페이지를 순회합니다.
- API 응답의 totalSize 값에만 의존하지 않고, 실제 반환되는 상품 목록(products)이 없을 때까지 1페이지부터 마지막 페이지까지 순차적으로 요청하여 데이터를 수집합니다.
- 수집된 모든 페이지의 데이터를 취합하여 JSON 및 CSV 파일로 저장합니다.
"""

import requests
import json
import os
import time
import pandas as pd

def fetch_all_pages():
    url = "https://catalog.app.iherb.com/category/sports/specials"
    headers = {
        "origin": "https://kr.iherb.com",
        "referer": "https://kr.iherb.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    }
    
    all_products = []
    page = 1
    page_size = 18
    
    print("1페이지부터 마지막 페이지까지 데이터 수집 시작...")
    
    while True:
        params = {
            "isMobile": "false",
            "page": page,
            "pageSize": page_size
        }
        
        print(f"페이지 {page} 요청 중...")
        try:
            response = requests.get(url, headers=headers, params=params)
        except Exception as e:
            print(f"네트워크 오류 발생: {e}")
            break
            
        if response.status_code != 200:
            print(f"에러 발생 (상태 코드 {response.status_code}): {response.text}")
            break
            
        data = response.json()
        products = data.get("products", [])
        
        # 상품이 비어있으면 마지막 페이지에 도달한 것이므로 루프 종료
        if not products:
            print(f"페이지 {page}에 상품이 없습니다. 수집을 종료합니다.")
            break
            
        all_products.extend(products)
        print(f"페이지 {page}: {len(products)}개 상품 수집 완료. (현재 누적: {len(all_products)}개)")
        
        # 혹시 모를 무한 루프를 방지하기 위해 비정상적으로 많은 페이지 요청 시 제한
        if page > 100:
            print("안전을 위해 100페이지까지만 수집하고 중단합니다.")
            break
            
        page += 1
        time.sleep(1) # 서버 부하 방지
        
    # 데이터 폴더 생성 확인
    os.makedirs("iherb/data", exist_ok=True)
    
    # JSON 파일 저장
    json_path = "iherb/data/sports_specials_all.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"products": all_products, "totalSize": len(all_products)}, f, indent=4, ensure_ascii=False)
    print(f"전체 JSON 데이터 저장 완료: {json_path}")
    
    # CSV 파일 저장
    if all_products:
        df = pd.DataFrame(all_products)
        csv_path = "iherb/data/sports_specials_all.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"전체 CSV 데이터 저장 완료: {csv_path}")
    else:
        print("수집된 상품 데이터가 없어 CSV를 저장하지 않습니다.")

if __name__ == "__main__":
    fetch_all_pages()
