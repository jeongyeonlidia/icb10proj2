"""
이 스크립트는 실행 중인 Streamlit 대시보드(http://localhost:8503)에 백그라운드 Playwright 브라우저로 접속하여
완벽히 렌더링된 실시간 HTML 페이지 소스를 수집하고, project2/report/streamlit_dashboard.html 파일로 내보내는 도구입니다.
"""

import os
import time
from playwright.sync_api import sync_playwright

def dump_dashboard():
    output_dir = "project2/report"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "streamlit_dashboard.html")
    
    print("-> Playwright 백그라운드 브라우저 시동 중...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # 브라우저 뷰포트 크기 넉넉히 설정
        page.set_viewport_size({"width": 1400, "height": 900})
        
        print("-> http://localhost:8503 접속 중...")
        page.goto("http://localhost:8503", timeout=15000)
        
        # Plotly 차트와 Streamlit 컴포넌트 렌더링 완료 대기
        print("-> 대시보드 최종 렌더링 대기 중 (5초)...")
        time.sleep(5.0)
        
        # 첫 번째 탭 진단 실행 트리거 시도
        try:
            # 진단 버튼 찾아 클릭
            diagnose_btn = page.query_selector('button:has-text("나의 다차원 직무 적합도 진단 실행")')
            if diagnose_btn:
                print("-> 다차원 직무 적합도 진단 실행 버튼 클릭...")
                diagnose_btn.click()
                time.sleep(3.0)
        except Exception as btn_err:
            print(f"   (알림) 진단 버튼 클릭 우회: {btn_err}")
            
        html_content = page.content()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print(f"-> 최종 대시보드 HTML 저장 완료: {output_path} (크기: {os.path.getsize(output_path)} bytes)")
        browser.close()

if __name__ == "__main__":
    dump_dashboard()
