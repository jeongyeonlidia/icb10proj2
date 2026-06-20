"""
이 모듈은 교보문고 베스트셀러 데이터를 바탕으로 탐색적 데이터 분석(EDA)을 수행하는 스크립트입니다.
주요 기능:
- 수집된 베스트셀러 데이터의 요약 통계 정보 산출
- Matplotlib 및 Seaborn을 활용하여 총 11개의 시각화 차트 생성 및 저장
- 도서명과 이벤트 텍스트에 대한 TF-IDF 키워드 분석 수행
- 마케팅 및 운영 인사이트 도출을 위한 보조 분석 데이터 출력
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import koreanize_matplotlib
from sklearn.feature_extraction.text import TfidfVectorizer

def run_eda():
    # Windows 콘솔 등에서 유니코드 출력 시 에러 방지
    if sys.stdout and sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    # 파일 경로 설정 (상대 경로 활용)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(current_dir)
    data_path = os.path.join(project_dir, "data", "best_sellers.csv")
    image_dir = os.path.join(project_dir, "images")
    os.makedirs(image_dir, exist_ok=True)

    print(f"데이터 로딩 중: {data_path}")
    if not os.path.exists(data_path):
        print("오류: 데이터 파일이 존재하지 않습니다. 먼저 scraper.py를 실행하세요.")
        return

    df = pd.read_csv(data_path)

    # 1. 초기 데이터 검토 출력
    print("\n=== [1] 초기 데이터 검토 ===")
    print(f"전체 데이터 행 수: {df.shape[0]}, 열 수: {df.shape[1]}")
    print(f"중복 레코드 수: {df.duplicated().sum()}")
    print("\n--- 데이터 head(5) ---")
    print(df.head(5))
    print("\n--- 데이터 tail(5) ---")
    print(df.tail(5))
    print("\n--- 데이터 info() ---")
    df.info()

    # 2. 전처리
    # 수치 데이터 형 변환 및 결측치 처리
    df['정가'] = pd.to_numeric(df['정가'], errors='coerce')
    df['판매가'] = pd.to_numeric(df['판매가'], errors='coerce')
    df['할인율'] = pd.to_numeric(df['할인율'], errors='coerce')
    df['평점'] = pd.to_numeric(df['평점'], errors='coerce')
    df['리뷰수'] = pd.to_numeric(df['리뷰수'], errors='coerce')
    df['순위'] = pd.to_numeric(df['순위'], errors='coerce')
    df['이전순위'] = pd.to_numeric(df['이전순위'], errors='coerce')

    # 결측치 채우기
    df['이벤트'] = df['이벤트'].fillna('이벤트 없음')
    df['분류명'] = df['분류명'].fillna('분류 없음')

    # 차트 생성을 위한 공통 스타일 설정 (seaborn set_theme을 피하고 matplotlib 설정 변경)
    plt.rcParams['font.size'] = 11
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['figure.titlesize'] = 15

    # ------------------ 차트 1: 도서 판매가 분포 ------------------
    plt.figure(figsize=(10, 6))
    sns.histplot(data=df, x='판매가', kde=True, color='royalblue', bins=30)
    plt.title('도서 판매가 분포')
    plt.xlabel('판매가 (원)')
    plt.ylabel('도서 수')
    plt.tight_layout()
    chart1_path = os.path.join(image_dir, '01_price_distribution.png')
    plt.savefig(chart1_path, dpi=150)
    plt.close()
    print("차트 1 저장 완료")

    # ------------------ 차트 2: 도서 평점 분포 ------------------
    plt.figure(figsize=(10, 6))
    sns.histplot(data=df, x='평점', kde=True, color='darkorange', bins=20)
    plt.title('도서 평점 분포')
    plt.xlabel('평점 (10점 만점)')
    plt.ylabel('도서 수')
    plt.tight_layout()
    chart2_path = os.path.join(image_dir, '02_rating_distribution.png')
    plt.savefig(chart2_path, dpi=150)
    plt.close()
    print("차트 2 저장 완료")

    # ------------------ 차트 3: 도서 리뷰 수 분포 ------------------
    plt.figure(figsize=(10, 6))
    # 극단값 배제를 위해 리뷰수 로그 스케일 또는 일반 히스토그램
    sns.histplot(data=df, x='리뷰수', kde=True, color='teal', bins=30, log_scale=(True, False))
    plt.title('도서 리뷰 수 분포 (로그 스케일 X축)')
    plt.xlabel('리뷰 수 (로그 스케일)')
    plt.ylabel('도서 수')
    plt.tight_layout()
    chart3_path = os.path.join(image_dir, '03_review_distribution.png')
    plt.savefig(chart3_path, dpi=150)
    plt.close()
    print("차트 3 저장 완료")

    # ------------------ 차트 4: 도서 할인율 분포 ------------------
    plt.figure(figsize=(10, 6))
    sns.countplot(data=df, x='할인율', palette='muted')
    plt.title('도서 할인율 분포')
    plt.xlabel('할인율 (%)')
    plt.ylabel('도서 수')
    plt.tight_layout()
    chart4_path = os.path.join(image_dir, '04_discount_distribution.png')
    plt.savefig(chart4_path, dpi=150)
    plt.close()
    print("차트 4 저장 완료")

    # ------------------ 차트 5: 출판사 빈도수 (상위 30개) ------------------
    plt.figure(figsize=(12, 8))
    publisher_counts = df['출판사'].value_counts().head(30)
    sns.barplot(x=publisher_counts.values, y=publisher_counts.index, palette='viridis')
    plt.title('베스트셀러 출판사 상위 30개')
    plt.xlabel('도서 등록 수')
    plt.ylabel('출판사명')
    plt.tight_layout()
    chart5_path = os.path.join(image_dir, '05_publisher_distribution.png')
    plt.savefig(chart5_path, dpi=150)
    plt.close()
    print("차트 5 저장 완료")

    # ------------------ 차트 6: 저자 빈도수 (상위 30개) ------------------
    plt.figure(figsize=(12, 8))
    author_counts = df['저자'].value_counts().head(30)
    sns.barplot(x=author_counts.values, y=author_counts.index, palette='magma')
    plt.title('베스트셀러 저자 상위 30개')
    plt.xlabel('도서 등록 수')
    plt.ylabel('저자명')
    plt.tight_layout()
    chart6_path = os.path.join(image_dir, '06_author_distribution.png')
    plt.savefig(chart6_path, dpi=150)
    plt.close()
    print("차트 6 저장 완료")

    # ------------------ 차트 7: 분류명 빈도수 (상위 30개) ------------------
    plt.figure(figsize=(12, 8))
    category_counts = df['분류명'].value_counts().head(30)
    sns.barplot(x=category_counts.values, y=category_counts.index, palette='cubehelix')
    plt.title('베스트셀러 도서 분류(장르) 상위 30개')
    plt.xlabel('도서 등록 수')
    plt.ylabel('분류명')
    plt.tight_layout()
    chart7_path = os.path.join(image_dir, '07_category_distribution.png')
    plt.savefig(chart7_path, dpi=150)
    plt.close()
    print("차트 7 저장 완료")

    # ------------------ 차트 8: 판매가와 리뷰 수 간의 상관 관계 (산점도) ------------------
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x='판매가', y='리뷰수', alpha=0.6, color='purple')
    plt.title('도서 판매가 vs 리뷰 수')
    plt.xlabel('판매가 (원)')
    plt.ylabel('리뷰 수')
    plt.xscale('linear')
    plt.yscale('log') # 리뷰 수가 범위가 크므로 y축은 로그 스케일
    plt.tight_layout()
    chart8_path = os.path.join(image_dir, '08_price_vs_reviews.png')
    plt.savefig(chart8_path, dpi=150)
    plt.close()
    print("차트 8 저장 완료")

    # ------------------ 차트 9: 평점과 리뷰 수 간의 상관 관계 (산점도) ------------------
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x='평점', y='리뷰수', alpha=0.6, color='crimson')
    plt.title('도서 평점 vs 리뷰 수')
    plt.xlabel('평점')
    plt.ylabel('리뷰 수')
    plt.yscale('log')
    plt.tight_layout()
    chart9_path = os.path.join(image_dir, '09_rating_vs_reviews.png')
    plt.savefig(chart9_path, dpi=150)
    plt.close()
    print("차트 9 저장 완료")

    # ------------------ 차트 10: 도서명 TF-IDF 상위 30개 키워드 분석 ------------------
    print("도서명 TF-IDF 키워드 추출 중...")
    # 결측치 처리
    titles = df['도서명'].fillna('').tolist()
    
    # 한국어 단어 기준 TF-IDF 벡터라이징
    vectorizer = TfidfVectorizer(max_features=100, stop_words=None)
    tfidf_matrix = vectorizer.fit_transform(titles)
    
    # 피처명과 TF-IDF 합산값 매핑
    words = vectorizer.get_feature_names_out()
    sums = tfidf_matrix.sum(axis=0).A1
    word_freq = pd.Series(sums, index=words).sort_values(ascending=False).head(30)
    
    plt.figure(figsize=(12, 8))
    sns.barplot(x=word_freq.values, y=word_freq.index, palette='copper')
    plt.title('도서명 TF-IDF 상위 30개 핵심 키워드')
    plt.xlabel('TF-IDF 가중치 합')
    plt.ylabel('키워드')
    plt.tight_layout()
    chart10_path = os.path.join(image_dir, '10_title_tfidf.png')
    plt.savefig(chart10_path, dpi=150)
    plt.close()
    print("차트 10 저장 완료")

    # ------------------ 차트 11: 이벤트 필드 TF-IDF 상위 30개 키워드 분석 ------------------
    print("이벤트 TF-IDF 키워드 추출 중...")
    events = df['이벤트'].fillna('').tolist()
    
    vectorizer_ev = TfidfVectorizer(max_features=100)
    tfidf_ev = vectorizer_ev.fit_transform(events)
    
    words_ev = vectorizer_ev.get_feature_names_out()
    sums_ev = tfidf_ev.sum(axis=0).A1
    # '이벤트', '없음' 같은 불필요한 단어가 최상단에 올 경우를 대비해 수집
    word_freq_ev = pd.Series(sums_ev, index=words_ev).sort_values(ascending=False).head(30)
    
    plt.figure(figsize=(12, 8))
    sns.barplot(x=word_freq_ev.values, y=word_freq_ev.index, palette='bone')
    plt.title('이벤트 문구 TF-IDF 상위 30개 핵심 키워드')
    plt.xlabel('TF-IDF 가중치 합')
    plt.ylabel('이벤트 키워드')
    plt.tight_layout()
    chart11_path = os.path.join(image_dir, '11_event_tfidf.png')
    plt.savefig(chart11_path, dpi=150)
    plt.close()
    print("차트 11 저장 완료")

    # 3. 보조 분석 데이터를 콘솔에 출력 (상세 테이블 작성 시 활용)
    print("\n=== [2] 기술 통계 요약 ===")
    print(df[['정가', '판매가', '할인율', '평점', '리뷰수']].describe())

    print("\n=== [3] 카테고리(분류명)별 주요 지표 평균 ===")
    cat_summary = df.groupby('분류명')[['판매가', '평점', '리뷰수']].agg(['mean', 'count']).sort_values(by=('리뷰수', 'count'), ascending=False)
    print(cat_summary.head(10))

    print("\n=== [4] 도서명 TF-IDF 상위 키워드 테이블 ===")
    print(word_freq)

    print("\n=== [5] 이벤트 TF-IDF 상위 키워드 테이블 ===")
    print(word_freq_ev)

    print("\n모든 EDA 시각화 데이터 및 차트 생성 프로세스가 성공적으로 완료되었습니다.")

if __name__ == "__main__":
    run_eda()
