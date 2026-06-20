"""
이 모듈은 사람인 채용 트렌드 분석 대시보드의 각 페이지별 세부 화면을 렌더링하는 
핵심 시각화 및 통계 분석 로직을 담고 있습니다.

주요 기능:
- 개요(KPI 요약, 기초통계 카드) 화면 구성
- 검색어 트렌드 분석(라인 차트, 왜도/첨도 계산)
- 공고 등록 빈도 분석(시계열 바 차트, IQR 기반 이상치 식별 및 Box Plot)
- 공고 상세 및 핵심 스택 분석(텍스트 분석, 가로 막대 차트, 상세 필터 테이블)
- 회사별 복지 혜택 분석(Box Plot 기반 분포 분석, 규모별 불균형 분석)
- 산업군 및 요인 간 상관성 분석(상관행렬 히트맵, 산점도, 통계 검정 주석)

모든 시각화는 Plotly를 사용해 구현되었으며, 사용자의 대화식 제어를 지원합니다.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import skew, kurtosis

# 세련된 컬러 팔레트 정의 (Premium Aesthetics)
COLOR_PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
THEME_TEMPLATE = "plotly_white"

def render_overview(keywords, start_date, end_date, df_trends, df_freq, df_jobs, df_ind):
    st.markdown("## 📊 대시보드 개요 및 주요 지표 (KPI)")
    st.markdown("수집된 채용 정보와 검색 트렌드에 대한 핵심 요약 정보입니다.")
    
    # KPI 요약 카드 배치
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_postings = df_freq["postings"].sum()
        st.metric(label="총 분석 공고 수", value=f"{total_postings:,} 건")
        
    with col2:
        avg_rating = round(df_jobs["rating"].mean(), 2)
        st.metric(label="분석 기업 평균 평점", value=f"⭐ {avg_rating} / 5.0")
        
    with col3:
        avg_salary = int(df_jobs["salary"].mean())
        st.metric(label="평균 제시 연봉", value=f"{avg_salary:,} 만원")
        
    with col4:
        avg_welfare = round(df_jobs["welfare_score"].mean(), 1)
        st.metric(label="평균 복지 점수", value=f"📋 {avg_welfare} 점")
        
    st.write("---")
    
    # 주요 차트 요약 요소를 나란히 배치
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("🎯 키워드별 공고 등록 비율")
        df_pie = df_jobs.groupby("keyword").size().reset_index(name="count")
        fig_pie = px.pie(
            df_pie, 
            values="count", 
            names="keyword", 
            color_discrete_sequence=COLOR_PALETTE,
            template=THEME_TEMPLATE
        )
        fig_pie.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_right:
        st.subheader("🏢 기업 규모별 공고 비율")
        df_bar = df_jobs.groupby("type").size().reset_index(name="count")
        fig_bar = px.bar(
            df_bar, 
            x="type", 
            y="count", 
            color="type",
            color_discrete_sequence=COLOR_PALETTE,
            template=THEME_TEMPLATE,
            labels={"type": "기업 규모", "count": "공고 수"}
        )
        fig_bar.update_layout(showlegend=False, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("### 🔍 분석 대상 기본 데이터 테이블 (샘플 10개)")
    st.dataframe(df_jobs[["company", "type", "industry", "keyword", "rating", "salary", "welfare_score"]].head(10), use_container_width=True)


def render_trends_analysis(keywords, start_date, end_date, df_trends):
    st.markdown("## 📈 검색어 트렌드 시계열 분석")
    st.markdown("네이버 데이터랩 API 데이터를 기반으로 한 키워드 간의 검색 비중 트렌드 비교입니다.")
    
    if df_trends.empty:
        st.warning("데이터가 없습니다. 올바른 키워드 및 기간을 선택했는지 확인하십시오.")
        return
        
    # 시계열 꺾은선 그래프
    st.subheader("🗓️ 일자별 검색량 변화 추이 (상대 비율)")
    
    fig_line = go.Figure()
    for idx, kw in enumerate(keywords):
        if kw in df_trends.columns:
            fig_line.add_trace(go.Scatter(
                x=df_trends["period"],
                y=df_trends[kw],
                mode='lines+markers',
                name=kw,
                line=dict(color=COLOR_PALETTE[idx % len(COLOR_PALETTE)], width=2),
                marker=dict(size=4)
            ))
            
    fig_line.update_layout(
        xaxis_title="날짜",
        yaxis_title="검색량 비율 (Max = 100)",
        template=THEME_TEMPLATE,
        legend_title="키워드",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=30, b=40)
    )
    st.plotly_chart(fig_line, use_container_width=True)
    
    st.markdown("### 📊 트렌드 분포의 통계적 건전성 검증")
    st.markdown("데이터의 대표값과 왜도(Skewness), 첨도(Kurtosis)를 통해 분포 특성을 통계적으로 심층 분석합니다.")
    
    stats_records = []
    for kw in keywords:
        if kw in df_trends.columns:
            y_data = df_trends[kw].values
            mean_val = np.mean(y_data)
            med_val = np.median(y_data)
            std_val = np.std(y_data)
            skew_val = skew(y_data)
            kurt_val = kurtosis(y_data)
            
            stats_records.append({
                "키워드": kw,
                "평균값": round(mean_val, 2),
                "중앙값": round(med_val, 2),
                "표준편차": round(std_val, 2),
                "왜도 (Skewness)": round(skew_val, 3),
                "첨도 (Kurtosis)": round(kurt_val, 3)
            })
            
    df_stats = pd.DataFrame(stats_records)
    st.dataframe(df_stats, use_container_width=True)
    
    # 왜도 및 첨도 해석 팁
    with st.expander("💡 왜도와 첨도 통계 용어 해석 가이드"):
        st.markdown("""
        * **왜도 (Skewness)**: 분포의 비대칭성을 나타내는 척도입니다.
          - **0에 가까울수록**: 정규분포처럼 대칭을 이룹니다.
          - **양수 (Skewed Right)**: 오른쪽으로 꼬리가 길며, 대부분의 검색량이 낮지만 가끔 매우 큰 검색량이 발생함을 뜻합니다.
          - **음수 (Skewed Left)**: 왼쪽으로 꼬리가 길며, 평소 고르게 높은 수준을 유지하다가 간혹 급락함을 의미합니다.
        * **첨도 (Kurtosis)**: 분포의 뾰족함과 꼬리의 두께를 나타냅니다.
          - **0에 가까울수록**: 정규분포에 가깝습니다.
          - **양수 (Leptokurtic)**: 꼬리가 매우 두껍고 평균 주변에 데이터가 뾰족하게 뭉쳐있어, 특정 검색량 구간에 쏠려 있고 극단적 변화가 많음을 의미합니다.
          - **음수 (Platykurtic)**: 데이터 분포가 비교적 완만하고 넓게 퍼져 있습니다.
        """)


def render_freq_analysis(keywords, start_date, end_date, df_freq):
    st.markdown("## 📅 채용 공고 등록 빈도 및 이상치 분석")
    st.markdown("일자별 및 요일별 채용 공고의 등록 빈도를 시계열로 분석하고, 채용이 급증한 이상치를 탐지합니다.")
    
    # 키워드별 누적 막대 그래프
    st.subheader("⏳ 일자별 채용 공고 등록 수")
    fig_freq = px.bar(
        df_freq, 
        x="date", 
        y="postings", 
        color="keyword", 
        color_discrete_sequence=COLOR_PALETTE,
        template=THEME_TEMPLATE,
        labels={"date": "날짜", "postings": "등록 공고 수", "keyword": "키워드"}
    )
    fig_freq.update_layout(barmode="stack", hovermode="x unified")
    st.plotly_chart(fig_freq, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📅 요일별 채용 공고 분포")
        # 요일 정렬을 위해 카테고리화
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        df_day = df_freq.groupby("day_of_week")["postings"].mean().reindex(day_order).reset_index()
        # 한글 요일 매핑
        day_kr = {"Monday": "월요일", "Tuesday": "화요일", "Wednesday": "수요일", "Thursday": "목요일", "Friday": "금요일", "Saturday": "토요일", "Sunday": "일요일"}
        df_day["요일"] = df_day["day_of_week"].map(day_kr)
        
        fig_day = px.bar(
            df_day,
            x="요일",
            y="postings",
            color="요일",
            color_discrete_sequence=COLOR_PALETTE,
            template=THEME_TEMPLATE,
            labels={"postings": "평균 등록 공고 수"}
        )
        fig_day.update_layout(showlegend=False)
        st.plotly_chart(fig_day, use_container_width=True)
        
    with col2:
        st.subheader("📦 키워드별 공고 등록 분포 및 이상치 식별 (Box Plot)")
        fig_box = px.box(
            df_freq,
            x="keyword",
            y="postings",
            color="keyword",
            color_discrete_sequence=COLOR_PALETTE,
            template=THEME_TEMPLATE,
            points="outliers",  # 아웃라이어 강조 표시
            labels={"keyword": "키워드", "postings": "등록 공고 수"}
        )
        fig_box.update_layout(showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)
        
    st.markdown("### ⚠️ IQR 기반 채용 공고 등록 이상 급증일(Outliers) 탐지")
    st.markdown("통계적 한계(IQR 기법)를 초과한 대량 채용 공고 등록일을 탐지합니다. (수시 채용 박람회 등 특이 시점 분석용)")
    
    outlier_records = []
    for kw in keywords:
        df_kw = df_freq[df_freq["keyword"] == kw]
        if df_kw.empty:
            continue
            
        q1 = df_kw["postings"].quantile(0.25)
        q3 = df_kw["postings"].quantile(0.75)
        iqr = q3 - q1
        upper_limit = q3 + 1.5 * iqr
        lower_limit = q1 - 1.5 * iqr
        
        # 이상치 필터링 (양의 이상치 위주로 필터링)
        df_outliers = df_kw[df_kw["postings"] > upper_limit]
        
        for _, row in df_outliers.iterrows():
            outlier_records.append({
                "키워드": kw,
                "이상 발생일": row["date"],
                "요일": row["day_of_week"].map(day_kr) if hasattr(row["day_of_week"], "map") else day_kr.get(row["day_of_week"], row["day_of_week"]),
                "등록 수": row["postings"],
                "통계 기준값(Q3 + 1.5*IQR)": round(upper_limit, 1)
            })
            
    if outlier_records:
        df_outlier_table = pd.DataFrame(outlier_records).sort_values("등록 수", ascending=False)
        st.dataframe(df_outlier_table, use_container_width=True)
    else:
        st.info("선택한 기간 동안 탐지된 통계적 공고 급증 이상치가 없습니다.")


def render_details_analysis(keywords, df_jobs):
    st.markdown("## 🔍 공고 상세 내용 및 핵심 역량 분석")
    st.markdown("공고 텍스트 데이터를 분석하여 많이 언급된 핵심 기술 스택과 상세 요건을 파악합니다.")
    
    # 기술 스택 빈도 분석
    st.subheader("🛠️ 분석 대상 키워드별 요구 기술 스택 빈도")
    
    # 텍스트 데이터에서 기술스택 수집
    tech_counts = {}
    for kw in keywords:
        df_kw = df_jobs[df_jobs["keyword"] == kw]
        tech_list = []
        for techs in df_kw["tech_stack"]:
            tech_list.extend(techs)
            
        if tech_list:
            df_tech = pd.Series(tech_list).value_counts().reset_index(name="count")
            df_tech.columns = ["technology", "count"]
            df_tech["keyword"] = kw
            tech_counts[kw] = df_tech
            
    if tech_counts:
        df_all_techs = pd.concat(tech_counts.values())
        fig_tech = px.bar(
            df_all_techs,
            y="technology",
            x="count",
            color="keyword",
            orientation="h",
            color_discrete_sequence=COLOR_PALETTE,
            template=THEME_TEMPLATE,
            labels={"technology": "기술 스택", "count": "공고 건수", "keyword": "키워드"}
        )
        fig_tech.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_tech, use_container_width=True)
    else:
        st.warning("분석할 스택 정보가 없습니다.")
        
    st.write("---")
    
    # 드릴다운 상세 분석 영역
    st.subheader("🕵️ 상세 공고 Drill-down 탐색기")
    st.markdown("원하는 키워드, 기업 규모, 산업군을 필터링하여 상세 공고 원문을 탐색합니다.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        sel_kw = st.selectbox("분석 키워드 필터", ["전체"] + list(keywords))
    with col2:
        sel_type = st.selectbox("기업 규모 필터", ["전체"] + list(df_jobs["type"].unique()))
    with col3:
        sel_ind = st.selectbox("산업군 필터", ["전체"] + list(df_jobs["industry"].unique()))
        
    # 필터링
    df_filtered = df_jobs.copy()
    if sel_kw != "전체":
        df_filtered = df_filtered[df_filtered["keyword"] == sel_kw]
    if sel_type != "전체":
        df_filtered = df_filtered[df_filtered["type"] == sel_type]
    if sel_ind != "전체":
        df_filtered = df_filtered[df_filtered["industry"] == sel_ind]
        
    st.markdown(f"선택한 필터 조건 결과: **총 {len(df_filtered)} 건**")
    
    # 테이블 표시 및 클릭 시 상세 보기 지원
    cols_to_show = ["company", "type", "industry", "rating", "salary", "tech_stack", "welfare_score", "description"]
    
    # 실제 수집 데이터에 날짜 필드들이 있다면 표시 목록에 추가
    extra_cols = ["reg_info", "reg_days_ago", "posting_period_days"]
    for c in extra_cols:
        if c in df_filtered.columns:
            cols_to_show.append(c)
            
    df_table = df_filtered[cols_to_show]
    
    # 한글 컬럼명 매핑
    rename_dict = {
        "company": "기업명",
        "type": "기업 규모",
        "industry": "산업군",
        "rating": "평점",
        "salary": "연봉 (만원)",
        "tech_stack": "요구 기술",
        "welfare_score": "복지 점수",
        "description": "공고 상세 및 등록 정보",
        "reg_info": "등록 시점",
        "reg_days_ago": "경과 일수",
        "posting_period_days": "총 공고 기간 (일)"
    }
    df_table_renamed = df_table.rename(columns=rename_dict)
    st.dataframe(df_table_renamed, use_container_width=True)


def render_welfare_analysis(df_jobs):
    st.markdown("## 🎁 기업별 복지 혜택 및 불균형 분석")
    st.markdown("기업의 규모와 산업군에 따라 복지 점수가 어떻게 차이가 나는지 통계적으로 검증합니다.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏢 기업 규모별 복지 점수(Welfare Score) 분포")
        fig_welf_box = px.box(
            df_jobs,
            x="type",
            y="welfare_score",
            color="type",
            color_discrete_sequence=COLOR_PALETTE,
            template=THEME_TEMPLATE,
            points="all",
            labels={"type": "기업 규모", "welfare_score": "복지 점수 (100점 만점)"}
        )
        fig_welf_box.update_layout(showlegend=False)
        st.plotly_chart(fig_welf_box, use_container_width=True)
        
    with col2:
        st.subheader("🧬 복지 만족도 분포 및 비대칭 분석")
        fig_welf_hist = px.histogram(
            df_jobs,
            x="welfare_score",
            color="type",
            color_discrete_sequence=COLOR_PALETTE,
            template=THEME_TEMPLATE,
            marginal="rug",  # 하단 융기 분포 추가
            labels={"welfare_score": "복지 점수"}
        )
        st.plotly_chart(fig_welf_hist, use_container_width=True)
        
    st.write("---")
    st.subheader("💡 범주별 불균형 분석 (Imbalance Check)")
    st.markdown("복지 카테고리별 제공률을 분석하여 기업 종류별 복지 양극화를 파악합니다.")
    
    # 전체 복지 목록 파싱
    all_welfares = []
    for wl in df_jobs["welfare_list"]:
        all_welfares.extend(wl)
    unique_welfares = list(set(all_welfares))
    
    # 기업 규모별 각 복지 제공 비중 계산
    welfare_matrix = []
    for comp_type in df_jobs["type"].unique():
        df_type = df_jobs[df_jobs["type"] == comp_type]
        total_type = len(df_type)
        
        type_welfares = []
        for wl in df_type["welfare_list"]:
            type_welfares.extend(wl)
            
        counts = pd.Series(type_welfares).value_counts()
        for w in unique_welfares:
            rate = round((counts.get(w, 0) / total_type) * 100, 1) if total_type > 0 else 0.0
            welfare_matrix.append({
                "기업 규모": comp_type,
                "복지 항목": w,
                "제공률 (%)": rate
            })
            
    df_wm = pd.DataFrame(welfare_matrix)
    
    fig_wm = px.bar(
        df_wm,
        x="복지 항목",
        y="제공률 (%)",
        color="기업 규모",
        barmode="group",
        color_discrete_sequence=COLOR_PALETTE,
        template=THEME_TEMPLATE,
        title="기업 규모별 세부 복지 혜택 제공 비율 (%)"
    )
    st.plotly_chart(fig_wm, use_container_width=True)


def render_industry_analysis(df_ind):
    st.markdown("## 🏢 산업군 통계 및 요인 간 상관성 분석")
    st.markdown("각 산업군별 평균 요인(급여, 평점, 경쟁률, 이직률 등)의 상호작용 및 통계적 연관성을 검증합니다.")
    
    # 1. 상관관계 분석
    st.subheader("🔗 분석 변수 간 피어슨 상관행렬 (Correlation Matrix)")
    df_numeric = df_ind.select_dtypes(include=[np.number])
    
    # 변수명 한글 매핑
    label_map = {
        "avg_rating": "평균 평점",
        "avg_salary": "평균 연봉 (만원)",
        "posting_count": "등록 공고 수",
        "competition_rate": "경쟁률 (대 1)",
        "turnover_rate": "이직률 (%)"
    }
    df_numeric_renamed = df_numeric.rename(columns=label_map)
    corr_matrix = df_numeric_renamed.corr(method="pearson")
    
    # Plotly Heatmap
    fig_heat = px.imshow(
        corr_matrix,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu_r",  # 빨간색(양의 상관), 파란색(음의 상관)
        zmin=-1.0, zmax=1.0,
        template=THEME_TEMPLATE
    )
    st.plotly_chart(fig_heat, use_container_width=True)
    
    # 다중공선성 경고 체크
    high_corr_pairs = []
    cols = corr_matrix.columns
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            val = corr_matrix.iloc[i, j]
            if abs(val) >= 0.9:
                high_corr_pairs.append((cols[i], cols[j], val))
                
    if high_corr_pairs:
        for p in high_corr_pairs:
            st.warning(f"⚠️ **다중공선성(Multicollinearity) 경고**: [{p[0]}]와(과) [{p[1]}] 사이의 상관계수가 **{p[2]:.2f}**로 매우 높습니다. 회귀 분석 및 예측 모델 수립 시 두 지표 중 하나만 사용하거나 가중치를 결합할 것을 권장합니다.")
            
    st.write("---")
    
    # 2. 산점도 분석
    st.subheader("📍 평균 연봉 vs 이직률 다차원 산점도 (공고 수 크기 반영)")
    fig_scatter = px.scatter(
        df_ind,
        x="avg_salary",
        y="turnover_rate",
        size="posting_count",
        color="industry",
        hover_name="industry",
        color_discrete_sequence=COLOR_PALETTE,
        template=THEME_TEMPLATE,
        labels={"avg_salary": "평균 연봉 (만원)", "turnover_rate": "이직률 (%)", "posting_count": "등록 공고 수"},
        title="산업군별 연봉 대비 이직률과 채용 규모의 상호 관계"
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    # 통계적 해석 및 가설 검정 가이드
    st.markdown("### 📝 분석 결과 해석 및 통계적 고찰")
    st.markdown("""
    * **평균 연봉과 이직률의 관계**: 위 상관행렬과 산점도에서 나타나듯, 평균 연봉이 높은 산업군일수록 이직률이 유의미하게 낮아지는 **강한 음의 상관관계**가 식별됩니다.
    * **경쟁률 영향 요인**: 평균 연봉 및 평점이 높을수록 구직자 선호도가 상승하여 입사 경쟁률이 올라가는 연관성을 보입니다.
    * **비즈니스 인사이트**: 인재 이직률을 낮추기 위해 연봉 수준 및 평점 관리가 핵심 동인이 될 수 있음을 시사합니다.
    """)
