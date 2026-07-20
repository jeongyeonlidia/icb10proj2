import os
import sys
import urllib.request
import json
import pandas as pd
import time

# 1. 네이버 API 인증 정보 세팅
client_id = "YOUR_CLIENT_ID"       # 발급받은 애플리케이션 Client ID
client_secret = "YOUR_CLIENT_SECRET" # 발급받은 애플리케이션 Client Secret

# 2. 자동화할 타겟 키워드 리스트 (사람인 데이터에서 추출된 스킬셋)
# 기획/전략 직무 마스터 스킬셋을 리스트로 정의하면 코드가 알아서 순회합니다.
target_keywords = ['SQLD', 'Figma', '컴퓨터활용능력', 'GA4', 'CFA']

# 3. 특정 취업 카페로 한정하기 위한 네이버 검색 쿼리 튜닝 (치트키)
# 검색어 뒤에 'site:cafe.naver.com/독취사 URL' 등을 붙이면 해당 카페 글만 필터링됩니다.
# 혹은 가장 대중적인 취업 카페명인 "독취사" 또는 "스펙업"을 키워드와 조합합니다.
def get_naver_cafe_counts(keyword):
    encText = urllib.parse.quote(f"{keyword} 독취사") # 예: "SQLD 독취사"
    url = f"https://openapi.naver.com/v1/search/cafearticle.json?query={encText}&display=100"
    
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)
    
    try:
        response = urllib.request.urlopen(request)
        rescode = response.getcode()
        if rescode == 200:
            response_body = response.read()
            data = json.loads(response_body.decode('utf-8'))
            return data
        else:
            return None
    except Exception as e:
        print(f"Error for {keyword}: {e}")
        return None

# 4. 자동 루프(Loop) 가동 및 데이터 마트 통합
merged_results = []

for kw in target_keywords:
    print(f"🔄 {kw} 관련 취업 카페 데이터 자동 수집 중...")
    api_result = get_naver_cafe_counts(kw)
    
    if api_result and 'items' in api_result:
        # 해당 키워드의 총 검색 결과 개수 (수요-공급 지표의 '공급량'으로 활용)
        total_count = api_result['total'] 
        
        # 상세 게시글 리스트 파싱
        for item in api_result['items']:
            merged_results.append({
                'keyword': kw,
                'total_market_supply': total_count, # 총 게시글 수
                'title': item['title'],             # 게시글 제목
                'description': item['description'], # 게시글 본문 요약
                'cafename': item['cafename'],       # 카페 이름
                'cafeurl': item['cafeurl']          # 카페 주소
            })
    
    # 네이버 API 호출 제한 및 차단 방지를 위해 0.5초씩 쉬어줍니다.
    time.sleep(0.5)

# 5. 최종 데이터프레임 변환 및 안티 그래비티에 CSV 저장
df_cafe_market = pd.DataFrame(merged_results)
df_cafe_market.to_csv("automated_cafe_supply.csv", index=False)
print("✅ 취업 카페 데이터 자동화 수집 완료! 'automated_cafe_supply.csv'로 저장되었습니다.")