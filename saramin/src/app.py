"""
이 파일은 사람인 채용 트렌드 및 검색어 분석 Streamlit 대시보드의 메인 엔트리 포인트(app.py)입니다.

주요 기능:
- 사이드바 컨트롤러 (네이버/사람인 API Key 입력, 검색어 컴마 구분 입력, 검색 기간 달력 필터)
- 실시간 네이버 데이터랩 검색어 트렌드 API 연동 및 예외 처리 (API Key 미입력 시 고품질 시뮬레이션 데이터 제공)
- 탭/페이지 기반의 네비게이션 (대시보드 개요, 검색어 트렌드, 공고 등록 빈도, 공고 상세 분석, 기업 복지 분석, 산업군 분석)
- 현재 필터링 상태를 반영한 오프라인 정적 HTML 대시보드 리포트 생성 및 저장 기능
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import urllib.request
import json
import os
from dotenv import load_dotenv

# .env 환경 변수 로드
load_dotenv()
load_dotenv(dotenv_path="saramin/.env")

# st.secrets 우선 조회 후, 없으면 .env 환경 변수를 폴백으로 사용
default_client_id = st.secrets.get("NAVER_CLIENT_ID", os.getenv("NAVER_CLIENT_ID", ""))
default_client_secret = st.secrets.get("NAVER_CLIENT_SECRET", os.getenv("NAVER_CLIENT_SECRET", ""))
default_saramin_key = st.secrets.get("SARAMIN_API_KEY", os.getenv("SARAMIN_API_KEY", ""))

# 모듈 상대 경로 임포트
from data_generator import (
    generate_trend_data, generate_job_frequency, 
    generate_job_details, generate_industry_data, 
    load_and_enrich_scraped_data
)
from pages_content import (
    render_overview, render_trends_analysis, render_freq_analysis, 
    render_details_analysis, render_welfare_analysis, render_industry_analysis
)
from export_report import export_to_html

# 페이지 기본 설정
st.set_page_config(
    page_title="사람인 채용 트렌드 분석 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
if "demo_mode" not in st.session_state:
    st.session_state["demo_mode"] = True
if "api_status" not in st.session_state:
    st.session_state["api_status"] = "미연동 (데모 모드)"

# ----------------- 사이드바 설정 -----------------
st.sidebar.title("🔍 분석 필터 설정")

# 1. API Key 입력 섹션
st.sidebar.markdown("### 🔑 API Key 인증")
naver_client_id = st.sidebar.text_input("Naver Client ID", value=default_client_id, type="password", help="네이버 개발자 센터에서 발급받은 Client ID를 입력하세요.")
naver_client_secret = st.sidebar.text_input("Naver Client Secret", value=default_client_secret, type="password", help="네이버 개발자 센터에서 발급받은 Client Secret을 입력하세요.")
saramin_api_key = st.sidebar.text_input("Saramin API Key (선택)", value=default_saramin_key, type="password", help="사람인 API 키가 있는 경우 입력하세요. 없을 경우 고품질 시뮬레이션 데이터가 활성화됩니다.")

# API Key 상태 판별 및 알림
if naver_client_id and naver_client_secret:
    st.session_state["demo_mode"] = False
    st.session_state["api_status"] = "연동 완료"
    st.sidebar.success("✅ 네이버 API 연동 모드 활성화")
else:
    st.session_state["demo_mode"] = True
    st.session_state["api_status"] = "미연동 (데모 모드)"
    st.sidebar.info("💡 API Key 미입력으로 '시뮬레이션 데모 모드'로 작동 중입니다.")

st.sidebar.write("---")

# 2. 검색어 입력 섹션 (컴마로 구분)
st.sidebar.markdown("### 🏷️ 검색 키워드 설정")
keywords_input = st.sidebar.text_input(
    "검색어 입력 (쉼표 , 로 구분)", 
    value="Python, Java, React, AWS", 
    help="분석하고자 하는 채용 기술이나 검색어를 입력하세요."
)
# 키워드 가공 및 공백 제거
keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

# 3. 검색 기간 설정
st.sidebar.markdown("### 📅 검색 기간 설정")
default_start = datetime.today() - timedelta(days=90)
default_end = datetime.today()

date_range = st.sidebar.date_input(
    "조회 기간", 
    value=(default_start, default_end),
    help="시계열 트렌드 및 공고 등록 빈도를 분석할 기간을 설정하세요."
)

# 날짜 검증
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = default_start
    end_date = default_end

# 4. 페이지 이동 네비게이션
st.sidebar.markdown("### 🧭 대시보드 메뉴")
menu = st.sidebar.radio(
    "이동할 페이지 선택",
    [
        "홈 / 개요", 
        "검색어 트렌드 분석", 
        "공고 등록 빈도 분석", 
        "공고 상세 내용 분석", 
        "회사별 복지 혜택 분석", 
        "산업군별 특성 분석"
    ]
)

st.sidebar.write("---")

# ----------------- 실시간 네이버 API 데이터랩 호출 로직 -----------------
@st.cache_data(show_spinner="네이버 트렌드 데이터를 로딩 중입니다...")
def fetch_naver_trend(keywords, start, end, client_id=None, client_secret=None):
    """
    네이버 데이터랩 API를 호출하여 검색 트렌드 데이터를 가져옵니다.
    실패하거나 인증정보가 없는 경우 시뮬레이션 데이터를 반환합니다.
    """
    if not client_id or not client_secret:
        # 키가 없으면 시뮬레이션 데이터 반환
        return generate_trend_data(keywords, start, end)
        
    url = "https://openapi.naver.com/v1/datalab/search"
    
    # 네이버 데이터랩 API 형식에 맞게 바디 구성
    keyword_groups = []
    for kw in keywords:
        keyword_groups.append({
            "groupName": kw,
            "keywords": [kw]
        })
        
    body = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "timeUnit": "date",
        "keywordGroups": keyword_groups
    }
    
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"))
    req.add_header("X-Naver-Client-Id", client_id)
    req.add_header("X-Naver-Client-Secret", client_secret)
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req) as response:
            res_code = response.getcode()
            if res_code == 200:
                res_data = json.loads(response.read().decode("utf-8"))
                
                # 결과 가공하여 DataFrame 생성
                results = res_data["results"]
                date_range_len = len(results[0]["data"])
                
                df_data = {"period": [d["period"] for d in results[0]["data"]]}
                for group in results:
                    g_name = group["title"]
                    # 데이터 매핑 (일자별 ratio 수집)
                    ratio_dict = {d["period"]: d["ratio"] for d in group["data"]}
                    df_data[g_name] = [ratio_dict.get(p, 0.0) for p in df_data["period"]]
                    
                return pd.DataFrame(df_data)
            else:
                st.sidebar.warning(f"네이버 API 호출 에러: {res_code}. 모의 데이터로 대체합니다.")
                return generate_trend_data(keywords, start, end)
    except Exception as e:
        st.sidebar.warning(f"네이버 API 호출 중 예외 발생: {e}. 모의 데이터로 대체합니다.")
        return generate_trend_data(keywords, start, end)

# ----------------- 데이터 로드 단계 -----------------
# 1. 트렌드 데이터
df_trends = fetch_naver_trend(keywords, start_date, end_date, naver_client_id, naver_client_secret)

# 2. 공고 등록 빈도 데이터
@st.cache_data(show_spinner="채용 공고 빈도 데이터를 수집 중입니다...")
def get_job_freq(keywords, start, end):
    return generate_job_frequency(keywords, start, end)
df_freq = get_job_freq(keywords, start_date, end_date)

# 3. 공고 상세 데이터 (실제 수집 데이터 우선 로드)
@st.cache_data(show_spinner="상세 공고 내용을 매칭하는 중입니다...")
def get_job_details(keywords):
    return load_and_enrich_scraped_data(keywords)
df_jobs = get_job_details(keywords)

# 4. 산업군별 분석 데이터
@st.cache_data(show_spinner="산업군 지표를 분석 중입니다...")
def get_industry_data_cached():
    return generate_industry_data()
df_ind = get_industry_data_cached()


# ----------------- 정적 HTML 내보내기 자동화 -----------------
# 대시보드가 구동/갱신될 때 분석 결과를 report 폴더에 항상 최신으로 정적 백업합니다.
try:
    export_to_html(keywords, df_trends, df_freq, df_jobs, df_ind)
except Exception as e:
    st.sidebar.error(f"정적 보고서 자동 저장 중 오류: {e}")

# 정적 보고서 저장 안내 및 다운로드 버튼 제공
st.sidebar.markdown("### 💾 오프라인 보고서 저장")
with open("saramin/report/dashboard_report.html", "r", encoding="utf-8") as f:
    html_bytes = f.read().encode("utf-8")

st.sidebar.download_button(
    label="HTML 정적 보고서 다운로드",
    data=html_bytes,
    file_name="saramin_recruitment_report.html",
    mime="text/html",
    help="대시보드와 동일한 Plotly 시각화가 담긴 오프라인 HTML 보고서를 다운로드합니다."
)


# ----------------- 메인 콘텐츠 영역 -----------------
st.title("📊 사람인 채용 트렌드 & 검색어 빅데이터 대시보드")
st.markdown(f"**현재 모드**: `{st.session_state['api_status']}` | **기간**: `{start_date}` ~ `{end_date}`")
st.write("---")

# 메뉴 분기 처리
if menu == "홈 / 개요":
    render_overview(keywords, start_date, end_date, df_trends, df_freq, df_jobs, df_ind)
elif menu == "검색어 트렌드 분석":
    render_trends_analysis(keywords, start_date, end_date, df_trends)
elif menu == "공고 등록 빈도 분석":
    render_freq_analysis(keywords, start_date, end_date, df_freq)
elif menu == "공고 상세 내용 분석":
    render_details_analysis(keywords, df_jobs)
elif menu == "회사별 복지 혜택 분석":
    render_welfare_analysis(df_jobs)
elif menu == "산업군별 특성 분석":
    render_industry_analysis(df_ind)
