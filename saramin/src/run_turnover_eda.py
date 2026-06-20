"""
이 모듈은 인력 턴오버 데이터 마트(saramin_turnover_datamart.csv)를 로드하여 탐색적 데이터 분석(EDA)을 수행합니다.
10개의 분석 차트를 생성하여 saramin/images/ 폴더에 저장하고, 
보고서 작성에 필요한 각종 기초 통계 매트릭스를 saramin/report/turnover_raw_stats.txt 파일에 UTF-8 인코딩으로 저장합니다.

주요 분석 내용:
1. 턴오버 위험 등급(turnover_risk_level) 및 독박 직무(is_toxic_rotation) 기본 빈도
2. 수치형 피처(rotation_index, reposting_interval_days, jd_copy_paste_ratio, toxic_jd_score) 분포 분석
3. 기업 규모별 턴오버 리스크 점수 비교 분석
4. 턴오버 고위험 공고 제목에 대한 TF-IDF 핵심 키워드 마이닝
5. 위험 수준과 독박 직무 여부의 교차 빈도 열지도(Heatmap) 생성
"""

import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
import koreanize_matplotlib

# 경로 설정
DATA_PATH = "saramin/data/saramin_turnover_datamart.csv"
IMAGE_DIR = "saramin/images"
REPORT_DIR = "saramin/report"
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

def load_data():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"데이터 파일이 없습니다: {DATA_PATH}")
    return pd.read_csv(DATA_PATH)

def analyze_basic_stats(df):
    print("=== [1. 턴오버 데이터 마트 초기 검토] ===")
    print(f"총 행 수: {df.shape[0]}개")
    print(f"총 열 수: {df.shape[1]}개")
    print(f"중복 레코드 수: {df.duplicated().sum()}개")
    print("\n--- 결측치 정보 ---")
    print(df.isnull().sum())
    
    print("\n--- 수치형 피처 기술 통계 ---")
    numeric_cols = [
        "employee_count", "reposting_interval_days", "company_sector_postings",
        "rotation_index", "toxic_jd_score", "jd_copy_paste_ratio", "turnover_risk_score"
    ]
    print(df[numeric_cols].describe())
    
    print("\n--- 범주형 및 바이너리 피처 빈도 ---")
    for col in ["company_type", "primary_sector", "is_toxic_rotation", "turnover_risk_level"]:
        print(f"\n[{col} 빈도표]")
        print(df[col].value_counts(dropna=False).head(10))
    print("=========================================\n")

def generate_turnover_visualizations(df):
    print("=== [2. 데이터 시각화 생성 시작] ===")
    plt.rcParams['figure.figsize'] = (10, 6)
    plt.rcParams['font.size'] = 11
    plt.rcParams['axes.unicode_minus'] = False
    
    # 1. 턴오버 위험 수준 분포 (turnover_risk_level)
    plt.figure()
    risk_counts = df["turnover_risk_level"].value_counts(dropna=False)
    risk_counts.plot(kind="bar", color="#d62728")
    plt.title("턴오버 위험 수준 분포 (turnover_risk_level)")
    plt.xlabel("위험 등급")
    plt.ylabel("공고 수")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "turnover_01_risk_level_dist.png"))
    plt.close()
    print("차트 1 저장: turnover_01_risk_level_dist.png")
    
    # 2. 독박 직무 판정 여부 분포 (is_toxic_rotation)
    plt.figure()
    toxic_counts = df["is_toxic_rotation"].value_counts()
    toxic_counts.plot(kind="pie", autopct="%1.1f%%", colors=["#2ca02c", "#d62728"], labels=["정상 직무 (0)", "독박 직무 (1)"])
    plt.title("독박 직무(Toxic Rotation) 판정 분포")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "turnover_02_toxic_rotation_pie.png"))
    plt.close()
    print("차트 2 저장: turnover_02_toxic_rotation_pie.png")
    
    # 3. 직무별(primary_sector) 평균 턴오버 위험 점수 비교 (상위 30개)
    plt.figure(figsize=(12, 6))
    df_sec_risk = df.groupby("primary_sector")["turnover_risk_score"].mean().reset_index()
    df_sec_risk = df_sec_risk.sort_values(by="turnover_risk_score", ascending=False).head(30)
    plt.bar(df_sec_risk["primary_sector"], df_sec_risk["turnover_risk_score"], color="#1f77b4")
    plt.title("직무별 평균 턴오버 위험 점수 상위 30개")
    plt.xlabel("직무 분야")
    plt.ylabel("평균 턴오버 위험 점수 (100점 만점)")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "turnover_03_sector_risk_bar.png"))
    plt.close()
    print("차트 3 저장: turnover_03_sector_risk_bar.png")
    
    # 4. 공고 회전문 지수 분포 (rotation_index)
    plt.figure()
    plt.hist(df["rotation_index"], bins=20, color="#9467bd", edgecolor="black")
    plt.title("공고 회전문 지수 분포 (Rotation Index)")
    plt.xlabel("회전문 지수")
    plt.ylabel("빈도")
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "turnover_04_rotation_index_hist.png"))
    plt.close()
    print("차트 4 저장: turnover_04_rotation_index_hist.png")
    
    # 5. 공고 재등록 주기 분포 (reposting_interval_days) - 결측치 제외
    plt.figure()
    df_interval = df[df["reposting_interval_days"].notna()]
    if not df_interval.empty:
        plt.boxplot(df_interval["reposting_interval_days"], vert=False, patch_artist=True,
                    boxprops=dict(facecolor="#8c564b", color="black"),
                    medianprops=dict(color="red"))
        plt.title("공고 재등록 주기 분포 상자그림 (Interval)")
        plt.xlabel("재등록 주기 (일 간격)")
    else:
        plt.text(0.5, 0.5, "재등록 데이터 없음", ha='center', va='center')
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "turnover_05_reposting_interval_box.png"))
    plt.close()
    print("차트 5 저장: turnover_05_reposting_interval_box.png")
    
    # 6. JD 복사-붙여넣기 비율 분포 (jd_copy_paste_ratio)
    plt.figure()
    plt.hist(df["jd_copy_paste_ratio"].fillna(0), bins=15, color="#bcbd22", edgecolor="black")
    plt.title("JD 복사-붙여넣기 지수 분포 (Jaccard Similarity)")
    plt.xlabel("유사도 지수 (1.0 = 동일 공고)")
    plt.ylabel("빈도")
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "turnover_06_copy_paste_ratio_hist.png"))
    plt.close()
    print("차트 6 저장: turnover_06_copy_paste_ratio_hist.png")
    
    # 7. JD 독성 점수 분포 (toxic_jd_score)
    plt.figure()
    df["toxic_jd_score"].value_counts().sort_index().plot(kind="bar", color="#e377c2")
    plt.title("JD 독성 키워드 점수 분포 (toxic_jd_score)")
    plt.xlabel("독성 키워드 검출 수 (개)")
    plt.ylabel("공고 수")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "turnover_07_toxic_jd_score_bar.png"))
    plt.close()
    print("차트 7 저장: turnover_07_toxic_jd_score_bar.png")
    
    # 8. 기업 규모(company_type)에 따른 평균 턴오버 위험 점수 비교
    plt.figure()
    df_comp_risk = df.groupby("company_type")["turnover_risk_score"].mean().reset_index()
    df_comp_risk = df_comp_risk.sort_values(by="turnover_risk_score", ascending=False)
    plt.bar(df_comp_risk["company_type"], df_comp_risk["turnover_risk_score"], color="#17becf")
    plt.title("기업 규모별 평균 턴오버 위험 점수")
    plt.xlabel("기업 규모")
    plt.ylabel("평균 턴오버 위험 점수")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "turnover_08_company_type_risk_bar.png"))
    plt.close()
    print("차트 8 저장: turnover_08_company_type_risk_bar.png")
    
    # 9. 턴오버 고위험 군집(High Risk) 공고 제목의 TF-IDF 분석 (상위 30개)
    plt.figure(figsize=(12, 6))
    high_risk_df = df[df["turnover_risk_score"] >= 40]
    titles = high_risk_df["title"].fillna("").tolist()
    
    df_tfidf = pd.DataFrame()
    if titles:
        vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b\w+\b', max_features=100)
        tfidf_matrix = vectorizer.fit_transform(titles)
        feature_names = vectorizer.get_feature_names_out()
        tfidf_sums = tfidf_matrix.sum(axis=0).A1
        df_tfidf = pd.DataFrame({"word": feature_names, "score": tfidf_sums})
        df_tfidf = df_tfidf.sort_values(by="score", ascending=False).head(30)
        
        plt.bar(df_tfidf["word"], df_tfidf["score"], color="#7f7f7f")
        plt.title("고위험 군집 채용 공고 제목 TF-IDF 상위 30개")
        plt.xlabel("핵심 키워드")
        plt.ylabel("TF-IDF 중요도 점수")
        plt.xticks(rotation=90)
    else:
        plt.text(0.5, 0.5, "고위험군 데이터 없음", ha='center', va='center')
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "turnover_09_high_risk_tfidf_bar.png"))
    plt.close()
    print("차트 9 저장: turnover_09_high_risk_tfidf_bar.png")
    
    # 10. 턴오버 위험 등급(turnover_risk_level)과 독박 직무 여부(is_toxic_rotation) 교차 분석
    plt.figure(figsize=(8, 6))
    ct = pd.crosstab(df["turnover_risk_level"], df["is_toxic_rotation"])
    sns.heatmap(ct, annot=True, fmt="d", cmap="Oranges", cbar=True)
    plt.title("턴오버 위험 등급 vs 독박 직무 교차 빈도 (Heatmap)")
    plt.xlabel("독박 직무 여부 (0: 정상, 1: 독박)")
    plt.ylabel("턴오버 위험 등급")
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "turnover_10_risk_vs_toxic_heatmap.png"))
    plt.close()
    print("차트 10 저장: turnover_10_risk_vs_toxic_heatmap.png")
    
    print("=== [시각화 생성 완료] ===")
    
    # 보고서 보조용 출력
    print("\n--- [High Risk TF-IDF Table] ---")
    if not df_tfidf.empty:
        print(df_tfidf.to_string(index=False))
    print("\n--- [Risk Level vs Toxic Rotation Crosstab] ---")
    print(ct.to_string())

if __name__ == "__main__":
    import sys
    orig_stdout = sys.stdout
    with open(os.path.join(REPORT_DIR, "turnover_raw_stats.txt"), "w", encoding="utf-8") as f:
        sys.stdout = f
        df = load_data()
        analyze_basic_stats(df)
        generate_turnover_visualizations(df)
    sys.stdout = orig_stdout
    print("턴오버 EDA 분석 완료! 결과가 'saramin/report/turnover_raw_stats.txt'에 저장되었습니다.")
