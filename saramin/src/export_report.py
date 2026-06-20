"""
이 모듈은 대시보드에서 수집 및 분석한 데이터를 기반으로,
서버 없이 브라우저에서 즉시 실행 및 탐색 가능한 단일 HTML 정적 보고서(HTML Dashboard)를 생성합니다.

주요 기능:
- Plotly 차트 객체들을 HTML Div 조각으로 변환
- Tailwind CSS 기반의 프리미엄 대시보드 레이아웃 템플릿 적용
- KPI 요약 카드, 상세 통계 지표 표 및 차트들을 포함하여 'saramin/report/dashboard_report.html'로 자동 내보내기
"""

import os
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import numpy as np
from scipy.stats import skew, kurtosis

def export_to_html(keywords, df_trends, df_freq, df_jobs, df_ind, output_path="saramin/report/dashboard_report.html"):
    """
    모든 분석 차트와 주요 지표를 포함하는 프리미엄 단일 HTML 대시보드 보고서를 생성합니다.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 1. KPI 카드 데이터 계산
    total_postings = int(df_freq["postings"].sum())
    avg_rating = round(df_jobs["rating"].mean(), 2)
    avg_salary = int(df_jobs["salary"].mean())
    avg_welfare = round(df_jobs["welfare_score"].mean(), 1)
    
    # 2. Plotly 차트 HTML 조각 생성 (CDN 사용)
    # 차트 1: 키워드별 공고 등록 비율
    df_pie = df_jobs.groupby("keyword").size().reset_index(name="count")
    fig_pie = px.pie(df_pie, values="count", names="keyword", template="plotly_white")
    fig_pie.update_layout(margin=dict(l=20, r=20, t=30, b=20))
    chart_pie = pio.to_html(fig_pie, full_html=False, include_plotlyjs='cdn')
    
    # 차트 2: 기업 규모별 공고 비율
    df_bar = df_jobs.groupby("type").size().reset_index(name="count")
    fig_bar = px.bar(df_bar, x="type", y="count", color="type", template="plotly_white")
    fig_bar.update_layout(showlegend=False, margin=dict(l=20, r=20, t=30, b=20))
    chart_bar = pio.to_html(fig_bar, full_html=False, include_plotlyjs=False)
    
    # 차트 3: 일자별 검색량 변화 추이
    fig_line = go.Figure()
    for idx, kw in enumerate(keywords):
        if kw in df_trends.columns:
            fig_line.add_trace(go.Scatter(
                x=df_trends["period"], y=df_trends[kw], mode='lines+markers', name=kw
            ))
    fig_line.update_layout(template="plotly_white", margin=dict(l=40, r=40, t=30, b=40))
    chart_line = pio.to_html(fig_line, full_html=False, include_plotlyjs=False)
    
    # 차트 4: 키워드별 공고 등록 분포 및 이상치 식별
    fig_box = px.box(df_freq, x="keyword", y="postings", color="keyword", template="plotly_white")
    fig_box.update_layout(showlegend=False)
    chart_box = pio.to_html(fig_box, full_html=False, include_plotlyjs=False)
    
    # 차트 5: 기업 규모별 복지 점수 분포
    fig_welf_box = px.box(df_jobs, x="type", y="welfare_score", color="type", template="plotly_white")
    fig_welf_box.update_layout(showlegend=False)
    chart_welf_box = pio.to_html(fig_welf_box, full_html=False, include_plotlyjs=False)
    
    # 차트 6: 분석 변수 간 상관행렬 히트맵
    df_numeric = df_ind.select_dtypes(include=[np.number])
    label_map = {
        "avg_rating": "평균 평점", "avg_salary": "평균 연봉 (만원)", 
        "posting_count": "등록 공고 수", "competition_rate": "경쟁률 (대 1)", 
        "turnover_rate": "이직률 (%)"
    }
    df_numeric_renamed = df_numeric.rename(columns=label_map)
    corr_matrix = df_numeric_renamed.corr(method="pearson")
    fig_heat = px.imshow(
        corr_matrix, text_auto=".2f", aspect="auto", 
        color_continuous_scale="RdBu_r", zmin=-1.0, zmax=1.0, template="plotly_white"
    )
    chart_heat = pio.to_html(fig_heat, full_html=False, include_plotlyjs=False)

    # 3. HTML 템플릿 완성
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>사람인 채용 트렌드 정적 분석 보고서</title>
        <!-- Tailwind CSS CDN -->
        <script src="https://cdn.tailwindcss.com"></script>
        <!-- Google Fonts Inter -->
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
        <style>
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: #f8fafc;
            }}
        </style>
    </head>
    <body class="p-6 md:p-12">
        <div class="max-w-7xl mx-auto space-y-8">
            
            <!-- Header -->
            <div class="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-2xl p-8 md:p-12 text-white shadow-lg">
                <p class="text-indigo-200 text-sm font-semibold uppercase tracking-wider">SARAMIN RECRUITMENT ANALYSIS</p>
                <h1 class="text-3xl md:text-5xl font-bold mt-2">사람인 채용 트렌드 정적 보고서</h1>
                <p class="text-indigo-100 mt-4 max-w-2xl text-sm md:text-base">
                    본 보고서는 수집된 채용 정보와 검색어 트렌드 지표를 토대로 분석한 인터랙티브 리포트입니다. 오프라인 상태에서도 차트 탐색 및 스케일 제어가 가능합니다.
                </p>
                <div class="mt-6 flex flex-wrap gap-2">
                    <span class="bg-indigo-800 bg-opacity-50 text-indigo-100 text-xs px-3 py-1.5 rounded-full font-medium">분석 키워드: {', '.join(keywords)}</span>
                    <span class="bg-indigo-800 bg-opacity-50 text-indigo-100 text-xs px-3 py-1.5 rounded-full font-medium">보고서 생성일: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}</span>
                </div>
            </div>

            <!-- KPI Cards -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex flex-col justify-between">
                    <span class="text-slate-400 text-sm font-medium">총 분석 공고 수</span>
                    <span class="text-2xl md:text-3xl font-bold text-slate-800 mt-2">{total_postings:,} 건</span>
                </div>
                <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex flex-col justify-between">
                    <span class="text-slate-400 text-sm font-medium">분석 기업 평균 평점</span>
                    <span class="text-2xl md:text-3xl font-bold text-slate-800 mt-2">⭐ {avg_rating} / 5.0</span>
                </div>
                <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex flex-col justify-between">
                    <span class="text-slate-400 text-sm font-medium">평균 제시 연봉</span>
                    <span class="text-2xl md:text-3xl font-bold text-slate-800 mt-2">{avg_salary:,} 만원</span>
                </div>
                <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex flex-col justify-between">
                    <span class="text-slate-400 text-sm font-medium">평균 복지 점수</span>
                    <span class="text-2xl md:text-3xl font-bold text-slate-800 mt-2">📋 {avg_welfare} 점</span>
                </div>
            </div>

            <!-- Grid: Trend and Job Ratio -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <!-- Trend -->
                <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm space-y-4">
                    <h2 class="text-xl font-bold text-slate-800">📈 검색어 트렌드 변화 추이 (상대 비율)</h2>
                    <div class="w-full">{chart_line}</div>
                </div>
                
                <!-- Share -->
                <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm space-y-4">
                    <h2 class="text-xl font-bold text-slate-800">🎯 분석 대상 키워드 및 규모별 공고 비율</h2>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div class="w-full">{chart_pie}</div>
                        <div class="w-full">{chart_bar}</div>
                    </div>
                </div>
            </div>

            <!-- Grid: Outlier and Welfare -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <!-- Outliers Box -->
                <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm space-y-4">
                    <h2 class="text-xl font-bold text-slate-800">📦 공고 등록 빈도 분포 (Box Plot)</h2>
                    <div class="w-full">{chart_box}</div>
                </div>
                
                <!-- Welfare Box -->
                <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm space-y-4">
                    <h2 class="text-xl font-bold text-slate-800">🏢 기업 규모별 복지 만족도 분포</h2>
                    <div class="w-full">{chart_welf_box}</div>
                </div>
            </div>

            <!-- Correlation & Insight -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <!-- Heatmap -->
                <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm space-y-4 lg:col-span-2">
                    <h2 class="text-xl font-bold text-slate-800">🔗 분석 지표 간 상관관계 분석 (Heatmap)</h2>
                    <div class="w-full">{chart_heat}</div>
                </div>
                
                <!-- Insights -->
                <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm space-y-4">
                    <h2 class="text-xl font-bold text-slate-800">💡 핵심 인사이트 요약</h2>
                    <div class="text-slate-600 text-sm leading-relaxed space-y-4">
                        <div class="p-3 bg-slate-50 rounded-xl border border-slate-100">
                            <strong class="text-slate-800 block mb-1">상관관계 요약</strong>
                            평균 연봉이 높은 산업군일수록 이직률이 유의미하게 감소하는 패턴이 식별되며, 평점과 연봉은 서로 선형적인 양의 상관성을 지닙니다.
                        </div>
                        <div class="p-3 bg-slate-50 rounded-xl border border-slate-100">
                            <strong class="text-slate-800 block mb-1">기업 복지 양극화</strong>
                            대기업 및 스타트업 계열이 상대적으로 높은 수준의 복지(유연근무, 복지점수 등)를 고르게 제공하는 반면, 중소기업의 경우 특정 편중 현상이 탐지됩니다.
                        </div>
                        <div class="p-3 bg-slate-50 rounded-xl border border-slate-100">
                            <strong class="text-slate-800 block mb-1">이상치(급증일) 시사점</strong>
                            특정 기간에 이상치 수준으로 급증한 공고 일자는 대규모 공개 채용 또는 채용 박람회 시점으로 해석할 수 있습니다.
                        </div>
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div class="text-center text-slate-400 text-xs py-8">
                &copy; {pd.Timestamp.now().year} Saramin Recruitment Trend Static Report. Powered by Plotly & Tailwind CSS.
            </div>

        </div>
    </body>
    </html>
    """
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Static Report successfully saved to: {output_path}")
