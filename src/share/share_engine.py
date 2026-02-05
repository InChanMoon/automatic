"""
블로그 공유 엔진

네이버 블로그 글을 여러 계정으로 공유(스크랩)합니다.
모바일 버전(m.blog.naver.com)으로 접근합니다.
"""

import time
import random
import threading
import re
from typing import Callable, List, Dict, Optional, Tuple
from datetime import datetime

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from playwright_stealth import stealth_sync


class ShareEngine:
    """블로그 공유 엔진 (모바일 버전)"""

    # 모바일 셀렉터 상수
    SELECTORS = {
        # 로그인 (모바일)
        "id_input": "#id",
        "pw_input": "#pw",
        "login_button": ".btn_login, #log\\.login, button[type='submit']",

        # 모바일 블로그 글 페이지
        "hamburger_button": "button._btn_tools",  # 햄버거 메뉴 버튼
        "tools_layer": "#_tools_layer",  # 메뉴 레이어
        "share_button": "a.naver-splugin",  # 공유하기 버튼
        "blog_share_button": "a._spi_blog, a[data-button='blog']",  # 블로그 공유 버튼

        # 스크랩 폼 페이지
        "scrap_submit": "a.btn_ok",  # 등록 버튼

        # 완료 확인 오버레이
        "confirm_ok": "#_confirmLayerOk, a.btn_50.green",  # 확인 버튼
        "confirm_cancel": "#_confirmLayercancel",  # 취소 버튼

        # 신고하기
        "report_button": "a._report",  # 신고하기 버튼
        "report_reason_illegal": "#3",  # 불법정보 (id="3")
        "report_reason_spam": "#1",  # 스팸홍보 (id="1")
        "report_submit": "a.btn_submit",  # 신고하기 최종 버튼
    }

    URLS = {
        "login": "https://nid.naver.com/nidlogin.login?url=https%3A%2F%2Fm.blog.naver.com",
        "login_mobile": "https://nid.naver.com/nidlogin.login?svctype=262144",
        "blog_home": "https://m.blog.naver.com",
    }

    # 태블릿 viewport 고정 (iPad)
    TABLET_VIEWPORT = {"width": 768, "height": 1024}

    # 태블릿 User-Agent (iPad Safari)
    TABLET_USER_AGENT = "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"

    def __init__(self, headless: bool = False):
        """
        Args:
            headless: 브라우저를 백그라운드에서 실행할지 여부
        """
        self.headless = headless

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        self.is_logged_in = False
        self.is_running = False
        self.stop_requested = False

        # 현재 상태
        self.current_account: Optional[str] = None
        self.current_account_index = 0
        self.current_post_index = 0

        # 통계
        self.stats = {
            'total_accounts': 0,
            'completed_accounts': 0,
            'total_posts': 0,
            'shared_posts': 0,
            'skipped_posts': 0,
            'failed_posts': 0,
        }

        # 콜백
        self.log_callback: Optional[Callable[[str], None]] = None
        self.progress_callback: Optional[Callable[[Dict], None]] = None
        self.ip_change_callback: Optional[Callable[[], bool]] = None

    def set_log_callback(self, callback: Callable[[str], None]):
        """로그 콜백 설정"""
        self.log_callback = callback

    def set_progress_callback(self, callback: Callable[[Dict], None]):
        """진행 상황 콜백 설정"""
        self.progress_callback = callback

    def set_ip_change_callback(self, callback: Callable[[], bool]):
        """IP 변경 콜백 설정"""
        self.ip_change_callback = callback

    def log(self, message: str):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        if self.log_callback:
            self.log_callback(message)

    def _update_progress(self):
        """진행 상황 업데이트"""
        if self.progress_callback:
            self.progress_callback({
                'current_account': self.current_account,
                'current_account_index': self.current_account_index,
                'current_post_index': self.current_post_index,
                **self.stats
            })

    def _random_delay(self, min_sec: float = 0.5, max_sec: float = 1.5):
        """랜덤 지연"""
        if self.stop_requested:
            return
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def _random_wait(self, interval: Tuple[int, int]):
        """랜덤 대기 (초 단위)"""
        if self.stop_requested:
            return
        min_sec, max_sec = interval
        wait_time = random.randint(min_sec, max_sec)
        self.log(f"대기 중... ({wait_time}초)")

        for _ in range(wait_time):
            if self.stop_requested:
                return
            time.sleep(1)

    def _to_mobile_url(self, url: str) -> str:
        """PC URL을 모바일 URL로 변환"""
        # blog.naver.com -> m.blog.naver.com
        if "m.blog.naver.com" in url:
            return url
        return re.sub(r'(https?://)blog\.naver\.com', r'\1m.blog.naver.com', url)

    def _click_with_offset(self, element, max_offset: int = 5):
        """요소 클릭 (랜덤 오프셋 적용)"""
        try:
            box = element.bounding_box()
            if box:
                # 요소 중심에서 랜덤 오프셋
                center_x = box['x'] + box['width'] / 2
                center_y = box['y'] + box['height'] / 2

                offset_x = random.randint(-max_offset, max_offset)
                offset_y = random.randint(-max_offset, max_offset)

                self.page.mouse.click(center_x + offset_x, center_y + offset_y)
            else:
                element.click()
        except:
            element.click()

    def start_browser(self):
        """브라우저 시작 (태블릿 설정)"""
        self.log("브라우저 시작 중 (태블릿 모드)...")

        self.playwright = sync_playwright().start()

        # 태블릿 고정 viewport
        viewport = self.TABLET_VIEWPORT
        user_agent = self.TABLET_USER_AGENT

        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-dev-shm-usage",
                "--disable-browser-side-navigation",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-extensions",
                "--lang=ko-KR",
            ]
        )

        self.context = self.browser.new_context(
            viewport=viewport,
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            user_agent=user_agent,
            is_mobile=True,
            has_touch=True,
        )

        self.page = self.context.new_page()

        # playwright-stealth 적용
        stealth_sync(self.page)

        self.log(f"브라우저 시작 완료 (viewport: {viewport['width']}x{viewport['height']})")

    def close_browser(self):
        """브라우저 종료"""
        try:
            if self.page:
                try:
                    self.page.close()
                except:
                    pass
                self.page = None

            if self.context:
                try:
                    self.context.close()
                except:
                    pass
                self.context = None

            if self.browser:
                try:
                    self.browser.close()
                except:
                    pass
                self.browser = None

            if self.playwright:
                try:
                    self.playwright.stop()
                except:
                    pass
                self.playwright = None

            self.is_logged_in = False
            self.log("브라우저 종료")
        except Exception as e:
            self.log(f"브라우저 종료 중 오류 (무시됨): {e}")

    def login(self, account_id: str, password: str) -> Dict:
        """
        네이버 모바일 로그인

        Args:
            account_id: 네이버 아이디
            password: 네이버 비밀번호

        Returns:
            dict: {success: bool, reason: str}
        """
        self.log(f"로그인 시도: {account_id}")
        self.current_account = account_id
        self._update_progress()

        try:
            self.page.goto(self.URLS["login"])
            self._random_delay(2, 4)

            # 아이디 입력
            self.page.wait_for_selector(self.SELECTORS["id_input"], timeout=20000)

            id_input = self.page.query_selector(self.SELECTORS["id_input"])
            self._click_with_offset(id_input)
            self._random_delay(0.3, 0.5)

            # 타이핑 (모바일에서는 클립보드보다 타이핑이 더 자연스러움)
            self.page.keyboard.type(account_id, delay=random.randint(50, 100))
            self._random_delay(0.3, 0.5)
            self.log("아이디 입력 완료")

            # 비밀번호 입력
            pw_input = self.page.query_selector(self.SELECTORS["pw_input"])
            self._click_with_offset(pw_input)
            self._random_delay(0.3, 0.5)

            self.page.keyboard.type(password, delay=random.randint(50, 100))
            self._random_delay(0.3, 0.5)
            self.log("비밀번호 입력 완료")

            # 로그인 버튼 클릭
            self._random_delay(0.5, 1.0)
            login_btn = self.page.query_selector(self.SELECTORS["login_button"])
            if login_btn:
                self._click_with_offset(login_btn)
            else:
                # 대체 방법: Enter 키
                self.page.keyboard.press("Enter")
            self.log("로그인 버튼 클릭")

            self._random_delay(3, 5)

            # 로그인 성공 확인
            try:
                self.page.wait_for_url(
                    lambda url: "nid.naver.com" not in url,
                    timeout=15000
                )
                self.is_logged_in = True
                self.log(f"로그인 성공: {account_id}")
                return {'success': True, 'reason': ''}

            except:
                current_url = self.page.url

                # 캡차 감지
                if self._detect_captcha():
                    self.log("캡차 감지됨 - 이 계정 건너뜀")
                    return {'success': False, 'reason': '캡차 필요'}

                # 보호조치 감지
                if self._check_protection():
                    self.log("계정 보호조치 감지됨")
                    return {'success': False, 'reason': '계정 보호조치'}

                self.log(f"로그인 실패 - URL: {current_url}")
                return {'success': False, 'reason': '로그인 실패'}

        except Exception as e:
            self.log(f"로그인 오류: {e}")
            return {'success': False, 'reason': str(e)}

    def _detect_captcha(self) -> bool:
        """캡차 감지"""
        try:
            captcha_selectors = [
                "#captcha",
                "input[name='captcha']",
                "#captchaimg",
                ".captcha_wrap",
            ]

            for selector in captcha_selectors:
                if self.page.query_selector(selector):
                    return True

            return False
        except:
            return False

    def _check_protection(self) -> bool:
        """계정 보호조치 감지"""
        try:
            current_url = self.page.url
            protection_keywords = ['보호조치', '스팸', '제한', 'restrict', 'protect']

            if any(kw in current_url for kw in protection_keywords):
                return True

            page_text = self.page.inner_text("body") if self.page.query_selector("body") else ""
            if any(kw in page_text for kw in ['보호조치', '스팸성 홍보활동', '계정 보호']):
                return True

            return False
        except:
            return False

    def share_post(self, post_url: str) -> Dict:
        """
        블로그 글 공유 (스크랩) - 모바일 버전

        프로세스:
        1. 모바일 URL로 이동
        2. 햄버거 버튼 클릭 (button._btn_tools)
        3. 공유하기 클릭 (a.naver-splugin)
        4. 블로그 클릭 (a._spi_blog)
        5. 등록 클릭 (a.btn_ok)
        6. 확인 클릭 (#_confirmLayerOk)

        Args:
            post_url: 공유할 글 URL

        Returns:
            dict: {success: bool, reason: str, skipped: bool}
        """
        if self.stop_requested:
            return {'success': False, 'reason': '중지됨', 'skipped': False}

        if not self.is_logged_in:
            return {'success': False, 'reason': '로그인 필요', 'skipped': False}

        # 모바일 URL로 변환
        mobile_url = self._to_mobile_url(post_url)
        self.log(f"공유 시도: {mobile_url[:50]}...")

        try:
            # 1. 글 페이지로 이동
            self.page.goto(mobile_url)
            self._random_delay(2, 4)

            # 페이지 로드 대기
            self.page.wait_for_load_state("networkidle", timeout=15000)

            # 2. 햄버거 버튼 확인 (없으면 skip)
            hamburger = self.page.query_selector(self.SELECTORS["hamburger_button"])
            if not hamburger:
                self.log(f"공유 버튼 없음 - 건너뜀: {mobile_url[:40]}...")
                self.stats['skipped_posts'] += 1
                self._update_progress()
                return {'success': True, 'reason': 'skipped', 'skipped': True}

            # 햄버거 버튼 클릭
            self._click_with_offset(hamburger)
            self.log("햄버거 버튼 클릭")
            self._random_delay(0.8, 1.5)

            # 3. 메뉴 레이어 표시 대기
            tools_layer = self.page.query_selector(self.SELECTORS["tools_layer"])
            if tools_layer:
                # display 확인
                display = tools_layer.evaluate("el => getComputedStyle(el).display")
                if display == "none":
                    self.log("메뉴가 열리지 않음")
                    self.stats['failed_posts'] += 1
                    self._update_progress()
                    return {'success': False, 'reason': '메뉴 열기 실패', 'skipped': False}

            # 4. 공유하기 버튼 클릭
            try:
                share_btn = self.page.wait_for_selector(
                    self.SELECTORS["share_button"],
                    timeout=5000
                )
            except:
                share_btn = None

            if not share_btn or not share_btn.is_visible():
                self.log(f"공유하기 버튼 없음 - 건너뜀: {mobile_url[:40]}...")
                self.stats['skipped_posts'] += 1
                self._update_progress()
                return {'success': True, 'reason': 'skipped', 'skipped': True}

            self._click_with_offset(share_btn)
            self.log("공유하기 버튼 클릭")
            self._random_delay(1, 2)

            # 5. 블로그 공유 버튼 클릭 (오버레이에서)
            try:
                blog_btn = self.page.wait_for_selector(
                    self.SELECTORS["blog_share_button"],
                    timeout=5000
                )
            except:
                blog_btn = None

            if not blog_btn:
                self.stats['failed_posts'] += 1
                self._update_progress()
                return {'success': False, 'reason': '블로그 버튼 없음', 'skipped': False}

            self._click_with_offset(blog_btn)
            self.log("블로그 공유 버튼 클릭")
            self._random_delay(2, 4)

            # 6. 스크랩 폼 페이지 대기 (BlogScrapForm.naver)
            try:
                self.page.wait_for_url(
                    lambda url: "BlogScrapForm" in url,
                    timeout=10000
                )
            except:
                self.log("스크랩 폼 페이지 이동 실패")
                self.stats['failed_posts'] += 1
                self._update_progress()
                return {'success': False, 'reason': '스크랩 폼 이동 실패', 'skipped': False}

            self._random_delay(1, 2)

            # 7. 등록 버튼 클릭
            try:
                submit_btn = self.page.wait_for_selector(
                    self.SELECTORS["scrap_submit"],
                    timeout=10000
                )
            except:
                submit_btn = None

            if not submit_btn:
                self.stats['failed_posts'] += 1
                self._update_progress()
                return {'success': False, 'reason': '등록 버튼 없음', 'skipped': False}

            self._click_with_offset(submit_btn)
            self.log("등록 버튼 클릭")
            self._random_delay(2, 4)

            # 8. 완료 확인 오버레이 대기 및 확인 클릭
            try:
                confirm_btn = self.page.wait_for_selector(
                    self.SELECTORS["confirm_ok"],
                    timeout=10000
                )
                if confirm_btn:
                    self._click_with_offset(confirm_btn)
                    self.log("확인 버튼 클릭")
                    self._random_delay(1, 2)
            except:
                # 확인 버튼이 없어도 등록은 완료됐을 수 있음
                self.log("확인 오버레이 없음 (무시)")

            # 성공
            self.stats['shared_posts'] += 1
            self._update_progress()
            self.log(f"공유 완료: {mobile_url[:40]}...")
            return {'success': True, 'reason': '', 'skipped': False}

        except Exception as e:
            self.stats['failed_posts'] += 1
            self._update_progress()
            self.log(f"공유 오류: {e}")
            return {'success': False, 'reason': str(e), 'skipped': False}

    def report_post(self, post_url: str, reason: str = "illegal") -> Dict:
        """
        블로그 글 신고하기 - 모바일 버전

        프로세스:
        1. 모바일 URL로 이동
        2. 햄버거 버튼 클릭 (button._btn_tools)
        3. 신고하기 클릭 (a._report) → 팝업창 열림
        4. 신고 사유 선택 (id="3" 불법정보 또는 id="1" 스팸홍보)
        5. 신고하기 최종 버튼 클릭 (a.btn_submit)
        6. 이미 신고된 경우 alert 처리

        Args:
            post_url: 신고할 글 URL
            reason: "illegal" (불법정보) 또는 "spam" (스팸홍보)

        Returns:
            dict: {success: bool, reason: str, already_reported: bool}
        """
        if self.stop_requested:
            return {'success': False, 'reason': '중지됨', 'already_reported': False}

        if not self.is_logged_in:
            return {'success': False, 'reason': '로그인 필요', 'already_reported': False}

        # 모바일 URL로 변환
        mobile_url = self._to_mobile_url(post_url)
        self.log(f"신고 시도: {mobile_url[:50]}...")

        try:
            # 1. 글 페이지로 이동
            self.page.goto(mobile_url)
            self._random_delay(2, 4)

            # 페이지 로드 대기
            self.page.wait_for_load_state("networkidle", timeout=15000)

            # 2. 햄버거 버튼 확인 (없으면 skip)
            hamburger = self.page.query_selector(self.SELECTORS["hamburger_button"])
            if not hamburger:
                self.log(f"햄버거 버튼 없음 - 건너뜀: {mobile_url[:40]}...")
                return {'success': False, 'reason': '햄버거 버튼 없음', 'already_reported': False}

            # 햄버거 버튼 클릭
            self._click_with_offset(hamburger)
            self.log("햄버거 버튼 클릭")
            self._random_delay(0.8, 1.5)

            # 3. 메뉴 레이어 표시 대기
            tools_layer = self.page.query_selector(self.SELECTORS["tools_layer"])
            if tools_layer:
                display = tools_layer.evaluate("el => getComputedStyle(el).display")
                if display == "none":
                    self.log("메뉴가 열리지 않음")
                    return {'success': False, 'reason': '메뉴 열기 실패', 'already_reported': False}

            # 4. 신고하기 버튼 클릭
            try:
                report_btn = self.page.wait_for_selector(
                    self.SELECTORS["report_button"],
                    timeout=5000
                )
            except:
                report_btn = None

            if not report_btn or not report_btn.is_visible():
                self.log(f"신고하기 버튼 없음 - 건너뜀: {mobile_url[:40]}...")
                return {'success': False, 'reason': '신고하기 버튼 없음', 'already_reported': False}

            # alert 다이얼로그 핸들러 설정 (이미 신고된 경우)
            already_reported = False
            alert_message = ""

            def handle_dialog(dialog):
                nonlocal already_reported, alert_message
                alert_message = dialog.message
                if "이미" in alert_message or "신고" in alert_message:
                    already_reported = True
                dialog.accept()

            self.page.on("dialog", handle_dialog)

            # 신고하기 버튼 클릭 → 팝업창 또는 alert
            self._click_with_offset(report_btn)
            self.log("신고하기 버튼 클릭")
            self._random_delay(1.5, 2.5)

            # 이미 신고된 경우 처리
            if already_reported:
                self.log(f"이미 신고된 글: {alert_message}")
                self.page.remove_listener("dialog", handle_dialog)
                return {'success': True, 'reason': '이미 신고됨', 'already_reported': True}

            # 5. 팝업창 대기 및 처리
            # 팝업창이 새 페이지로 열리는 경우
            popup_page = None
            try:
                # 팝업창 대기 (최대 5초)
                with self.page.expect_popup(timeout=5000) as popup_info:
                    pass
                popup_page = popup_info.value
                self.log("신고 팝업창 열림")
                self._random_delay(1, 2)
            except:
                # 팝업이 없으면 현재 페이지에서 처리
                popup_page = self.page
                self.log("팝업창이 현재 페이지에서 열림")

            # 6. 신고 사유 선택
            reason_selector = self.SELECTORS["report_reason_illegal"] if reason == "illegal" else self.SELECTORS["report_reason_spam"]
            reason_text = "불법정보" if reason == "illegal" else "스팸홍보"

            try:
                reason_input = popup_page.wait_for_selector(reason_selector, timeout=5000)
                if reason_input:
                    reason_input.click()
                    self.log(f"신고 사유 선택: {reason_text}")
                    self._random_delay(0.5, 1)
            except Exception as e:
                self.log(f"신고 사유 선택 실패: {e}")
                self.page.remove_listener("dialog", handle_dialog)
                if popup_page != self.page:
                    popup_page.close()
                return {'success': False, 'reason': '신고 사유 선택 실패', 'already_reported': False}

            # 7. 신고하기 최종 버튼 클릭
            try:
                submit_btn = popup_page.wait_for_selector(
                    self.SELECTORS["report_submit"],
                    timeout=5000
                )
                if submit_btn:
                    self._random_delay(0.3, 0.7)
                    submit_btn.click()
                    self.log("신고하기 버튼 클릭")
                    self._random_delay(2, 3)
            except Exception as e:
                self.log(f"신고하기 버튼 클릭 실패: {e}")
                self.page.remove_listener("dialog", handle_dialog)
                if popup_page != self.page:
                    popup_page.close()
                return {'success': False, 'reason': '신고 제출 실패', 'already_reported': False}

            # 팝업창 닫기
            if popup_page != self.page:
                try:
                    popup_page.close()
                except:
                    pass

            # 리스너 제거
            self.page.remove_listener("dialog", handle_dialog)

            self.log(f"신고 완료: {mobile_url[:40]}...")
            return {'success': True, 'reason': '', 'already_reported': False}

        except Exception as e:
            self.log(f"신고 오류: {e}")
            return {'success': False, 'reason': str(e), 'already_reported': False}

    def request_stop(self):
        """작업 중지 요청"""
        self.stop_requested = True
        self.is_running = False
        self.log("중지 요청됨")

    def start_sharing(
        self,
        accounts: List[Dict],
        post_urls: List[str],
        post_interval: Tuple[int, int] = (5, 15),
        account_interval: Tuple[int, int] = (30, 60),
        ip_change_enabled: bool = False
    ):
        """
        공유 작업 시작 (별도 스레드에서 실행)

        Args:
            accounts: [{'id': str, 'pw': str}, ...]
            post_urls: ['https://blog.naver.com/...', ...]
            post_interval: (min_sec, max_sec) 글 간 대기 시간
            account_interval: (min_sec, max_sec) 계정 간 대기 시간
            ip_change_enabled: IP 변경 활성화 여부
        """
        self.is_running = True
        self.stop_requested = False

        # 통계 초기화
        self.stats = {
            'total_accounts': len(accounts),
            'completed_accounts': 0,
            'total_posts': len(post_urls),
            'shared_posts': 0,
            'skipped_posts': 0,
            'failed_posts': 0,
        }
        self._update_progress()

        thread = threading.Thread(
            target=self._sharing_loop,
            args=(accounts, post_urls, post_interval, account_interval, ip_change_enabled),
            daemon=True
        )
        thread.start()

    def _sharing_loop(
        self,
        accounts: List[Dict],
        post_urls: List[str],
        post_interval: Tuple[int, int],
        account_interval: Tuple[int, int],
        ip_change_enabled: bool
    ):
        """공유 작업 루프"""
        try:
            self.start_browser()

            for i, account in enumerate(accounts):
                if self.stop_requested:
                    break

                self.current_account_index = i + 1
                self._update_progress()

                account_id = account.get('id', '')
                password = account.get('pw', '')

                if not account_id or not password:
                    self.log(f"계정 정보 누락: {account}")
                    continue

                # 로그인
                login_result = self.login(account_id, password)

                if not login_result['success']:
                    self.log(f"로그인 실패 ({account_id}): {login_result['reason']}")
                    continue

                # 모든 글 공유
                for j, post_url in enumerate(post_urls):
                    if self.stop_requested:
                        break

                    self.current_post_index = j + 1
                    self._update_progress()

                    result = self.share_post(post_url)

                    if not result['success']:
                        self.log(f"공유 실패: {result['reason']}")

                    # 글 간 대기
                    if j < len(post_urls) - 1:
                        self._random_wait(post_interval)

                # 계정 완료
                self.stats['completed_accounts'] += 1
                self._update_progress()
                self.log(f"계정 완료: {account_id} ({self.current_account_index}/{len(accounts)})")

                # 브라우저 컨텍스트 초기화 (로그아웃 효과)
                self.close_browser()

                # 다음 계정 전 대기
                if i < len(accounts) - 1:
                    # IP 변경
                    if ip_change_enabled and self.ip_change_callback:
                        self.log("IP 변경 중...")
                        try:
                            if self.ip_change_callback():
                                self.log("IP 변경 완료")
                            else:
                                self.log("IP 변경 실패 (계속 진행)")
                        except Exception as e:
                            self.log(f"IP 변경 오류: {e}")

                    # 계정 간 대기
                    self._random_wait(account_interval)

                    # 다음 계정을 위해 브라우저 재시작
                    self.start_browser()

            self.log("=== 공유 작업 완료 ===")
            self.log(f"계정: {self.stats['completed_accounts']}/{self.stats['total_accounts']}")
            self.log(f"공유: {self.stats['shared_posts']}, 건너뜀: {self.stats['skipped_posts']}, 실패: {self.stats['failed_posts']}")

        except Exception as e:
            self.log(f"공유 작업 오류: {e}")

        finally:
            self.close_browser()
            self.is_running = False
            self._update_progress()
