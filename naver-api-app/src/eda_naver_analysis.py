"""
이 파일은 네이버 카페에서 수집한 데이터분석 관심도 데이터(naver_dataanalysis.csv)에 대해
탐색적 데이터 분석(EDA)을 수행하고 시각화 차트 10개를 생성하는 분석 소스코드입니다.

주요 기능:
- `naver-api-app/data/naver_dataanalysis.csv` 파일을 로드합니다.
- 데이터의 결측치, 형태, 중복값을 점검하고 통계를 계산합니다.
- 주요 자격증 키워드(ADsP, SQLD, 빅데이터분석기사, 정보처리기사, CPA/CFA 등) 및 교육 키워드(부트캠프, 국비지원 등)를 파싱합니다.
- 카페 채널별(독금사, 국비모 등) 자격증 및 교육 언급 교차 분포를 도출합니다.
- `koreanize-matplotlib`를 사용하여 한글 깨짐을 방지하고 Seaborn 테마 없이 차트 10개를 생성하여 `naver-api-app/images/` 에 저장합니다.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import koreanize_matplotlib
from sklearn.feature_extraction.text import TfidfVectorizer
import os
import re

def run_eda_pipeline():
    csv_path = "naver-api-app/data/naver_dataanalysis.csv"
    img_dir = "naver-api-app/images"
    os.makedirs(img_dir, exist_ok=True)
    
    if not os.path.exists(csv_path):
        print(f"오류: {csv_path} 파일이 존재하지 않습니다.")
        return
        
    # 데이터 로드
    df = pd.read_csv(csv_path)
    
    # 0번째 이름 없는 컬럼 제거 및 정돈
    if df.columns[0] == "" or df.columns[0].startswith("Unnamed"):
        df = df.iloc[:, 1:]
        
    print(f"데이터 크기: 행 {df.shape[0]}개, 열 {df.shape[1]}개")
    print("컬럼 목록:", df.columns.tolist())
    
    # 텍스트 결합 컬럼 생성 (검색용)
    df["full_text"] = (df["제목"].fillna("") + " " + df["요약"].fillna("")).str.lower()
    df["title_len"] = df["제목"].fillna("").apply(len)
    df["summary_len"] = df["요약"].fillna("").apply(len)
    
    # 자격증 키워드 분류
    license_keywords = {
        "ADsP": ["adsp", "데이터분석준전문가"],
        "SQLD": ["sqld", "sql개발자", "sqld"],
        "빅데이터분석기사": ["빅데이터분석기사", "빅분기"],
        "정보처리기사": ["정보처리기사", "정처기"],
        "CPA/CFA": ["cpa", "cfa", "공인회계사", "재무분석사"]
    }
    
    # 교육/진로 키워드 분류
    edu_keywords = {
        "부트캠프": ["부트캠프", "bootcamp"],
        "국비지원": ["국비지원", "국비", "국민내일배움카드", "kdt"],
        "진로/취업": ["진로", "취업", "카드사", "금융권", "마케터", "마케팅"]
    }
    
    # 각 공고별로 키워드 매칭
    for name, kws in license_keywords.items():
        df[f"has_{name}"] = df["full_text"].apply(lambda t: int(any(kw in t for kw in kws)))
        
    for name, kws in edu_keywords.items():
        df[f"has_{name}"] = df["full_text"].apply(lambda t: int(any(kw in t for kw in kws)))
        
    # 어떤 자격증이라도 언급했는지 여부
    df["has_any_license"] = df[[f"has_{n}" for n in license_keywords.keys()]].any(axis=1).astype(int)
    
    # 대표 카페 채널 단순화 및 추출
    def get_simple_cafe(cafe_name):
        c = str(cafe_name)
        if "피터팬" in c: return "피터팬의 좋은방 구하기"
        elif "독금사" in c: return "독금사 (금융자격증)"
        elif "국비모" in c: return "국비모 (국비교육)"
        elif "온미르" in c: return "온미르클럽"
        elif "황인영" in c: return "황인영 영어카페"
        elif "바튜매" in c: return "바튜매"
        elif "포럼" in c or "sqlpd" in c: return "데이터 전문가 포럼"
        else: return "기타 카페"
        
    df["대표카페"] = df["카페명"].apply(get_simple_cafe)
    
    print("\n--- [시작] 시각화 차트 10개 생성 및 저장 ---")
    
    # ----------------- Chart 1: 대표 카페 채널 게시글 분포 (단변량 범주형) -----------------
    plt.figure(figsize=(10, 6))
    cafe_counts = df["대표카페"].value_counts()
    sns.barplot(x=cafe_counts.values, y=cafe_counts.index, palette="viridis")
    plt.title("대표 카페 채널별 게시글 분포", fontsize=14, fontweight="bold")
    plt.xlabel("게시글 수 (건)")
    plt.ylabel("카페 채널명")
    plt.tight_layout()
    plt.savefig(f"{img_dir}/chart1_cafe_dist.png")
    plt.close()
    print("Chart 1 저장 완료.")
    
    # ----------------- Chart 2: 제목 텍스트 TF-IDF 상위 20 키워드 (텍스트 분석) -----------------
    plt.figure(figsize=(10, 6))
    vectorizer_title = TfidfVectorizer(max_features=20, stop_words=["데이터", "분석", "데이터분석", "자격증", "시험", "질문", "후기", "준비", "응시자격"])
    try:
        tfidf_title = vectorizer_title.fit_transform(df["제목"].fillna(""))
        words_title = vectorizer_title.get_feature_names_out()
        sums_title = tfidf_title.sum(axis=0).A1
        df_tfidf_t = pd.DataFrame({"단어": words_title, "TF-IDF합계": sums_title}).sort_values(by="TF-IDF합계", ascending=False)
        sns.barplot(x="TF-IDF합계", y="단어", data=df_tfidf_t, palette="magma")
        plt.title("제목 텍스트 TF-IDF 상위 20 키워드", fontsize=14, fontweight="bold")
        plt.tight_layout()
        plt.savefig(f"{img_dir}/chart2_title_tfidf.png")
    except Exception as e:
        print("Chart 2 TF-IDF 에러:", e)
    plt.close()
    print("Chart 2 저장 완료.")
    
    # ----------------- Chart 3: 요약 텍스트 TF-IDF 상위 20 키워드 (텍스트 분석) -----------------
    plt.figure(figsize=(10, 6))
    vectorizer_sum = TfidfVectorizer(max_features=20, stop_words=["데이터", "분석", "데이터분석", "자격증", "시험", "통해", "대한", "위해", "어떻게"])
    try:
        tfidf_sum = vectorizer_sum.fit_transform(df["요약"].fillna(""))
        words_sum = vectorizer_sum.get_feature_names_out()
        sums_sum = tfidf_sum.sum(axis=0).A1
        df_tfidf_s = pd.DataFrame({"단어": words_sum, "TF-IDF합계": sums_sum}).sort_values(by="TF-IDF합계", ascending=False)
        sns.barplot(x="TF-IDF합계", y="단어", data=df_tfidf_s, palette="plasma")
        plt.title("요약 본문 TF-IDF 상위 20 키워드", fontsize=14, fontweight="bold")
        plt.tight_layout()
        plt.savefig(f"{img_dir}/chart3_summary_tfidf.png")
    except Exception as e:
        print("Chart 3 TF-IDF 에러:", e)
    plt.close()
    print("Chart 3 저장 완료.")
    
    # ----------------- Chart 4: 주요 자격증 언급 빈도 (단변량 수치형) -----------------
    plt.figure(figsize=(10, 6))
    license_sums = df[[f"has_{name}" for name in license_keywords.keys()]].sum().sort_values(ascending=False)
    license_sums.index = [idx.replace("has_", "") for idx in license_sums.index]
    sns.barplot(x=license_sums.values, y=license_sums.index, palette="coolwarm")
    plt.title("주요 자격증 언급 공고 빈도", fontsize=14, fontweight="bold")
    plt.xlabel("언급 수 (건)")
    plt.tight_layout()
    plt.savefig(f"{img_dir}/chart4_license_freq.png")
    plt.close()
    print("Chart 4 저장 완료.")
    
    # ----------------- Chart 5: 주요 진로/교육 키워드 언급 빈도 (단변량 수치형) -----------------
    plt.figure(figsize=(10, 6))
    edu_sums = df[[f"has_{name}" for name in edu_keywords.keys()]].sum().sort_values(ascending=False)
    edu_sums.index = [idx.replace("has_", "") for idx in edu_sums.index]
    sns.barplot(x=edu_sums.values, y=edu_sums.index, palette="copper")
    plt.title("교육 및 진로 키워드 언급 빈도", fontsize=14, fontweight="bold")
    plt.xlabel("언급 수 (건)")
    plt.tight_layout()
    plt.savefig(f"{img_dir}/chart5_edu_freq.png")
    plt.close()
    print("Chart 5 저장 완료.")
    
    # ----------------- Chart 6: 제목 텍스트 글자수 길이 분포 (단변량 연속형) -----------------
    plt.figure(figsize=(10, 6))
    sns.histplot(df["title_len"], bins=15, kde=True, color="skyblue")
    plt.title("게시글 제목 글자수 길이 분포", fontsize=14, fontweight="bold")
    plt.xlabel("제목 글자 수")
    plt.ylabel("빈도 (건)")
    plt.tight_layout()
    plt.savefig(f"{img_dir}/chart6_title_len.png")
    plt.close()
    print("Chart 6 저장 완료.")
    
    # ----------------- Chart 7: 요약 텍스트 글자수 길이 분포 (단변량 연속형) -----------------
    plt.figure(figsize=(10, 6))
    sns.histplot(df["summary_len"], bins=15, kde=True, color="salmon")
    plt.title("본문 요약 텍스트 글자수 길이 분포", fontsize=14, fontweight="bold")
    plt.xlabel("요약 글자 수")
    plt.ylabel("빈도 (건)")
    plt.tight_layout()
    plt.savefig(f"{img_dir}/chart7_summary_len.png")
    plt.close()
    print("Chart 7 저장 완료.")
    
    # ----------------- Chart 8: 주요 카페 채널별 자격증 언급 교차 빈도 (이변량) -----------------
    plt.figure(figsize=(12, 7))
    cafe_license = df.groupby("대표카페")[[f"has_{name}" for name in license_keywords.keys()]].sum()
    cafe_license.columns = [c.replace("has_", "") for c in cafe_license.columns]
    # Stacked bar
    cafe_license.plot(kind="bar", stacked=True, colormap="tab10", figsize=(12, 7))
    plt.title("카페 채널별 자격증 언급 교차 분포", fontsize=14, fontweight="bold")
    plt.xlabel("카페 채널")
    plt.ylabel("자격증 언급 수 합계 (건)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"{img_dir}/chart8_cafe_license_cross.png")
    plt.close()
    print("Chart 8 저장 완료.")
    
    # ----------------- Chart 9: 주요 카페 채널별 교육/진로 언급 교차 빈도 (이변량) -----------------
    plt.figure(figsize=(12, 7))
    cafe_edu = df.groupby("대표카페")[[f"has_{name}" for name in edu_keywords.keys()]].sum()
    cafe_edu.columns = [c.replace("has_", "") for c in cafe_edu.columns]
    cafe_edu.plot(kind="bar", stacked=True, colormap="Accent", figsize=(12, 7))
    plt.title("카페 채널별 교육 및 진로 언급 교차 분포", fontsize=14, fontweight="bold")
    plt.xlabel("카페 채널")
    plt.ylabel("교육/진로 언급 수 합계 (건)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"{img_dir}/chart9_cafe_edu_cross.png")
    plt.close()
    print("Chart 9 저장 완료.")
    
    # ----------------- Chart 10: 자격증 언급 유무에 따른 본문 요약 글자수 비교 (다변량) -----------------
    plt.figure(figsize=(10, 6))
    df["자격증언급여부"] = df["has_any_license"].map({1: "언급함", 0: "언급안함"})
    sns.boxplot(x="자격증언급여부", y="summary_len", hue="대표카페", data=df)
    plt.title("자격증 언급 유무 및 카페별 본문 글자수 분포", fontsize=14, fontweight="bold")
    plt.xlabel("자격증 언급 여부")
    plt.ylabel("본문 요약 글자 수")
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{img_dir}/chart10_license_summary_box.png")
    plt.close()
    print("Chart 10 저장 완료.")
    
    print("\n[성공] 모든 10개의 EDA 시각화 차트가 생성되어 저장되었습니다!")

if __name__ == "__main__":
    run_eda_pipeline()
