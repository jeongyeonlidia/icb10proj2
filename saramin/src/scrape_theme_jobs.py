"""
이 모듈은 사람인 테마 채용공고의 첫 페이지 데이터를 수집하는 스크래퍼 스크립트입니다.

주요 기능:
- 사람인의 테마 채용공고 AJAX API(`get-theme-jobs-for-list`)를 호출하여 첫 페이지 HTML을 가져옵니다.
- `a.newcomer_link_view` 요소를 추출하고, 그 하위의 `list_curation_slide` 요소를 파싱하여 채용 데이터를 정형화합니다.
- 수집된 공고의 회사명, 공고 제목, 링크, 근무지역, 경력, 마감일 등의 필드를 정형 데이터로 변환합니다.
- 최종 결과를 Pandas DataFrame으로 변환하여 `saramin/data/saramin_theme_jobs.csv`로 저장합니다.
"""

import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
import os
import re

def scrape_theme_jobs():
    url = "https://www.saramin.co.kr/zf_user/jobs/public/get-theme-jobs-for-list"
    
    headers = {
        "host": "www.saramin.co.kr",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
        "referer": "https://www.saramin.co.kr/zf_user/jobs/public/list?page=1&isAjaxRequest=y"
    }
    
    params = {
        "layout": "true"
    }
    
    print("사람인 테마 채용공고 API 호출 시작...")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"API 호출 실패: HTTP 상태 코드 {response.status_code}")
            return
            
        # JSON 응답 파싱
        try:
            res_data = response.json()
        except Exception as json_err:
            print(f"JSON 파싱 실패: {json_err}")
            return
            
        html_content = res_data.get("innerHTML", "")
        if not html_content:
            print("응답 내 innerHTML 본문이 비어 있습니다.")
            return
            
        soup = BeautifulSoup(html_content, "html.parser")
        
        # <a> 태그 중 newcomer_link_view 클래스를 가진 공고 리스트 아이템 수집
        job_links = soup.find_all("a", class_="newcomer_link_view")
        print(f"발견된 테마 채용 공고 수: {len(job_links)}개")
        
        jobs_list = []
        
        for item in job_links:
            # 1. 공고 링크
            href = item.get("href", "")
            job_link = href if href.startswith("http") else "https://www.saramin.co.kr" + href
            
            # 2. 내부 list_curation_slide 파싱
            curation_slide = item.find("div", class_="list_curation_slide")
            
            company_name = ""
            job_title = ""
            work_place = ""
            career = ""
            education = ""
            deadline = ""
            
            if curation_slide:
                # 회사명
                company_span = curation_slide.find("span", class_="company_name")
                if company_span:
                    # cover text 제거 방어 로직
                    cover = company_span.find("span", class_="cover")
                    if cover:
                        cover.decompose()
                    company_name = company_span.get_text(strip=True)
                
                # 공고 제목
                title_span = curation_slide.find("span", class_="announcement")
                if title_span:
                    cover = title_span.find("span", class_="cover")
                    if cover:
                        cover.decompose()
                    job_title = title_span.get_text(strip=True)
                
                # 상세 정보 (지역, 경력 등)
                info_div = curation_slide.find("div", class_="info")
                if info_div:
                    spans = info_div.find_all("span")
                    if len(spans) >= 1:
                        work_place = spans[0].get_text(strip=True)
                    if len(spans) >= 2:
                        career = spans[1].get_text(strip=True)
                    if len(spans) >= 3:
                        education = spans[2].get_text(strip=True)
                        
                # 마감일
                day_span = curation_slide.find("span", class_="day")
                if day_span:
                    deadline = day_span.get_text(strip=True)
            
            if company_name or job_title:
                jobs_list.append({
                    "company": company_name,
                    "title": job_title,
                    "link": job_link,
                    "work_place": work_place,
                    "career": career,
                    "education": education,
                    "deadline": deadline
                })
                
        # DataFrame 저장
        if jobs_list:
            df = pd.DataFrame(jobs_list)
            output_dir = "saramin/data"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "saramin_theme_jobs.csv")
            
            # BOM을 추가하여 Excel에서 한글 깨짐 방지
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
            print(f"테마 채용공고 1페이지 수집이 성공적으로 완료되었습니다!")
            print(f"수집된 데이터 개수: {len(df)}건")
            print(f"저장 경로: {output_path}")
        else:
            print("수집 및 파싱된 채용 공고 데이터가 존재하지 않습니다.")
            
    except Exception as e:
        print(f"테마 채용공고 수집 과정 중 오류 발생: {e}")

if __name__ == "__main__":
    scrape_theme_jobs()
