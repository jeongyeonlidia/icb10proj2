"""
이 모듈은 사람인 채용공고 목록 1페이지를 스크래핑하여 
공고 데이터를 정형화된 형태(회사명, 공고 제목, 링크, 근무지, 경력, 학력, 급여, 기술 분야 등)로 수집하고,
그 결과를 CSV 파일로 저장하는 스크래퍼 스크립트입니다.

주요 기능:
- 사람인 채용공고 AJAX API 호출 및 HTML 파싱
- 주요 필드(회사명, 기업형태, 제목, 직무스택, 근무지역, 경력요건, 학력요건, 연봉/급여, 마감일 등) 추출
- 수집 데이터를 DataFrame으로 변환 및 'saramin/data/saramin_jobs.csv'로 저장
"""

import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime, timedelta

def scrape_saramin_first_page():
    url = "https://www.saramin.co.kr/zf_user/jobs/public/list"
    params = {
        "page": "1",
        "isAjaxRequest": "y"
    }
    headers = {
        "host": "www.saramin.co.kr",
        "referer": "https://www.saramin.co.kr/zf_user/jobs/public/list?page=1&isAjaxRequest=y",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest"
    }
    
    print("사람인 채용공고 1페이지 수집 시작...")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"오류 발생: HTTP 상태 코드 {response.status_code}")
            return
            
        # AJAX JSON 응답 파싱
        data_json = response.json()
        html_content = data_json.get("innerHTML", "")
        
        if not html_content:
            print("응답 내 HTML 본문(innerHTML)이 비어 있습니다.")
            return
            
        soup = BeautifulSoup(html_content, "html.parser")
        list_items = soup.find_all("div", class_="list_item")
        
        print(f"발견된 채용 공고 수: {len(list_items)}개")
        
        jobs_list = []
        
        for item in list_items:
            # 1. 회사명
            company_nm_div = item.find("div", class_="company_nm")
            company_name = ""
            company_type = "일반기업"
            if company_nm_div:
                company_link = company_nm_div.find("a", class_="str_tit")
                if company_link:
                    company_name = company_link.get_text(strip=True)
                else:
                    company_span = company_nm_div.find("span", class_="str_tit")
                    if company_span:
                        company_name = company_span.get_text(strip=True)
                
                # 기업 규모 형태 (대기업, 중견기업 등)
                stock_span = company_nm_div.find("span", class_="info_stock")
                if stock_span:
                    company_type = stock_span.get_text(strip=True)
            
            # 2. 공고 제목 및 링크
            notification_info = item.find("div", class_="notification_info")
            job_title = ""
            job_link = ""
            sectors = []
            
            if notification_info:
                job_tit_div = notification_info.find("div", class_="job_tit")
                if job_tit_div:
                    job_a = job_tit_div.find("a", class_="str_tit")
                    if job_a:
                        job_title = job_a.get_text(strip=True)
                        href = job_a.get("href", "")
                        if href:
                            job_link = "https://www.saramin.co.kr" + href
                
                # 직무 섹터
                job_sector = notification_info.find("span", class_="job_sector")
                if job_sector:
                    sectors = [s.get_text(strip=True) for s in job_sector.find_all("span")]
            
            # 3. 채용 상세 정보
            recruit_info = item.find("div", class_="recruit_info")
            work_place = ""
            career = ""
            education = ""
            salary = ""
            
            if recruit_info:
                ul = recruit_info.find("ul")
                if ul:
                    lis = ul.find_all("li")
                    # 각 li 내의 p 텍스트 추출
                    for li in lis:
                        p_work = li.find("p", class_="work_place")
                        if p_work:
                            work_place = p_work.get_text(strip=True)
                        p_career = li.find("p", class_="career")
                        if p_career:
                            career = p_career.get_text(strip=True)
                        p_edu = li.find("p", class_="education")
                        if p_edu:
                            education = p_edu.get_text(strip=True)
                        p_sal = li.find("p", class_="salary")
                        if p_sal:
                            salary = p_sal.get_text(strip=True)
            
            # 4. 지원 정보 및 마감일
            support_info = item.find("div", class_="support_info")
            deadline = ""
            reg_info = ""
            reg_days_ago = 0
            posting_period_days = "알수없음"
            
            if support_info:
                support_detail = support_info.find("p", class_="support_detail")
                if support_detail:
                    date_span = support_detail.find("span", class_="date")
                    if date_span:
                        deadline = date_span.get_text(strip=True)
                    
                    deadlines_span = support_detail.find("span", class_="deadlines")
                    if deadlines_span:
                        reg_info = deadlines_span.get_text(strip=True)
                        
                        # 몇 일 전 등록/수정인지 계산
                        if any(x in reg_info for x in ["시간 전", "분 전", "초 전", "방금", "오늘"]):
                            reg_days_ago = 0
                        elif "일 전" in reg_info:
                            match = re.search(r'(\d+)일 전', reg_info)
                            if match:
                                reg_days_ago = int(match.group(1))
                        
                        # 공고 게시 간격 (등록일 ~ 마감일) 계산
                        today = datetime.today()
                        reg_date = today - timedelta(days=reg_days_ago)
                        
                        end_date = None
                        if "D-" in deadline:
                            match_d = re.search(r'D-(\d+)', deadline)
                            if match_d:
                                days_left = int(match_d.group(1))
                                end_date = today + timedelta(days=days_left)
                        elif "~" in deadline:
                            match_date = re.search(r'~(\d{2})\.(\d{2})', deadline)
                            if match_date:
                                month = int(match_date.group(1))
                                day = int(match_date.group(2))
                                try:
                                    end_date = datetime(today.year, month, day)
                                    if end_date < reg_date:
                                        end_date = datetime(today.year + 1, month, day)
                                except:
                                    pass
                        
                        if end_date:
                            posting_period_days = (end_date - reg_date).days
            
            # 데이터 수집 딕셔너리 생성
            jobs_list.append({
                "company": company_name,
                "company_type": company_type,
                "title": job_title,
                "link": job_link,
                "sectors": ", ".join(sectors),
                "work_place": work_place,
                "career": career,
                "education": education,
                "salary": salary,
                "deadline": deadline,
                "reg_info": reg_info,
                "reg_days_ago": reg_days_ago,
                "posting_period_days": posting_period_days
            })
            
        # DataFrame 변환 및 저장
        df = pd.DataFrame(jobs_list)
        
        # 데이터 저장 폴더 생성 및 저장
        output_dir = "saramin/data"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "saramin_jobs.csv")
        
        # utf-8-sig 인코딩으로 한글 깨짐 방지
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"수집 완료: {len(df)}건의 채용 정보가 {output_path} 에 저장되었습니다.")
        
    except Exception as e:
        print(f"스크래핑 진행 중 예외 발생: {e}")

if __name__ == "__main__":
    scrape_saramin_first_page()
