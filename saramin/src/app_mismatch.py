"""
이 파일은 자격증 미스매치(Gap) 분석 및 지원 적합도 자가진단 Streamlit 대시보드(app_mismatch.py)입니다.

주요 기능:
- 사이드바 필터를 통해 직무(인사, 회계, 감사, 데이터분석)를 선택하고 분석을 수행합니다.
- [구직자 탭]: 구직자가 자신의 자격증을 입력하면 직무별 우대사항 일치율(%)을 산출하고, TOP 3 추천 자격증을 제안합니다.
- [인사팀 탭]: 구직자의 자격증 관심도(검색량)와 기업의 채용 공고 요구도(등장수)를 이중 축 Plotly 막대 차트로 시각화하여 미스매치를 보여줍니다.
- [정적 HTML 리포트 저장]: 대시보드 실행 및 진단 시, 현 상태를 요약한 모던 디자인의 HTML 리포트를 자동으로 생성하여 report 폴더에 저장합니다.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as gr
from plotly.subplots import make_subplots
import os

# 페이지 기본 설정 (와이드 레이아웃 및 세련된 테마 적용)
st.set_page_config(
    page_title="자격증 미스매치 분석 및 자가진단 대시보드",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- 1. 가상 데이터 셋 (Mock Data) 정의 -----------------
@st.cache_data
def get_mock_data():
    # 1) 공고 데이터 (df_jobs)
    # 직무별로 5개씩 총 20개 공고를 구성합니다.
    jobs_data = [
        # 데이터분석 직무
        {"공고ID": 101, "기업명": "네이버", "직무": "데이터분석", "우대자격증": "SQLD, 정보처리기사"},
        {"공고ID": 102, "기업명": "카카오", "직무": "데이터분석", "우대자격증": "SQLD, ADsP"},
        {"공고ID": 103, "기업명": "토스", "직무": "데이터분석", "우대자격증": "SQLP, ADP, 정보처리기사"},
        {"공고ID": 104, "기업명": "라인", "직무": "데이터분석", "우대자격증": "SQLD, ADsP, 정보처리기사"},
        {"공고ID": 105, "기업명": "쿠팡", "직무": "데이터분석", "우대자격증": "SQLD, SQLP, ADsP"},
        
        # 인사 직무
        {"공고ID": 201, "기업명": "배달의민족", "직무": "인사", "우대자격증": "공인노무사, ERP정보관리사"},
        {"공고ID": 202, "기업명": "직방", "직무": "인사", "우대자격증": "ERP정보관리사, 컴퓨터활용능력"},
        {"공고ID": 203, "기업명": "야놀자", "직무": "인사", "우대자격증": "공인노무사, 컴퓨터활용능력"},
        {"공고ID": 204, "기업명": "당근마켓", "직무": "인사", "우대자격증": "ERP정보관리사"},
        {"공고ID": 205, "기업명": "무신사", "직무": "인사", "우대자격증": "공인노무사, ERP정보관리사, 컴퓨터활용능력"},
        
        # 회계 직무
        {"공고ID": 301, "기업명": "쏘카", "직무": "회계", "우대자격증": "전산세무, 전산회계"},
        {"공고ID": 302, "기업명": "샌드박스", "직무": "회계", "우대자격증": "재경관리사, CPA"},
        {"공고ID": 303, "기업명": "크래프톤", "직무": "회계", "우대자격증": "전산세무, 재경관리사"},
        {"공고ID": 304, "기업명": "넷마블", "직무": "회계", "우대자격증": "CPA, 전산세무"},
        {"공고ID": 305, "기업명": "엔씨소프트", "직무": "회계", "우대자격증": "재경관리사, 전산회계"},
        
        # 감사 직무
        {"공고ID": 401, "기업명": "넥슨", "직무": "감사", "우대자격증": "CISA, CIA"},
        {"공고ID": 402, "기업명": "셀트리온", "직무": "감사", "우대자격증": "CISA, CPA"},
        {"공고ID": 403, "기업명": "삼성바이오", "직무": "감사", "우대자격증": "CIA, CPA"},
        {"공고ID": 404, "기업명": "SK하이닉스", "직무": "감사", "우대자격증": "CISA, 컴퓨터활용능력"},
        {"공고ID": 405, "기업명": "LG전자", "직무": "감사", "우대자격증": "CIA, 컴퓨터활용능력"},
    ]
    df_jobs = pd.DataFrame(jobs_data)
    
    # 2) 자격증 통계 데이터 (df_licenses)
    # 구직자 월간 검색량(공급 측면)과 실제 공고 등장수(수요 측면)를 비교 분석하기 위한 데이터셋입니다.
    licenses_data = [
        # 데이터분석
        {"자격증명": "SQLD", "구직자_월간검색량": 15000, "실제_공고_등장수": 12, "대상직무": "데이터분석"},
        {"자격증명": "ADsP", "구직자_월간검색량": 12000, "실제_공고_등장수": 9, "대상직무": "데이터분석"},
        {"자격증명": "정보처리기사", "구직자_월간검색량": 20000, "실제_공고_등장수": 8, "대상직무": "데이터분석"},
        {"자격증명": "SQLP", "구직자_월간검색량": 4000, "실제_공고_등장수": 4, "대상직무": "데이터분석"},
        {"자격증명": "ADP", "구직자_월간검색량": 3000, "실제_공고_등장수": 2, "대상직무": "데이터분석"},
        
        # 인사
        {"자격증명": "컴퓨터활용능력", "구직자_월간검색량": 45000, "실제_공고_등장수": 3, "대상직무": "인사"},
        {"자격증명": "공인노무사", "구직자_월간검색량": 8000, "실제_공고_등장수": 7, "대상직무": "인사"},
        {"자격증명": "ERP정보관리사", "구직자_월간검색량": 5000, "실제_공고_등장수": 9, "대상직무": "인사"},
        
        # 회계
        {"자격증명": "컴퓨터활용능력", "구직자_월간검색량": 45000, "실제_공고_등장수": 1, "대상직무": "회계"},
        {"자격증명": "전산회계", "구직자_월간검색량": 25000, "실제_공고_등장수": 6, "대상직무": "회계"},
        {"자격증명": "전산세무", "구직자_월간검색량": 20000, "실제_공고_등장수": 8, "대상직무": "회계"},
        {"자격증명": "재경관리사", "구직자_월간검색량": 12000, "실제_공고_등장수": 7, "대상직무": "회계"},
        {"자격증명": "CPA", "구직자_월간검색량": 15000, "실제_공고_등장수": 5, "대상직무": "회계"},
        
        # 감사
        {"자격증명": "컴퓨터활용능력", "구직자_월간검색량": 45000, "실제_공고_등장수": 2, "대상직무": "감사"},
        {"자격증명": "CISA", "구직자_월간검색량": 3000, "실제_공고_등장수": 12, "대상직무": "감사"},
        {"자격증명": "CIA", "구직자_월간검색량": 2500, "실제_공고_등장수": 10, "대상직무": "감사"},
        {"자격증명": "CPA", "구직자_월간검색량": 15000, "실제_공고_등장수": 6, "대상직무": "감사"},
    ]
    df_licenses = pd.DataFrame(licenses_data)
    
    return df_jobs, df_licenses

df_jobs, df_licenses = get_mock_data()


# ----------------- 2. 정적 HTML 리포트 생성 함수 -----------------
def generate_static_report(selected_job, user_certs, match_rate, missing_certs, fig_html):
    """
    분석 및 진단 결과를 가독성 높은 모던한 반응형 HTML 보고서로 저장합니다.
    """
    report_dir = "saramin/report"
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "mismatch_report.html")
    
    certs_list_str = ", ".join(user_certs) if user_certs else "없음"
    missing_list_str = ", ".join(missing_certs) if missing_certs else "필수 우대 자격증을 모두 보유하고 있습니다!"
    
    # 직무별 비즈니스 제언
    insights = {
        "인사": "인사 직무 구직자들은 '컴퓨터활용능력' 등 기본 사무 능력 검색 비중이 높지만, 실제 공고는 '공인노무사'와 'ERP정보관리사' 우대 빈도가 높습니다. 기업은 채용 공고 시 구직자들이 선호하는 키워드를 포함시키고, 구직자들은 실무 전문 자격증을 추가로 확보할 필요가 있습니다.",
        "회계": "회계 직무 구직자들은 범용적인 '컴퓨터활용능력'에 높은 관심을 보이지만, 공고에서는 '전산세무/회계' 및 '재경관리사'가 실무 우대 자격증으로 자주 쓰입니다. 기업은 직무 필수 자격증 요구사항을 명확히 하고, 구직자들은 기초 자격증 외 실무 자격을 취득해야 합니다.",
        "감사": "감사 직무 구직자들은 '컴퓨터활용능력'을 다수 검색하는 반면, 채용 기업은 'CISA/CIA'의 고도화된 정보시스템 및 내부감사 전문 자격을 선호합니다. 미스매치를 해결하기 위해 채용 브랜딩에 구직자 검색 키워드를 효과적으로 배치하는 것을 제안합니다.",
        "데이터분석": "데이터분석 구직자들은 주로 '정보처리기사'를 선호하지만, 기업은 실무 분석 데이터 가공에 유용한 'SQLD' 및 'ADsP'의 우대 빈도가 더 높습니다. 실무 지향적 스킬셋 매칭을 위해 요구역량을 구체화하는 것이 바람직합니다."
    }
    selected_insight = insights.get(selected_job, "")

    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>자격증 미스매치 및 자가진단 리포트</title>
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
                <span class="bg-indigo-500/10 text-indigo-400 text-xs font-semibold px-3 py-1.5 rounded-full border border-indigo-500/20 uppercase tracking-wider">Mismatch Analysis Report</span>
                <h1 class="text-3xl md:text-4xl font-bold mt-3 text-white tracking-tight">자격증 미스매치 및 자가진단 리포트</h1>
                <p class="text-slate-400 text-sm mt-1">구직자 공급 데이터와 채용 공고 수요 데이터의 실시간 격차 분석 결과</p>
            </div>
            <div class="mt-4 md:mt-0 text-left md:text-right">
                <p class="text-xs text-slate-500">분석 기준 직무</p>
                <p class="text-lg font-bold text-indigo-400">{selected_job} 직무</p>
            </div>
        </div>

        <!-- 2컬럼 레이아웃: 자가진단 & 스펙 제언 -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-slate-800/40 border border-slate-700/30 rounded-2xl p-6 flex flex-col justify-between">
                <div>
                    <h3 class="text-slate-400 text-xs font-semibold uppercase tracking-wider">나의 자격요건 일치율</h3>
                    <p class="text-4xl font-black text-indigo-400 mt-2 font-outfit">{match_rate:.1f}%</p>
                </div>
                <div class="mt-4 pt-4 border-t border-slate-800">
                    <p class="text-xs text-slate-500">보유 자격증</p>
                    <p class="text-sm font-semibold text-white truncate mt-1">{certs_list_str}</p>
                </div>
            </div>
            <div class="bg-slate-800/40 border border-slate-700/30 rounded-2xl p-6 md:col-span-2 flex flex-col justify-between">
                <div>
                    <h3 class="text-slate-400 text-xs font-semibold uppercase tracking-wider">나에게 지금 부족한 추천 스펙</h3>
                    <div class="flex flex-wrap gap-2 mt-3">
                        {"" if missing_certs else '<span class="text-emerald-400 text-sm font-medium">모든 필수 자격증을 보유 중입니다! 🎉</span>'}
    """
    for cert in missing_certs:
        html_content += f'<span class="bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-semibold px-3 py-1 rounded-full">{cert}</span>'
        
    html_content += f"""
                    </div>
                </div>
                <div class="mt-4 pt-4 border-t border-slate-800">
                    <p class="text-xs text-slate-500">추천 스펙 가이드</p>
                    <p class="text-sm text-slate-300 mt-1">기업이 우대하는 공고 비중 대비 미보유한 역량 순위입니다.</p>
                </div>
            </div>
        </div>

        <!-- 시각화 영역 -->
        <div class="bg-slate-800/20 border border-slate-800 rounded-2xl p-6 mb-8">
            <h2 class="text-xl font-bold text-white mb-4">📊 구직자 관심도 vs 채용공고 우대 비교</h2>
            <div class="w-full overflow-hidden rounded-xl bg-slate-900/50 p-2">
                {fig_html}
            </div>
        </div>

        <!-- 비즈니스 제언 영역 -->
        <div class="bg-indigo-950/40 border border-indigo-900/40 rounded-2xl p-6">
            <h2 class="text-lg font-bold text-indigo-300 mb-2">💡 인사/채용 전략적 제언</h2>
            <p class="text-sm text-slate-300 leading-relaxed">{selected_insight}</p>
        </div>

        <!-- 푸터 -->
        <div class="border-t border-slate-800 mt-8 pt-6 flex justify-between items-center text-xs text-slate-500">
            <p>© 사람인 자격증 미스매치 분석 시스템</p>
            <p>Generated dynamically via Streamlit</p>
        </div>
    </div>
</body>
</html>
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)


# ----------------- 3. 사이드바 구성 -----------------
st.sidebar.title("🔎 자격증 미스매치 필터")

# 직무 선택 box
selected_job = st.sidebar.selectbox(
    "분석 직무 선택",
    ["인사", "회계", "감사", "데이터분석"],
    help="분석 및 진단을 진행할 대상 직무를 선택합니다."
)

st.sidebar.write("---")
st.sidebar.info(
    "💡 대시보드가 업데이트될 때마다 `saramin/report/mismatch_report.html`에 "
    "인터랙티브 리포트가 실시간 저장됩니다."
)


# ----------------- 4. 메인 화면 및 탭 구조 구성 -----------------
st.title("🎓 취업 시장 자격증 미스매치(Gap) 분석 & 자가진단")
st.markdown(f"선택된 직무: **{selected_job}** | 구직자 공급 데이터와 기업의 실제 채용 우대 사항 간의 매칭")
st.write("---")

tab1, tab2 = st.tabs(["💻 구직자 탭 (스펙 자가진단)", "🏢 인사팀 탭 (시장 미스매치 분석)"])

# 데이터 처리용 사전 준비
# 해당 직무의 모든 공고 필터링
df_jobs_filtered = df_jobs[df_jobs["직무"] == selected_job]

# 해당 직무의 공고들이 요구하는 전체 우대 자격증 목록 및 빈도 계산
all_job_certs = []
for certs_str in df_jobs_filtered["우대자격증"]:
    certs = [c.strip() for c in certs_str.split(",") if c.strip()]
    all_job_certs.extend(certs)

# 평균 필요 자격증 수 계산 (공고별 평균)
job_certs_counts = df_jobs_filtered["우대자격증"].apply(lambda x: len([c.strip() for c in x.split(",") if c.strip()]))
avg_certs_needed = job_certs_counts.mean() if len(job_certs_counts) > 0 else 1.0

# 중복 제거된 직무의 요구 자격증 및 빈도 DataFrame 생성
from collections import Counter
cert_counts = Counter(all_job_certs)
df_job_demand = pd.DataFrame(cert_counts.items(), columns=["자격증명", "우대빈도"]).sort_values(by="우대빈도", ascending=False)


# 💻 탭 1: 구직자 탭 (스펙 자가진단)
with tab1:
    st.header("💻 나의 자격증 자가진단 및 추천 스펙")
    st.markdown("자신이 보유한 자격증을 다중 선택하고, 해당 직무의 실제 채용 요구조건과 얼마나 부합하는지 진단해 보세요.")
    
    # multiselect의 선택 품목은 해당 직무 자격증 통계에 있는 자격증들을 디폴트로 하고, 기본 보유 후보들을 추가합니다.
    available_certs = list(df_licenses[df_licenses["대상직무"] == selected_job]["자격증명"].unique())
    # 혹시 타 직무 자격증도 가지고 있을 수 있으므로 전체 자격증을 선택 후보로 제공합니다.
    all_available_certs = list(df_licenses["자격증명"].unique())
    
    user_certs = st.multiselect(
        "보유 자격증 다중 선택",
        options=all_available_certs,
        default=[],
        help="현재 구직자 본인이 취득 완료한 자격증들을 모두 선택해 주세요."
    )
    
    # 진단 버튼 클릭 시 연산 수행
    diagnose_clicked = st.button("📊 나의 스펙 자가진단 실행")
    
    # 결과 처리 (버튼을 누르지 않았더라도 기본 일치율을 표시하기 위해 세션 혹은 변수 제어)
    # 1. 일치율 계산
    # 일치율 공식: (유저 자격증 중 공고 우대사항에 포함된 개수 / 해당 직무 공고들의 평균 필요 자격증 수) * 100
    job_certs_set = set(all_job_certs)
    user_matched_certs = set(user_certs).intersection(job_certs_set)
    user_matched_count = len(user_matched_certs)
    
    match_rate = (user_matched_count / avg_certs_needed) * 100 if avg_certs_needed > 0 else 0.0
    match_rate = min(match_rate, 100.0)  # 일치율 상한을 100%로 보정하여 직관성 확보
    
    # 2. 부족한 추천 스펙 TOP 3 도출
    # 해당 직무의 공고 우대빈도가 높은 순서대로 정렬된 리스트에서, 유저가 미보유한 것들 추출
    missing_certs_df = df_job_demand[~df_job_demand["자격증명"].isin(user_certs)]
    missing_certs = list(missing_certs_df["자격증명"].head(3))
    
    if diagnose_clicked or len(user_certs) > 0:
        st.subheader("📋 진단 결과 리포트")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric(
                label="내 자격요건 일치율",
                value=f"{match_rate:.1f}%",
                help="계산 기준: (보유 자격증 중 공고 우대사항 포함 수 / 직무 공고의 평균 우대자격증 개수)"
            )
        
        with col2:
            st.markdown("##### 🚀 나에게 지금 부족한 추천 스펙 (TOP 3)")
            if missing_certs:
                for idx, cert in enumerate(missing_certs):
                    # 해당 자격증의 채용 공고 등장 비중 계산
                    cert_freq = cert_counts.get(cert, 0)
                    total_jobs = len(df_jobs_filtered)
                    pct = (cert_freq / total_jobs) * 100 if total_jobs > 0 else 0
                    st.markdown(f"**{idx+1}위. {cert}** (이 직무 공고의 {pct:.0f}%에서 우대 중)")
            else:
                st.success("🎉 축하합니다! 이 직무에서 우대하는 핵심 자격증을 이미 모두 보유 중입니다.")
        
        # 상세 매칭 분석 현황 테이블 제공
        st.write("---")
        st.markdown("##### 🔍 직무 공고 우대 자격증 목록과 나의 매칭 상세")
        
        match_table = []
        for idx, row in df_job_demand.iterrows():
            cert_name = row["자격증명"]
            freq = row["우대빈도"]
            has_it = "✅ 보유 중" if cert_name in user_certs else "❌ 미보유"
            match_table.append({
                "자격증명": cert_name,
                "공고 내 우대 언급 빈도 (건)": freq,
                "나의 보유 여부": has_it
            })
        
        st.table(pd.DataFrame(match_table))
    else:
        st.info("💡 위의 입력창에서 취득하신 자격증을 선택한 후 **'나의 스펙 자가진단 실행'** 버튼을 클릭하시면 맞춤형 진단을 확인하실 수 있습니다.")


# 🏢 탭 2: 인사팀 탭 (시장 미스매치 분석)
with tab2:
    st.header("🏢 구직자 자격증 관심도(공급) vs 실제 기업 우대 빈도(수요) 비교")
    st.markdown(
        "구직자의 월간 자격증 검색량(네이버 데이터랩 기반 공급 지표)과 "
        "사람인 공고의 우대 자격증 빈도(수요 지표)를 비교하여 수급 미스매치(Gap)를 시각화합니다."
    )
    
    # 선택된 직무에 해당하는 자격증 통계 데이터 필터링
    df_lic_filtered = df_licenses[df_licenses["대상직무"] == selected_job].copy()
    
    # ----------------- 5. Plotly 이중 축 Grouped Bar Chart 시각화 -----------------
    # 두 지표의 Scale 차이(검색량: 수만 vs 등장수: 1~20건)를 극복하기 위해 이중 축 차트 구성
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 1) 구직자 관심도 (검색량) - Bar Chart (왼쪽 축)
    fig.add_trace(
        gr.Bar(
            x=df_lic_filtered["자격증명"],
            y=df_lic_filtered["구직자_월간검색량"],
            name="구직자 월간 검색량 (공급)",
            marker_color="#818cf8",
            opacity=0.85,
            hovertemplate="자격증: %{x}<br>월간 검색량: %{y:,.0f}회<extra></extra>"
        ),
        secondary_y=False
    )
    
    # 2) 실제 기업 우대 빈도 (공고 등장수) - Bar Chart (오른쪽 축)
    fig.add_trace(
        gr.Bar(
            x=df_lic_filtered["자격증명"],
            y=df_lic_filtered["실제_공고_등장수"],
            name="실제 공고 등장수 (수요)",
            marker_color="#fb7185",
            opacity=0.85,
            hovertemplate="자격증: %{x}<br>실제 공고 등장수: %{y}건<extra></extra>"
        ),
        secondary_y=True
    )
    
    # 레이아웃 스타일 설정
    fig.update_layout(
        title=dict(
            text=f"[{selected_job} 직무] 구직자 관심도 vs 채용 공고 수요 미스매치 분석",
            font=dict(size=16, color="#f1f5f9")
        ),
        barmode="group",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#f1f5f9")
        ),
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    # X축 / Y축 라벨 설정
    fig.update_xaxes(
        title_text="자격증명",
        showgrid=True,
        gridcolor="#334155",
        tickfont=dict(color="#f1f5f9"),
        title_font=dict(color="#f1f5f9")
    )
    
    fig.update_yaxes(
        title_text="구직자 월간 검색량 (회)",
        showgrid=True,
        gridcolor="#334155",
        tickfont=dict(color="#818cf8"),
        title_font=dict(color="#818cf8"),
        secondary_y=False
    )
    
    fig.update_yaxes(
        title_text="실제 공고 등장수 (건)",
        showgrid=False,
        tickfont=dict(color="#fb7185"),
        title_font=dict(color="#fb7185"),
        secondary_y=True
    )
    
    # Streamlit에 Plotly 차트 렌더링
    st.plotly_chart(fig, use_container_width=True)
    
    # ----------------- 6. 인사팀 대상 비즈니스 제언 출력 -----------------
    st.subheader("💡 인사팀을 위한 비즈니스 제언")
    
    if selected_job == "인사":
        st.info(
            "현재 인사 직무 구직자들은 '컴퓨터활용능력'에 압도적으로 높은 검색량(45,000회)을 보이지만, "
            "실제 공고 우대사항에서는 실무 중심인 'ERP정보관리사'와 전문 자격인 '공인노무사'의 수요가 훨씬 큽니다. "
            "인사팀에서는 유능한 실무 인재를 조기에 확보하기 위해 채용 공고에 구직자들에게 친숙한 키워드를 의도적으로 결합 배치하고, "
            "자사 우대 조건의 실무적 필요성을 명확히 공지하여 직무 지원 허들을 낮출 것을 제안합니다."
        )
    elif selected_job == "회계":
        st.info(
            "회계 부서 채용 시 구직자들은 주로 범용 사무 자격인 '컴퓨터활용능력' 위주로 준비하는 경향이 강하나, "
            "실제 채용 공고에서는 '전산세무(8건)', '재경관리사(7건)' 등의 직무 밀착형 세무회계 자격 비중이 매우 높습니다. "
            "따라서 공고 우대사항에 범용 IT 역량과 전문 자격 간의 적정 조화를 가이드하고, 신입 채용 시 사내 실무 OJT 로드맵을 선제 공시함으로써 "
            "준비된 인재들의 유입을 적극 유도해야 합니다."
        )
    elif selected_job == "감사":
        st.success(
            "현재 감사 직무 구직자들은 '컴퓨터활용능력'을 많이 검색하지만, 실제 공고에서는 'CISA/CIA'의 수요가 압도적입니다. "
            "양질의 전문 감사 인력을 유입시키려면 공고 우대사항 태그에 구직자 검색 키워드를 의도적으로 배치하여 검색 엔진 노출율을 극대화하십시오. "
            "동시에 전문 자격 미취득자라 하더라도 관련 유관 전공이나 직무 적합성을 갖춘 지원자에게 입사 후 취득 지원책을 제시하는 차별화된 "
            "채용 마케팅이 효과적일 수 있습니다."
        )
    elif selected_job == "데이터분석":
        st.info(
            "데이터분석 구직자들은 '정보처리기사(20,000회)' 등 기사 자격 취득에 쏠려 있으나, 실제 기업 공고는 데이터 처리와 직접적 연관이 높은 "
            "'SQLD(12건)' 및 'ADsP(9건)'를 우대하는 경향이 뚜렷합니다. 인사담당자는 채용 정보 제공 시 실실적인 데이터 핸들링(SQL 쿼리 작성 등) 역량에 "
            "우대 가중치가 부여됨을 상세히 안내해 줄 필요가 있습니다."
        )


# ----------------- 7. 정적 리포트 실시간 동기화 및 다운로드 제공 -----------------
# Plotly 피규어의 HTML 문자열 획득
fig_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

# 정적 리포트 저장 로직 트리거
generate_static_report(selected_job, user_certs, match_rate, missing_certs, fig_html)

# 사이드바 다운로드 버튼 데이터 준비
report_file_path = "saramin/report/mismatch_report.html"
if os.path.exists(report_file_path):
    with open(report_file_path, "r", encoding="utf-8") as f:
        html_bytes = f.read().encode("utf-8")
        
    st.sidebar.download_button(
        label="HTML 정적 보고서 다운로드",
        data=html_bytes,
        file_name=f"mismatch_report_{selected_job}.html",
        mime="text/html",
        help="현재 분석 필터가 반영된 고품질 오프라인 HTML 보고서를 다운로드합니다."
    )
