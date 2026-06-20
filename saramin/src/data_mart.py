"""
이 모듈은 사람인 채용공고 크롤링 데이터를 기반으로 인력 턴오버(퇴사율) 리스크 분석을 심도 있게 수행하기 위해
비즈니스 데이터 마트(Data Mart)를 구축하고 고도화된 피처 엔지니어링(Feature Engineering)을 처리합니다.

주요 피처 엔지니어링 로직:
1. 회사별 '공고 회전문 지수(Rotation Index)' 산출:
   - 기업 규모(company_type)에 따라 가상의 국민연금 가입 종사자 수를 매핑하여 분모로 삼고,
     특정 회사-직무별 연간 누적 공고 건수를 분자로 삼아 회전문 지수를 구합니다.
2. 직무별 기저값(Baseline 12일) 대비 '공고 재등록 주기(Interval)' 계산 및 '독박 직무(Toxic Rotation)' 판정:
   - 등록 경과일과 게시 기간을 기반으로 공고 등록일(registration_date) 및 마감일(end_date)을 역산합니다.
   - 동일 기업 내 동일 직무 분류에 대해 이전 공고의 마감일과 다음 공고의 등록일 간격(Time Delta)을 연산하고,
     2주 이내(14일 이하) 재등록 현상이 반복되는지 탐지하여 독박 직무 여부를 판정합니다.
3. 텍스트 마이닝을 통한 JD(직무기술서) 특징 추출 및 독성/유사도 스코어 산출:
   - 추상적이고 회피적인 키워드('가족 같은', '열정', '급구' 등)의 포함 여부를 스코어링하고,
     동일 기업 내 공고 텍스트 간 자카드 유사도를 계산하여 '복사-붙여넣기 비율(Copy-Paste Ratio)'을 측정합니다.
"""

import os
import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 파일 경로 정의
INPUT_CSV_PATH = "saramin/data/saramin_jobs.csv"
OUTPUT_DATAMART_PATH = "saramin/data/saramin_turnover_datamart.csv"

def jaccard_similarity(str1, str2):
    """
    두 텍스트 간의 자카드 유사도(Jaccard Similarity)를 단어 수준에서 계산합니다.
    """
    words1 = set(re.findall(r'\w+', str(str1)))
    words2 = set(re.findall(r'\w+', str(str2)))
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union)

def build_advanced_turnover_data_mart():
    """
    사람인 채용 공고 데이터를 로드하여 회전문 지수, 재등록 주기, JD 텍스트 특징을 수치화한
    퇴사율 분석용 비즈니스 데이터 마트를 구축합니다.
    """
    if not os.path.exists(INPUT_CSV_PATH):
        raise FileNotFoundError(f"원본 데이터 파일이 존재하지 않습니다: {INPUT_CSV_PATH}")
        
    df = pd.read_csv(INPUT_CSV_PATH)
    
    # 0. 날짜 파생변수 생성 (기준일은 데이터 수집 시점인 2026-06-20)
    base_date = datetime(2026, 6, 20)
    
    # 등록일(registration_date)과 마감일(end_date) 생성
    df["reg_days_ago_clean"] = pd.to_numeric(df["reg_days_ago"], errors="coerce").fillna(0).astype(int)
    df["posting_period_clean"] = pd.to_numeric(df["posting_period_days"], errors="coerce").fillna(12).astype(int)
    
    df["registration_date"] = df["reg_days_ago_clean"].apply(lambda x: base_date - timedelta(days=x))
    df["end_date"] = df.apply(lambda row: row["registration_date"] + timedelta(days=row["posting_period_clean"]), axis=1)
    
    # 1. 1️⃣ 회사별 '공고 회전문 지수 (Rotation Index)' 파생변수 생성
    # 국민연금 기준 가상의 회사 전체 종사자 수 매핑
    employee_map = {
        "대기업": 1500,
        "코스피": 1000,
        "공사·공기업": 800,
        "코스닥": 300,
        "외국계": 150,
        "일반기업": 50
    }
    df["employee_count"] = df["company_type"].map(employee_map).fillna(40).astype(int)
    
    # 첫 번째 대표 직무를 주 직무(primary_sector)로 파싱
    df["primary_sector"] = df["sectors"].fillna("").apply(
        lambda x: [s.strip() for s in x.split(",")][0] if x else "기타"
    )
    
    # 회사별 & 직무별 총 공고 등록 횟수
    company_sector_counts = df.groupby(["company", "primary_sector"]).size().to_dict()
    df["company_sector_postings"] = df.apply(
        lambda row: company_sector_counts.get((row["company"], row["primary_sector"]), 1), axis=1
    )
    
    # Rotation Index 산출: 특정 직무 공고 등록 횟수 / 회사 전체 종사자 수
    df["rotation_index"] = df["company_sector_postings"] / df["employee_count"]
    
    # 2. 2️⃣ 직무별 기저값(12일) 대비 '공고 재등록 주기(Interval)' 계산 및 '독박 직무' 판정
    # 동일 기업 내에서 동일한 직무의 공고 간 등록 간격을 계산하기 위해 정렬
    df_sorted = df.sort_values(by=["company", "primary_sector", "registration_date"])
    
    # 동일 회사-직무 그룹화하여 이전 마감일과 다음 등록일의 차이 계산
    df_sorted["prev_end_date"] = df_sorted.groupby(["company", "primary_sector"])["end_date"].shift(1)
    
    # 간격(Interval) 일수 계산 (등록일 - 이전 마감일)
    def calc_interval(row):
        if pd.isna(row["prev_end_date"]):
            return np.nan
        delta = (row["registration_date"] - row["prev_end_date"]).days
        return delta
        
    df_sorted["reposting_interval_days"] = df_sorted.apply(calc_interval, axis=1)
    
    # 독박 직무(Toxic Rotation) 판정: 
    # 동일 기업-직무 내에서 2주(14일) 이내 재등록이 발생하는 패턴 탐지
    # 데이터셋의 시간 범위가 10일 이내이므로(reg_days_ago 0~9일) 14일 이하의 리프레시 횟수를 카운트함
    df_sorted["is_under_14_days"] = (df_sorted["reposting_interval_days"] <= 14).astype(int)
    
    toxic_group = df_sorted.groupby(["company", "primary_sector"])["is_under_14_days"].sum().reset_index()
    # 수집 데이터 크기가 600개이므로, 9일간의 범위 내에서 1회 이상 재등록이 확인되면 회전문이 돌기 시작하는 신호로 판단
    toxic_group["is_toxic_rotation"] = (toxic_group["is_under_14_days"] >= 1).astype(int)
    
    # 원본 데이터에 병합 (고유 키인 link를 기준으로 1:1 결합 보장)
    df_merged = pd.merge(
        df, 
        df_sorted[["link", "reposting_interval_days"]], 
        on="link",
        how="left"
    )
    
    df_merged = pd.merge(
        df_merged,
        toxic_group[["company", "primary_sector", "is_toxic_rotation"]],
        on=["company", "primary_sector"],
        how="left"
    )
    
    # 3. 3️⃣ 텍스트 마이닝: JD 특징 추출 및 독성/유사도 분석
    # 추상적 단어 및 턴오버 유발성 키워드 목록
    toxic_keywords = ["가족", "가족같은", "열정", "급구", "긴급", "인내", "보조", "초보", "단순", "야근"]
    
    def calc_toxic_jd_score(row):
        text = str(row["title"]) + " " + str(row["sectors"])
        score = sum(1 for kw in toxic_keywords if kw in text)
        return score
        
    df_merged["toxic_jd_score"] = df_merged.apply(calc_toxic_jd_score, axis=1)
    
    # 동일 회사 내 공고 간 텍스트 유사도 (자카드) 계산 -> 복사 붙여넣기 지수
    df_sorted_copy = df_merged.sort_values(by=["company", "registration_date"])
    df_sorted_copy["prev_title"] = df_sorted_copy.groupby("company")["title"].shift(1)
    
    def calc_title_similarity(row):
        if pd.isna(row["prev_title"]) or pd.isna(row["title"]):
            return 0.0
        return jaccard_similarity(row["title"], row["prev_title"])
        
    df_sorted_copy["copy_paste_ratio"] = df_sorted_copy.apply(calc_title_similarity, axis=1)
    
    # 원본 병합 (고유 키인 link 기준으로 1:1 결합 보장)
    df_final = pd.merge(
        df_merged,
        df_sorted_copy[["link", "copy_paste_ratio"]],
        on="link",
        how="left"
    )
    
    # 4. 분석 위험 점수 통합 재산정 (100점 만점)
    # Rotation Index, Toxic Rotation 여부, 복사 붙여넣기 유사도, 독성 키워드 스코어를 조합
    # - rotation_index 위험도 (25%)
    # - is_toxic_rotation 여부 (25%)
    # - copy_paste_ratio 유사도 (25%)
    # - toxic_jd_score 위험도 (25%)
    
    def normalize(series):
        min_v = series.min()
        max_v = series.max()
        if max_v == min_v:
            return pd.Series(0.5, index=series.index)
        return (series - min_v) / (max_v - min_v)
        
    norm_rot = normalize(df_final["rotation_index"])
    norm_toxic = df_final["is_toxic_rotation"].fillna(0)
    norm_copy = normalize(df_final["copy_paste_ratio"].fillna(0))
    norm_jd = normalize(df_final["toxic_jd_score"])
    
    df_final["turnover_risk_score"] = (
        (norm_rot * 0.25) +
        (norm_toxic * 0.25) +
        (norm_copy * 0.25) +
        (norm_jd * 0.25)
    ) * 100
    
    # 등급 분류 (High, Medium, Low)
    df_final["turnover_risk_level"] = pd.cut(
        df_final["turnover_risk_score"],
        bins=[0, 30, 60, 100],
        labels=["Low", "Medium", "High"],
        include_lowest=True
    )
    
    # 5. 불필요 임시 컬럼 정리 및 정렬
    columns_to_save = [
        "company", "company_type", "employee_count", "primary_sector", "title", 
        "registration_date", "end_date", "posting_period_clean", "reposting_interval_days",
        "company_sector_postings", "rotation_index", "is_toxic_rotation", 
        "toxic_jd_score", "copy_paste_ratio", "turnover_risk_score", "turnover_risk_level", "link"
    ]
    
    df_datamart = df_final[columns_to_save].rename(columns={
        "posting_period_clean": "posting_period_days",
        "copy_paste_ratio": "jd_copy_paste_ratio"
    })
    
    # CSV 저장
    os.makedirs(os.path.dirname(OUTPUT_DATAMART_PATH), exist_ok=True)
    df_datamart.to_csv(OUTPUT_DATAMART_PATH, index=False, encoding="utf-8-sig")
    
    print("\n=== [고급 턴오버 데이터 마트 구축 결과] ===")
    print(f"저장 경로: {OUTPUT_DATAMART_PATH}")
    print(f"전체 레코드 수: {len(df_datamart)}개")
    print(f"독박 직무(Toxic Rotation) 탐지 수: {df_datamart['is_toxic_rotation'].sum()}건")
    print("\n--- 위험도 레벨별 통계 ---")
    print(df_datamart["turnover_risk_level"].value_counts())
    
    # 텍스트 마이닝 군집별 Gap 분석 요약 출력
    print("\n--- [텍스트 마이닝 Gap 분석 요약] ---")
    high_risk_companies = df_datamart[df_datamart["turnover_risk_score"] >= 50]["company"].unique()
    low_risk_companies = df_datamart[df_datamart["turnover_risk_score"] < 25]["company"].unique()
    print(f"위험 군집 기업 수 (점수 >= 50): {len(high_risk_companies)}개")
    print(f"우수 군집 기업 수 (점수 < 25): {len(low_risk_companies)}개")
    
    return df_datamart
