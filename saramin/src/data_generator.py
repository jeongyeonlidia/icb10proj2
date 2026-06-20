"""
이 모듈은 사람인 채용 트렌드 분석 및 네이버 검색어 트렌드 시각화를 위해 
실제 데이터의 성격을 띤 고품질 시뮬레이션 데이터를 생성합니다.
대시보드에 사용되는 다양한 통계 기법(IQR 이상치 탐지, 피어슨 상관관계, 왜도/첨도 등)을
성공적으로 시뮬레이션할 수 있도록 통계적 연관성을 부여하여 데이터를 만듭니다.

주요 기능:
- 입력 키워드 기반의 시계열 검색어 트렌드 데이터 생성
- 요일별 패턴 및 이상치(IQR 기반 급증일)가 포함된 일자별 공고 등록 빈도 데이터 생성
- 기술 스택, 복지 카테고리, 연봉, 평점이 포함된 기업 규모별 상세 공고 데이터 생성
- 다변량 상관성을 지닌 산업군 분석용 지표 데이터 생성
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

def generate_trend_data(keywords, start_date, end_date):
    """
    네이버 데이터랩 통합 검색어 트렌드 형식의 일자별 검색량 비율 데이터를 생성합니다.
    트렌드와 요일별 변동, 그리고 약간의 왜곡(왜도/첨도 검증용)을 반영합니다.
    """
    date_range = pd.date_range(start=start_date, end=end_date)
    data = {"period": date_range.strftime("%Y-%m-%d")}
    
    # 각 키워드별로 다른 베이스 트렌드 및 변동을 부여
    for idx, kw in enumerate(keywords):
        # 키워드별 고유 임의 파라미터
        base = random.uniform(20, 60)
        trend = np.linspace(0, random.uniform(-10, 30), len(date_range))
        # 주간 주기성 (주말에 감소)
        weekly = np.sin(date_range.dayofweek * (2 * np.pi / 7)) * random.uniform(5, 12)
        # 무작위 노이즈 (로그정규분포를 사용해 왜도를 가짐)
        noise = np.random.lognormal(mean=1.5, sigma=0.5, size=len(date_range)) * random.uniform(1, 3)
        
        values = base + trend + weekly + noise
        # 0 ~ 100 사이로 스케일링
        values = np.clip(values, 0, None)
        max_val = np.max(values) if np.max(values) > 0 else 1
        data[kw] = (values / max_val * 100).round(2)
        
    return pd.DataFrame(data)

def generate_job_frequency(keywords, start_date, end_date):
    """
    각 키워드별 채용공고 일자별 등록 빈도를 생성합니다.
    주중에는 공고 등록이 활발하고 주말에는 급감하는 명확한 패턴을 지니며,
    통계적 이상치(Outlier) 탐지를 위해 특정 일자에 공고 등록이 급증하는 아웃라이어를 강제 주입합니다.
    """
    date_range = pd.date_range(start=start_date, end=end_date)
    records = []
    
    for kw in keywords:
        # 키워드별 평균 공고 등록 수
        mean_postings = random.randint(15, 40)
        for d in date_range:
            # 주말 패턴 반영 (토/일요일에는 공고가 매우 적음)
            if d.dayofweek in [5, 6]:
                count = int(np.random.poisson(mean_postings * 0.15))
            else:
                count = int(np.random.poisson(mean_postings))
            
            # 아웃라이어 인위적 주입 (약 3%의 확률로 대규모 채용박람회나 수시채용 대방출 상황 연출)
            if random.random() < 0.03:
                count += random.randint(40, 100)
                
            records.append({
                "date": d.strftime("%Y-%m-%d"),
                "keyword": kw,
                "postings": count,
                "day_of_week": d.strftime("%A")
            })
            
    return pd.DataFrame(records)

def generate_job_details(keywords, n_samples=200):
    """
    회사별 상세 공고 데이터 세트를 생성합니다.
    기업규모, 복지 점수, 평점, 연봉 간에 통계적인 선형적/비선형적 상관성이 나타나도록 엮어줍니다.
    """
    company_types = ["대기업", "중견기업", "중소기업", "스타트업"]
    industries = ["IT/웹/통신", "제조/화학", "서비스업", "금융/은행", "교육/미디어"]
    
    # 주요 기술 스택 목록
    tech_pool = ["Python", "Java", "JavaScript", "React", "AWS", "Spring", "Docker", "SQL", "Git", "Kubernetes", "TypeScript", "Node.js"]
    # 복지 카테고리
    welfare_pool = ["유연근무제", "도서구입비지원", "사내스낵바", "자녀학자금", "장기근근속포상", "건강검진지원", "사내대출", "통신비지원", "반차/반반차"]
    
    companies = [f"주식회사 {name}" for name in ["카카오", "네이버", "라인", "쿠팡", "배달의민족", "토스", "직방", "야놀자", "당근마켓", "무신사", "버킷플레이스", "원티드", "사람인", "잡코리아", "원티드랩", "스푼라디오", "채널톡", "두나무", "빗썸", "직방"]]
    
    records = []
    for i in range(n_samples):
        kw = random.choice(keywords)
        comp_type = random.choices(company_types, weights=[0.15, 0.25, 0.40, 0.20])[0]
        industry = random.choice(industries)
        company_name = f"{random.choice(companies)}_{i}"
        
        # 1. 평점 (기업규모에 따른 차별화된 정규분포)
        if comp_type == "대기업":
            rating = round(np.random.normal(3.8, 0.4), 2)
        elif comp_type == "중견기업":
            rating = round(np.random.normal(3.4, 0.5), 2)
        elif comp_type == "스타트업":
            rating = round(np.random.normal(3.5, 0.7), 2)  # 스타트업은 편차가 매우 큼
        else:
            rating = round(np.random.normal(2.8, 0.5), 2)
        rating = np.clip(rating, 1.0, 5.0)
        
        # 2. 연봉 (평점 및 기업규모와 선형 상관성 유지)
        base_salary = {"대기업": 5500, "중견기업": 4200, "스타트업": 4000, "중소기업": 3000}[comp_type]
        # 평점이 높을수록 연봉도 오르는 트렌드 부여
        rating_bonus = (rating - 3.0) * 800
        noise = np.random.normal(0, 400)
        salary = int(base_salary + rating_bonus + noise)
        salary = np.clip(salary, 2600, 12000)
        
        # 3. 복지 개수 및 점수 (기업규모에 따른 불균형 분석 가능하도록 설계)
        # 대기업은 복지가 많고, 중소기업은 상대적으로 적음
        welfare_count_map = {"대기업": (6, 9), "중견기업": (4, 7), "스타트업": (4, 8), "중소기업": (1, 4)}
        min_w, max_w = welfare_count_map[comp_type]
        w_count = random.randint(min_w, max_w)
        active_welfares = random.sample(welfare_pool, w_count)
        
        # 복지 만족도 점수 (1 ~ 100점)
        welfare_score = int(w_count * 10 + rating * 2.5 + random.randint(0, 15))
        welfare_score = np.clip(welfare_score, 10, 100)
        
        # 4. 요구 기술 스택
        n_techs = random.randint(2, 5)
        active_techs = random.sample(tech_pool, n_techs)
        
        # 5. 상세 설명 텍스트
        job_descs = [
            f"우리는 {kw} 기술을 활용하여 세상을 변화시킬 역량 있는 인재를 모십니다.",
            f"국내 선도 {industry} 기업에서 {kw} 전문가로서 새로운 서비스를 주도적으로 설계해 나갈 동료를 찾습니다.",
            f"빠르게 성장하는 {comp_type}에서 {kw} 스택을 고도화하고 대규모 트래픽을 처리하는 과제를 해결할 엔지니어를 모집합니다."
        ]
        job_desc = random.choice(job_descs) + " 요구되는 스택은 다음과 같습니다: " + ", ".join(active_techs) + ". 복지 혜택: " + ", ".join(active_welfares)
        
        records.append({
            "company": company_name,
            "type": comp_type,
            "industry": industry,
            "keyword": kw,
            "rating": rating,
            "salary": salary,
            "welfare_score": welfare_score,
            "welfare_list": active_welfares,
            "welfare_count": w_count,
            "tech_stack": active_techs,
            "description": job_desc,
            "reg_info": "오늘 등록",
            "reg_days_ago": 0,
            "posting_period_days": 14
        })
        
    return pd.DataFrame(records)

def generate_industry_data():
    """
    산업군 분석 페이지를 위해 다변량 상관관계(Multi-variable Correlation)가 뚜렷이 드러나는 데이터를 생성합니다.
    평균 연봉, 평점, 공고 수, 경쟁률, 이직률 변수 간에 명확한 선형 및 비선형 관계가 내재되어 있습니다.
    """
    industries = ["IT/웹/통신", "제조/화학", "서비스업", "금융/은행", "교육/미디어", "의료/제약", "건설/토목", "판매/유통"]
    
    records = []
    for idx, ind in enumerate(industries):
        # 고유한 난수 시드로 상관성을 구현
        # 1. 평점
        rating = round(3.0 + (idx % 3) * 0.3 + random.uniform(-0.2, 0.2), 2)
        # 2. 평균 연봉 (평점과 강력한 양의 상관관계)
        salary = int(3200 + rating * 600 + random.randint(-300, 300))
        # 3. 공고 수 (IT와 금융 등이 높음)
        postings = random.randint(100, 1500) if ind in ["IT/웹/통신", "서비스업"] else random.randint(50, 400)
        # 4. 경쟁률 (연봉과 평점이 높을수록 경쟁률 상승)
        competition_rate = round(5.0 + (salary - 3000) * 0.008 + rating * 1.5 + random.uniform(-2, 2), 1)
        # 5. 이직률 (평점 및 연봉과 강력한 음의 상관관계)
        turnover_rate = round(25.0 - (rating - 2.5) * 5.0 - (salary - 3000) * 0.0025 + random.uniform(-1.5, 1.5), 1)
        turnover_rate = np.clip(turnover_rate, 3.0, 35.0)
        
        records.append({
            "industry": ind,
            "avg_rating": rating,
            "avg_salary": salary,
            "posting_count": postings,
            "competition_rate": competition_rate,
            "turnover_rate": turnover_rate
        })
        
    return pd.DataFrame(records)


def load_and_enrich_scraped_data(keywords, file_path="saramin/data/saramin_jobs.csv"):
    """
    실제 수집된 사람인 채용공고 CSV 파일을 로드하고, 
    대시보드 분석 기법에 필요한 추가적인 통계 지표(평점, 급여, 복지점수, 기술 스택 등)를 
    기업 규모별 패턴에 맞춰 보강하여 DataFrame으로 반환합니다.
    파일이 존재하지 않는 경우 원래의 모의 데이터 생성기로 폴백합니다.
    """
    if not os.path.exists(file_path):
        return generate_job_details(keywords)
        
    try:
        df_real = pd.read_csv(file_path)
        
        enriched_records = []
        industries = ["IT/웹/통신", "제조/화학", "서비스업", "금융/은행", "교육/미디어"]
        tech_pool = ["Python", "Java", "JavaScript", "React", "AWS", "Spring", "Docker", "SQL", "Git", "Kubernetes", "TypeScript", "Node.js"]
        welfare_pool = ["유연근무제", "도서구입비지원", "사내스낵바", "자녀학자금", "장기근근속포상", "건강검진지원", "사내대출", "통신비지원", "반차/반반차"]
        
        for idx, row in df_real.iterrows():
            comp_type = row["company_type"] if pd.notna(row["company_type"]) else "일반기업"
            # 대시보드 내 type 명칭 호환성 (대기업, 중견기업, 중소기업, 스타트업 중 하나로 매핑)
            if "대기업" in str(comp_type):
                mapped_type = "대기업"
            elif "중견" in str(comp_type):
                mapped_type = "중견기업"
            elif "스타트업" in str(comp_type):
                mapped_type = "스타트업"
            else:
                mapped_type = random.choice(["중소기업", "중견기업"])
                
            # 1. 평점 보강
            if mapped_type == "대기업":
                rating = round(np.random.normal(3.8, 0.4), 2)
            elif mapped_type == "중견기업":
                rating = round(np.random.normal(3.4, 0.5), 2)
            elif mapped_type == "스타트업":
                rating = round(np.random.normal(3.5, 0.7), 2)
            else:
                rating = round(np.random.normal(2.8, 0.5), 2)
            rating = np.clip(rating, 1.0, 5.0)
            
            # 2. 연봉 보강
            base_salary = {"대기업": 5500, "중견기업": 4200, "스타트업": 4000, "중소기업": 3000}[mapped_type]
            rating_bonus = (rating - 3.0) * 800
            salary = int(base_salary + rating_bonus + np.random.normal(0, 400))
            salary = np.clip(salary, 2600, 12000)
            
            # 3. 복지 정보 보강
            welfare_count_map = {"대기업": (6, 9), "중견기업": (4, 7), "스타트업": (4, 8), "중소기업": (1, 4)}
            min_w, max_w = welfare_count_map[mapped_type]
            w_count = random.randint(min_w, max_w)
            active_welfares = random.sample(welfare_pool, w_count)
            welfare_score = int(w_count * 10 + rating * 2.5 + random.randint(0, 15))
            welfare_score = np.clip(welfare_score, 10, 100)
            
            # 4. 직무 분야(sectors) 또는 제목에서 스택 매칭
            active_techs = []
            title_lower = str(row["title"]).lower() if pd.notna(row["title"]) else ""
            sectors_str = str(row["sectors"]).lower() if pd.notna(row["sectors"]) else ""
            
            # 실제 스택명과 매핑 검색
            for tech in tech_pool:
                if tech.lower() in title_lower or tech.lower() in sectors_str:
                    active_techs.append(tech)
            
            # 만약 매칭되는 스택이 없으면 임의로 1~3개 부여
            if not active_techs:
                active_techs = random.sample(tech_pool, random.randint(1, 3))
                
            # 대시보드 분석용 키워드 매핑 (검색 키워드들과 엮어줌)
            matched_kw = "Python" # 기본 폴백
            for kw in keywords:
                if kw.lower() in title_lower or kw.lower() in sectors_str:
                    matched_kw = kw
                    break
            
            # 5. 산업군 매핑
            industry = "IT/웹/통신"
            if pd.notna(row["sectors"]):
                sec = row["sectors"]
                if any(x in sec for x in ["의료", "수의", "병원", "간호"]):
                    industry = "의료/제약"
                elif any(x in sec for x in ["사무", "행정", "비서", "정산"]):
                    industry = "서비스업"
                elif any(x in sec for x in ["증권", "금융", "예산", "자금"]):
                    industry = "금융/은행"
                    
            enriched_records.append({
                "company": row["company"],
                "type": mapped_type,
                "industry": industry,
                "keyword": matched_kw,
                "rating": rating,
                "salary": salary,
                "welfare_score": welfare_score,
                "welfare_list": active_welfares,
                "welfare_count": w_count,
                "tech_stack": active_techs,
                "description": f"{row['title']} (직무: {row['sectors']})",
                "reg_info": row.get("reg_info", "알수없음"),
                "reg_days_ago": int(row.get("reg_days_ago", 0)) if pd.notna(row.get("reg_days_ago")) else 0,
                "posting_period_days": row.get("posting_period_days", "알수없음")
            })
            
        return pd.DataFrame(enriched_records)
    except Exception as e:
        print(f"실제 CSV 로드 실패, 모의 데이터로 대체합니다: {e}")
        return generate_job_details(keywords)
