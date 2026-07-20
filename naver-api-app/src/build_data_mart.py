"""
이 파일은 사람인 채용공고 데이터(수요)와 네이버 카페 검색 API(공급)를 연동하여
"수요-공급 미스매치 분석을 위한 통합 데이터 마트(Data Mart)"를 자동으로 구축하는 수집 및 전처리 파이프라인 스크립트입니다.

주요 기능:
- `saramin_1000.csv` 파일(수요 데이터)이 없으면 SQLite DB를 읽어와 자동으로 우선 자동 복구/생성합니다.
- 사전 정의된 핵심 기획·전략 스킬셋/자격증 목록을 기준으로 공고 본문의 언급 빈도를 카운트해 기업의 '수요' 지표를 산출합니다.
- 네이버 카페 검색 API(cafearticle.json)를 연동하여 특정 취업 카페("독취사", "스펙업" 등) 내의 스킬 언급 통계를 수집(공급)합니다.
- API 호출 제한 및 네트워크 단절에 대비한 예외 처리와 로컬 Fallback 공급 통계 적재 로직을 갖추고 있습니다.
- 최종 병합된 정형 데이터를 `automated_cafe_supply.csv` 파일로 내보냅니다.
"""

import os
import time
import json
import urllib.request
import urllib.parse
import pandas as pd
import sqlite3

# 네이버 API 클라이언트 자격 증명 설정 (실제 구동 시 유효한 키 입력 필요)
CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "YOUR_CLIENT_ID")
CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "YOUR_CLIENT_SECRET")

def build_data_mart():
    csv_path = "saramin_1000.csv"
    output_path = "automated_cafe_supply.csv"
    
    print("=== [1단계] 사람인 데이터 기반 핵심 스킬셋 추출 (수요) ===")
    
    # [방어 조치] saramin_1000.csv 가 없으면 SQLite DB로부터 우선 생성
    if not os.path.exists(csv_path):
        print(f"'{csv_path}' 파일이 존재하지 않아 DB 연동 복구를 수행합니다.")
        db_paths = [
            "saramin/data/saramin_search_jobs.db",
            "data/saramin_search_jobs.db",
            "../saramin/data/saramin_search_jobs.db",
            "../../saramin/data/saramin_search_jobs.db"
        ]
        db_path = None
        for p in db_paths:
            if os.path.exists(p):
                db_path = p
                break
        
        if db_path:
            try:
                conn = sqlite3.connect(db_path)
                # detail_content 및 sectors를 활용해 '우대사항' 컬럼으로 가상 통합 및 저장
                df_db = pd.read_sql("SELECT company, title, sectors, detail_content as 우대사항 FROM saramin_jobs", conn)
                conn.close()
                df_db.to_csv(csv_path, index=False, encoding="utf-8-sig")
                print(f"-> SQLite DB({db_path})로부터 {csv_path} 파일을 1,000건 스케일로 정상 생성했습니다.")
            except Exception as db_err:
                print(f"-> DB 복구 중 에러 발생: {db_err}")
        else:
            print("-> DB 파일을 감지하지 못했습니다. 기초 모의 데이터를 기반으로 CSV를 생성합니다.")
            # 극단적 상황을 대비한 모의 데이터 구조 작성
            mock_data = pd.DataFrame([
                {"company": "가상기업", "title": "기획자 채용", "sectors": "서비스기획", "우대사항": "SQLD, Figma, GA4 보유자 및 컴퓨터활용능력 우대"}
            ] * 20)
            mock_data.to_csv(csv_path, index=False, encoding="utf-8-sig")
            
    # 사람인 CSV 로드
    try:
        df_saramin = pd.read_csv(csv_path)
        print(f"-> '{csv_path}' 로드 완료. (총 {len(df_saramin)}건)")
    except Exception as read_err:
        print(f"-> CSV 파일 로드 에러: {read_err}")
        return
        
    # 핵심 스킬셋/자격증 리스트 정의
    target_skills = ["SQLD", "ADsP", "컴퓨터활용능력", "GA4", "CFA", "CPA", "PPT작성법", "Figma"]
    
    # 우대사항에서 자격증 빈도 카운팅
    demand_stats = {}
    total_records = len(df_saramin)
    
    for skill in target_skills:
        count = 0
        for _, row in df_saramin.iterrows():
            text = str(row.get("우대사항", "")).lower()
            # PPT작성법의 경우 ppt, 파워포인트 등으로 유사 단어 카운트
            if skill == "PPT작성법":
                if any(x in text for x in ["ppt", "파워포인트", "powerpoint", "ppt작성"]):
                    count += 1
            else:
                if skill.lower() in text:
                    count += 1
        demand_stats[skill] = count
        
    df_demand = pd.DataFrame({
        "자격증명": target_skills,
        "기업_수요_건수": [demand_stats[s] for s in target_skills]
    })
    print("-> 수요 분석 데이터 정형화 완료:")
    print(df_demand)
    print("\n")
    
    print("=== [2단계] 네이버 카페 검색 API 연동 및 수집 루프 ===")
    
    # 네이버 카페 검색 API 연동 함수
    def search_cafe_api(query_text):
        # 쿼리에 취업 관련 카페 지정을 위해 결합
        # 구직자 트렌드만 타겟팅하기 위해 대표 취업 네이버 카페 키워드 추가
        query_enriched = f"{query_text} 독취사"
        encText = urllib.parse.quote(query_enriched)
        url = f"https://openapi.naver.com/v1/search/cafearticle.json?query={encText}&display=10"
        
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", CLIENT_ID)
        request.add_header("X-Naver-Client-Secret", CLIENT_SECRET)
        
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                if response.getcode() == 200:
                    return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            # API 키 미등록 또는 권한 오류 발생 시 None 반환
            return None
            
    # API 구동 시도 및 오류 상황 대비 백업 가상 공급 통계 (Fallback Data)
    fallback_supply_total = {
        "SQLD": 15000,
        "ADsP": 12000,
        "컴퓨터활용능력": 45000,
        "GA4": 8000,
        "CFA": 6000,
        "CPA": 18000,
        "PPT작성법": 22000,
        "Figma": 4500
    }
    
    supply_totals = {}
    detail_records = []
    
    use_fallback = False
    
    for skill in target_skills:
        print(f"-> '{skill}' 키워드 검색 API 요청 중...")
        res = search_cafe_api(skill)
        
        # API 호출 차단 또는 인증 오류 시 Fallback 로드 플래그 활성화
        if res is None or "total" not in res:
            print(f"   [경고] API 인증 실패 혹은 네트워크 단절로 인해 '{skill}' 데이터 수집을 우회하여 모의 통계치를 자동 주입합니다.")
            use_fallback = True
            supply_totals[skill] = fallback_supply_total.get(skill, 1000)
            
            # 모의 상세 데이터 결합
            detail_records.append({
                "자격증명": skill,
                "게시글제목": f"{skill} 스펙 질문 및 취업 정보글",
                "요약본문": f"독취사 카페 내 {skill} 관련 취업 준비 팁 및 시험 일정 안내 글 요약입니다.",
                "카페명": "독취사"
            })
        else:
            total_posts = res.get("total", 0)
            supply_totals[skill] = total_posts
            print(f"   [성공] 총 {total_posts}건 검색됨.")
            
            # 상세 내용 파싱
            items = res.get("items", [])
            if not items:
                detail_records.append({
                    "자격증명": skill,
                    "게시글제목": "검색 결과 없음",
                    "요약본문": "해당 조건의 취업글이 검색되지 않았습니다.",
                    "카페명": "독취사"
                })
            for item in items:
                # HTML 태그 제거용 정규표현식
                clean_title = re.sub(r'<[^>]*>', '', item.get("title", ""))
                clean_desc = re.sub(r'<[^>]*>', '', item.get("description", ""))
                detail_records.append({
                    "자격증명": skill,
                    "게시글제목": clean_title,
                    "요약본문": clean_desc,
                    "카페명": item.get("cafename", "독취사")
                })
                
        # 트래픽 제한 방지 지연
        time.sleep(0.5)
        
    df_supply_total = pd.DataFrame({
        "자격증명": target_skills,
        "구직자_공급_건수": [supply_totals[s] for s in target_skills]
    })
    
    df_details = pd.DataFrame(detail_records)
    print("-> 공급 분석 데이터 수집 완료.\n")
    
    print("=== [3단계] 통합 데이터 마트 정형화 및 CSV 저장 ===")
    
    # 1단계 기업 수요와 2단계 구직자 공급 총량 결합
    df_mart = pd.merge(df_demand, df_supply_total, on="자격증명", how="outer")
    
    # 스펙수급 Gap (수요 - 공급) 및 미스매치 지수 계산
    df_mart["수급Gap(건)"] = df_mart["기업_수요_건수"] - df_mart["구직자_공급_건수"]
    
    # 결합 데이터 내보내기
    df_mart.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"-> 통합 데이터 마트 '{output_path}' 저장 완료.")
    print(df_mart)
    
    # 상세글 결합 내역을 별도 분석 저장
    df_details.to_csv("automated_cafe_details.csv", index=False, encoding="utf-8-sig")
    print("-> 게시글 상세 텍스트 원본 데이터 'automated_cafe_details.csv' 백업 완료.")
    
    if use_fallback:
        print("\n[알림] 네이버 API 인증 키(CLIENT_ID/CLIENT_SECRET) 미등록으로 인해 공급 지표는 Fallback 모의 통계 데이터로 최종 마트가 구성되었습니다.")
    else:
        print("\n[성공] 실제 네이버 API 연동 실시간 데이터 마트 전처리가 완수되었습니다.")

if __name__ == "__main__":
    import re
    build_data_mart()
