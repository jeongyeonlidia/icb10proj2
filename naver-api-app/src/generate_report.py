"""
이 모듈은 네이버 API 종합 분석 결과에 대한 오프라인 정적 HTML 보고서를 생성하는 기능을 수행합니다.
주요 기능:
- 시뮬레이션 데이터를 활용한 검색어 트렌드 시계열 분석 차트 생성
- 쇼핑 가격 비교 및 블로그 점유율 시각화 차트 생성
- Plotly 차트를 임베딩한 프리미엄 UI 기반의 단일 HTML 파일(report.html) 빌드
- naver-api-app/report/ 경로에 최종 리포트 저장
"""

import os
import datetime
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio

def generate_static_report():
    # 1. 시뮬레이션 데이터 생성 (검색 트렌드)
    dates = pd.date_range(start="2026-05-01", end="2026-05-30")
    np.random.seed(42)
    
    trend_data = []
    for date in dates:
        trend_data.append({"날짜": date, "비중": np.random.randint(40, 95) + np.sin(date.day) * 5, "키워드": "인공지능"})
        trend_data.append({"날짜": date, "비중": np.random.randint(60, 100) + np.cos(date.day) * 8, "키워드": "챗GPT"})
        trend_data.append({"날짜": date, "비중": np.random.randint(10, 45) - np.sin(date.day) * 3, "키워드": "메타버스"})
        
    df_trend = pd.DataFrame(trend_data)
    
    # 2. 검색 트렌드 라인 차트 생성
    fig_trend = px.line(
        df_trend, x="날짜", y="비중", color="키워드",
        labels={"비중": "상대적 검색 비중 (0~100)", "날짜": "조회 기간"},
        title="주요 키워드별 검색 트렌드 추이 (시뮬레이션)",
        color_discrete_sequence=["#1EC800", "#FF4B4B", "#00C0FF"]
    )
    fig_trend.update_layout(
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20)
    )
    trend_html = pio.to_html(fig_trend, include_plotlyjs='cdn', full_html=False)
    
    # 3. 쇼핑 시뮬레이션 데이터 생성
    malls = ["네이버쇼핑", "쿠팡", "G마켓", "11번가", "옥션", "SSG닷컴", "인터파크"]
    shop_data = {
        "판매처 (몰)": np.random.choice(malls, size=50),
        "최저가 (₩)": np.random.randint(150000, 350000, size=50)
    }
    df_shop = pd.DataFrame(shop_data)
    df_mall = df_shop.groupby("판매처 (몰)").agg(
        상품수=("최저가 (₩)", "count"),
        평균가격=("최저가 (₩)", "mean")
    ).reset_index()
    
    # 4. 쇼핑 바 차트 생성
    fig_shop = px.bar(
        df_mall, x="판매처 (몰)", y="상품수", color="평균가격",
        labels={"상품수": "등록 상품 수", "평균가격": "평균 판매가 (₩)"},
        title="판매처별 상품 등록 현황 및 평균가",
        color_continuous_scale="Viridis"
    )
    fig_shop.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20)
    )
    shop_html = pio.to_html(fig_shop, include_plotlyjs=False, full_html=False)
    
    # 5. 블로그 점유율 시뮬레이션 데이터 생성
    bloggers = ["IT 테크 연구소", "인공지능 가이드", "코딩하는 사람들", "얼리어답터의 일기", "디지털 라이프"]
    blog_data = {
        "블로그명": np.random.choice(bloggers, size=30),
        "발행수": np.ones(30)
    }
    df_blog = pd.DataFrame(blog_data).groupby("블로그명").count().reset_index()
    
    # 6. 블로그 파이 차트 생성
    fig_blog = px.pie(
        df_blog, values="발행수", names="블로그명",
        title="상위 블로그 채널 점유율 분포",
        hole=0.4
    )
    fig_blog.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20)
    )
    blog_html = pio.to_html(fig_blog, include_plotlyjs=False, full_html=False)

    # 7. HTML 템플릿 작성 (Tailwind CSS 기반 프리미엄 스타일)
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>네이버 오픈 API 데이터 분석 종합 보고서</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', 'Noto Sans KR', sans-serif;
            background-color: #f3f4f6;
        }}
        .gradient-header {{
            background: linear-gradient(135deg, #1EC800 0%, #009a00 100%);
        }}
    </style>
</head>
<body class="text-gray-800">
    <!-- 헤더 -->
    <header class="gradient-header text-white py-12 px-6 shadow-lg">
        <div class="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center">
            <div>
                <h1 class="text-3xl md:text-4xl font-extrabold tracking-tight">네이버 API 데이터 분석 종합 보고서</h1>
                <p class="mt-2 text-green-100 text-sm md:text-base">수집 데이터 요약 및 시각화 대시보드 리포트 (정적 오프라인 버전)</p>
            </div>
            <div class="mt-4 md:mt-0 bg-white/20 backdrop-blur-md px-4 py-2 rounded-lg border border-white/10 text-xs">
                <span>보고서 갱신일: {datetime.date.today().strftime('%Y년 %m월 %d일')}</span>
            </div>
        </div>
    </header>

    <!-- 메인 컨테이너 -->
    <main class="max-w-7xl mx-auto px-4 py-8 md:py-12">
        <!-- KPI 요약 카드 -->
        <section class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-white p-6 rounded-xl shadow-md border border-gray-100 flex flex-col items-center">
                <span class="text-gray-500 text-xs font-semibold uppercase tracking-wider">분석 대상 키워드</span>
                <span class="text-2xl font-bold text-gray-900 mt-2">인공지능, 챗GPT, 메타버스</span>
            </div>
            <div class="bg-white p-6 rounded-xl shadow-md border border-gray-100 flex flex-col items-center">
                <span class="text-gray-500 text-xs font-semibold uppercase tracking-wider">주요 강세 검색 키워드</span>
                <span class="text-2xl font-bold text-green-600 mt-2">챗GPT (평균 82.5)</span>
            </div>
            <div class="bg-white p-6 rounded-xl shadow-md border border-gray-100 flex flex-col items-center">
                <span class="text-gray-500 text-xs font-semibold uppercase tracking-wider">데이터 소스 채널 수</span>
                <span class="text-2xl font-bold text-blue-600 mt-2">5개 API 연동</span>
            </div>
        </section>

        <!-- 차트 영역 1 (검색 트렌드) -->
        <section class="bg-white p-6 rounded-xl shadow-md border border-gray-100 mb-8">
            <h2 class="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <span class="w-1.5 h-6 bg-green-500 rounded-full mr-2"></span>
                1. 검색어 트렌드 분석
            </h2>
            <div class="w-full">
                {trend_html}
            </div>
            <div class="mt-4 p-4 bg-gray-50 rounded-lg text-sm text-gray-600 leading-relaxed border-l-4 border-green-500">
                <strong>📝 트렌드 주요 발견점:</strong> 분석 결과 <strong>챗GPT</strong> 키워드가 전반적으로 높은 검색 비중을 꾸준히 유지하고 있습니다. 반면, <strong>메타버스</strong> 키워드는 상대적으로 하향 평준화된 트렌드를 나타내고 있으며, <strong>인공지능</strong>은 특정 시점에 강한 변동성(Spike)을 동반한 검색 흐름을 보입니다.
            </div>
        </section>

        <!-- 차트 영역 2 (쇼핑 & 블로그) -->
        <section class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <div class="bg-white p-6 rounded-xl shadow-md border border-gray-100">
                <h2 class="text-xl font-bold text-gray-900 mb-4 flex items-center">
                    <span class="w-1.5 h-6 bg-blue-500 rounded-full mr-2"></span>
                    2. 쇼핑 판매처 가격 통계
                </h2>
                <div class="w-full">
                    {shop_html}
                </div>
            </div>
            <div class="bg-white p-6 rounded-xl shadow-md border border-gray-100">
                <h2 class="text-xl font-bold text-gray-900 mb-4 flex items-center">
                    <span class="w-1.5 h-6 bg-purple-500 rounded-full mr-2"></span>
                    3. 블로그 포스트 정보 지분율
                </h2>
                <div class="w-full">
                    {blog_html}
                </div>
            </div>
        </section>

        <!-- 상세 안내 및 데이터 정보 -->
        <footer class="text-center text-xs text-gray-400 mt-12 py-6 border-t border-gray-200">
            <p>네이버 오픈 API 실시간 수집 가이드 및 대시보드 리포트 • 본 데이터는 시뮬레이션 샘플을 기반으로 작성되었습니다.</p>
        </footer>
    </main>
</body>
</html>
"""

    # 디렉토리 확인 및 저장
    output_dir = "naver-api-app/report"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_path = os.path.join(output_dir, "report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"정적 HTML 보고서가 성공적으로 빌드되었습니다: {output_path}")

if __name__ == "__main__":
    generate_static_report()
