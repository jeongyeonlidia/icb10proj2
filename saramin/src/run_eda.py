"""
이 모듈은 사람인 수집 데이터(saramin_jobs.csv)를 로드하여 탐색적 데이터 분석(EDA)을 수행하고,
10개의 분석 차트 이미지를 생성하여 saramin/images/ 폴더에 저장하며,
보고서 작성에 필요한 각종 기초 통계 테이블 정보를 표준 출력으로 렌더링합니다.

주요 분석 내용:
1. 초기 데이터 검토 (행/열 수, 결측치, 중복 데이터)
2. 범주형 데이터 빈도 분석 (기업 규모, 학력 요건, 근무지, 경력 요건)
3. 수치형 데이터 분석 (공고 등록 경과일, 공고 게시 기간)
4. 텍스트 데이터 분석 (공고 제목 및 직무 스택의 TF-IDF 분석)
5. 다변량 및 교차 분석 (기업 규모별 공고 기간 비교, 기업 규모와 학력 교차 분석)
"""

import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
import koreanize_matplotlib

# 프로젝트 경로 설정
DATA_PATH = "saramin/data/saramin_jobs.csv"
IMAGE_DIR = "saramin/images"
os.makedirs(IMAGE_DIR, exist_ok=True)

def load_data():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"데이터 파일이 존재하지 않습니다: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    return df

def analyze_basic_info(df):
    print("=== [1. 초기 데이터 검토] ===")
    print(f"총 행 수: {df.shape[0]}개")
    print(f"총 열 수: {df.shape[1]}개")
    print(f"중복 레코드 수: {df.duplicated().sum()}개")
    print("\n--- 결측치 정보 ---")
    print(df.isnull().sum())
    print("\n--- 데이터 Head(5) ---")
    print(df.head(5).to_string())
    print("\n--- 데이터 Tail(5) ---")
    print(df.tail(5).to_string())
    print("============================\n")

def analyze_descriptive_stats(df):
    print("=== [2. 기술 통계] ===")
    # 수치형 변수 변환 및 통계
    df_clean = df.copy()
    
    # posting_period_days를 수치형으로 안전하게 변환 ('알수없음'은 NaN으로)
    df_clean["posting_period_days"] = pd.to_numeric(df_clean["posting_period_days"], errors='coerce')
    
    print("\n--- 수치형 기술 통계 (reg_days_ago, posting_period_days) ---")
    print(df_clean[["reg_days_ago", "posting_period_days"]].describe())
    
    print("\n--- 범주형 기술 통계 (company_type, education, work_place, career, salary) ---")
    for col in ["company_type", "education", "work_place", "career", "salary"]:
        print(f"\n[{col} 빈도표]")
        print(df_clean[col].value_counts(dropna=False).head(10))
    print("========================\n")
    return df_clean

def generate_visualizations(df):
    print("=== [3. 데이터 시각화 생성 시작] ===")
    
    # Matplotlib 스타일 초기화 (Seaborn 테마 설정 배제)
    plt.rcParams['figure.figsize'] = (10, 6)
    plt.rcParams['font.size'] = 11
    plt.rcParams['axes.unicode_minus'] = False
    
    # 1. 기업 규모 분포 (company_type)
    plt.figure()
    comp_counts = df["company_type"].value_counts(dropna=False)
    comp_counts.plot(kind="bar", color="#1f77b4")
    plt.title("기업 규모 분포 (company_type)")
    plt.xlabel("기업 규모")
    plt.ylabel("공고 수")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "01_company_type_dist.png"))
    plt.close()
    print("차트 1 저장 완료: 01_company_type_dist.png")
    
    # 2. 학력 요건 분포 (education)
    plt.figure()
    edu_counts = df["education"].value_counts(dropna=False)
    edu_counts.plot(kind="bar", color="#ff7f0e")
    plt.title("학력 요건 분포 (education)")
    plt.xlabel("학력 요건")
    plt.ylabel("공고 수")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "02_education_dist.png"))
    plt.close()
    print("차트 2 저장 완료: 02_education_dist.png")
    
    # 3. 근무지 분포 (work_place) - 상위 30개
    plt.figure(figsize=(12, 6))
    wp_counts = df["work_place"].value_counts().head(30)
    wp_counts.plot(kind="bar", color="#2ca02c")
    plt.title("근무지 분포 상위 30개 (work_place)")
    plt.xlabel("근무지")
    plt.ylabel("공고 수")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "03_work_place_dist.png"))
    plt.close()
    print("차트 3 저장 완료: 03_work_place_dist.png")
    
    # 4. 경력 및 계약 형태 분포 (career) - 상위 30개
    plt.figure(figsize=(12, 6))
    career_counts = df["career"].value_counts().head(30)
    career_counts.plot(kind="bar", color="#d62728")
    plt.title("경력 요건 및 근무형태 분포 상위 30개 (career)")
    plt.xlabel("경력 요건 및 근무형태")
    plt.ylabel("공고 수")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "04_career_dist.png"))
    plt.close()
    print("차트 4 저장 완료: 04_career_dist.png")
    
    # 5. 공고 등록 경과일 분포 (reg_days_ago)
    plt.figure()
    df["reg_days_ago"].plot(kind="hist", bins=10, color="#9467bd", edgecolor="black")
    plt.title("공고 등록 경과일 분포 (reg_days_ago)")
    plt.xlabel("등록 경과일 (일 전)")
    plt.ylabel("공고 수")
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "05_reg_days_ago_hist.png"))
    plt.close()
    print("차트 5 저장 완료: 05_reg_days_ago_hist.png")
    
    # 6. 공고 게시 기간 분포 (posting_period_days) - 수치형만 처리
    plt.figure()
    df_valid_period = df[df["posting_period_days"].notna()]
    plt.boxplot(df_valid_period["posting_period_days"], vert=False, patch_artist=True,
                boxprops=dict(facecolor="#8c564b", color="black"),
                medianprops=dict(color="red"))
    plt.title("공고 게시 기간 상자그림 (posting_period_days)")
    plt.xlabel("게시 기간 (일)")
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "06_posting_period_box.png"))
    plt.close()
    print("차트 6 저장 완료: 06_posting_period_box.png")
    
    # 7. 기업 규모별 평균 공고 게시 기간 비교 (company_type vs posting_period_days)
    plt.figure()
    df_grouped = df_valid_period.groupby("company_type")["posting_period_days"].mean().reset_index()
    df_grouped = df_grouped.sort_values(by="posting_period_days", ascending=False)
    plt.bar(df_grouped["company_type"], df_grouped["posting_period_days"], color="#e377c2")
    plt.title("기업 규모별 평균 공고 게시 기간 비교")
    plt.xlabel("기업 규모")
    plt.ylabel("평균 게시 기간 (일)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "07_company_vs_period_bar.png"))
    plt.close()
    print("차트 7 저장 완료: 07_company_vs_period_bar.png")
    
    # 8. 공고 제목(title) 키워드 빈도 분석 (TF-IDF 상위 30개)
    plt.figure(figsize=(12, 6))
    titles = df["title"].fillna("").tolist()
    # 공백 단위 또는 정규식으로 한글/영문 단어 토큰화
    vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b\w+\b', max_features=100)
    tfidf_matrix = vectorizer.fit_transform(titles)
    feature_names = vectorizer.get_feature_names_out()
    tfidf_sums = tfidf_matrix.sum(axis=0).A1
    
    df_tfidf = pd.DataFrame({"word": feature_names, "score": tfidf_sums})
    df_tfidf = df_tfidf.sort_values(by="score", ascending=False).head(30)
    
    plt.bar(df_tfidf["word"], df_tfidf["score"], color="#7f7f7f")
    plt.title("공고 제목 TF-IDF 핵심 키워드 상위 30개")
    plt.xlabel("키워드")
    plt.ylabel("TF-IDF 중요도 점수")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "08_title_tfidf_bar.png"))
    plt.close()
    print("차트 8 저장 완료: 08_title_tfidf_bar.png")
    
    # 9. 직무 분야(sectors) 키워드 빈도 분석 (TF-IDF 상위 30개)
    plt.figure(figsize=(12, 6))
    sectors_list = df["sectors"].fillna("").tolist()
    vectorizer_sec = TfidfVectorizer(token_pattern=r'(?u)\b\w+\b', max_features=100)
    tfidf_matrix_sec = vectorizer_sec.fit_transform(sectors_list)
    feature_names_sec = vectorizer_sec.get_feature_names_out()
    tfidf_sums_sec = tfidf_matrix_sec.sum(axis=0).A1
    
    df_tfidf_sec = pd.DataFrame({"word": feature_names_sec, "score": tfidf_sums_sec})
    df_tfidf_sec = df_tfidf_sec.sort_values(by="score", ascending=False).head(30)
    
    plt.bar(df_tfidf_sec["word"], df_tfidf_sec["score"], color="#bcbd22")
    plt.title("직무 분야(sectors) TF-IDF 핵심 키워드 상위 30개")
    plt.xlabel("키워드")
    plt.ylabel("TF-IDF 중요도 점수")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "09_sectors_tfidf_bar.png"))
    plt.close()
    print("차트 9 저장 완료: 09_sectors_tfidf_bar.png")
    
    # 10. 기업 규모와 학력 요건 교차 분석 Heatmap (Crosstab)
    plt.figure(figsize=(10, 8))
    ct = pd.crosstab(df["company_type"], df["education"])
    # Matplotlib 표를 직접 그리거나 seaborn heatmap 대신 단순 시각화
    # Seaborn 테마 설정 sns.set_theme()은 사용 금지이나 sns.heatmap 단독 호출은 가능
    # (Seaborn 라이브러리는 불러오되 sns.set_theme() 같은 전역 테마 설정을 피하는 것)
    sns.heatmap(ct, annot=True, fmt="d", cmap="YlGnBu", cbar=True)
    plt.title("기업 규모 vs 학력 요건 교차 빈도 (Crosstab Heatmap)")
    plt.xlabel("학력 요건")
    plt.ylabel("기업 규모")
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "10_company_vs_education_heatmap.png"))
    plt.close()
    print("차트 10 저장 완료: 10_company_vs_education_heatmap.png")
    
    print("=== [데이터 시각화 완료] ===")
    
    # 보고서 출력을 위해 TF-IDF 테이블과 Crosstab 테이블 텍스트 출력
    print("\n--- [Title TF-IDF Table] ---")
    print(df_tfidf.to_string(index=False))
    print("\n--- [Sectors TF-IDF Table] ---")
    print(df_tfidf_sec.to_string(index=False))
    print("\n--- [Company Type vs Education Crosstab Table] ---")
    print(ct.to_string())

if __name__ == "__main__":
    import sys
    os.makedirs("saramin/report", exist_ok=True)
    # 표준 출력을 UTF-8 파일로 리다이렉트하여 윈도우 인코딩 깨짐 우회
    orig_stdout = sys.stdout
    with open("saramin/report/raw_stats.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        df = load_data()
        analyze_basic_info(df)
        df_clean = analyze_descriptive_stats(df)
        generate_visualizations(df_clean)
    sys.stdout = orig_stdout
    print("EDA 분석 완료! 통계 결과가 'saramin/report/raw_stats.txt'에 저장되었습니다.")

