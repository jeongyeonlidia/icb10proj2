"""
이 모듈은 사람인 기획·전략 채용공고의 상세 요강 내용을 추가로 수집하여 기존 데이터셋을 보강하는 스크립트입니다.

주요 기능:
- `saramin/data/saramin_search_jobs.csv` 파일을 읽어들입니다.
- 각 공고의 고유 식별자(`rec_idx`)를 추출합니다.
- 사람인 상세 요강 본문 API(`view-detail`)를 순차 호출하여 `div.user_content` 내의 상세 텍스트를 크롤링합니다.
- 대량 수집 시 진행률을 실시간 백분율(%)로 표기하여 모니터링이 가능하도록 개선했습니다.
- 크롤링 중 차단 및 부하 방지를 위해 랜덤 시간 지연(Sleep)을 적용합니다.
- 기존 CSV 파일에 `detail_content` 컬럼을 추가한 뒤 덮어쓰기 저장합니다.
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
import os
import re
import time
import random

def scrape_job_details():
    csv_path = "saramin/data/saramin_search_jobs.csv"
    
    if not os.path.exists(csv_path):
        print(f"오류: 기준이 되는 공고 목록 파일({csv_path})이 존재하지 않습니다.")
        return
        
    # 기존 데이터 로드
    df = pd.read_csv(csv_path)
    total_count = len(df)
    print(f"로드 완료: 총 {total_count}건의 공고 상세내용 수집을 시작합니다.")
    
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "referer": "https://www.saramin.co.kr/zf_user/search?searchType=search&searchword=%EA%B8%B0%ED%9A%8D%C2%B7%EC%A0%84%EB%9E%B5"
    }
    
    detail_contents = []
    
    for idx, row in df.iterrows():
        link = row["link"]
        company = row["company"]
        title = row["title"]
        
        # rec_idx 파싱
        match = re.search(r"rec_idx=(\d+)", str(link))
        if not match:
            detail_contents.append("링크 형식 이상으로 상세 요강 수집 불가")
            continue
            
        rec_idx = match.group(1)
        detail_url = "https://www.saramin.co.kr/zf_user/jobs/relay/view-detail"
        params = {"rec_idx": rec_idx}
        
        progress = ((idx + 1) / total_count) * 100
        print(f"[{idx+1}/{total_count}] {progress:.1f}% 완료 | 수집 중: {company} | {title[:20]}...")
        
        # 랜덤 딜레이 적용 (0.2 ~ 0.8초)
        time.sleep(random.uniform(0.2, 0.8))
        
        try:
            resp = requests.get(detail_url, params=params, headers=headers, timeout=12)
            
            if resp.status_code != 200:
                detail_contents.append("상세 요강 로드 실패 (HTTP 에러)")
                continue
                
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 상세 요강 본문 영역 찾기
            content_div = soup.find(class_="user_content")
            
            if content_div:
                # 텍스트 추출 및 불필요한 연속 공백/줄바꿈 정제
                text_content = content_div.get_text(separator="\n", strip=True)
                # 다중 개행문자를 단일 혹은 이중 개행으로 압축
                text_content = re.sub(r'\n+', '\n', text_content)
                detail_contents.append(text_content)
            else:
                # user_content가 없을 경우 전체 텍스트 수집
                text_content = soup.get_text(separator="\n", strip=True)
                text_content = re.sub(r'\n+', '\n', text_content)
                detail_contents.append(text_content[:1500] + "\n...(중략)")
                
        except Exception as err:
            detail_contents.append(f"수집 중 예외 발생 ({err})")
            
    # DataFrame 업데이트
    df["detail_content"] = detail_contents
    
    # 데이터 파일 덮어쓰기 저장
    try:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"\n상세 정보 수집 완료! 전체 결과가 {csv_path} 에 성공적으로 업데이트되었습니다.")
    except Exception as save_err:
        print(f"파일 저장 오류: {save_err}")

if __name__ == "__main__":
    scrape_job_details()
