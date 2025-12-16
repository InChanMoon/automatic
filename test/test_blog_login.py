"""
네이버 블로그 로그인 + 글쓰기 테스트기 (Phase 0)

목적:
- 본격 개발 전 네이버 로그인과 글쓰기가 정상 작동하는지 검증
- Playwright + playwright-stealth로 안티봇탐지 우회 검증
- 클립보드 붙여넣기 방식 로그인 검증
- iframe 에디터 조작 검증

실행 방법:
    python test_blog_login.py
"""

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import pyperclip
import time
import random
from datetime import datetime


# ========== 설정 ==========

URLS = {
    "login": "https://nid.naver.com/nidlogin.login?url=https%3A%2F%2Fsection.blog.naver.com%2FBlogHome.naver",
    "blog_write": "https://blog.naver.com/GoBlogWrite.naver"
}

SELECTORS = {
    # 로그인 페이지
    "id_input": "#id",
    "pw_input": "#pw",
    "login_button": "#log\\.login",

    # 글쓰기 페이지
    "main_frame": "#mainFrame",
    "draft_popup_cancel": "button.se-popup-button-cancel",
    "help_panel_close": ".se-help-panel-close-button",
    "title_area": ".se-section-documentTitle",
    "content_area": ".se-section-text",
    "image_upload_button": "button[data-name='image']",  # 이미지 업로드 버튼
    "image_file_input": "input[type='file']",  # 파일 선택 input
    "publish_button": "button[data-click-area='tpb.publish']",
    "publish_confirm": "button[data-testid='seOnePublishBtn']",
}

DELAYS = {
    "page_load": (2, 5),
    "before_click": (0.3, 0.8),
    "after_input": (0.5, 1.5),
    "between_actions": (1, 3),
    "before_publish": (2, 4),
}


# ========== 유틸리티 함수 ==========

def random_delay(delay_type):
    """랜덤 지연"""
    min_sec, max_sec = DELAYS[delay_type]
    delay = random.uniform(min_sec, max_sec)
    print(f"⏳ {delay:.2f}초 대기 중...")
    time.sleep(delay)


def paste_text(page, selector, text):
    """클립보드 복사 후 Ctrl+V로 붙여넣기"""
    pyperclip.copy(text)
    page.click(selector)
    time.sleep(random.uniform(0.3, 0.7))
    page.keyboard.press("Control+v")
    time.sleep(random.uniform(0.5, 1.2))


def create_browser():
    """Playwright + stealth로 브라우저 생성 (안티봇탐지 설정 적용)"""
    print("\n🌐 브라우저 초기화 중...")

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=False,  # 눈으로 확인
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--disable-browser-side-navigation",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-extensions",
            "--lang=ko-KR",
            "--window-size=1920,1080",
        ]
    )

    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="ko-KR",
        timezone_id="Asia/Seoul",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )

    page = context.new_page()

    # playwright-stealth 적용 (봇 탐지 우회)
    stealth_sync(page)

    print("✅ 브라우저 초기화 완료")

    return playwright, browser, context, page


# ========== 메인 테스트 함수 ==========

def test_naver_blog_login():
    """네이버 블로그 로그인 + 글쓰기 테스트"""

    playwright = None
    browser = None

    try:
        # 0. 입력받기
        print("\n" + "="*60)
        print("네이버 블로그 자동화 테스트기 (Phase 0)")
        print("="*60)

        naver_id = input("\n네이버 아이디: ").strip()
        naver_pw = input("네이버 비밀번호: ").strip()

        if not naver_id or not naver_pw:
            print("❌ 아이디 또는 비밀번호가 비어있습니다.")
            return

        # 이미지 업로드 테스트 여부
        test_image = input("\n이미지 업로드 테스트? (y/n, 기본값: n): ").strip().lower()
        image_path = None
        if test_image == 'y':
            image_path = input("이미지 파일 경로 (절대 경로): ").strip()
            if image_path and not image_path.startswith('"'):
                # 경로에 공백이 있을 수 있으므로 검증
                import os
                if not os.path.exists(image_path):
                    print(f"⚠️ 이미지 파일을 찾을 수 없습니다: {image_path}")
                    print("   이미지 없이 진행합니다.")
                    image_path = None
                else:
                    print(f"✅ 이미지 파일 확인: {image_path}")

        # 1. 브라우저 생성
        playwright, browser, context, page = create_browser()

        # 2. 로그인 페이지 접속
        print("\n📄 로그인 페이지 접속 중...")
        page.goto(URLS["login"])
        random_delay("page_load")

        # 3. 로그인
        print("\n🔐 로그인 시도 중...")

        # 아이디 입력
        page.wait_for_selector(SELECTORS["id_input"], timeout=20000)
        paste_text(page, SELECTORS["id_input"], naver_id)
        print("✅ 아이디 입력 완료")

        # 비밀번호 입력
        paste_text(page, SELECTORS["pw_input"], naver_pw)
        print("✅ 비밀번호 입력 완료")

        # 로그인 버튼 클릭
        random_delay("before_click")
        page.click(SELECTORS["login_button"])
        print("✅ 로그인 버튼 클릭")

        # 로그인 성공 확인 (URL 변경 대기)
        print("\n로그인 처리 중...")
        try:
            # nid.naver.com에서 벗어날 때까지 대기 (최대 15초)
            page.wait_for_url(lambda url: "nid.naver.com" not in url, timeout=15000)
            print("✅ 로그인 성공!")
        except:
            # 타임아웃 시 현재 URL 확인
            current_url = page.url
            if "nid.naver.com" in current_url:
                print("❌ 로그인 실패 - 로그인 페이지에 머물러 있습니다.")
                print(f"   현재 URL: {current_url}")
                print("   캡차가 발생했거나 아이디/비밀번호가 틀렸을 수 있습니다.")
                input("\n브라우저를 확인하세요. 계속하려면 Enter...")
                return
            else:
                # URL은 변경됐지만 예상과 다른 경우
                print(f"⚠️ 예상치 못한 URL로 이동: {current_url}")
                print("   계속 진행합니다...")

        random_delay("page_load")

        # 4. 글쓰기 페이지 이동
        print("\n📝 글쓰기 페이지 이동 중...")
        page.goto(URLS["blog_write"])
        random_delay("page_load")

        # 5. iframe 전환
        print("\n🔄 iframe 전환 중...")
        try:
            # iframe이 로드될 때까지 대기
            page.wait_for_selector(SELECTORS["main_frame"], timeout=20000)

            # frame_locator를 사용하여 iframe 내부 접근
            frame = page.frame_locator(SELECTORS["main_frame"])
            print("✅ iframe 전환 완료")
        except Exception as e:
            print(f"❌ iframe 전환 실패: {e}")
            input("\n브라우저를 확인하세요. 계속하려면 Enter...")
            return

        random_delay("between_actions")

        # 6. 팝업/도움말 닫기
        print("\n🗑️ 팝업 닫기 시도 중...")

        # 6-1. 임시 저장 글 팝업 ("작성 중인 글이 있습니다") - 취소 버튼 클릭
        try:
            if frame.locator(SELECTORS["draft_popup_cancel"]).count() > 0:
                frame.locator(SELECTORS["draft_popup_cancel"]).click()
                print("✅ 임시 저장 글 팝업 닫기 (취소 버튼 클릭)")
                random_delay("before_click")
            else:
                print("ℹ️ 임시 저장 글 팝업 없음 (정상)")
        except Exception as e:
            print(f"ℹ️ 임시 저장 글 팝업 처리 스킵: {e}")

        # 6-2. 도움말 패널 닫기
        try:
            if frame.locator(SELECTORS["help_panel_close"]).count() > 0:
                frame.locator(SELECTORS["help_panel_close"]).click()
                print("✅ 도움말 패널 닫기 완료")
                random_delay("before_click")
            else:
                print("ℹ️ 도움말 패널 없음 (정상)")
        except Exception as e:
            print(f"ℹ️ 도움말 패널 닫기 스킵: {e}")

        # 7. 테스트 글 작성
        print("\n✍️ 테스트 글 작성 중...")

        # 제목 입력
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title_text = f"테스트 글 - {current_time}"

        # iframe 내부에서 제목 입력
        title_locator = frame.locator(SELECTORS["title_area"])
        title_locator.click()
        time.sleep(random.uniform(0.3, 0.7))

        pyperclip.copy(title_text)
        page.keyboard.press("Control+v")
        time.sleep(random.uniform(0.5, 1.2))
        print(f"✅ 제목 입력: {title_text}")

        # 본문 입력
        content_text = "이것은 테스트 글입니다."

        content_locator = frame.locator(SELECTORS["content_area"])
        content_locator.click()
        time.sleep(random.uniform(0.3, 0.7))

        pyperclip.copy(content_text)
        page.keyboard.press("Control+v")
        time.sleep(random.uniform(0.5, 1.2))
        print(f"✅ 본문 입력: {content_text}")

        # 7-1. 이미지 업로드 (선택 사항)
        if image_path:
            print("\n🖼️ 이미지 업로드 시도 중...")
            try:
                # 본문 영역에 커서가 있는 상태에서 이미지 버튼 클릭
                # 또는 파일 input에 직접 파일 설정

                # 방법 1: 파일 input에 직접 파일 설정 (더 안정적)
                file_input = frame.locator(SELECTORS["image_file_input"])

                # Playwright의 set_input_files 사용
                file_input.set_input_files(image_path)
                print("✅ 이미지 파일 선택 완료")

                # 업로드 완료 대기
                time.sleep(3)
                print("✅ 이미지 업로드 완료")

            except Exception as e:
                print(f"⚠️ 이미지 업로드 실패: {e}")
                print("   이미지 없이 계속 진행합니다...")

        # 8. 발행
        print("\n📤 발행 시도 중...")
        random_delay("before_publish")

        # 발행 버튼은 iframe 내부에 있음
        try:
            # iframe 내부에서 발행 버튼 클릭
            publish_btn = frame.locator(SELECTORS["publish_button"])
            publish_btn.wait_for(state="visible", timeout=10000)
            publish_btn.click()
            print("✅ 발행 버튼 클릭")
            random_delay("between_actions")
        except Exception as e:
            print(f"❌ 발행 버튼 클릭 실패: {e}")
            input("\n브라우저를 확인하세요. 계속하려면 Enter...")
            return

        # 발행 확인 버튼 클릭 (팝업)
        try:
            # 발행 확인 버튼도 iframe 내부
            confirm_btn = frame.locator(SELECTORS["publish_confirm"])
            confirm_btn.wait_for(state="visible", timeout=10000)
            confirm_btn.click()
            print("✅ 발행 확인 버튼 클릭")
        except Exception as e:
            print(f"❌ 발행 확인 버튼 클릭 실패: {e}")
            input("\n브라우저를 확인하세요. 계속하려면 Enter...")
            return

        # 9. 발행 완료 대기 및 URL 확인
        print("\n📋 발행 완료 대기 중...")
        try:
            # 글쓰기 페이지에서 벗어날 때까지 대기 (발행 완료 후 리다이렉트)
            # GoBlogWrite.naver가 아닌 다른 URL로 변경될 때까지 대기
            page.wait_for_url(lambda url: "GoBlogWrite" not in url, timeout=30000)

            # 추가 안정화 대기
            time.sleep(2)

            published_url = page.url

            print("\n" + "="*60)
            print("✅ 테스트 완료!")
            print("="*60)
            print(f"발행된 글 제목: {title_text}")
            print(f"발행된 URL: {published_url}")

            if "blog.naver.com" in published_url and "/PostView" in published_url:
                print("\n✅ 발행 성공! 글이 정상적으로 발행되었습니다.")
            else:
                print(f"\n⚠️ 예상치 못한 URL 형태: {published_url}")
                print("   브라우저에서 직접 확인하세요.")

        except Exception as e:
            print(f"\n⚠️ URL 변경 대기 타임아웃: {e}")
            print(f"   현재 URL: {page.url}")
            print("   발행은 진행되었을 수 있습니다. 브라우저를 확인하세요.")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 10. 종료 전 대기
        print("\n" + "="*60)
        input("브라우저를 확인하세요. 종료하려면 Enter를 누르세요...")

        if browser:
            print("브라우저 종료 중...")
            browser.close()

        if playwright:
            playwright.stop()

        print("✅ 테스트 종료")


# ========== 실행 ==========

if __name__ == "__main__":
    test_naver_blog_login()
