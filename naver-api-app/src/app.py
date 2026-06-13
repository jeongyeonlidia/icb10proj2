"""
네이버 오픈 API(검색 트렌드, 쇼핑, 블로그, 카페글, 뉴스, 쇼핑 트렌드)를 활용한 
실시간 데이터 수집 및 시각화 대시보드 어플리케이션입니다.

주요 기능:
- 네이버 API 인증 키(Client ID, Secret) 수신 및 세션 관리
- 검색어 트렌드 시계열 분석 및 통계 분석 (왜도, 첨도 포함)
- 쇼핑인사이트 키워드 클릭 트렌드 연동 비교
- 쇼핑 상품 검색 결과에 대한 가격 비교 및 주요 판매처 분포 분석
- 블로그, 카페글, 뉴스 검색 결과 수집 및 발행 추이 시각화
"""

import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import datetime
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드 (.env)
dotenv_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=dotenv_path, override=True)

# 1. 페이지 기본 설정 및 디자인
st.set_page_config(
    page_title="네이버 API 종합 분석 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS를 통한 디자인 향상 (글라스모피즘 스타일 가미)
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1EC800;
        text-align: center;
        margin-bottom: 2rem;
        border-bottom: 2px solid #1EC800;
        padding-bottom: 10px;
    }
    .sub-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #333333;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .kpi-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .kpi-val {
        font-size: 2rem;
        font-weight: 700;
        color: #1EC800;
    }
</style>
""", unsafe_allow_html=True)

# 2. 사이드바 - API 키 수신 및 공통 설정
st.sidebar.markdown("# 🔑 네이버 API 설정")

client_id = ""
client_secret = ""

# 1. Streamlit Secrets(배포 환경용) 우선 로드
if "NAVER_CLIENT_ID" in st.secrets:
    client_id = st.secrets["NAVER_CLIENT_ID"].strip()
if "NAVER_CLIENT_SECRET" in st.secrets:
    client_secret = st.secrets["NAVER_CLIENT_SECRET"].strip()

# 2. 로컬 환경 변수(.env) 백업 로드
if not client_id:
    client_id = os.getenv("NAVER_CLIENT_ID", "").strip()
if not client_secret:
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip()

# ASCII 인코딩 검증을 통한 헤더 인코딩 에러(UnicodeEncodeError) 원천 차단
is_valid_keys = True
if client_id or client_secret:
    try:
        if client_id:
            client_id.encode('ascii')
        if client_secret:
            client_secret.encode('ascii')
    except UnicodeEncodeError:
        is_valid_keys = False
        st.sidebar.error("⚠️ Client ID와 Secret은 영문, 숫자, 아스키 문자만 포함해야 합니다. 설정값에 한글이나 보이지 않는 유니코드 공백문자가 섞여있는지 확인해 주세요.")
        client_id = ""
        client_secret = ""

# API 상태 표시기 및 로드 소스 표시
if client_id and client_secret and is_valid_keys:
    source = "Secrets" if "NAVER_CLIENT_ID" in st.secrets else ".env"
    st.sidebar.success(f"🟢 API 인증 정보 로드 완료 (From {source})")
else:
    st.sidebar.error("🔴 Streamlit Secrets 혹은 .env 파일에 네이버 API 인증 정보를 기입해 주세요.")

st.sidebar.markdown("---")
st.sidebar.markdown("# ⚙️ 공통 분석 필터")

# 조회 기간 설정
today = datetime.date.today()
six_months_ago = today - datetime.timedelta(days=180)
date_range = st.sidebar.date_input("조회 기간 설정", [six_months_ago, today])
if isinstance(date_range, list) or isinstance(date_range, tuple):
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = date_range[0]
        end_date = today
else:
    start_date = date_range
    end_date = today

start_date_str = start_date.strftime("%Y-%m-%d")
end_date_str = end_date.strftime("%Y-%m-%d")

# 조회 주기 설정
time_unit = st.sidebar.selectbox("조회 주기", ["일간 (date)", "주간 (week)", "월간 (month)"], index=0)
time_unit_val = "date" if "일간" in time_unit else "week" if "주간" in time_unit else "month"

# 검색어 쉼표 구분 입력
keyword_input = st.sidebar.text_input("검색어 입력 (쉼표로 구분)", "인공지능, 챗GPT, 메타버스", help="여러 개의 검색어를 쉼표(,)로 분리하여 입력하세요.")
keywords = [k.strip() for k in keyword_input.split(",") if k.strip()]

# 세부 타겟 필터
st.sidebar.markdown("### 🎯 타겟 필터 (트렌드 조회용)")
device = st.sidebar.selectbox("기기 구분", ["전체 기기", "PC", "모바일 (mo)"], index=0)
device_val = "" if "전체" in device else "pc" if device == "PC" else "mo"

gender = st.sidebar.selectbox("성별 구분", ["전체 성별", "남성 (m)", "여성 (f)"], index=0)
gender_val = "" if "전체" in gender else "m" if "남성" in gender else "f"

ages = st.sidebar.multiselect(
    "연령대 구분", 
    ["10대 이하", "20대", "30대", "40대", "50대", "60대 이상"],
    default=[]
)
# 연령대 코드 매핑
age_map = {"10대 이하": ["1", "2"], "20대": ["3", "4"], "30대": ["5", "6"], "40대": ["7", "8"], "50대": ["9", "10"], "60대 이상": ["11"]}
age_codes = []
for a in ages:
    age_codes.extend(age_map[a])

# 3. 메뉴 이동
menu = st.sidebar.selectbox(
    "📋 대시보드 페이지 이동", 
    [
        "🏠 홈 및 사용 가이드", 
        "📊 검색어 트렌드 분석", 
        "📈 쇼핑 클릭 트렌드", 
        "🛒 쇼핑 상품 검색", 
        "📝 블로그 검색 분석", 
        "☕ 카페글 검색 분석", 
        "📰 뉴스 검색 분석"
    ]
)

# 4. 공통 API 에러 메시지 래퍼
def handle_api_error(status_code, response_json):
    if status_code == 401:
        st.error(f"❌ 인증 실패 (401): Client ID/Secret 정보를 확인해 주세요. (에러 코드: {response_json.get('errorCode')})")
    elif status_code == 403:
        st.error(f"❌ 권한 없음 (403): 개발자 센터에서 해당 API를 애플리케이션의 'API 설정' 탭에 추가하셨는지 확인해 주세요. (에러 코드: {response_json.get('errorCode')})")
    else:
        st.error(f"❌ API 호출 실패 (상태 코드: {status_code}): {response_json.get('errorMessage', '알 수 없는 서버 에러가 발생했습니다.')}")

# 5. 각 페이지 비즈니스 로직
if menu == "🏠 홈 및 사용 가이드":
    st.markdown("<div class='main-title'>네이버 API 데이터 수집 및 분석 대시보드</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        ### 💡 서비스 개요
        본 대시보드는 네이버 오픈 API를 실시간으로 호출하여 트렌드 정보, 상품 검색, 블로그, 카페글, 뉴스 기사를 다각도로 수집하고 분석할 수 있는 종합 비즈니스 시각화 도구입니다.
        
        #### ⚙️ 시작 방법:
        1. **로컬 실행**: 루트 디렉토리의 **.env** 파일에 **NAVER_CLIENT_ID**와 **NAVER_CLIENT_SECRET**을 기입합니다.
        2. **배포 환경**: Streamlit Cloud의 **Secrets** 관리 탭에 동일 키들을 기입합니다.
        3. 공통 필터(조회 기간, 검색 키워드)를 정의합니다.
        4. 왼쪽 페이지 목록에서 원하는 분석 영역을 클릭하여 모니터링을 개시합니다.
        """)
    
    with col2:
        st.image("https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=600&q=80", caption="비즈니스 데이터 인텔리전스 분석 시각화")

    st.markdown("---")
    st.markdown("### 📁 제공 기능 가이드")
    
    doc_cols = st.columns(3)
    with doc_cols[0]:
        st.subheader("📊 검색어 트렌드")
        st.write("키워드 간 검색량 비중 및 변화 추이를 상댓값(0~100)으로 추적 및 통계 분석을 제공합니다.")
    with doc_cols[1]:
        st.subheader("📈 쇼핑 클릭 트렌드")
        st.write("특정 쇼핑 카테고리 내 제품 키워드가 모바일, PC 등 조건별로 어떤 클릭율 흐름을 보이는지 분석합니다.")
    with doc_cols[2]:
        st.subheader("🛒 쇼핑 상품 검색")
        st.write("네이버 쇼핑 상품을 조회하고, 판매처별 최저가 분포 및 상품군 구성을 인터랙티브 차트로 가시화합니다.")

    doc_cols2 = st.columns(3)
    with doc_cols2[0]:
        st.subheader("📝 블로그 검색 분석")
        st.write("블로그 글을 수집하여 포스트 작성 시간 분포 및 블로그 브랜드별 점유율을 집계합니다.")
    with doc_cols2[1]:
        st.subheader("☕ 카페글 검색 분석")
        st.write("네이버 카페에 공유된 글들의 빈도를 조사하여 커뮤니티 여론을 탐지할 수 있도록 돕습니다.")
    with doc_cols2[2]:
        st.subheader("📰 뉴스 검색 분석")
        st.write("관련 기사들의 등록 타임라인을 파악하여 미디어 노출 추세를 분석합니다.")

elif menu == "📊 검색어 트렌드 분석":
    st.markdown("<div class='main-title'>📊 네이버 검색어 트렌드 분석</div>", unsafe_allow_html=True)
    
    if not client_id or not client_secret:
        st.warning("👉 대시보드를 활성화하기 위해 Streamlit Secrets 또는 프로젝트 루트의 .env 파일에 Client ID 및 Client Secret을 입력해 주세요.")
    elif len(keywords) == 0:
        st.info("💡 사이드바에 검색 키워드를 입력해 주세요.")
    else:
        st.markdown(f"**현재 설정 키워드**: {', '.join(keywords)} (총 {len(keywords)}개)")
        
        # API 요청 데이터 생성
        url = "https://openapi.naver.com/v1/datalab/search"
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
            "Content-Type": "application/json"
        }
        
        keyword_groups = [{"groupName": kw, "keywords": [kw]} for kw in keywords]
        
        body = {
            "startDate": start_date_str,
            "endDate": end_date_str,
            "timeUnit": time_unit_val,
            "keywordGroups": keyword_groups
        }
        if device_val:
            body["device"] = device_val
        if gender_val:
            body["gender"] = gender_val
        if age_codes:
            body["ages"] = age_codes
            
        with st.spinner("네이버 검색 트렌드 데이터를 수집 중입니다..."):
            res = requests.post(url, json=body, headers=headers)
            
        if res.status_code == 200:
            data = res.json()
            
            # 데이터 파싱
            records = []
            for group in data['results']:
                group_name = group['title']
                for d in group['data']:
                    records.append({
                        "period": d['period'],
                        "ratio": d['ratio'],
                        "keyword": group_name
                    })
                    
            if len(records) > 0:
                df = pd.DataFrame(records)
                df['period'] = pd.to_datetime(df['period'])
                
                # 피벗 형식 변환
                df_pivot = df.pivot(index='period', columns='keyword', values='ratio').reset_index()
                
                # 1. 시계열 선 차트 시각화
                fig = px.line(
                    df, x="period", y="ratio", color="keyword",
                    labels={"period": "조회 기간", "ratio": "상대적 검색 비중 (0~100)", "keyword": "키워드"},
                    title=f"검색 트렌드 추이 ({time_unit_val} 단위)",
                    color_discrete_sequence=px.colors.qualitative.Plotly
                )
                fig.update_layout(hovermode="x unified", legend_title_text="키워드")
                st.plotly_chart(fig, use_container_width=True)
                
                # 2. 기술 통계량 산출 (체크리스트 1, 2 만족)
                st.markdown("<div class='sub-title'>📈 검색 트렌드 기술 통계량</div>", unsafe_allow_html=True)
                
                stats_list = []
                for col in df_pivot.columns:
                    if col == 'period':
                        continue
                    series = df_pivot[col].dropna()
                    if len(series) > 0:
                        stats_list.append({
                            "키워드": col,
                            "평균 (Mean)": np.round(series.mean(), 2),
                            "중앙값 (Median)": np.round(series.median(), 2),
                            "최댓값 (Max)": np.round(series.max(), 2),
                            "최소값 (Min)": np.round(series.min(), 2),
                            "표준편차 (Std)": np.round(series.std(), 2),
                            "왜도 (Skewness)": np.round(series.skew(), 2) if not pd.isna(series.skew()) else 0.0,
                            "첨도 (Kurtosis)": np.round(series.kurtosis(), 2) if not pd.isna(series.kurtosis()) else 0.0
                        })
                
                df_stats = pd.DataFrame(stats_list)
                st.dataframe(df_stats, use_container_width=True)
                
                # 3. 데이터 요약
                st.markdown("<div class='sub-title'>📝 데이터 분석 발견 사항 (Key Findings)</div>", unsafe_allow_html=True)
                for index, row in df_stats.iterrows():
                    kw = row["키워드"]
                    max_ratio = row["최댓값 (Max)"]
                    avg_ratio = row["평균 (Mean)"]
                    skewness = row["왜도 (Skewness)"]
                    
                    skew_desc = "우측으로 꼬리가 길며 대부분 낮은 수치를 유지하다가 간헐적으로 강하게 검색되는 형태" if skewness > 0 else "좌측으로 꼬리가 길고 대체로 높은 검색 비중을 유지하는 형태"
                    st.write(f"💡 **{kw}**: 최대 검색 비중은 **{max_ratio}** 이며, 평균적인 검색 지수는 **{avg_ratio}** 입니다. 분포의 비대칭도(왜도)가 **{skewness}**인 것으로 보아, **{skew_desc}**를 띱니다.")
                
                # 4. 미래 예측 및 What-if 시뮬레이션 섹션
                st.markdown("---")
                st.markdown("<div class='sub-title'>🔮 미래 트렌드 예측 및 What-if 시뮬레이션</div>", unsafe_allow_html=True)
                st.write("과거 검색 트렌드 데이터를 기반으로 선형 추세를 분석하고, 마케팅 효과 등의 가중치를 반영하여 향후 트렌드를 시뮬레이션합니다.")
                
                sim_col1, sim_col2 = st.columns(2)
                with sim_col1:
                    pred_days = st.slider("예측 기간 설정 (일)", min_value=10, max_value=90, value=30, step=10)
                with sim_col2:
                    growth_rate = st.slider(
                        "마케팅 및 성장 가중치 (%)", 
                        min_value=-50, 
                        max_value=50, 
                        value=0, 
                        step=5,
                        help="미래 트렌드 기울기에 반영할 성장 시너지 가중치입니다. 양수이면 성장이 가속화되고, 음수이면 성장세가 둔화됩니다."
                    )
                
                # 예측 시뮬레이션 차트 생성 (Plotly go 사용)
                fig_sim = go.Figure()
                colors = px.colors.qualitative.Plotly
                
                last_date = df_pivot['period'].max()
                future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=pred_days)
                
                # 과거 데이터의 총 일수 계산 (기울기 계산 시점용)
                x_past = np.arange(len(df_pivot))
                x_future = np.arange(len(df_pivot), len(df_pivot) + pred_days)
                
                st.markdown("##### 💡 시나리오 기반 예측 결과 코멘트")
                
                for idx, col in enumerate(df_pivot.columns):
                    if col == 'period':
                        continue
                    
                    series = df_pivot[col].values
                    # 결측치 보정 (선형 회귀 적합용으로 dropna 처리한 x, y 쌍 구성)
                    valid_idx = ~pd.isna(series)
                    x_valid = x_past[valid_idx]
                    y_valid = series[valid_idx]
                    
                    if len(y_valid) < 2:
                        continue
                        
                    # 선형 회귀 계수 구하기 (1차 다항식)
                    slope, intercept = np.polyfit(x_valid, y_valid, 1)
                    
                    # 마케팅 가중치 반영 기울기 조정
                    adjusted_slope = slope * (1 + growth_rate / 100.0)
                    
                    # 예측값 계산 및 0~100 범위 바인딩
                    pred_y = adjusted_slope * x_future + intercept
                    pred_y = np.clip(pred_y, 0.0, 100.0)
                    
                    color = colors[idx % len(colors)]
                    
                    # 1. 과거 실측 데이터 추가 (실선)
                    fig_sim.add_trace(go.Scatter(
                        x=df_pivot['period'],
                        y=series,
                        mode='lines',
                        name=f"{col} (실측)",
                        line=dict(color=color, width=2.5)
                    ))
                    
                    # 2. 미래 예측 데이터 추가 (점선)
                    # 시각적 연속성을 위해 과거 마지막 데이터포인트를 미래 데이터 처음에 결합
                    last_past_val = series[-1] if not pd.isna(series[-1]) else y_valid[-1]
                    comb_dates = [df_pivot['period'].iloc[-1]] + list(future_dates)
                    comb_pred_y = [last_past_val] + list(pred_y)
                    
                    fig_sim.add_trace(go.Scatter(
                        x=comb_dates,
                        y=comb_pred_y,
                        mode='lines',
                        name=f"{col} (예측)",
                        line=dict(color=color, width=2, dash='dash')
                    ))
                    
                    # 키워드별 코멘트 생성
                    final_pred_val = np.round(pred_y[-1], 2)
                    trend_dir = "상승" if adjusted_slope > 0 else "하락" if adjusted_slope < 0 else "보합"
                    st.write(f"- 📢 **{col}**: {pred_days}일 뒤 예상 검색 비중 지수는 **{final_pred_val}** (추세: **{trend_dir}**)으로 전망됩니다.")
                
                fig_sim.update_layout(
                    title=f"미래 트렌드 예측 시뮬레이션 (성장 가중치: {growth_rate}%)",
                    xaxis_title="기간",
                    yaxis_title="검색 비중 (0~100)",
                    hovermode="x unified",
                    legend_title_text="범례",
                    template="plotly_white"
                )
                st.plotly_chart(fig_sim, use_container_width=True)
            else:
                st.warning("⚠️ 조회 조건에 일치하는 데이터가 데이터 소스 내에 존재하지 않습니다.")
        else:
            handle_api_error(res.status_code, res.json())

elif menu == "📈 쇼핑 클릭 트렌드":
    st.markdown("<div class='main-title'>📈 네이버 쇼핑 클릭 트렌드 분석</div>", unsafe_allow_html=True)
    
    if not client_id or not client_secret:
        st.warning("👉 대시보드를 활성화하기 위해 Streamlit Secrets 또는 프로젝트 루트의 .env 파일에 Client ID 및 Client Secret을 입력해 주세요.")
    elif len(keywords) == 0:
        st.info("💡 사이드바에 검색 키워드를 입력해 주세요.")
    else:
        # 카테고리 ID 선택 구성
        cat_choices = {
            "패션의류 (50000000)": "50000000",
            "패션잡화 (50000001)": "50000001",
            "화장품/미용 (50000002)": "50000002",
            "디지털/가전 (50000003)": "50000003",
            "가구/인테리어 (50000004)": "50000004",
            "출산/육아 (50000005)": "50000005",
            "식품 (50000006)": "50000006",
            "스포츠/레저 (50000007)": "50000007",
            "생활/건강 (50000008)": "50000008",
            "여가/생활편의 (50000009)": "50000009",
            "면세점 (50000010)": "50000010",
            "도서 (50005542)": "50005542"
        }
        
        selected_cat_name = st.selectbox("쇼핑 분야 카테고리 선택", list(cat_choices.keys()))
        selected_cat_id = cat_choices[selected_cat_name]
        
        st.markdown(f"**조회 분야**: {selected_cat_name} | **대상 키워드**: {', '.join(keywords)}")
        
        url = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
            "Content-Type": "application/json"
        }
        
        all_keyword_records = []
        
        with st.spinner("쇼핑 클릭 트렌드 수집 중 (각 키워드별 순차 호출)..."):
            for kw in keywords:
                body = {
                    "startDate": start_date_str,
                    "endDate": end_date_str,
                    "timeUnit": time_unit_val,
                    "category": selected_cat_id,
                    "keyword": kw
                }
                if device_val:
                    body["device"] = device_val
                if gender_val:
                    body["gender"] = gender_val
                if age_codes:
                    body["ages"] = age_codes
                    
                res = requests.post(url, json=body, headers=headers)
                
                if res.status_code == 200:
                    data = res.json()
                    # data['results']에 해당 키워드 결과 리스트 수신됨
                    for res_item in data['results']:
                        for d in res_item['data']:
                            all_keyword_records.append({
                                "period": d['period'],
                                "ratio": d['ratio'],
                                "keyword": kw
                            })
                elif res.status_code in [401, 403]:
                    handle_api_error(res.status_code, res.json())
                    break
                    
        if len(all_keyword_records) > 0:
            df_shop = pd.DataFrame(all_keyword_records)
            df_shop['period'] = pd.to_datetime(df_shop['period'])
            
            # 시계열 추이 시각화
            fig_shop = px.line(
                df_shop, x="period", y="ratio", color="keyword",
                labels={"period": "조회 기간", "ratio": "쇼핑 클릭율 비율 (상대치)", "keyword": "키워드"},
                title="쇼핑 클릭 트렌드 비교",
                color_discrete_sequence=px.colors.qualitative.Alphabet
            )
            fig_shop.update_layout(hovermode="x unified")
            st.plotly_chart(fig_shop, use_container_width=True)
            
            # 상세 통계 테이블 표시
            st.markdown("<div class='sub-title'>📊 쇼핑 트렌드 통계 집계</div>", unsafe_allow_html=True)
            
            df_shop_pivot = df_shop.pivot(index='period', columns='keyword', values='ratio').reset_index()
            shop_stats = []
            for col in df_shop_pivot.columns:
                if col == 'period':
                    continue
                series = df_shop_pivot[col].dropna()
                if len(series) > 0:
                    shop_stats.append({
                        "키워드": col,
                        "평균 클릭율": np.round(series.mean(), 2),
                        "최대 클릭율": np.round(series.max(), 2),
                        "최소 클릭율": np.round(series.min(), 2),
                        "표준편차": np.round(series.std(), 2)
                    })
            st.table(pd.DataFrame(shop_stats))
        else:
            st.warning("⚠️ 데이터를 성공적으로 수집하지 못했습니다. 키워드 혹은 API 키 설정을 확인해 주세요.")

elif menu == "🛒 쇼핑 상품 검색":
    st.markdown("<div class='main-title'>🛒 네이버 쇼핑 상품 검색 및 가격 분석</div>", unsafe_allow_html=True)
    
    if not client_id or not client_secret:
        st.warning("👉 대시보드를 활성화하기 위해 Streamlit Secrets 또는 프로젝트 루트의 .env 파일에 Client ID 및 Client Secret을 입력해 주세요.")
    elif len(keywords) == 0:
        st.info("💡 사이드바에 검색 키워드를 입력해 주세요.")
    else:
        # 단일 검색 키워드 선택
        selected_kw = st.selectbox("검색 키워드 선택", keywords)
        
        display_num = st.slider("조회할 상품 수", min_value=10, max_value=100, value=30, step=10)
        sort_option = st.selectbox("정렬 기준", ["정확도순 (sim)", "날짜순 (date)", "가격 오름차순 (asc)", "가격 내림차순 (dsc)"])
        sort_val = sort_option.split(" ")[-1].replace("(", "").replace(")", "")
        
        url = "https://openapi.naver.com/v1/search/shop.json"
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret
        }
        params = {
            "query": selected_kw,
            "display": display_num,
            "sort": sort_val
        }
        
        with st.spinner("상품 정보를 검색 중입니다..."):
            res = requests.get(url, params=params, headers=headers)
            
        if res.status_code == 200:
            data = res.json()
            
            items = data.get('items', [])
            if len(items) > 0:
                # 데이터 가공
                records = []
                for item in items:
                    lprice = float(item['lprice']) if item['lprice'] else 0.0
                    records.append({
                        "상품명": item['title'].replace("<b>", "").replace("</b>", ""),
                        "최저가 (₩)": lprice,
                        "판매처 (몰)": item['mallName'] if item['mallName'] else "기타",
                        "제조사": item['maker'] if item['maker'] else "미지정",
                        "브랜드": item['brand'] if item['brand'] else "미지정",
                        "카테고리": f"{item['category1']} > {item['category2']}"
                    })
                df_products = pd.DataFrame(records)
                
                # 수치 정제 (0원 데이터 제외 처리)
                df_valid_price = df_products[df_products["최저가 (₩)"] > 0]
                
                # 1. 가격 통계
                st.markdown("<div class='sub-title'>💰 상품 가격 분석</div>", unsafe_allow_html=True)
                
                kpi_cols = st.columns(3)
                with kpi_cols[0]:
                    st.markdown(f"<div class='kpi-card'>평균 가격<br><span class='kpi-val'>₩ {int(df_valid_price['최저가 (₩)'].mean()):,}</span></div>", unsafe_allow_html=True)
                with kpi_cols[1]:
                    st.markdown(f"<div class='kpi-card'>최저 가격<br><span class='kpi-val'>₩ {int(df_valid_price['최저가 (₩)'].min()):,}</span></div>", unsafe_allow_html=True)
                with kpi_cols[2]:
                    st.markdown(f"<div class='kpi-card'>최고 가격<br><span class='kpi-val'>₩ {int(df_valid_price['최저가 (₩)'].max()):,}</span></div>", unsafe_allow_html=True)
                
                # 2. 판매처별 상품 수 및 평균가 분석
                st.markdown("<div class='sub-title'>🏢 판매처별 상품 통계</div>", unsafe_allow_html=True)
                df_mall = df_valid_price.groupby("판매처 (몰)").agg(
                    상품수=("최저가 (₩)", "count"),
                    평균가격=("최저가 (₩)", "mean")
                ).reset_index().sort_values(by="상품수", ascending=False)
                
                fig_mall = px.bar(
                    df_mall.head(15), x="판매처 (몰)", y="상품수", color="평균가격",
                    labels={"상품수": "등록 상품 수", "평균가격": "평균 가격 (₩)"},
                    title="주요 판매처별 상품 등록 수 및 평균 판매가",
                    color_continuous_scale="Viridis"
                )
                st.plotly_chart(fig_mall, use_container_width=True)
                
                # 3. 상품 목록 표출
                st.markdown("<div class='sub-title'>📋 검색 상품 상세 목록</div>", unsafe_allow_html=True)
                st.dataframe(df_products, use_container_width=True)
            else:
                st.warning("⚠️ 검색 결과가 존재하지 않습니다.")
        else:
            handle_api_error(res.status_code, res.json())

elif menu == "📝 블로그 검색 분석":
    st.markdown("<div class='main-title'>📝 블로그 검색 데이터 분석</div>", unsafe_allow_html=True)
    
    if not client_id or not client_secret:
        st.warning("👉 대시보드를 활성화하기 위해 Streamlit Secrets 또는 프로젝트 루트의 .env 파일에 Client ID 및 Client Secret을 입력해 주세요.")
    elif len(keywords) == 0:
        st.info("💡 사이드바에 검색 키워드를 입력해 주세요.")
    else:
        selected_kw = st.selectbox("검색 키워드 선택", keywords)
        display_num = st.slider("조회할 블로그 개수", min_value=10, max_value=100, value=50, step=10)
        
        url = "https://openapi.naver.com/v1/search/blog.json"
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret
        }
        params = {
            "query": selected_kw,
            "display": display_num,
            "sort": "sim"
        }
        
        with st.spinner("블로그 포스트 데이터를 조회 중입니다..."):
            res = requests.get(url, params=params, headers=headers)
            
        if res.status_code == 200:
            data = res.json()
            items = data.get('items', [])
            
            if len(items) > 0:
                records = []
                for item in items:
                    records.append({
                        "제목": item['title'].replace("<b>", "").replace("</b>", ""),
                        "블로그명": item['bloggername'],
                        "작성일": item['postdate'],
                        "링크": item['link'],
                        "요약": item['description'].replace("<b>", "").replace("</b>", "")
                    })
                df_blog = pd.DataFrame(records)
                
                # 1. 작성 날짜별 추이 분석
                df_date_count = df_blog.groupby("작성일").size().reset_index(name="포스트수")
                df_date_count['작성일'] = pd.to_datetime(df_date_count['작성일'])
                df_date_count = df_date_count.sort_values(by="작성일")
                
                fig_date = px.bar(
                    df_date_count, x="작성일", y="포스트수",
                    title="일자별 블로그 글 발행 빈도",
                    labels={"작성일": "포스팅 일자", "포스트수": "발행 수"},
                    color_discrete_sequence=["#1EC800"]
                )
                st.plotly_chart(fig_date, use_container_width=True)
                
                # 2. 블로그 채널 점유율 Top 10
                st.markdown("<div class='sub-title'>👑 주요 블로그 채널 점유율</div>", unsafe_allow_html=True)
                df_blogger = df_blog["블로그명"].value_counts().reset_index()
                df_blogger.columns = ["블로그명", "발행수"]
                
                fig_blogger = px.pie(
                    df_blogger.head(10), values="발행수", names="블로그명",
                    title="검색 결과 내 지분율 상위 10개 블로그",
                    hole=0.4
                )
                st.plotly_chart(fig_blogger, use_container_width=True)
                
                # 3. 원본 리스트 출력
                st.markdown("<div class='sub-title'>📰 포스트 상세 보기</div>", unsafe_allow_html=True)
                for i, row in df_blog.iterrows():
                    with st.expander(f"📌 {row['제목']} (블로그: {row['블로그명']} / 작성일: {row['작성일']})"):
                        st.write(f"**요약**: {row['요약']}")
                        st.markdown(f"[포스트 바로가기]({row['링크']})")
            else:
                st.warning("⚠️ 검색 결과가 존재하지 않습니다.")
        else:
            handle_api_error(res.status_code, res.json())

elif menu == "☕ 카페글 검색 분석":
    st.markdown("<div class='main-title'>☕ 카페글 검색 데이터 분석</div>", unsafe_allow_html=True)
    
    if not client_id or not client_secret:
        st.warning("👉 대시보드를 활성화하기 위해 Streamlit Secrets 또는 프로젝트 루트의 .env 파일에 Client ID 및 Client Secret을 입력해 주세요.")
    elif len(keywords) == 0:
        st.info("💡 사이드바에 검색 키워드를 입력해 주세요.")
    else:
        selected_kw = st.selectbox("검색 키워드 선택", keywords)
        display_num = st.slider("조회할 카페글 수", min_value=10, max_value=100, value=50, step=10)
        
        url = "https://openapi.naver.com/v1/search/cafearticle.json"
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret
        }
        params = {
            "query": selected_kw,
            "display": display_num,
            "sort": "sim"
        }
        
        with st.spinner("카페글을 수집하고 있습니다..."):
            res = requests.get(url, params=params, headers=headers)
            
        if res.status_code == 200:
            data = res.json()
            items = data.get('items', [])
            
            if len(items) > 0:
                records = []
                for item in items:
                    records.append({
                        "제목": item['title'].replace("<b>", "").replace("</b>", ""),
                        "카페명": item['cafename'],
                        "카페주소": item['cafeurl'],
                        "글링크": item['link'],
                        "요약": item['description'].replace("<b>", "").replace("</b>", "")
                    })
                df_cafe = pd.DataFrame(records)
                
                # 1. 카페 브랜드 점유율
                st.markdown("<div class='sub-title'>☕ 주요 커뮤니티(카페)별 발행 지분</div>", unsafe_allow_html=True)
                df_cafe_counts = df_cafe["카페명"].value_counts().reset_index()
                df_cafe_counts.columns = ["카페명", "발행 건수"]
                
                fig_cafe = px.bar(
                    df_cafe_counts.head(10), x="발행 건수", y="카페명",
                    title="상위 10개 카페 채널별 발행 수 비교",
                    orientation="h",
                    color="발행 건수",
                    color_continuous_scale="Viridis"
                )
                fig_cafe.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_cafe, use_container_width=True)
                
                # 2. 리스트 출력
                st.markdown("<div class='sub-title'>💬 카페 포스팅 목록</div>", unsafe_allow_html=True)
                st.dataframe(df_cafe, use_container_width=True)
            else:
                st.warning("⚠️ 검색 결과가 존재하지 않습니다.")
        else:
            handle_api_error(res.status_code, res.json())

elif menu == "📰 뉴스 검색 분석":
    st.markdown("<div class='main-title'>📰 뉴스 검색 트렌드 분석</div>", unsafe_allow_html=True)
    
    if not client_id or not client_secret:
        st.warning("👉 대시보드를 활성화하기 위해 Streamlit Secrets 또는 프로젝트 루트의 .env 파일에 Client ID 및 Client Secret을 입력해 주세요.")
    elif len(keywords) == 0:
        st.info("💡 사이드바에 검색 키워드를 입력해 주세요.")
    else:
        selected_kw = st.selectbox("검색 키워드 선택", keywords)
        display_num = st.slider("조회할 뉴스 기사 수", min_value=10, max_value=100, value=50, step=10)
        sort_opt = st.selectbox("정렬 옵션", ["정확도순 (sim)", "날짜순 (date)"])
        sort_val = "sim" if "정확도" in sort_opt else "date"
        
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret
        }
        params = {
            "query": selected_kw,
            "display": display_num,
            "sort": sort_val
        }
        
        with st.spinner("뉴스 기사를 조회 중입니다..."):
            res = requests.get(url, params=params, headers=headers)
            
        if res.status_code == 200:
            data = res.json()
            items = data.get('items', [])
            
            if len(items) > 0:
                records = []
                for item in items:
                    # pubDate 파싱 (예: Mon, 26 Sep 2016 07:50:00 +0900)
                    pub_date_raw = item['pubDate']
                    try:
                        pub_date = datetime.datetime.strptime(pub_date_raw, "%a, %d %b %Y %H:%M:%S +0900")
                    except:
                        try:
                            pub_date = datetime.datetime.strptime(pub_date_raw, "%a, %d %b %Y %H:%M:%S GMT")
                        except:
                            pub_date = datetime.datetime.now()
                            
                    records.append({
                        "제목": item['title'].replace("<b>", "").replace("</b>", ""),
                        "원문링크": item['originallink'],
                        "네이버뉴스": item['link'],
                        "발행일자": pub_date.strftime("%Y-%m-%d"),
                        "발행시간": pub_date.strftime("%H:%M:%S"),
                        "요약": item['description'].replace("<b>", "").replace("</b>", "")
                    })
                df_news = pd.DataFrame(records)
                
                # 1. 일자별 발행 빈도
                df_news_date = df_news.groupby("발행일자").size().reset_index(name="기사수")
                df_news_date = df_news_date.sort_values(by="발행일자")
                
                fig_news = px.line(
                    df_news_date, x="발행일자", y="기사수",
                    title="일자별 관련 기사 보도 건수",
                    labels={"발행일자": "보도 일자", "기사수": "보도량"},
                    color_discrete_sequence=["#FF4B4B"]
                )
                fig_news.update_layout(hovermode="x unified")
                st.plotly_chart(fig_news, use_container_width=True)
                
                # 2. 기사 리스트
                st.markdown("<div class='sub-title'>📰 보도 뉴스 상세 내역</div>", unsafe_allow_html=True)
                st.dataframe(df_news, use_container_width=True)
            else:
                st.warning("⚠️ 검색 결과가 존재하지 않습니다.")
        else:
            handle_api_error(res.status_code, res.json())
