"""
이 모듈은 수집된 채용공고 CSV 데이터를 SQLite 데이터베이스 파일로 변환하여 저장하는 스크립트입니다.

주요 기능:
- `saramin/data/saramin_search_jobs.csv` 파일을 Pandas DataFrame으로 읽어옵니다.
- `sqlite3` 라이브러리를 이용하여 `saramin/data/saramin_search_jobs.db` 파일에 접속합니다.
- DataFrame 데이터를 `saramin_jobs` 테이블로 변환하여 적재(덮어쓰기 방식)합니다.
- 데이터베이스 변환 완료 및 적재 건수를 콘솔에 기록합니다.
"""

import pandas as pd
import sqlite3
import os

def convert_csv_to_sqlite():
    csv_path = "saramin/data/saramin_search_jobs.csv"
    db_path = "saramin/data/saramin_search_jobs.db"
    
    if not os.path.exists(csv_path):
        print(f"오류: 대상 CSV 파일({csv_path})이 존재하지 않습니다.")
        return
        
    try:
        # CSV 로드
        print(f"CSV 데이터 로드 중: {csv_path}")
        df = pd.read_csv(csv_path)
        
        # SQLite 연결 생성
        print(f"SQLite DB 연결 중: {db_path}")
        conn = sqlite3.connect(db_path)
        
        # 데이터베이스 적재 (index 제외, 덮어쓰기 옵션)
        table_name = "saramin_jobs"
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        
        # 확인 쿼리 수행
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        print("\nSQLite 데이터베이스 저장 완료!")
        print(f"테이블명: {table_name}")
        print(f"총 적재 행(Row) 수: {row_count}건")
        
        # 연결 종료
        conn.close()
        
    except Exception as e:
        print(f"SQLite 변환 중 에러 발생: {e}")

if __name__ == "__main__":
    convert_csv_to_sqlite()
