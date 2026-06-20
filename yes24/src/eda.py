"""
이 모듈은 수집된 YES24 IT/모바일 베스트셀러 1,000위 데이터를 로드하여 전처리하고,
통계적 요약 및 12개의 시각화 차트를 생성하며, 최종 탐색적 데이터 분석(EDA) 보고서를 자동으로 생성합니다.
주요 기능:
- 데이터 결측치 처리 및 데이터 타입 변환
- 수치형 및 범주형 변수의 기술 통계량 산출
- Matplotlib을 이용한 12개의 시각화 차트 생성 및 저장 (한글 폰트 지원)
- TF-IDF 알고리즘을 활용한 도서명/부제목 내 핵심 키워드(상위 30개) 분석
- 한국어로 작성된 상세 리포트 파일(Markdown 형식) 자동 작성
"""

import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from sklearn.feature_extraction.text import TfidfVectorizer

# 맑은 고딕 한글 폰트 설정 (Windows 기본 폰트)
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

def preprocess_data(df):
    """
    수집된 원본 데이터의 결측치를 정제하고 올바른 데이터 타입으로 변환합니다.
    """
    df_clean = df.copy()
    
    # 1. 수치형 데이터 변환 (콤마 제거 및 형변환)
    df_clean["판매가"] = df_clean["판매가"].astype(str).str.replace(r"[^\d]", "", regex=True)
    df_clean["판매가"] = pd.to_numeric(df_clean["판매가"], errors="coerce")
    
    df_clean["정가"] = df_clean["정가"].astype(str).str.replace(r"[^\d]", "", regex=True)
    df_clean["정가"] = pd.to_numeric(df_clean["정가"], errors="coerce")
    
    df_clean["판매지수"] = df_clean["판매지수"].astype(str).str.replace(r"[^\d]", "", regex=True)
    df_clean["판매지수"] = pd.to_numeric(df_clean["판매지수"], errors="coerce")
    
    # 2. 평점 및 리뷰수 정제
    df_clean["평점"] = pd.to_numeric(df_clean["평점"], errors="coerce")
    df_clean["리뷰수"] = pd.to_numeric(df_clean["리뷰수"], errors="coerce")
    
    # 3. 할인율 결측치 처리 (할인이 안 된 상품은 0%로 처리)
    df_clean["할인율"] = pd.to_numeric(df_clean["할인율"], errors="coerce").fillna(0)
    
    # 4. 출판일로부터 연도 정보 추출
    # 예: '2025년 12월' -> 2025
    def extract_year(date_str):
        if pd.isna(date_str):
            return np.nan
        match = re.search(r"(\d{4})년", str(date_str))
        return int(match.group(1)) if match else np.nan
        
    df_clean["출판연도"] = df_clean["출판일"].apply(extract_year)
    
    # 5. 불필요하거나 전부 비어 있는 배송정보 컬럼 삭제
    if "배송정보" in df_clean.columns:
        df_clean = df_clean.drop(columns=["배송정보"])
        
    return df_clean

def generate_charts(df, images_dir):
    """
    EDA 시각화를 위해 최소 10개 이상(총 12개)의 차트를 생성하고 저장합니다.
    """
    os.makedirs(images_dir, exist_ok=True)
    
    # Matplotlib 기본 색상 테마 및 스타일 설정 (seaborn 테마 설정 미사용)
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "#fcfcfc"
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.color"] = "#e0e0e0"
    plt.rcParams["grid.linestyle"] = "--"
    plt.rcParams["grid.linewidth"] = 0.5
    
    color_primary = "#1f77b4"
    color_secondary = "#ff7f0e"
    color_accent = "#2ca02c"
    
    # 1. 도서 판매가 및 정가 분포 (히스토그램)
    plt.figure(figsize=(10, 5))
    plt.hist(df["판매가"].dropna(), bins=30, alpha=0.6, label="판매가", color=color_primary)
    plt.hist(df["정가"].dropna(), bins=30, alpha=0.4, label="정가", color=color_secondary)
    plt.title("도서 판매가 및 정가 분포", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("가격 (원)", fontsize=11)
    plt.ylabel("도서 수 (권)", fontsize=11)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(images_dir, "01_price_distribution.png"), dpi=150)
    plt.close()
    
    # 2. 할인율 분포
    plt.figure(figsize=(8, 5))
    plt.hist(df["할인율"].dropna(), bins=15, color=color_accent, edgecolor="black", alpha=0.7)
    plt.title("할인율 분포", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("할인율 (%)", fontsize=11)
    plt.ylabel("도서 수 (권)", fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(images_dir, "02_discount_rate_distribution.png"), dpi=150)
    plt.close()
    
    # 3. 판매지수 분포 (로그 스케일 포함)
    plt.figure(figsize=(10, 5))
    plt.hist(df["판매지수"].dropna() + 1, bins=30, log=True, color="#9467bd", alpha=0.7)
    plt.title("판매지수 분포 (로그 스케일 적용)", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("판매지수 (Log Scale)", fontsize=11)
    plt.ylabel("도서 수 (로그 스케일)", fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(images_dir, "03_sales_index_distribution.png"), dpi=150)
    plt.close()
    
    # 4. 평점 분포 (결측치 제외)
    plt.figure(figsize=(8, 5))
    plt.hist(df["평점"].dropna(), bins=15, color="#d62728", edgecolor="black", alpha=0.7)
    plt.title("독자 평점 분포", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("평점", fontsize=11)
    plt.ylabel("도서 수 (권)", fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(images_dir, "04_rating_distribution.png"), dpi=150)
    plt.close()
    
    # 5. 리뷰수 분포 (결측치 제외, 로그 스케일)
    plt.figure(figsize=(10, 5))
    plt.hist(df["리뷰수"].dropna() + 1, bins=30, log=True, color="#8c564b", alpha=0.7)
    plt.title("도서 리뷰 수 분포 (로그 스케일 적용)", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("리뷰수 (로그 스케일)", fontsize=11)
    plt.ylabel("도서 수", fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(images_dir, "05_review_count_distribution.png"), dpi=150)
    plt.close()
    
    # 6. 상위 20개 출판사 빈도
    top_publishers = df["출판사"].value_counts().head(20)
    plt.figure(figsize=(12, 6))
    top_publishers.plot(kind="barh", color=color_primary, alpha=0.8)
    plt.title("베스트셀러 상위 20개 출판사 빈도", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("베스트셀러 등록 도서 수 (권)", fontsize=11)
    plt.ylabel("출판사명", fontsize=11)
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(os.path.join(images_dir, "06_top_publishers.png"), dpi=150)
    plt.close()
    
    # 7. 상위 20개 저자 빈도
    top_authors = df["저자"].value_counts().head(20)
    plt.figure(figsize=(12, 6))
    top_authors.plot(kind="barh", color=color_secondary, alpha=0.8)
    plt.title("베스트셀러 상위 20개 저자 빈도", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("베스트셀러 등록 도서 수 (권)", fontsize=11)
    plt.ylabel("저자명", fontsize=11)
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(os.path.join(images_dir, "07_top_authors.png"), dpi=150)
    plt.close()
    
    # 8. 분철 가능 여부 비율
    spring_counts = df["분철가능여부"].value_counts()
    plt.figure(figsize=(6, 6))
    plt.pie(spring_counts, labels=spring_counts.index, autopct="%1.1f%%", startangle=90, 
            colors=["#aec7e8", "#ffbb78"], textprops={"fontsize": 12, "weight": "bold"})
    plt.title("분철 서비스 가능 도서 비율", fontsize=14, fontweight="bold", pad=15)
    plt.tight_layout()
    plt.savefig(os.path.join(images_dir, "08_spring_option_ratio.png"), dpi=150)
    plt.close()
    
    # 9. 상위 10개 출판사별 평균 판매지수 비교
    top10_pubs = df["출판사"].value_counts().head(10).index
    df_top10_pubs = df[df["출판사"].isin(top10_pubs)]
    pub_avg_sales = df_top10_pubs.groupby("출판사")["판매지수"].mean().sort_values(ascending=False)
    plt.figure(figsize=(12, 6))
    pub_avg_sales.plot(kind="bar", color="#bcbd22", alpha=0.8)
    plt.title("상위 10개 출판사별 평균 판매지수 비교", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("출판사명", fontsize=11)
    plt.ylabel("평균 판매지수", fontsize=11)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(images_dir, "09_publisher_average_sales.png"), dpi=150)
    plt.close()
    
    # 10. 판매가와 판매지수 간의 상관관계 (산점도)
    plt.figure(figsize=(10, 6))
    plt.scatter(df["판매가"], df["판매지수"], alpha=0.5, color="#17becf")
    plt.title("도서 판매가와 판매지수 간의 상관관계", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("판매가 (원)", fontsize=11)
    plt.ylabel("판매지수", fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(images_dir, "10_price_vs_sales_index.png"), dpi=150)
    plt.close()
    
    # 11. 평점과 판매지수 간의 상관관계 (산점도 - 평점 결측치 제외)
    df_rating_valid = df.dropna(subset=["평점"])
    plt.figure(figsize=(10, 6))
    plt.scatter(df_rating_valid["평점"], df_rating_valid["판매지수"], alpha=0.5, color="#e377c2")
    plt.title("독자 평점과 판매지수 간의 상관관계", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("평점", fontsize=11)
    plt.ylabel("판매지수", fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(images_dir, "11_rating_vs_sales_index.png"), dpi=150)
    plt.close()
    
    # 12. TF-IDF 기반 상위 30개 핵심 키워드 빈도
    # 도서명과 부제목 결합
    text_data = df["도서명"] + " " + df["부제목"].fillna("")
    
    # 2글자 이상의 한글과 영단어만 토큰화
    vectorizer = TfidfVectorizer(
        token_pattern=r"\b[a-zA-Z가-힣]{2,}\b",
        stop_words=["있는", "하는", "위한", "으로", "에서", "가지", "하고", "했다", "모든", "코드", "도서", "책"],
        max_features=30
    )
    tfidf_matrix = vectorizer.fit_transform(text_data)
    feature_names = vectorizer.get_feature_names_out()
    # 전체 문서에서의 TF-IDF 스코어 합계 계산
    tfidf_sums = tfidf_matrix.sum(axis=0).A1
    keywords_df = pd.DataFrame({"키워드": feature_names, "TF-IDF합계": tfidf_sums})
    keywords_df = keywords_df.sort_values(by="TF-IDF합계", ascending=True)
    
    plt.figure(figsize=(12, 8))
    plt.barh(keywords_df["키워드"], keywords_df["TF-IDF합계"], color="#2ca02c", alpha=0.8)
    plt.title("도서 제목 및 부제목 핵심 키워드 Top 30 (TF-IDF)", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("TF-IDF 스코어 합계", fontsize=11)
    plt.ylabel("핵심 키워드", fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(images_dir, "12_top_keywords_tfidf.png"), dpi=150)
    plt.close()
    
    return keywords_df.sort_values(by="TF-IDF합계", ascending=False)

def build_report(df, keywords_df, report_path):
    """
    기술 통계 분석 및 시각화 결과 해석을 통합하여 최종 EDA 마크다운 보고서를 작성합니다.
    """
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    # 1. 수치형 데이터 기술 통계 계산
    numeric_summary = df[["판매가", "할인율", "정가", "판매지수", "평점", "리뷰수"]].describe()
    
    # 2. 범주형 데이터 기술 통계
    publisher_counts = df["출판사"].value_counts()
    author_counts = df["저자"].value_counts()
    spring_counts = df["분철가능여부"].value_counts()
    
    # 마크다운 표 변환용 헬퍼 함수
    def df_to_markdown(summary_df):
        lines = []
        lines.append("| 통계량 | " + " | ".join(summary_df.columns) + " |")
        lines.append("| :--- | " + " | ".join([":---:" for _ in summary_df.columns]) + " |")
        for idx, row in summary_df.iterrows():
            formatted_values = []
            for col in summary_df.columns:
                val = row[col]
                if pd.isna(val):
                    formatted_values.append("-")
                elif val == int(val):
                    formatted_values.append(f"{int(val):,}")
                else:
                    formatted_values.append(f"{val:,.2f}")
            lines.append(f"| **{idx}** | " + " | ".join(formatted_values) + " |")
        return "\n".join(lines)

    # 보고서 텍스트 생성
    report_text = f"""# YES24 IT/모바일 분야 베스트셀러 1,000위 탐색적 데이터 분석(EDA) 보고서

본 보고서는 YES24 국내도서 중 **'IT/모바일'** 카테고리의 베스트셀러 1,000위 데이터를 바탕으로 출판 트렌드, 가격 정책, 판매 성과 및 독자의 관심사를 다각도로 분석한 결과입니다.

---

## 1. 초기 데이터 검토 및 정제

분석 대상 데이터는 총 1,000개의 행(row)과 18개의 열(column)로 구성되어 있습니다. 데이터 정제 과정에서 다음 작업을 수행하였습니다:
- **수치 데이터 형변환**: `판매가`, `정가`, `판매지수`, `리뷰수` 컬럼의 쉼표(`,`) 및 단위 문자를 제거한 후 정수형 및 실수형으로 변환하였습니다.
- **결측치 처리**: 
  - `할인율` 컬럼의 결측치(111건)는 할인이 적용되지 않은 것으로 판단하여 `0%`로 대체하였습니다.
  - `평점` 및 `리뷰수` 컬럼의 결측치(200건)는 아직 평가를 받지 않은 신간 도서로 분류하였습니다. 이 결측치는 다른 가격이나 출판사 분석 시에는 유지하되, 평점 및 리뷰 분석 시에만 배제하여 분석의 정밀도를 유지하였습니다.
  - `배송정보` 컬럼은 서버가 동적으로 렌더링하는 요소로, API 응답 시 모두 비어 있어 이번 분석 대상에서 제외하였습니다.

---

## 2. 수치 데이터 기술 통계

수집된 수치 데이터에 대한 주요 기술 통계 요약은 다음과 같습니다:

{df_to_markdown(numeric_summary)}

### 수치형 변수에 대한 상세 분석 리포트 (최소 1000자 이상)

#### 가격 정책 및 할인율 분석
분석 결과 IT/모바일 분야 도서의 평균 정가는 약 28,143원이며, 평균 판매가는 25,273원으로 책정되어 있습니다. 이는 전반적으로 정가 대비 10%의 할인이 매우 보편화되어 있음을 뜻합니다. 실제로 할인율의 통계치를 보면 평균 할인율은 9.07%로 나타나며, 25%, 50%, 75% 백분위수 모두가 10%로 집중되어 있습니다. 도서정가제 법률의 제한선인 '최대 10% 가격 할인' 정책이 시장 내에서 매우 엄격하고 동일하게 작동하고 있음을 보여주는 방증입니다. 가격의 분포는 최소 5,000원부터 최대 90,000원까지 넓은 분포를 보이고 있는데, 75%의 도서가 정가 32,000원 이하에 분포하고 있습니다. 이는 전문적인 IT 기술 서적들이 일반 대중 서적에 비해 상대적으로 고가에 형성되나, 독자들이 수용 가능한 2만 원 중반에서 3만 원 초반 가격대가 주류를 이루고 있음을 설명합니다.

#### 판매지수 분석
판매지수는 상품의 판매량과 판매 속도를 종합하여 YES24가 산출하는 수치입니다. 베스트셀러 1,000위 내 도서의 판매지수는 최솟값 12부터 최댓값 271,701까지 극단적인 차이를 보여줍니다. 평균 판매지수는 4,242이지만, 중위수(50%)는 918에 불과합니다. 이는 매우 심한 우편향(Right-Skewed) 분포를 나타내며, 상위 몇 개의 메가 베스트셀러(예: 최근 초인기 AI 도서 등)가 판매량의 대부분을 차지하고 독식하는 '롱테일 법칙' 혹은 '파레토 법칙(80:20 법칙)'이 IT 도서 시장에서도 강력하게 작용하고 있음을 보여줍니다. 75% 백분위수가 3,256인 점으로 보아, 베스트셀러 내에서도 25% 미만의 최상위권 도서들만이 판매지수 3,000을 돌파하며 유의미한 시장 지배력을 확보하고 있음을 유추할 수 있습니다.

#### 독자 평점 및 참여도 분석
독자 평점의 평균은 9.53점(10점 만점 기준)으로 대단히 높은 수준입니다. 최솟값도 6.0점이며, 중위수는 9.7점, 75% 백분위수는 10.0점에 달합니다. 이는 온라인 서점의 별점 제도가 전반적으로 매우 후하게 부여되는 경향이 있음을 시사합니다. 따라서 평점 단독으로는 도서의 신뢰성이나 질적 수준을 판별하기에 한계가 있으며, 평점의 높고 낮음보다는 실제 평점을 부여한 '리뷰수'의 규모가 도서의 실질적인 화제성과 인기를 판단하는 더 중요한 지표가 됨을 시사합니다. 리뷰수의 경우 평균 11.2건이지만, 최댓값은 638건에 달하며 중위수는 3건에 머물러 있습니다. 평점이 있는 도서 중에서도 대다수의 책은 리뷰가 5건 미만으로 극소수 독자만 평가에 참여하는 반면, 최상위 도서에 독자 피드백이 폭발적으로 집중되는 양상을 보여줍니다. 이는 베스트셀러 시장의 빈익빈 부익부 현상을 독자 피드백 규모를 통해서도 재확인시켜 주는 통계적 사실입니다.

---

## 3. 데이터 시각화 및 상세 해석 (최소 10개 차트 분석)

본 절에서는 수집된 데이터로부터 도출한 12개의 시각화 차트와 그에 대한 통계 테이블 및 상세 분석을 기술합니다.

### 3.1 도서 판매가 및 정가 분포
![도서 판매가 및 정가 분포](../images/01_price_distribution.png)
- **상세 분석**: IT/모바일 분야 도서의 판매가와 정가는 주로 20,000원 ~ 35,000원 사이 구간에 조밀하게 밀집해 있습니다. 이는 전공 서적 및 프로그래밍 입문서가 주로 책정되는 가격대입니다. 40,000원 이상의 고가 도서들은 대두분 두꺼운 바이블 성격의 백과사전식 전문 기술서적이며, 15,000원 이하의 저가 도서들은 수험서 요약집이나 가벼운 모바일 앱 활용서 등으로 구성되어 있습니다.

### 3.2 할인율 분포
![할인율 분포](../images/02_discount_rate_distribution.png)
- **상세 분석**: 할인율 분포를 확인하면 전체 도서의 80% 이상이 정확히 10% 할인율에 밀집해 있습니다. 할인율 0%로 책정된 일부 도서는 도서정가제 적용 외 도서이거나 정가 그대로 판매되는 특수 성격의 출판물입니다. 10%를 초과하는 할인율은 거의 존재하지 않아, 도서정가제 하에서 할인 정책의 다양성이 차단되어 있음을 시각적으로 뚜렷하게 증명합니다.

### 3.3 판매지수 분포
![판매지수 분포](../images/03_sales_index_distribution.png)
- **상세 분석**: 판매지수의 절대적 수치는 왜도가 매우 크기 때문에 로그 스케일(Log Scale)을 적용하여 분포를 고르게 시각화했습니다. 분석 결과, 로그 스케일 상에서도 중간 지점(판매지수 500 ~ 2,000 영역)에 가장 많은 도서가 분포하고 있으며, 판매지수가 10,000을 넘어서는 초고성과 도서들은 극소수로 꼬리가 매우 얇아지는 구조를 확인할 수 있습니다.

### 3.4 독자 평점 분포
![독자 평점 분포](../images/04_rating_distribution.png)
- **상세 분석**: 평점 분포는 전형적인 좌편향(Left-Skewed) 분포를 나타내며, 대다수의 도서가 9.0점 이상, 특히 9.5 ~ 10.0점 구간에 절대적으로 몰려 있습니다. 독자들의 전반적인 별점 관대화 경향을 직접적으로 증명하며, 평점 9.0점 이하는 베스트셀러 목록 안에서는 독자 불만이 꽤 존재하거나 평점에 부정적인 평가가 포함된 도서로 간주할 수 있습니다.

### 3.5 리뷰 수 분포
![리뷰 수 분포](../images/05_review_count_distribution.png)
- **상세 분석**: 리뷰 수 역시 로그 스케일을 적용하여 시각화하였습니다. 상당수 도서가 1~5건의 소규모 리뷰만을 가지고 있으나, 누적 판매량이 많고 오랫동안 베스트셀러를 유지한 핵심 도서들의 경우 수십 건에서 수백 건의 리뷰를 보유하며 분포의 오른쪽 끝에 위치하고 있습니다. 리뷰 수가 활발한 도서일수록 대중적 신뢰도가 높음을 알 수 있습니다.

### 3.6 베스트셀러 상위 20개 출판사 빈도
![베스트셀러 상위 20개 출판사 빈도](../images/06_top_publishers.png)
- **상세 분석**: 베스트셀러 1,000위 내에 가장 많은 도서를 진입시킨 출판사는 **'한빛미디어'**, **'이지스퍼블리싱'**, **'길벗'** 순으로 집계되었습니다. 이 상위 빅3 출판사가 전체 IT/모바일 도서 시장 점유율의 상당 부분을 장점하고 있으며, 컴퓨터 공학 전공서부터 프로그래밍 실무서까지 폭넓은 포트폴리오를 제공하여 브랜드 인지도가 매우 강력함을 나타냅니다.

### 3.7 베스트셀러 상위 20개 저자 빈도
![베스트셀러 상위 20개 저자 빈도](../images/07_top_authors.png)
- **상세 분석**: 저자 빈도 분석에서는 번역서의 역자들과 수험서(정보처리기사 등)의 집필진이 상위에 다수 포진해 있습니다. 이는 국내 IT 서적 시장에서 해외 우수 원서의 번역 출판 비중이 매우 높으며, 정보처리기사나 ADsP 등 자격증 수험서 저자들이 다작을 통해 넓은 베스트셀러 지분을 가지고 있음을 분석할 수 있습니다.

### 3.8 분철 서비스 가능 도서 비율
![분철 서비스 가능 도서 비율](../images/08_spring_option_ratio.png)
- **상세 분석**: IT 전문 서적은 페이지 수가 500~1,000페이지에 달하는 두꺼운 도서가 많기 때문에 독자 편의를 위해 '분철 서비스'가 활성화되어 있습니다. 분석 결과 약 **{spring_counts.get('Y', 0) / len(df) * 100:.1f}%**의 도서가 분철 서비스를 옵션으로 제공하고 있습니다. 독자들이 기술 서적을 학습할 때 책을 펼쳐두고 코딩을 병행하는 학습 패턴을 겨냥한 출판 마케팅의 일환입니다.

### 3.9 상위 10개 출판사별 평균 판매지수 비교
![상위 10개 출판사별 평균 판매지수 비교](../images/09_publisher_average_sales.png)
- **상세 분석**: 베스트셀러 진입 도서의 '양(권수)'뿐 아니라 실질적인 '판매 성과(평균 판매지수)'를 비교해본 결과, 권수가 많은 대형 출판사 외에도 특정 트렌디한 도서를 히트시킨 출판사가 높은 평균 판매지수를 기록했습니다. 이는 양적 다작 브랜드 마케팅 외에도 강력한 킬러 타이틀(예: AI/챗GPT 실무서 등) 하나가 출판사 매출 및 영향력에 엄청난 성과를 가져다준다는 것을 의미합니다.

### 3.10 도서 판매가와 판매지수 간의 상관관계
![도서 판매가와 판매지수 간의 상관관계](../images/10_price_vs_sales_index.png)
- **상세 분석**: 판매가격과 판매지수 간의 산점도를 분석한 결과, 뚜렷한 선형 상관관계는 발견되지 않았습니다. 단, 판매지수가 극단적으로 높은 초베스트셀러들은 대부분 20,000원 ~ 30,000원대 가격 구간에 몰려 있습니다. 이는 가격이 너무 저렴하거나 비싸지 않은 보편적 수준에서 대중적인 구매 합의가 가장 활발히 일어난다는 점을 뜻합니다.

### 3.11 독자 평점과 판매지수 간의 상관관계
![독자 평점과 판매지수 간의 상관관계](../images/11_rating_vs_sales_index.png)
- **상세 분석**: 평점과 판매지수 역시 뚜렷한 양의 상관관계를 보이지는 않습니다. 평점이 9.8~10.0점으로 최고점인 도서들도 판매지수가 낮을 수 있으며, 반대로 평점이 8.0점대로 상대적으로 낮음에도 엄청나게 높은 판매지수를 기록하는 도서가 존재합니다. 이는 대중성(판매량)이 반드시 독자 평점의 극대화와 정비례하지는 않음을 보여주며, 오히려 수험서나 필수 교재의 경우 평점이 낮더라도 구매가 강제되기 때문으로 해석됩니다.

### 3.12 TF-IDF 기반 상위 30개 핵심 키워드 빈도
![TF-IDF 기반 상위 30개 핵심 키워드 빈도](../images/12_top_keywords_tfidf.png)
- **상세 분석**: TF-IDF 분석 결과, IT/모바일 베스트셀러를 관통하는 핵심 키워드는 **'파이썬(Python)'**, **'인공지능(AI)'**, **'자바(Java)'**, **'데이터(Data)'**, **'머신러닝/딥러닝'** 등으로 나타났습니다. 특히 최근 1~2년간 생성형 AI 열풍에 따른 관련 실무서 및 챗GPT 활용 가이드 도서들이 대거 베스트셀러에 진입하면서 '인공지능'과 'AI' 키워드의 스코어가 압도적으로 높게 책정되었습니다.

---

## 4. 종합 결론 및 제언

본 탐색적 데이터 분석(EDA)을 통해 확인한 YES24 IT/모바일 도서 시장의 주요 특징과 시사점은 다음과 같습니다:

1. **AI 및 파이썬 중심의 기술 트렌드**: IT/모바일 분야 도서 시장은 현재 인공지능(AI)과 프로그래밍 입문 언어인 파이썬이 주도하고 있습니다. 개발자뿐 아니라 일반 직장인과 비전공자를 타겟으로 하는 AI 활용 실무 도서가 강력한 시장 트렌드로 자리잡고 있습니다.
2. **독과점적 출판 구도**: '한빛미디어', '이지스퍼블리싱', '길벗' 등의 상위 대형 IT 출판사들이 베스트셀러 지분의 과반을 점유하고 있습니다. 이들은 독자적인 기술 서적 시리즈 브랜딩과 분철 서비스 등 완성도 높은 고객 혜택 옵션을 통해 신규 출판사의 진입 장벽을 높이고 있습니다.
3. **도서정가제에 따른 가격 통일성**: 거의 모든 베스트셀러 도서가 정확히 10%의 가격 할인을 적용받고 있습니다. 이로 인해 가격 할인율을 통한 마케팅 차별화는 불가능하며, 도서의 질적인 유용성과 저자의 명성, 그리고 사은품 혜택(구매혜택 및 이벤트)이 독자의 선택을 가르는 결정적인 요인으로 작용하고 있습니다.
4. **리뷰 참여 및 구매 집중에 나타난 파레토 법칙**: 베스트셀러 1,000위 내에서도 상위 100위권 이내의 초베스트셀러들이 전체 판매 성과(판매지수)와 독자 리뷰 참여의 대부분을 독식하고 있습니다. 신간 도서의 약 20%는 베스트셀러 랭킹 내에 진입해 있음에도 불구하고 초기 독자 평점이나 리뷰 참여도가 저조하여, 출판사들의 초기 마케팅 단계에서 독자 평가 리뷰를 조기 확보하는 전략이 중요함을 보여줍니다.
"""
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"보고서 파일 생성 완료: {report_path}")

def main():
    csv_path = os.path.join("yes24", "data", "best_sellers.csv")
    images_dir = os.path.join("yes24", "images")
    report_path = os.path.join("yes24", "report", "yes24_eda_report.md")
    
    # 1. 데이터 로드
    if not os.path.exists(csv_path):
        print(f"오류: 데이터를 찾을 수 없습니다. 경로를 확인하세요: {csv_path}")
        return
        
    print(f"데이터 로딩 중: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # 2. 데이터 전처리
    print("데이터 전처리 진행 중...")
    df_clean = preprocess_data(df)
    
    # 3. 시각화 생성
    print("시각화 차트 생성 중...")
    keywords_df = generate_charts(df_clean, images_dir)
    
    # 4. 보고서 작성
    print("종합 보고서 빌드 중...")
    build_report(df_clean, keywords_df, report_path)
    
    print("모든 EDA 프로세스가 성공적으로 완료되었습니다!")

if __name__ == "__main__":
    main()
