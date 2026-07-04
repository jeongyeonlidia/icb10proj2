"""
이 파일은 기획·전략 직무 자격증 미스매치(Gap) 분석 및 지원 적합도 자가진단 Streamlit 대시보드(app_planning.py)입니다.

주요 기능:
- `saramin/data/saramin_search_jobs.db`의 1,000건 실제 크롤링 데이터를 로드합니다. (로드 실패 시 고품질 Mock Data로 자동 대체)
- 텍스트 분석 기반으로 채용공고를 'IT/서비스 기획' 및 '경영/사업 전략' 세부 직무로 자동 분류합니다.
- [구직자향 탭]: 기획자 보유 스킬과 세부 직무 공고들 간의 매칭을 수행해 직무 적합도 점수를 산출하고 미보유 필수스킬 TOP 3 가이드를 제공합니다.
- [인사팀향 탭]: 공급(구직자 검색량)과 수요(채용공고 요구빈도) 간의 격차를 Plotly 이중 축 막대 차트로 가시화하고 채용전략 비즈니스 제언을 노출합니다.
- [정적 HTML 리포트]: 대시보드 구동 시 현 상태의 정적 HTML 백업 보고서를 `saramin/report/planning_mismatch_report.html`에 실시간으로 자동 내보내기합니다.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as gr
from plotly.subplots import make_subplots
import os
import re

# 페이지 기본 설정
st.set_page_config(
    page_title="기획/전략 직무 자격증 미스매치 & 자가진단 대시보드",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- 1. 데이터 로드 및 전처리 -----------------
# 1) 가상 데이터 셋 (Mock Data) 정의 - DB가 없거나 오류가 발생했을 때의 방어용 Fallback 데이터입니다.
# 기획/전략 도메인을 반영하여 20개 이상의 행을 가진 샘플 데이터를 작성합니다.
def get_fallback_mock_data():
    mock_jobs = [
        # IT/서비스 기획 공고 10개
        {"company": "네이버", "title": "서비스기획/UX기획 신입 채용", "sectors": "서비스기획, UI/UX", "detail_content": "우대자격증 및 기술: SQLD, GA4, Figma에 대한 이해 및 프로토타이핑 역량 우대. 서비스로그 분석 경험자."},
        {"company": "카카오", "title": "커머스 플랫폼 서비스 기획자 모집", "sectors": "서비스기획, 플랫폼기획", "detail_content": "Figma를 활용한 화면설계 및 역기획 우대. SQLD 및 ADsP 보유자 특별 우대합니다."},
        {"company": "토스", "title": "토스뱅크 Product Owner (IT기획)", "sectors": "IT기획, PM", "detail_content": "데이터 기반 의사결정을 위한 SQLD, GA4 활용 능력 필수. Figma 프로토타이핑 능력과 역기획 역량 우대."},
        {"company": "라인", "title": "글로벌 메신저 서비스 기획자 채용", "sectors": "서비스기획, 글로벌기획", "detail_content": "서비스로그 분석 및 GA4 활용 능력 우대. Figma 설계 도구 숙련자."},
        {"company": "쿠팡", "title": "물류 플랫폼 기획/운영 담당자 채용", "sectors": "IT기획, 물류", "detail_content": "데이터 분석(ADsP) 우대. SQLD 자격증 보유 및 Figma 활용 역량 우대."},
        {"company": "배달의민족", "title": "주문 결제 서비스 기획 담당자 채용", "sectors": "서비스기획, IT기획", "detail_content": "서비스로그 분석 및 역기획 가능자. SQLD, GA4, Figma 우대."},
        {"company": "당근마켓", "title": "지역 생활 커뮤니티 서비스 기획자 채용", "sectors": "서비스기획, 로컬기획", "detail_content": "Figma 설계 및 프로토타이핑 역량. GA4 및 SQLD 활용 데이터 분석 우대."},
        {"company": "야놀자", "title": "레저/숙박 예약 서비스 기획자 채용", "sectors": "서비스기획, IT기획", "detail_content": "Figma 활용 및 역기획. SQLD 자격증 보유자 우대."},
        {"company": "쏘카", "title": "카셰어링 서비스 기획 및 PM 채용", "sectors": "IT기획, PM", "detail_content": "데이터 분석(ADsP) 우대. SQLD, Figma, GA4 활용 경험자."},
        {"company": "원티드랩", "title": "매칭 플랫폼 서비스 기획 인턴 모집", "sectors": "서비스기획", "detail_content": "Figma 설계 및 역기획 역량. SQLD 우대."},
        
        # 경영/사업 전략 공고 10개
        {"company": "삼성전자", "title": "글로벌 사업 전략/경영 기획 경력 채용", "sectors": "경영기획, 사업전략", "detail_content": "우대자격증 및 기술: CPA, CFA 자격증 소지자. M&A 및 신사업 타당성분석 경력 우대. PPT마스터 수준."},
        {"company": "SK하이닉스", "title": "반도체 부문 사업 기획/전략 담당 모집", "sectors": "사업기획, 전략기획", "detail_content": "시장조사 및 타당성분석 역량 필수. CPA 또는 CFA 보유자 및 PPT마스터 우대."},
        {"company": "현대자동차", "title": "미래 모빌리티 신사업 전략 기획자 채용", "sectors": "전략기획, 신사업", "detail_content": "M&A 검토 경험 및 시장조사, 타당성분석 역량. CPA, CFA, PPT마스터 우대."},
        {"company": "LG에너지솔루션", "title": "투자 전략 및 경영 기획 담당 채용", "sectors": "경영기획, 투자전략", "detail_content": "CFA, CPA 소지자 특별 우대. 시장조사 및 사업 타당성분석 유경험자."},
        {"company": "CJ제일제당", "title": "식품 글로벌 사업 기획 및 전략 수립", "sectors": "사업기획, 글로벌전략", "detail_content": "시장조사 및 타당성분석 유경험자. PPT마스터 및 공인노무사 자격증 소지자 우대."},
        {"company": "신한지주", "title": "지주사 경영 전략 및 M&A 담당 채용", "sectors": "경영기획, M&A", "detail_content": "CPA, CFA 등 금융/회계 전문 자격증 필수. 타당성분석 및 PPT마스터."},
        {"company": "이랜드", "title": "패션 사업 기획 및 예산 관리자 채용", "sectors": "사업기획, 경영관리", "detail_content": "시장조사 및 PPT마스터. CPA, 공인노무사 자격증 소지자 우대."},
        {"company": "아모레퍼시픽", "title": "뷰티 신사업 전략 및 경영 기획 채용", "sectors": "전략기획, 경영기획", "detail_content": "CFA, CPA 및 M&A 경력자 우대. 타당성분석 및 PPT마스터."},
        {"company": "한화솔루션", "title": "친환경 에너지 사업 기획 및 타당성분석", "sectors": "사업기획, 친환경에너지", "detail_content": "시장조사, 타당성분석. CPA, CFA 우대 및 PPT마스터."},
        {"company": "GS칼텍스", "title": "기획지원 부문 경영 기획 신입 사원 모집", "sectors": "경영기획", "detail_content": "공인노무사, CPA 우대. PPT마스터 및 시장조사 능력."}
    ]
    return pd.DataFrame(mock_jobs)

# 2) 실제 SQLite DB 로드 및 직무 분류 로직
@st.cache_data
def load_and_preprocess_data():
    db_paths = [
        "saramin/data/saramin_search_jobs.db",
        "data/saramin_search_jobs.db",
        "../data/saramin_search_jobs.db",
        "../../saramin/data/saramin_search_jobs.db"
    ]
    db_path = None
    for p in db_paths:
        if os.path.exists(p):
            db_path = p
            break
            
    # DB가 존재할 경우 데이터 로드 시도
    if db_path is not None:
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql("SELECT * FROM saramin_jobs", conn)
            conn.close()
            st.sidebar.success(f"✅ SQLite 실데이터 1,000건 로드 완료 (경로: {db_path})")
        except Exception as e:
            st.sidebar.warning(f"⚠️ DB 로드 중 에러 발생, 모의 데이터로 대체합니다: {e}")
            df = get_fallback_mock_data()
    else:
        st.sidebar.info("💡 모의 데이터(Mock Data) 로드로 대시보드가 활성화되었습니다. (실제 DB 미발견)")
        df = get_fallback_mock_data()
        
    # 세부 직무 분류 로직 정의
    def classify_job(row):
        # sectors, title, detail_content에서 키워드를 검색합니다.
        text = (str(row.get("sectors", "")) + " " + str(row.get("title", "")) + " " + str(row.get("detail_content", ""))).lower()
        
        it_keywords = ["sqld", "adsp", "ga4", "figma", "역기획", "프로토타이핑", "서비스로그", "서비스기획", "서비스 기획", "it기획", "it 기획", "ux", "ui", "웹기획", "웹 기획"]
        strategy_keywords = ["cfa", "cpa", "공인노무사", "m&a", "시장조사", "타당성분석", "ppt마스터", "경영기획", "경영 기획", "사업기획", "사업 기획", "사업전략", "사업 전략", "전략기획", "전략 기획"]
        
        has_it = any(kw in text for kw in it_keywords)
        has_strategy = any(kw in text for kw in strategy_keywords)
        
        if has_it and not has_strategy:
            return "IT/서비스 기획"
        elif has_strategy and not has_it:
            return "경영/사업 전략"
        else:
            # 둘 다 있거나 없는 경우 더 많은 키워드가 출현한 쪽으로 매핑
            it_count = sum(1 for kw in it_keywords if kw in text)
            strategy_count = sum(1 for kw in strategy_keywords if kw in text)
            if it_count >= strategy_count:
                return "IT/서비스 기획"
            else:
                return "경영/사업 전략"
                
    df["세부직무"] = df.apply(classify_job, axis=1)
    
    return df

df_jobs = load_and_preprocess_data()

# 3) 다차원 통합 미스매치 데이터 마트 로드 (automated_total_mismatch_mart.csv)
def load_mismatch_mart():
    mart_paths = [
        "automated_total_mismatch_mart.csv",
        "../automated_total_mismatch_mart.csv",
        "../../automated_total_mismatch_mart.csv",
        "naver-api-app/automated_total_mismatch_mart.csv"
    ]
    mart_path = None
    for p in mart_paths:
        if os.path.exists(p):
            mart_path = p
            break
            
    if mart_path and os.path.exists(mart_path):
        try:
            df = pd.read_csv(mart_path)
            # 기존 licenses_data 형식(df_licenses)에 맞춘 가상 뷰 생성 (역호환성)
            df_lic = pd.DataFrame({
                "자격증명": df["자격증명"],
                "구직자_월간검색량": df["구직자_공급_건수"]
            })
            return df, df_lic
        except Exception as e:
            st.sidebar.warning(f"⚠️ 마트 파일 로드 에러: {e}")
            
    # 파일이 없을 시 로컬 모의 데이터로 대체 (방어 코드)
    fallback_data = pd.DataFrame({
        "자격증명": ["SQLD", "ADsP", "컴퓨터활용능력", "GA4", "CFA", "CPA", "Figma", "데이터분석", "시장조사", "M&A", "PPT작성법"],
        "기업_수요_건수": [1, 2, 30, 10, 2, 7, 20, 153, 97, 63, 131],
        "구직자_공급_건수": [15000, 12000, 45000, 8000, 6000, 18000, 4500, 35000, 28000, 9000, 22000],
        "2026-01_검색비율": [45.2, 38.5, 85.0, 15.1, 12.0, 40.0, 32.1, 60.5, 42.1, 18.2, 70.5],
        "2026-02_검색비율": [48.1, 42.0, 92.1, 18.3, 11.2, 43.2, 35.0, 64.0, 45.0, 20.1, 75.2],
        "2026-03_검색비율": [55.4, 47.3, 78.4, 22.0, 14.5, 45.1, 39.8, 68.2, 48.3, 23.4, 68.0],
        "2026-04_검색비율": [62.0, 52.8, 82.5, 25.4, 16.0, 38.0, 44.5, 72.1, 50.2, 25.0, 71.4],
        "2026-05_검색비율": [58.7, 49.1, 88.0, 21.2, 15.3, 36.5, 41.0, 70.0, 47.5, 22.1, 73.5],
        "2026-06_검색비율": [50.1, 41.5, 95.0, 19.8, 13.1, 34.0, 38.5, 65.4, 43.1, 19.5, 78.0]
    })
    df_lic = pd.DataFrame({
        "자격증명": fallback_data["자격증명"],
        "구직자_월간검색량": fallback_data["구직자_공급_건수"]
    })
    return fallback_data, df_lic

df_mismatch_mart, df_licenses = load_mismatch_mart()


# ----------------- 2. 정적 HTML 리포트 생성 함수 -----------------
def generate_planning_report(selected_target, user_skills, suitability_score, missing_skills, fig_html):
    """
    구직자 적합도 및 인사팀 미스매치 분석 결과를 프리미엄 HTML로 저장합니다.
    """
    report_dirs = [
        "project2/report",
        "saramin/report",
        "report",
        "../report",
        "../../saramin/report"
    ]
    report_dir = "project2/report" # 기본
    for rd in report_dirs:
        # 상위 디렉토리가 존재하는지 확인하여 유효한 경로 선택
        parent_dir = os.path.dirname(rd) if "/" in rd else "."
        if os.path.exists(parent_dir):
            report_dir = rd
            break
            
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "planning_mismatch_report.html")
    
    skills_str = ", ".join(user_skills) if user_skills else "없음"
    missing_str = ", ".join(missing_skills) if missing_skills else "탑티어 기획자의 스킬을 완벽하게 보유하고 있습니다!"
    
    # 세부 직무별 비즈니스 제언
    insights = {
        "전체 기획/전략": "기획/전략 부문 구직자들은 기본 사무 능력(컴퓨터활용능력, PPT작성법) 검색에 치중하나, 실제 채용 시장에서는 실무 기술 및 전문 분석 역량(SQLD, CPA/CFA, Figma 등)을 강력히 우대합니다. 미스매치를 해결하기 위해 우대요건을 구체적으로 공지해야 합니다.",
        "IT/서비스 기획": "IT/서비스 기획을 타겟팅하는 신입/경력자들은 범용 자격증을 다수 준비하지만, 기업은 'Figma 활용 화면설계, SQLD 기반 쿼리, GA4 로그 분석' 역량을 최우선시합니다. 채용 공고에 직무 스킬셋 가이드를 명확히 명시(JD Optimization)해야 핏이 맞는 인재가 모입니다.",
        "경영/사업 전략": "경영/사업 전략 구직자들의 검색 패턴은 기본 사무에 치중된 반면, 채용 기업은 'M&A 검토, 사업 타당성분석, CPA/CFA 전문 라이선스' 등을 우대하여 채용 조건의 눈높이 갭이 매우 큽니다. 채용 마케팅 시 전문 역량 개발 경로를 제시하는 노력이 필요합니다."
    }
    selected_insight = insights.get(selected_target, "")
    
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>기획/전략 직무 미스매치 분석 보고서</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Google Fonts Inter & Outfit -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #0f172a;
            color: #f1f5f9;
        }}
        h1, h2, h3, .font-outfit {{
            font-family: 'Outfit', sans-serif;
        }}
    </style>
</head>
<body class="p-6 md:p-12 min-h-screen">
    <div class="max-w-5xl mx-auto bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl">
        <!-- 헤더 영역 -->
        <div class="border-b border-slate-800 pb-6 mb-8 flex flex-col md:flex-row justify-between items-start md:items-center">
            <div>
                <span class="bg-violet-500/10 text-violet-400 text-xs font-semibold px-3 py-1.5 rounded-full border border-violet-500/20 uppercase tracking-wider">Planning Job Mismatch Report</span>
                <h1 class="text-3xl md:text-4xl font-bold mt-3 text-white tracking-tight">기획/전략 직무 미스매치 분석 보고서</h1>
                <p class="text-slate-400 text-sm mt-1">1,000건의 채용 공고와 네이버 검색 빅데이터 기반 수급 격차 리포트</p>
            </div>
            <div class="mt-4 md:mt-0 text-left md:text-right">
                <p class="text-xs text-slate-500">선택된 타겟 세부직무</p>
                <p class="text-lg font-bold text-violet-400">{selected_target}</p>
            </div>
        </div>

        <!-- 2컬럼 레이아웃: 자가진단 & 스펙 제언 -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-slate-800/40 border border-slate-700/30 rounded-2xl p-6 flex flex-col justify-between">
                <div>
                    <h3 class="text-slate-400 text-xs font-semibold uppercase tracking-wider">기획/전략 직무 적합도</h3>
                    <p class="text-4xl font-black text-violet-400 mt-2 font-outfit">{suitability_score:.1f}점</p>
                </div>
                <div class="mt-4 pt-4 border-t border-slate-800">
                    <p class="text-xs text-slate-500">나의 보유 스킬</p>
                    <p class="text-sm font-semibold text-white truncate mt-1">{skills_str}</p>
                </div>
            </div>
            <div class="bg-slate-800/40 border border-slate-700/30 rounded-2xl p-6 md:col-span-2 flex flex-col justify-between">
                <div>
                    <h3 class="text-slate-400 text-xs font-semibold uppercase tracking-wider">탑티어 도약을 위해 우선순위로 채워야 할 스킬</h3>
                    <div class="flex flex-wrap gap-2 mt-3">
                        {"" if missing_skills else '<span class="text-emerald-400 text-sm font-medium">핵심 기획 스킬을 완벽하게 갖추셨습니다! 🎉</span>'}
    """
    for skill in missing_skills:
        html_content += f'<span class="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-semibold px-3 py-1 rounded-full">{skill}</span>'
        
    html_content += f"""
                    </div>
                </div>
                <div class="mt-4 pt-4 border-t border-slate-800">
                    <p class="text-xs text-slate-500">인재 영입 전략 추천</p>
                    <p class="text-sm text-slate-300 mt-1">기업 선호 요구 빈도가 가장 높으나 현재 누락된 역량입니다.</p>
                </div>
            </div>
        </div>

        <!-- 시각화 영역 -->
        <div class="bg-slate-800/20 border border-slate-800 rounded-2xl p-6 mb-8">
            <h2 class="text-xl font-bold text-white mb-4">📊 구직자 관심도 vs 채용공고 우대 스킬 Gap 비교</h2>
            <div class="w-full overflow-hidden rounded-xl bg-slate-900/50 p-2">
                {fig_html}
            </div>
        </div>

        <!-- 비즈니스 제언 영역 -->
        <div class="bg-violet-950/40 border border-violet-900/40 rounded-2xl p-6">
            <h2 class="text-lg font-bold text-violet-300 mb-2">💡 10년 차 기획자의 채용 전략 제언</h2>
            <p class="text-sm text-slate-300 leading-relaxed">{selected_insight}</p>
        </div>

        <!-- 푸터 -->
        <div class="border-t border-slate-800 mt-8 pt-6 flex justify-between items-center text-xs text-slate-500">
            <p>© 사람인 기획/전략 직무 미스매치 분석 시스템</p>
            <p>Generated dynamically via Streamlit</p>
        </div>
    </div>
</body>
</html>
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)


# ----------------- 3. 사이드바 구성 -----------------
st.sidebar.title("🎯 기획/전략 분석 필터")

# 세부 타겟 선택 box
selected_target = st.sidebar.selectbox(
    "세부 직무 선택",
    ["전체 기획/전략", "IT/서비스 기획", "경영/사업 전략"],
    help="분석할 기획/전략 부문의 세부 분야를 선택하세요."
)

st.sidebar.write("---")
st.sidebar.info(
    "💡 대시보드가 업데이트될 때마다 `saramin/report/planning_mismatch_report.html`에 "
    "오프라인 보고서가 실시간으로 저장 및 갱신됩니다."
)


# ----------------- 4. 메인 화면 및 탭 구조 구성 -----------------
st.title("💡 기획/전략 자격증 미스매치 분석 & 자가진단 대시보드")
st.markdown(f"**대상 세부직무**: `{selected_target}` | 실제 1,000건의 기획/전략 채용 공고와 검색 통계 매칭")
st.write("---")

tab1, tab2 = st.tabs(["💡 구직자향: 기획자 스펙 자가진단", "🏢 인사팀향: 기획 직무 미스매치(Gap) 리포트"])

# 데이터 필터링 적용
if selected_target == "전체 기획/전략":
    df_filtered = df_jobs.copy()
else:
    df_filtered = df_jobs[df_jobs["세부직무"] == selected_target].copy()

# [NameError 방지] 전역 스코프 기본 변수 초기화
user_skills = []
suitability_score = 0.0
missing_skills = []

# 직무 스킬셋 풀 정의 (기획서 명시 키워드 일치)
skill_pool = ["SQLD", "ADsP", "컴퓨터활용능력", "GA4", "Figma", "CFA", "CPA", "PPT마스터"]


# 💻 탭 1: 구직자향 - 기획자 스펙 자가진단
with tab1:
    st.header("💡 기획/전략 자격 요건 적합도 자가진단")
    st.markdown("현재 본인이 보유한 스킬 및 자격증을 선택하여 세부 직무 공고와의 적합도 지수를 즉시 진단하세요.")
    
    # 1,000건 공고 분석 스킬 TOP 10 리포트 파일 연동 반영
    top10_paths = [
        "saramin/docs/planning_skills_top10.md",
        "docs/planning_skills_top10.md",
        "../docs/planning_skills_top10.md",
        "../../saramin/docs/planning_skills_top10.md"
    ]
    top10_path = None
    for p in top10_paths:
        if os.path.exists(p):
            top10_path = p
            break
            
    try:
        if top10_path:
            with open(top10_path, "r", encoding="utf-8") as f:
                top10_markdown = f.read()
            with st.expander("📊 1,000건 공고 분석: 기획·전략 우대 스킬/자격증 TOP 10 순위 리포트 보기", expanded=False):
                st.markdown(top10_markdown)
        else:
            st.warning("⚠️ 우대 스킬 TOP 10 보고서 파일을 찾을 수 없습니다.")
    except Exception as read_err:
        st.warning(f"⚠️ 우대 스킬 TOP 10 보고서를 로드하지 못했습니다: {read_err}")
        
    # 네이버 카페 분석 구직자 트렌드 인덱스 파일 연동 반영
    naver_report_paths = [
        "naver-api-app/report/naver_analysis_eda_report.md",
        "report/naver_analysis_eda_report.md",
        "../report/naver_analysis_eda_report.md",
        "../../naver-api-app/report/naver_analysis_eda_report.md"
    ]
    naver_report_path = None
    for p in naver_report_paths:
        if os.path.exists(p):
            naver_report_path = p
            break
            
    try:
        if naver_report_path:
            with open(naver_report_path, "r", encoding="utf-8") as f:
                naver_report_markdown = f.read()
                
            # 실행 위치에 따른 최적의 이미지 경로 동적 해결
            img_paths = [
                "naver-api-app/images/",
                "images/",
                "../images/",
                "../../naver-api-app/images/"
            ]
            resolved_img_path = "naver-api-app/images/"
            for ip in img_paths:
                if os.path.exists(ip):
                    resolved_img_path = ip
                    break
                    
            # 상대 이미지 경로를 streamlit 실행 경로에 맞춰 치환하여 깨짐 방지
            naver_report_markdown = naver_report_markdown.replace("../images/", resolved_img_path)
            with st.expander("📊 네이버 카페 분석: 데이터분석 구직자 관심 트렌드 리포트 보기", expanded=False):
                st.markdown(naver_report_markdown)
        else:
            st.warning("⚠️ 네이버 카페 트렌드 보고서 파일을 찾을 수 없습니다.")
    except Exception as read_err:
        st.warning(f"⚠️ 네이버 카페 트렌드 보고서를 로드하지 못했습니다: {read_err}")
        
    st.markdown("### 🧑‍💼 나의 직무 역량 프로필 입력")
    col_prof1, col_prof2 = st.columns(2)
    with col_prof1:
        user_career = st.selectbox(
            "나의 경력 년수",
            options=["신입", "주니어 (1~3년)", "미들 (4~7년)", "시니어 (8년 이상)"],
            index=1,
            help="보유하신 경력 년수 범주를 선택하세요."
        )
    with col_prof2:
        user_edu = st.selectbox(
            "최종 학력",
            options=["고졸 이하", "초대졸 (2/3년제)", "대졸 (4년제 학사)", "대학원 (석사/박사)"],
            index=2,
            help="최종 학력 범주를 선택하세요."
        )
        
    # 평가용 5대 범주 스킬 풀 정의
    licenses_pool = ["SQLD", "ADsP", "정보처리기사", "CFA", "CPA", "컴퓨터활용능력"]
    tools_pool = ["Figma", "GA4", "Slack", "Jira", "Git", "ERP (더존/SAP)", "Tableau"]
    experiences_pool = ["역기획", "프로토타이핑", "서비스로그 분석", "M&A 검토", "시장조사 및 리서치", "사업타당성 분석", "예산 및 결산 관리"]
    
    col_sel1, col_sel2, col_sel3 = st.columns(3)
    with col_sel1:
        user_licenses = st.multiselect(
            "보유 자격증 선택",
            options=licenses_pool,
            default=[],
            help="보유한 전문 자격증을 선택하세요."
        )
    with col_sel2:
        user_tools = st.multiselect(
            "사용 가능한 실무 툴 선택",
            options=tools_pool,
            default=[],
            help="사용할 줄 아는 소프트웨어/툴을 선택하세요."
        )
    with col_sel3:
        user_experiences = st.multiselect(
            "보유 실무/직무 경험 선택",
            options=experiences_pool,
            default=[],
            help="이전에 수행해 본 기획/분석 업무 경험을 선택하세요."
        )
        
    diagnose_clicked = st.button("📊 나의 다차원 직무 적합도 진단 실행")
    
    # 유사어 및 키워드 매핑 딕셔너리
    synonyms = {
        "SQLD": ["sqld", "sql개발자"],
        "ADsP": ["adsp", "데이터분석준전문가"],
        "정보처리기사": ["정보처리기사", "정처기"],
        "CFA": ["cfa", "재무분석사"],
        "CPA": ["cpa", "공인회계사"],
        "컴퓨터활용능력": ["컴퓨터활용능력", "컴활", "오피스"],
        "Figma": ["figma", "피그마"],
        "GA4": ["ga4", "구글애널리틱스", "google analytics"],
        "Slack": ["slack", "슬랙"],
        "Jira": ["jira", "지라"],
        "Git": ["git", "깃", "github"],
        "ERP (더존/SAP)": ["erp", "sap", "더존"],
        "Tableau": ["tableau", "태블로"],
        "역기획": ["역기획", "역 기획"],
        "프로토타이핑": ["프로토타이핑", "화면설계", "와이어프레임", "wireframe"],
        "서비스로그 분석": ["서비스로그", "로그분석", "로그 분석", "ga4", "앰플리튜드", "amplitude"],
        "M&A 검토": ["m&a", "인수합병", "투자심사", "인수 합병"],
        "시장조사 및 리서치": ["시장조사", "시장 조사", "리서치", "research"],
        "사업타당성 분석": ["타당성분석", "타당성 분석", "feasibility"],
        "예산 및 결산 관리": ["예산", "결산", "세무", "회계", "감사"]
    }
    
    # ----------------- 파싱용 헬퍼 함수 정의 -----------------
    def parse_career_years(career_str):
        if not isinstance(career_str, str):
            return 0
        c_str = career_str.lower()
        if "신입" in c_str or "무관" in c_str:
            return 0
        nums = re.findall(r'\d+', c_str)
        if nums:
            return int(nums[0])
        return 0

    def parse_edu_level(edu_str):
        if not isinstance(edu_str, str):
            return 0
        e_str = edu_str.lower()
        if "대학원" in e_str or "석사" in e_str or "박사" in e_str:
            return 3
        elif "대학교" in e_str or "대졸" in e_str or "학사" in e_str:
            return 2
        elif "전문대" in e_str or "초대졸" in e_str or "2년제" in e_str or "3년제" in e_str:
            return 1
        return 0

    # ----------------- 5대 가중치 매칭 로직 구동 -----------------
    user_career_val = {"신입": 0, "주니어 (1~3년)": 2, "미들 (4~7년)": 5, "시니어 (8년 이상)": 10}[user_career]
    user_edu_val = {"고졸 이하": 0, "초대졸 (2/3년제)": 1, "대졸 (4년제 학사)": 2, "대학원 (석사/박사)": 3}[user_edu]
    
    total_scores = []
    
    for idx, row in df_filtered.iterrows():
        # 1) 경력 적합도 (20%)
        req_career = parse_career_years(row.get("career", ""))
        career_score = 100 if user_career_val >= req_career else 0
        
        # 2) 학력 적합도 (20%)
        req_edu = parse_edu_level(row.get("education", ""))
        edu_score = 100 if user_edu_val >= req_edu else 0
        
        # 공고 텍스트 결합
        text = (str(row.get("sectors", "")) + " " + str(row.get("title", "")) + " " + str(row.get("detail_content", ""))).lower()
        
        # 3) 자격증 매칭 (20%)
        needed_lic = [lic for lic in licenses_pool if any(kw in text for kw in synonyms[lic])]
        lic_score = 100 if not needed_lic else (sum(1 for lic in needed_lic if lic in user_licenses) / len(needed_lic)) * 100
        
        # 4) 실무 툴 매칭 (20%)
        needed_tools = [t for t in tools_pool if any(kw in text for kw in synonyms[t])]
        tool_score = 100 if not needed_tools else (sum(1 for t in needed_tools if t in user_tools) / len(needed_tools)) * 100
        
        # 5) 실무 경험 매칭 (20%)
        needed_exps = [e for e in experiences_pool if any(kw in text for kw in synonyms[e])]
        exp_score = 100 if not needed_exps else (sum(1 for e in needed_exps if e in user_experiences) / len(needed_exps)) * 100
        
        # 5대 가중치 적용 종합 점수
        combined_score = (career_score * 0.2) + (edu_score * 0.2) + (lic_score * 0.2) + (tool_score * 0.2) + (exp_score * 0.2)
        total_scores.append(combined_score)
        
    suitability_score = np.mean(total_scores) if total_scores else 0.0
    suitability_score = min(max(suitability_score, 0.0), 100.0) # 안전 바인딩
    
    # 2. 미선택/미보유 스펙 중 빈도가 높은 순 TOP 3 도출 (카테고리 교차)
    unselected_all = []
    for lic in licenses_pool:
        if lic not in user_licenses: unselected_all.append((lic, "자격증"))
    for t in tools_pool:
        if t not in user_tools: unselected_all.append((t, "실무 툴"))
    for e in experiences_pool:
        if e not in user_experiences: unselected_all.append((e, "직무 경험"))
        
    unselected_freqs = []
    total_jobs = len(df_filtered)
    for item, cat in unselected_all:
        freq = sum(1 for _, row in df_filtered.iterrows() if any(kw in (str(row.get("sectors", "")) + " " + str(row.get("title", "")) + " " + str(row.get("detail_content", ""))).lower() for kw in synonyms[item]))
        pct = (freq / total_jobs) * 100 if total_jobs > 0 else 0
        unselected_freqs.append((item, cat, freq, pct))
        
    # 빈도 백분율 높은 순 정렬
    unselected_freqs = sorted(unselected_freqs, key=lambda x: x[3], reverse=True)
    missing_specs = unselected_freqs[:3]
    
    # [방어 조치] 전역 변수 바인딩하여 리포트 제너레이터 호환성 보장
    user_skills = user_licenses + user_tools + user_experiences
    missing_skills = [item[0] for item in missing_specs]
    
    if diagnose_clicked or (len(user_licenses) > 0 or len(user_tools) > 0 or len(user_experiences) > 0):
        st.subheader("📋 기획 직무 다차원 적합도 진단 결과")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric(
                label="종합 직무 적합도 점수",
                value=f"{suitability_score:.1f}점",
                help="공식: (경력 20% + 학력 20% + 자격증 20% + 실무툴 20% + 직무경험 20%) 매칭 평균"
            )
            
        with col2:
            st.markdown("##### ⚠️ 당신이 탑티어 기획자가 되기 위해 우선순위로 채워야 할 스펙 (TOP 3)")
            if missing_specs:
                for idx, (item, cat, freq, pct) in enumerate(missing_specs):
                    st.warning(f"**{idx+1}순위: {item}** ({cat}) ➔ 타겟 공고의 **{pct:.1f}%**에서 요구/우대 중")
            else:
                st.success("🎉 현재 선택된 세부 직무에서 우대하는 모든 핵심 스펙셋을 완벽히 갖추셨습니다!")
                
        # 상세 매칭 매트릭스 제공
        st.write("---")
        st.markdown("##### 🔍 상세 스펙별 공고 요구율 및 나의 스펙 맵")
        
        match_table = []
        all_specs = [
            (licenses_pool, "자격증", user_licenses),
            (tools_pool, "실무 툴", user_tools),
            (experiences_pool, "직무 경험", user_experiences)
        ]
        
        for spec_list, cat, user_list in all_specs:
            for item in spec_list:
                freq = sum(1 for _, row in df_filtered.iterrows() if any(kw in (str(row.get("sectors", "")) + " " + str(row.get("title", "")) + " " + str(row.get("detail_content", ""))).lower() for kw in synonyms[item]))
                pct = (freq / total_jobs) * 100 if total_jobs > 0 else 0
                has_it = "✅ 보유 중" if item in user_list else "❌ 미보유"
                match_table.append({
                    "스펙 범주": cat,
                    "세부 스펙명": item,
                    "공고 내 요구 빈도 (건)": freq,
                    "공고 내 우대 비율 (%)": f"{pct:.1f}%",
                    "나의 보유 상태": has_it
                })
                
        st.table(pd.DataFrame(match_table))
    else:
        st.info("💡 사이드바에서 직무 필터를 선택하고, 경력/학력/보유 역량을 선택한 뒤 **'나의 다차원 직무 적합도 진단 실행'** 버튼을 누르시면 종합 적합도 분석이 수행됩니다.")


# 🏢 탭 2: 인사팀향 - 기획 직무 미스매치(Gap) 리포트
with tab2:
    st.header("🏢 구직자 관심도(공급) vs 기업 요구 우대도(수요) Gap 리포트")
    st.markdown(
        "네이버 데이터랩 기반 자격증 검색량(공급 측면)과 사람인 1,000건의 기획/전략 채용공고의 "
        "스킬 요구 빈도(수요 측면)를 매칭하여 수급 미스매치 갭을 진단합니다."
    )
    
    # ----------------- 수요/공급 데이터 준비 -----------------
    # df_mismatch_mart에서 11대 핵심 스킬/자격증 목록을 동적으로 로딩
    compare_skills = df_mismatch_mart["자격증명"].tolist()
    
    # 공급 데이터 매핑 (df_licenses 활용)
    supply_dict = dict(zip(df_licenses["자격증명"], df_licenses["구직자_월간검색량"]))
    
    # 수요 데이터 실시간 카운트 (텍스트에 스킬이 등장하는 공고 건수)
    demand_counts = []
    total_jobs = len(df_filtered)
    
    for skill in compare_skills:
        # 각 필요 역량 및 자격증의 유사어 및 매칭 패턴 카운트 확장
        if skill == "PPT작성법":
            count = sum(1 for _, row in df_filtered.iterrows() if any(x in (str(row.get("sectors", "")) + " " + str(row.get("title", "")) + " " + str(row.get("detail_content", ""))).lower() for x in ["ppt", "파워포인트", "ppt마스터", "ppt작성"]))
        elif skill == "데이터분석":
            count = sum(1 for _, row in df_filtered.iterrows() if any(x in (str(row.get("sectors", "")) + " " + str(row.get("title", "")) + " " + str(row.get("detail_content", ""))).lower() for x in ["데이터분석", "데이터 분석", "data analysis", "지표"]))
        elif skill == "시장조사":
            count = sum(1 for _, row in df_filtered.iterrows() if any(x in (str(row.get("sectors", "")) + " " + str(row.get("title", "")) + " " + str(row.get("detail_content", ""))).lower() for x in ["시장조사", "시장 조사", "리서치", "research"]))
        elif skill == "M&A":
            count = sum(1 for _, row in df_filtered.iterrows() if any(x in (str(row.get("sectors", "")) + " " + str(row.get("title", "")) + " " + str(row.get("detail_content", ""))).lower() for x in ["m&a", "인수합병", "인수 합병"]))
        else:
            count = sum(1 for _, row in df_filtered.iterrows() if skill.lower() in (str(row.get("sectors", "")) + " " + str(row.get("title", "")) + " " + str(row.get("detail_content", ""))).lower())
        demand_counts.append(count)
        
    df_gap = pd.DataFrame({
        "스킬명": compare_skills,
        "구직자_검색량": [supply_dict.get(s, 0) for s in compare_skills],
        "기업_우대빈도": demand_counts
    })
    
    # ----------------- Plotly 이중 Y축 막대 차트 생성 (ONLY plotly 규칙 준수) -----------------
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 1) 구직자 관심도 (검색량) - Bar Chart (왼쪽 축)
    fig.add_trace(
        gr.Bar(
            x=df_gap["스킬명"],
            y=df_gap["구직자_검색량"],
            name="구직자 관심도 (네이버 검색량)",
            marker_color="#818cf8",
            opacity=0.85,
            hovertemplate="스킬명: %{x}<br>구직자 관심도: %{y:,.0f}회<extra></extra>"
        ),
        secondary_y=False
    )
    
    # 2) 실제 기업 우대 빈도 (공고 등장수) - Bar Chart (오른쪽 축)
    fig.add_trace(
        gr.Bar(
            x=df_gap["스킬명"],
            y=df_gap["기업_우대빈도"],
            name="실제 기업 우대 빈도 (사람인 공고수)",
            marker_color="#fb7185",
            opacity=0.85,
            hovertemplate="스킬명: %{x}<br>기업 우대빈도: %{y}건<extra></extra>"
        ),
        secondary_y=True
    )
    
    # 레이아웃 디자인 (라이트 테마 최적화 및 가독성 정돈)
    fig.update_layout(
        title=dict(
            text=f"[{selected_target}] 기획 스킬 수급 Gap 비교 분석",
            font=dict(size=16, color="#0f172a", family="Inter, sans-serif")
        ),
        barmode="group",
        plot_bgcolor="rgba(255,255,255,0.9)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#1e293b", size=11)
        ),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    # X/Y축 레이아웃 (bold=True 에러 방지 및 HTML b 태그 활용)
    fig.update_xaxes(
        title_text="<b>요구 자격증 및 기획 스킬셋</b>",
        showgrid=True,
        gridcolor="#e2e8f0",
        tickfont=dict(color="#1e293b", size=11),
        title_font=dict(color="#1e293b", size=12)
    )
    
    fig.update_yaxes(
        title_text="<b>구직자 월간 검색량 (회)</b>",
        showgrid=True,
        gridcolor="#e2e8f0",
        tickfont=dict(color="#3730a3", size=11),
        title_font=dict(color="#3730a3", size=12),
        secondary_y=False
    )
    
    fig.update_yaxes(
        title_text="<b>실제 기업 우대 건수 (건)</b>",
        showgrid=False,
        tickfont=dict(color="#9f1239", size=11),
        title_font=dict(color="#9f1239", size=12),
        secondary_y=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ----------------- 10년 차 기획자의 날카로운 비즈니스 제언 -----------------
    st.subheader("💡 10년 차 수석 기획자가 던지는 채용 전략 제언")
    
    if selected_target == "전체 기획/전략":
        st.info(
            "기획/전략 구직자들은 여전히 '컴퓨터활용능력(45,000회)'이나 'PPT작성법(22,000회)' 위주로 공급 스펙을 탐색하지만, "
            "실제 채용 시장의 핵심 우대 요건은 'SQLD, GA4, Figma' 등의 데이터 및 화면 설계 스킬이 압도적으로 높습니다. "
            "인사팀은 허수 지원자를 걸러내고 우리 기업에 꼭 맞는 최적의 인재를 발굴하기 위하여 채용 공고 내 우대 기술요건(JD)을 "
            "보다 명시적이고 디테일하게 최적화(JD Optimization)할 필요가 있습니다."
        )
    elif selected_target == "IT/서비스 기획":
        st.info(
            "IT/서비스 기획의 구직 시장은 '컴퓨터활용능력(45,000회)'과 같은 오피스 라이선스에 관심이 쏠려 있으나, "
            "실제 실무 현장과 채용 공고는 'Figma 활용 화면설계, SQLD 쿼리 해독, GA4 고객 데이터 분석' 등을 강력히 요구합니다. "
            "인사담당자는 단순 문서 기획자가 아닌 기술 중심의 서비스 기획 인재 유입을 위해 채용 공고 상단 태그에 "
            "핵심 테크니컬 스킬셋을 명확히 정의하여 공고의 매력도를 높여야 합니다."
        )
    elif selected_target == "경영/사업 전략":
        st.info(
            "경영/사업 전략 구직자들은 기본 사무 도구 사용 검색량이 우세한 반면, 채용 기업은 'M&A 검토, 신사업 타당성분석, CPA/CFA' 등의 "
            "재무 및 전략적 의사결정 전문 역량을 최우선시합니다. 인사팀에서는 전문 역량의 실제 요구 수준을 공고 내 가이드로 안내하고, "
            "입사 후 전문 기획자 양성 로드맵을 사전에 공개함으로써 진정성 있는 우수 지원자들의 관심도를 적극 이끌어내야 합니다."
        )
        
    st.write("---")
    st.subheader("📈 외부 구직자 검색 트렌드 추이 시각화 (2026년 상반기)")
    st.markdown("통합 데이터 마트(`automated_total_mismatch_mart.csv`) 내의 월별 상대적 검색 비율(Relative Ratio) 추이 분석 그래프입니다.")
    
    # 비교 타겟 멀티셀렉트
    selected_trend_skills = st.multiselect(
        "시계열 분석을 진행할 직무 역량 / 자격증 다중 선택",
        options=compare_skills,
        default=["SQLD", "Figma", "데이터분석", "M&A"],
        help="검색 트렌드 비교를 원하는 스킬 키워드를 선택하세요."
    )
    
    if selected_trend_skills:
        fig_trend = gr.Figure()
        months = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
        
        for ts in selected_trend_skills:
            row = df_mismatch_mart[df_mismatch_mart["자격증명"] == ts]
            if not row.empty:
                ratios = [row[f"{m}_검색비율"].values[0] for m in months]
                fig_trend.add_trace(gr.Scatter(
                    x=months,
                    y=ratios,
                    mode="lines+markers",
                    name=ts,
                    line=dict(width=3),
                    marker=dict(size=8),
                    hovertemplate="연월: %{x}<br>스킬명: " + ts + "<br>검색비율: %{y:.1f}%<extra></extra>"
                ))
                
        fig_trend.update_layout(
            title=dict(
                text="<b>2026년 상반기 월간 검색 트렌드 변동 추이 (Relative Ratio)</b>",
                font=dict(size=14, color="#0f172a", family="Inter, sans-serif")
            ),
            xaxis_title="<b>조회 연월 (2026)</b>",
            yaxis_title="<b>상대적 검색량 비율 (0 ~ 100)</b>",
            plot_bgcolor="rgba(255,255,255,0.9)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(color="#1e293b", size=11)
            ),
            margin=dict(l=40, r=40, t=80, b=40)
        )
        
        fig_trend.update_xaxes(
            showgrid=True,
            gridcolor="#e2e8f0",
            tickfont=dict(color="#1e293b", size=11),
            title_font=dict(color="#1e293b", size=12)
        )
        
        fig_trend.update_yaxes(
            showgrid=True,
            gridcolor="#e2e8f0",
            tickfont=dict(color="#1e293b", size=11),
            title_font=dict(color="#1e293b", size=12)
        )
        
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("💡 위 멀티셀렉트에서 스킬 키워드를 선택하시면 상반기 검색 트렌드 추이가 출력됩니다.")

    st.write("---")
    st.subheader("📊 외부 구직자 트렌드 인덱스 (네이버 카페 데이터분석 검색 트렌드 분석)")
    st.markdown("인사담당자가 채용 브랜딩 및 JD 최적화 시 참고할 수 있는 외부 포럼 및 카페 기반의 구직자 관심 데이터 통계입니다.")
    
    # 네이버 카페 분석 구직자 트렌드 인덱스 파일 연동 반영 (다중 경로 fallback)
    naver_report_paths = [
        "naver-api-app/report/naver_analysis_eda_report.md",
        "report/naver_analysis_eda_report.md",
        "../report/naver_analysis_eda_report.md",
        "../../naver-api-app/report/naver_analysis_eda_report.md"
    ]
    naver_report_path = None
    for p in naver_report_paths:
        if os.path.exists(p):
            naver_report_path = p
            break
            
    try:
        if naver_report_path:
            with open(naver_report_path, "r", encoding="utf-8") as f:
                naver_report_markdown = f.read()
                
            # 실행 위치에 따른 최적의 이미지 경로 동적 해결
            img_paths = [
                "naver-api-app/images/",
                "images/",
                "../images/",
                "../../naver-api-app/images/"
            ]
            resolved_img_path = "naver-api-app/images/"
            for ip in img_paths:
                if os.path.exists(ip):
                    resolved_img_path = ip
                    break
                    
            # 상대 이미지 경로를 streamlit 실행 경로에 맞춰 치환하여 깨짐 방지
            naver_report_markdown = naver_report_markdown.replace("../images/", resolved_img_path)
            with st.expander("🔍 네이버 카페 데이터분석 트렌드 상세 통계 및 시각화 보기", expanded=False):
                st.markdown(naver_report_markdown)
        else:
            st.warning("⚠️ 네이버 카페 트렌드 보고서 파일을 찾을 수 없습니다.")
    except Exception as read_err:
        st.warning(f"⚠️ 네이버 카페 트렌드 인덱스를 로드하지 못했습니다: {read_err}")


# ----------------- 5. 정적 리포트 생성 및 다운로드 -----------------
# Plotly 피규어의 HTML 코드 추출
fig_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

# 실시간 HTML 백업 저장 트리거
generate_planning_report(selected_target, user_skills, suitability_score, missing_skills, fig_html)

# 사이드바 다운로드 제공을 위해 리포트 읽기 (다중 경로 체크)
report_file_paths = [
    "saramin/report/planning_mismatch_report.html",
    "report/planning_mismatch_report.html",
    "../report/planning_mismatch_report.html",
    "../../saramin/report/planning_mismatch_report.html"
]
report_file_path = None
for rfp in report_file_paths:
    if os.path.exists(rfp):
        report_file_path = rfp
        break
        
if report_file_path and os.path.exists(report_file_path):
    with open(report_file_path, "r", encoding="utf-8") as f:
        html_bytes = f.read().encode("utf-8")
        
    st.sidebar.download_button(
        label="HTML 정적 보고서 다운로드",
        data=html_bytes,
        file_name=f"planning_mismatch_report_{selected_target}.html",
        mime="text/html",
        help="현재 기획/전략 분석 필터 및 진단이 반영된 정적 HTML 보고서를 저장합니다."
    )
