"""
이 모듈은 사람인 채용공고 크롤링 데이터를 기반으로 인력 턴오버(퇴사율) 리스크 분석을 수행하기 위해
비즈니스 데이터 마트(Data Mart)를 설계하고 피처 엔지니어링(Feature Engineering)을 처리하는 로직을 제공합니다.

주요 구현 사항:
1. 시장 평균 공고 게시 기간의 중앙값(12일)을 기준으로 한 기간 편차(Duration Deviation) 계산
2. 회사별 및 직무별 공고 재등록 빈도(Re-posting Frequency) 집계
3. 기업 규모별 연봉 격차 및 복리후생 지표 산출
4. 직무 기술 설명(JD)의 텍스트 밀도 및 요구 스택 수 수치화
5. 인사팀 관점의 가중치 기반 '턴오버 위험 점수(Turnover Risk Score)' 도출 및 데이터 마트 CSV 저장
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime

# 상대경로 정의
INPUT_CSV_PATH = "saramin/data/saramin_jobs.csv"
OUTPUT_DATAMART_PATH = "saramin/data/saramin_turnover_datamart.csv"

def build_turnover_data_mart():
    """
    사람인 원본 수집 데이터를 읽어 퇴사율 분석용 데이터 마트(Data Mart)를 구축합니다.
    """
    if not os.path.exists(INPUT_CSV_PATH):
        raise FileNotFoundError(f"원본 데이터 파일이 없습니다: {INPUT_CSV_PATH}")
        
    df = pd.read_csv(INPUT_CSV_PATH)
    
    # 0. 데이터 전처리 및 정비
    # posting_period_days 결측치/알수없음 처리 및 수치형 변환
    df["posting_period_days_clean"] = pd.to_numeric(df["posting_period_days"], errors="coerce")
    
    # 분석용 데이터프레임 복사
    dm = df.copy()
    
    # 1. 공고 유지 기간 격차 및 편차 피처 생성 (시장 중앙값 12일 기준)
    market_median_duration = 12
    # 단순 편차 (실제 기간 - 시장 중앙값)
    dm["duration_deviation"] = dm["posting_period_days_clean"] - market_median_duration
    # 절대 편차 (중앙값과의 격차 수준)
    dm["abs_duration_deviation"] = dm["duration_deviation"].abs()
    # 공고가 시장 평균 대비 비정상적으로 짧은지 여부 (예: 조기 마감 또는 채용 급구) -> 1 or 0
    dm["is_short_posting"] = (dm["posting_period_days_clean"] < market_median_duration).astype(int)
    # 공고가 시장 평균 대비 비정상적으로 긴지 여부 (예: 구인난 또는 상시 채용) -> 1 or 0
    dm["is_long_posting"] = (dm["posting_period_days_clean"] > market_median_duration).astype(int)
    
    # 2. 동일 회사 및 직무별 공고 재등록 빈도(Re-posting Frequency) 집계
    # 회사별 총 채용공고 등록 건수
    company_counts = dm["company"].value_counts().to_dict()
    dm["company_reposting_count"] = dm["company"].map(company_counts)
    
    # 개별 직무 분야(sectors) 분할 후 빈도 분석을 위해 텍스트 파싱
    # sectors는 쉼표로 연결되어 있으므로 첫 번째 대표 직무를 기준으로 매핑하거나 전체 매핑
    dm["primary_sector"] = dm["sectors"].fillna("").apply(lambda x: [s.strip() for s in x.split(",")][0] if x else "기타")
    sector_counts = dm["primary_sector"].value_counts().to_dict()
    dm["sector_reposting_count"] = dm["primary_sector"].map(sector_counts)
    
    # 3. 기업 특징 피처 엔지니어링 (연봉 및 복지 지표 보강 데이터 시뮬레이션 기반 모델링)
    # 실제 수집 데이터의 salary가 대부분 '면접 후 협의'이므로 기업 규모와 연계된 연봉 추정값 부여
    # (data_generator.py의 가이드 모델 활용)
    salary_map = {"대기업": 5800, "일반기업": 3800, "공사·공기업": 4200, "코스닥": 4500, "외국계": 4800, "코스피": 5200}
    dm["estimated_salary"] = dm["company_type"].map(salary_map).fillna(3500)
    
    # 복지 데이터 가공: sectors 또는 타이틀에 포함된 키워드로 대략적인 복지 매핑
    # 텍스트에 포함될 만한 대표 복지 키워드 매칭
    title_and_sector = (dm["title"] + " " + dm["sectors"]).fillna("")
    dm["has_flexible_work"] = title_and_sector.str.contains("유연근무|시차출퇴근|재택|자율", case=False).astype(int)
    dm["has_snack_bar"] = title_and_sector.str.contains("간식|스낵|음료|커피", case=False).astype(int)
    dm["has_incentive"] = title_and_sector.str.contains("인센티브|성과급|보너스", case=False).astype(int)
    
    # 가상의 복지 개수 지표 생성 (기업 규모별 차등화)
    welfare_count_base = {"대기업": 7, "일반기업": 3, "공사·공기업": 5, "코스닥": 4, "외국계": 5, "코스피": 6}
    dm["estimated_welfare_count"] = dm["company_type"].map(welfare_count_base).fillna(2)
    # 복지 지표 보완 (발견된 키워드 추가 합산)
    dm["estimated_welfare_count"] += (dm["has_flexible_work"] + dm["has_snack_bar"] + dm["has_incentive"])
    
    # 4. JD(Job Description) 형태 및 정보 밀도 분석
    # 공고 제목 글자 수 (정보성 판단 지표)
    dm["title_length"] = dm["title"].fillna("").apply(len)
    # 요구되는 직무 키워드 개수
    dm["sector_count"] = dm["sectors"].fillna("").apply(lambda x: len(x.split(",")) if x else 0)
    
    # 5. 인사팀 관점의 가중치 기반 '턴오버 위험 점수 (Turnover Risk Score)' 산출 (100점 만점)
    # 가설 설정: 
    # - 연봉이 낮을수록 턴오버가 높다. (가중치 20%)
    # - 복리후생 혜택이 적을수록 턴오버가 높다. (가중치 20%)
    # - 동일 회사의 재등록 빈도가 높을수록 턴오버가 높다. (가중치 30%)
    # - 공고 유지 기간의 격차가 클수록 (너무 짧아 즉시이탈이 많거나, 너무 길어 장기공석) 턴오버 리스크 징후이다. (가중치 30%)
    
    # 정규화 함수 (Min-Max Scaling)
    def min_max_normalize(series, invert=False):
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return pd.Series(0.5, index=series.index)
        normalized = (series - min_val) / (max_val - min_val)
        if invert:
            return 1.0 - normalized
        return normalized

    # 각 요인별 위험도 산출 (0 ~ 1 범위)
    salary_risk = min_max_normalize(dm["estimated_salary"], invert=True)
    welfare_risk = min_max_normalize(dm["estimated_welfare_count"], invert=True)
    reposting_risk = min_max_normalize(dm["company_reposting_count"])
    duration_risk = min_max_normalize(dm["abs_duration_deviation"].fillna(0))
    
    # 최종 가중치 합산 턴오버 위험 점수 계산
    dm["turnover_risk_score"] = (
        (salary_risk * 0.20) +
        (welfare_risk * 0.20) +
        (reposting_risk * 0.30) +
        (duration_risk * 0.30)
    ) * 100
    
    # 위험 등급 분류 (High, Medium, Low)
    dm["turnover_risk_level"] = pd.cut(
        dm["turnover_risk_score"], 
        bins=[0, 40, 70, 100], 
        labels=["Low", "Medium", "High"],
        include_lowest=True
    )
    
    # 6. 불필요한 보조 컬럼 제거 및 정렬
    columns_order = [
        "company", "company_type", "primary_sector", "title", "title_length", "sector_count",
        "posting_period_days_clean", "duration_deviation", "abs_duration_deviation",
        "is_short_posting", "is_long_posting", "company_reposting_count", "sector_reposting_count",
        "estimated_salary", "estimated_welfare_count", "has_flexible_work", "has_snack_bar", "has_incentive",
        "turnover_risk_score", "turnover_risk_level", "link"
    ]
    dm_final = dm[columns_order].rename(columns={"posting_period_days_clean": "posting_period_days"})
    
    # 결과 파일 저장
    os.makedirs(os.path.dirname(OUTPUT_DATAMART_PATH), exist_ok=True)
    dm_final.to_csv(OUTPUT_DATAMART_PATH, index=False, encoding="utf-8-sig")
    
    print(f"턴오버 분석 비즈니스 데이터 마트 구축 성공: {OUTPUT_DATAMART_PATH}")
    print(f"전체 레코드 수: {len(dm_final)}개")
    print(f"위험 수준 분포:\n{dm_final['turnover_risk_level'].value_counts()}")
    
    return dm_final

if __name__ == "__main__":
    build_turnover_data_mart()
