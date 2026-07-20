"""
이 모듈은 사람인 기획·전략 검색 결과 페이지의 여러 페이지 데이터를 수집하는 스크래퍼 스크립트입니다.

주요 기능:
- 사람인 통합 검색 URL(`zf_user/search`)을 호출하여 기획·전략 직무 카테고리의 데이터를 수집합니다.
- `recruitPage` 파라미터를 활용해 1페이지부터 최대 지정 페이지(기본 10페이지)까지 반복 수집합니다.
- HTML 문서 내 `div.item_recruit` 요소들을 파싱하여 회사명, 공고 제목, 공고 링크, 마감일, 근무조건(지역/경력/학력), 직무스택을 추출합니다.
- 수집된 가공 데이터를 Pandas DataFrame으로 정형화한 뒤 `saramin/data/saramin_search_jobs.csv` 파일로 저장합니다.
"""

import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
import os
import re
import time
import random

def scrape_search_jobs(max_pages=10):
    url = "https://www.saramin.co.kr/zf_user/search"
    
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "referer": "https://www.saramin.co.kr/zf_user/search?go=&flag=n&searchType=auto&searchword=%EA%B8%B0%ED%9A%8D%C2%B7%EC%A0%84%EB%9E%B5"
    }
    
    # 기본 검색 쿼리 조건 설정 (recruitPage는 루프 내에서 처리)
    params = {
        "searchType": "search",
        "searchword": "기획·전략",
        "company_cd": "0,1,2,3,4,5,6,7,9,10",
        "loc_mcd": "102000,108000,101000",
        "search_optional_item": "y",
        "search_done": "y",
        "panel_count": "y",
        "preview": "y"
    }
    
    jobs_list = []
    
    print(f"사람인 기획·전략 통합검색 수집 시작 (최대 {max_pages}페이지)...")
    
    for page in range(1, max_pages + 1):
        print(f"[{page}/{max_pages}] 페이지 수집 중...")
        params["recruitPage"] = str(page)
        
        # 페이지 조회 간 딜레이 (0.3 ~ 0.8초)
        time.sleep(random.uniform(0.3, 0.8))
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code != 200:
                print(f"    -> API 호출 실패: HTTP 상태 코드 {response.status_code}")
                break
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 각 채용 공고를 나타내는 div.item_recruit 수집
            items = soup.find_all("div", class_="item_recruit")
            print(f"    -> 발견된 공고 수: {len(items)}개")
            
            # 검색 결과가 없는 경우 조기 중단
            if not items:
                print("    -> 더 이상 발견된 공고가 없어 수집을 조기 종료합니다.")
                break
                
            for item in items:
                # 1. 회사명
                company_name = ""
                corp_area = item.find("div", class_="area_corp")
                if corp_area:
                    corp_name_strong = corp_area.find("strong", class_="corp_name")
                    if corp_name_strong:
                        corp_a = corp_name_strong.find("a")
                        if corp_a:
                            company_name = corp_a.get_text(strip=True)
                
                # 2. 공고 제목 및 링크
                job_title = ""
                job_link = ""
                
                job_tit_h2 = item.find("h2", class_="job_tit")
                if job_tit_h2:
                    job_a = job_tit_h2.find("a")
                    if job_a:
                        job_title = job_a.get_text(strip=True)
                        href = job_a.get("href", "")
                        if href:
                            job_link = href if href.startswith("http") else "https://www.saramin.co.kr" + href
                
                # 3. 근무조건 (지역, 경력, 학력, 고용형태 등)
                work_place = ""
                career = ""
                education = ""
                job_type = ""
                
                condition_div = item.find("div", class_="job_condition")
                if condition_div:
                    spans = condition_div.find_all("span")
                    if len(spans) >= 1:
                        work_place = spans[0].get_text(strip=True)
                    if len(spans) >= 2:
                        career = spans[1].get_text(strip=True)
                    if len(spans) >= 3:
                        education = spans[2].get_text(strip=True)
                    if len(spans) >= 4:
                        job_type = spans[3].get_text(strip=True)
                
                # 4. 마감일
                deadline = ""
                date_div = item.find("div", class_="job_date")
                if date_div:
                    date_span = date_div.find("span", class_="date")
                    if date_span:
                        deadline = date_span.get_text(strip=True)
                
                # 5. 직무 분야
                sectors = []
                sector_div = item.find("div", class_="job_sector")
                if sector_div:
                    sector_links = sector_div.find_all("a")
                    sectors = [a.get_text(strip=True) for a in sector_links]
                
                # 수집 데이터 추가
                if company_name or job_title:
                    jobs_list.append({
                        "company": company_name,
                        "title": job_title,
                        "link": job_link,
                        "work_place": work_place,
                        "career": career,
                        "education": education,
                        "job_type": job_type,
                        "deadline": deadline,
                        "sectors": ", ".join(sectors)
                    })
                    
        except Exception as e:
            print(f"    -> {page}페이지 수집 중 에러 발생: {e}")
            break
            
    # DataFrame 저장
    if jobs_list:
        df = pd.DataFrame(jobs_list)
        # 중복 공고 제거 (rec_idx 기반 중복 제거가 안전하나 간단하게 회사명과 제목 기준으로 제거 가능)
        # 겹칠 수 있으므로 link 기준 중복 제거 적용
        df = df.drop_duplicates(subset=["link"]).reset_index(drop=True)
        
        output_dir = "saramin/data"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "saramin_search_jobs.csv")
        
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"\n기획·전략 검색 결과 목록 수집 완료!")
        print(f"중복 제거 후 수집된 총 공고 개수: {len(df)}건")
        print(f"저장 경로: {output_path}")
    else:
        print("수집 및 파싱된 채용 공고가 존재하지 않습니다.")

if __name__ == "__main__":
    scrape_search_jobs(max_pages=10)
