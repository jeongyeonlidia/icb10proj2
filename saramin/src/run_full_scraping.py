"""
이 모듈은 사람인 기획·전략 채용공고의 페이징 수집, 상세페이지 크롤링, SQLite 데이터베이스 변환 적재를 순차적으로 실행하는 통합 마스터 스크립트입니다.

주요 기능:
- 1단계: `scrape_search_jobs`를 실행하여 다중 페이지(최대 10페이지) 목록 데이터를 수집해 CSV로 저장합니다.
- 2단계: `scrape_job_details`를 실행하여 수집된 목록에 명시된 상세페이지 본문 요강 텍스트를 크롤링해 CSV에 병합합니다.
- 3단계: `convert_csv_to_sqlite`를 실행하여 최종 가공 완료된 CSV 데이터를 SQLite 데이터베이스 파일(`saramin_search_jobs.db`)로 일괄 이관 및 저장합니다.
"""

from scrape_search_jobs import scrape_search_jobs
from scrape_search_details import scrape_job_details
from save_to_sqlite import convert_csv_to_sqlite
import time

def run_pipeline():
    start_time = time.time()
    print("==================================================================")
    print("[START] Saramin Job Scraping & SQLite Migration Pipeline")
    print("==================================================================")
    
    # 1. 채용공고 목록 수집 (최대 25페이지)
    print("\n--- [Step 1] Job List Pagination Scraping ---")
    scrape_search_jobs(max_pages=25)
    
    # 2. 상세 요강 본문 수집
    print("\n--- [Step 2] Job Descriptions Scraping ---")
    scrape_job_details()
    
    # 3. SQLite DB 변환 적재
    print("\n--- [Step 3] SQLite Database Migration ---")
    convert_csv_to_sqlite()
    
    elapsed_time = time.time() - start_time
    print("\n==================================================================")
    print(f"[SUCCESS] All pipelines completed successfully! (Elapsed: {elapsed_time:.1f}s)")
    print("==================================================================")

if __name__ == "__main__":
    run_pipeline()
