"""
네이버 블로그 자동 발행 모듈
Playwright + Stealth를 사용하여 네이버 블로그에 글을 발행합니다.

기존 test_blog_login.py 패턴 기반
"""

import time
import re
import random
import json
import os
from typing import Optional, Callable, List, Dict
from datetime import datetime

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from playwright_stealth import stealth_sync
import pyperclip


# 셀렉터 상수
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
    "image_upload_button": "button[data-name='image']",
    "image_file_input": "input[type='file']",
    "publish_button": "button[data-click-area='tpb.publish']",
    "publish_confirm": "button[data-testid='seOnePublishBtn']",
}

URLS = {
    "login": "https://nid.naver.com/nidlogin.login?url=https%3A%2F%2Fsection.blog.naver.com%2FBlogHome.naver",
    "blog_write": "https://blog.naver.com/GoBlogWrite.naver",
    "blog_home": "https://section.blog.naver.com/BlogHome.naver",
}


class NaverBlogPublisher:
    """네이버 블로그 자동 발행 클래스"""

    def __init__(self, headless: bool = False, cookie_path: str = None):
        """
        Args:
            headless: 브라우저를 백그라운드에서 실행할지 여부
            cookie_path: 쿠키 저장/로드 경로
        """
        self.headless = headless
        self.cookie_path = cookie_path or "naver_cookies.json"

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        self.is_logged_in = False
        self.current_blog_id = None
        self.log_callback: Optional[Callable[[str], None]] = None

    def set_log_callback(self, callback: Callable[[str], None]):
        """로그 콜백 설정"""
        self.log_callback = callback

    def log(self, message: str):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        if self.log_callback:
            self.log_callback(message)

    def _random_delay(self, min_sec: float = 0.3, max_sec: float = 1.0):
        """랜덤 지연"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def _paste_text(self, text: str):
        """클립보드 복사 후 Ctrl+V로 붙여넣기"""
        pyperclip.copy(text)
        self._random_delay(0.2, 0.5)
        self.page.keyboard.press("Control+v")
        self._random_delay(0.3, 0.8)

    def start_browser(self):
        """브라우저 시작"""
        self.log("브라우저 시작 중...")

        self.playwright = sync_playwright().start()

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
                "--window-size=1920,1080",
            ]
        )

        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        self.page = self.context.new_page()

        # playwright-stealth 적용
        stealth_sync(self.page)

        self.log("브라우저 시작 완료")

    def close_browser(self):
        """브라우저 종료"""
        if self.browser:
            self.browser.close()
            self.browser = None

        if self.playwright:
            self.playwright.stop()
            self.playwright = None

        self.context = None
        self.page = None
        self.is_logged_in = False
        self.log("브라우저 종료")

    def save_cookies(self):
        """현재 쿠키 저장"""
        if self.context:
            cookies = self.context.cookies()
            with open(self.cookie_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            self.log(f"쿠키 저장 완료: {self.cookie_path}")

    def load_cookies(self) -> bool:
        """저장된 쿠키 로드"""
        if not os.path.exists(self.cookie_path):
            return False

        try:
            with open(self.cookie_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            self.context.add_cookies(cookies)
            self.log("쿠키 로드 완료")
            return True
        except Exception as e:
            self.log(f"쿠키 로드 실패: {e}")
            return False

    def login_with_credentials(self, naver_id: str, naver_pw: str) -> bool:
        """아이디/비밀번호로 로그인

        Args:
            naver_id: 네이버 아이디
            naver_pw: 네이버 비밀번호

        Returns:
            로그인 성공 여부
        """
        self.log("로그인 페이지 접속 중...")
        self.page.goto(URLS["login"])
        self._random_delay(2, 4)

        try:
            # 아이디 입력
            self.page.wait_for_selector(SELECTORS["id_input"], timeout=20000)
            self.page.click(SELECTORS["id_input"])
            self._paste_text(naver_id)
            self.log("아이디 입력 완료")

            # 비밀번호 입력
            self.page.click(SELECTORS["pw_input"])
            self._paste_text(naver_pw)
            self.log("비밀번호 입력 완료")

            # 로그인 버튼 클릭
            self._random_delay(0.3, 0.8)
            self.page.click(SELECTORS["login_button"])
            self.log("로그인 버튼 클릭")

            # 로그인 성공 확인
            try:
                self.page.wait_for_url(
                    lambda url: "nid.naver.com" not in url,
                    timeout=15000
                )
                self.is_logged_in = True
                self.log("로그인 성공!")

                # 쿠키 저장
                self.save_cookies()

                return True

            except:
                current_url = self.page.url
                if "nid.naver.com" in current_url:
                    self.log("로그인 실패 - 캡차 또는 잘못된 인증정보")
                    return False
                else:
                    self.is_logged_in = True
                    self.save_cookies()
                    return True

        except Exception as e:
            self.log(f"로그인 오류: {e}")
            return False

    def login_with_cookies(self) -> bool:
        """저장된 쿠키로 로그인 시도

        Returns:
            로그인 성공 여부
        """
        if not self.load_cookies():
            return False

        self.log("쿠키로 로그인 확인 중...")
        self.page.goto(URLS["blog_home"])
        self._random_delay(2, 3)

        # 로그인 상태 확인 - 블로그 홈에서 내 블로그 접근 가능한지
        try:
            # 로그인되면 글쓰기 버튼이 보임
            self.page.wait_for_selector(
                'a[href*="GoBlogWrite"], button[class*="write"]',
                timeout=5000
            )
            self.is_logged_in = True
            self.log("쿠키 로그인 성공!")
            return True
        except:
            self.log("쿠키 만료 - 재로그인 필요")
            return False

    def wait_for_manual_login(self, timeout: int = 300) -> bool:
        """수동 로그인 대기

        사용자가 브라우저에서 직접 로그인할 때까지 대기합니다.

        Args:
            timeout: 최대 대기 시간 (초)

        Returns:
            로그인 성공 여부
        """
        self.log("로그인 페이지로 이동 중...")
        self.page.goto(URLS["login"])

        self.log(f"수동 로그인을 기다리는 중... (최대 {timeout}초)")
        self.log("브라우저에서 직접 로그인해주세요.")

        start_time = time.time()
        while time.time() - start_time < timeout:
            current_url = self.page.url

            # 로그인 후 리다이렉트 확인
            if "nid.naver.com" not in current_url and "naver.com" in current_url:
                self._random_delay(1, 2)

                # 블로그 홈 접근 확인
                self.page.goto(URLS["blog_home"])
                self._random_delay(2, 3)

                try:
                    self.page.wait_for_selector(
                        'a[href*="GoBlogWrite"], button[class*="write"]',
                        timeout=5000
                    )
                    self.is_logged_in = True
                    self.log("로그인 성공!")
                    self.save_cookies()
                    return True
                except:
                    pass

            time.sleep(1)

        self.log("로그인 시간 초과")
        return False

    def get_blog_id(self) -> Optional[str]:
        """현재 로그인된 계정의 블로그 ID 가져오기"""
        if self.current_blog_id:
            return self.current_blog_id

        try:
            self.page.goto(URLS["blog_home"])
            self._random_delay(2, 3)

            # 내 블로그 링크에서 ID 추출
            my_blog_link = self.page.query_selector('a[href*="blog.naver.com/"]')
            if my_blog_link:
                href = my_blog_link.get_attribute('href')
                # blog.naver.com/blogId 형태에서 추출
                match = re.search(r'blog\.naver\.com/([^/?]+)', href)
                if match:
                    self.current_blog_id = match.group(1)
                    self.log(f"블로그 ID: {self.current_blog_id}")
                    return self.current_blog_id

            return None
        except Exception as e:
            self.log(f"블로그 ID 가져오기 오류: {e}")
            return None

    def publish_post(
        self,
        title: str,
        content: str,
        images: List[str] = None,
        progress_callback: Callable[[str, int], None] = None
    ) -> Dict:
        """블로그 글 발행

        Args:
            title: 글 제목
            content: 글 내용 (이미지 마커 포함 가능: [image01], [image01:03])
            images: 이미지 파일 경로 리스트 (선택)
            progress_callback: 진행 상황 콜백 (메시지, 퍼센트)

        Returns:
            발행 결과 딕셔너리 {success: bool, url: str, error: str}
        """
        if not self.is_logged_in:
            return {'success': False, 'error': '로그인되지 않음', 'url': ''}

        def update_progress(msg: str, pct: int):
            self.log(msg)
            if progress_callback:
                progress_callback(msg, pct)

        try:
            update_progress("글쓰기 페이지로 이동 중...", 5)
            self.page.goto(URLS["blog_write"])
            self._random_delay(3, 5)

            update_progress("에디터 로딩 대기 중...", 10)

            # iframe 전환
            try:
                self.page.wait_for_selector(SELECTORS["main_frame"], timeout=20000)
                frame = self.page.frame_locator(SELECTORS["main_frame"])
                update_progress("에디터 iframe 로드 완료", 15)
            except Exception as e:
                return {'success': False, 'error': f'에디터 로드 실패: {e}', 'url': ''}

            self._random_delay(1, 2)

            # 팝업 닫기
            update_progress("팝업 처리 중...", 20)
            self._close_popups(frame)

            # 제목 입력
            update_progress("제목 입력 중...", 30)
            try:
                title_locator = frame.locator(SELECTORS["title_area"])
                title_locator.click()
                self._random_delay(0.3, 0.7)
                self._paste_text(title)
                update_progress(f"제목 입력 완료: {title[:30]}...", 35)
            except Exception as e:
                return {'success': False, 'error': f'제목 입력 실패: {e}', 'url': ''}

            # 본문으로 이동
            self._random_delay(0.5, 1)

            # 이미지 마커 처리
            processed_content = content
            if images:
                update_progress("이미지 업로드 중...", 40)
                processed_content = self._upload_images_at_markers(
                    frame, content, images, update_progress
                )
            else:
                # 이미지 없으면 마커 제거
                processed_content = self._remove_image_markers(content)

            # 본문 입력
            update_progress("본문 입력 중...", 60)
            try:
                content_locator = frame.locator(SELECTORS["content_area"])
                content_locator.click()
                self._random_delay(0.3, 0.7)

                # 긴 텍스트는 청크로 나누어 입력
                self._input_long_text(processed_content)
                update_progress("본문 입력 완료", 70)
            except Exception as e:
                return {'success': False, 'error': f'본문 입력 실패: {e}', 'url': ''}

            self._random_delay(2, 4)

            # 발행 버튼 클릭
            update_progress("발행 버튼 클릭 중...", 80)
            try:
                publish_btn = frame.locator(SELECTORS["publish_button"])
                publish_btn.wait_for(state="visible", timeout=10000)
                self._random_delay(1, 2)  # 버튼 클릭 전 대기
                publish_btn.click()
                update_progress("발행 버튼 클릭 완료", 85)
            except Exception as e:
                return {'success': False, 'error': f'발행 버튼 클릭 실패: {e}', 'url': ''}

            self._random_delay(3, 5)  # 발행 팝업 로딩 대기 (기존 1-2초 -> 3-5초)

            # 발행 확인 버튼 클릭
            update_progress("발행 확인 중...", 90)
            try:
                confirm_btn = frame.locator(SELECTORS["publish_confirm"])
                confirm_btn.wait_for(state="visible", timeout=15000)  # 타임아웃 증가
                self._random_delay(1, 2)  # 확인 버튼 클릭 전 대기
                confirm_btn.click()
                update_progress("발행 확인 버튼 클릭", 95)
            except Exception as e:
                return {'success': False, 'error': f'발행 확인 실패: {e}', 'url': ''}

            # 발행 완료 대기
            update_progress("발행 완료 대기 중...", 98)
            try:
                # URL 변경 대기 (타임아웃 60초로 증가)
                self.page.wait_for_url(
                    lambda url: "GoBlogWrite" not in url,
                    timeout=60000
                )
                self._random_delay(3, 5)  # URL 변경 후 추가 대기 (기존 1-2초 -> 3-5초)

                published_url = self.page.url

                if "blog.naver.com" in published_url:
                    update_progress("발행 완료!", 100)
                    return {
                        'success': True,
                        'url': published_url,
                        'error': ''
                    }
                else:
                    return {
                        'success': True,
                        'url': published_url,
                        'error': '예상과 다른 URL'
                    }

            except Exception as e:
                return {
                    'success': False,
                    'error': f'발행 완료 확인 실패: {e}',
                    'url': ''
                }

        except Exception as e:
            self.log(f"발행 오류: {e}")
            return {'success': False, 'error': str(e), 'url': ''}

    def _close_popups(self, frame):
        """팝업 닫기"""
        # 임시 저장 글 팝업
        try:
            if frame.locator(SELECTORS["draft_popup_cancel"]).count() > 0:
                frame.locator(SELECTORS["draft_popup_cancel"]).click()
                self.log("임시 저장 글 팝업 닫기")
                self._random_delay(0.3, 0.7)
        except:
            pass

        # 도움말 패널
        try:
            if frame.locator(SELECTORS["help_panel_close"]).count() > 0:
                frame.locator(SELECTORS["help_panel_close"]).click()
                self.log("도움말 패널 닫기")
                self._random_delay(0.3, 0.7)
        except:
            pass

    def _input_long_text(self, text: str):
        """긴 텍스트 입력 (청크 단위)"""
        # 줄바꿈 기준으로 분할하여 입력
        lines = text.split('\n')

        for i, line in enumerate(lines):
            if line.strip():
                pyperclip.copy(line)
                self._random_delay(0.1, 0.3)
                self.page.keyboard.press("Control+v")
                self._random_delay(0.1, 0.3)

            if i < len(lines) - 1:
                self.page.keyboard.press("Enter")
                self._random_delay(0.05, 0.15)

    def _upload_images_at_markers(
        self,
        frame,
        content: str,
        images: List[str],
        update_progress
    ) -> str:
        """이미지 마커 위치에 이미지 업로드

        Args:
            frame: iframe frame_locator
            content: 원본 컨텐츠
            images: 이미지 파일 경로 리스트
            update_progress: 진행률 콜백

        Returns:
            이미지 마커가 제거된 컨텐츠
        """
        # 이미지 마커 패턴: [image01], [image01:05]
        marker_pattern = r'\[image(\d+)(?::(\d+))?\]'

        # 마커 정보 수집
        markers = []
        for match in re.finditer(marker_pattern, content):
            start_num = int(match.group(1))
            end_num = int(match.group(2)) if match.group(2) else start_num
            markers.append({
                'full_match': match.group(0),
                'start': start_num,
                'end': end_num
            })

        if not markers:
            return content

        self.log(f"이미지 마커 {len(markers)}개 발견")

        # TODO: 실제 이미지 업로드 구현
        # 현재는 마커를 제거하고 [이미지 N] 텍스트로 대체
        result = content
        for marker in markers:
            if marker['start'] <= len(images):
                if marker['start'] == marker['end']:
                    replacement = f"\n\n[이미지 {marker['start']}번]\n\n"
                else:
                    replacement = f"\n\n[이미지 {marker['start']}~{marker['end']}번]\n\n"
            else:
                replacement = ""
            result = result.replace(marker['full_match'], replacement)

        # 실제 이미지 업로드 시도
        for i, img_path in enumerate(images[:5], 1):  # 최대 5개
            if os.path.exists(img_path):
                try:
                    update_progress(f"이미지 {i} 업로드 중...", 40 + i * 3)
                    file_input = frame.locator(SELECTORS["image_file_input"])
                    file_input.set_input_files(img_path)
                    self._random_delay(2, 3)
                    self.log(f"이미지 {i} 업로드 완료: {os.path.basename(img_path)}")
                except Exception as e:
                    self.log(f"이미지 {i} 업로드 실패: {e}")

        return result

    def _remove_image_markers(self, content: str) -> str:
        """이미지 마커 제거"""
        pattern = r'\[image\d+(?::\d+)?\]'
        return re.sub(pattern, '', content)

    def publish_multiple(
        self,
        posts: List[Dict],
        progress_callback: Callable[[int, int, str], None] = None,
        stop_flag: Callable[[], bool] = None
    ) -> List[Dict]:
        """여러 글 연속 발행

        Args:
            posts: 발행할 글 리스트 [{'title': str, 'content': str, 'images': list}, ...]
            progress_callback: 진행 콜백 (현재 번호, 전체 수, 상태 메시지)
            stop_flag: 중지 플래그 함수

        Returns:
            발행 결과 리스트
        """
        results = []
        total = len(posts)

        for i, post in enumerate(posts, 1):
            # 중지 확인
            if stop_flag and stop_flag():
                self.log("발행 중지됨")
                break

            if progress_callback:
                progress_callback(i, total, f"발행 중: {post.get('title', '')[:20]}...")

            result = self.publish_post(
                title=post.get('title', ''),
                content=post.get('content', ''),
                images=post.get('images', [])
            )

            result['title'] = post.get('title', '')
            results.append(result)

            if result['success']:
                self.log(f"[{i}/{total}] 발행 성공: {post.get('title', '')[:30]}")
            else:
                self.log(f"[{i}/{total}] 발행 실패: {result.get('error', '')}")

            # 다음 글 전 대기
            if i < total:
                self._random_delay(5, 10)

        return results
