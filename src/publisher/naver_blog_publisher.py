"""
네이버 블로그 자동 발행 모듈
Playwright + Stealth를 사용하여 네이버 블로그에 글을 발행합니다.

기존 test_blog_login.py 패턴 기반
"""

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

import time
import re
import random
import json
import os
import sys
from typing import Optional, Callable, List, Dict
from datetime import datetime

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from playwright_stealth import stealth_sync
import pyperclip
import google.generativeai as genai
from PIL import Image
import base64

# 텍스트 이미지 자동 생성
try:
    from src.utils.text_image_generator import (
        generate_auto_images_for_publish,
        cleanup_temp_images
    )
    HAS_TEXT_IMAGE_GENERATOR = True
except ImportError:
    HAS_TEXT_IMAGE_GENERATOR = False

# Windows 클립보드 이미지 지원
if sys.platform == 'win32':
    try:
        import win32clipboard
        from PIL import Image
        import io
        HAS_WIN32_CLIPBOARD = True
    except ImportError:
        HAS_WIN32_CLIPBOARD = False
else:
    HAS_WIN32_CLIPBOARD = False


# 셀렉터 상수
SELECTORS = {
    # 로그인 페이지
    "id_input": "#id",
    "pw_input": "#pw",
    "login_button": "#log\\.login",

    # 캡차
    "captcha_image": "#captchaimg",
    "captcha_input": "#captcha",
    "captcha_question": ".captcha_question, .question_text, #question",

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

    # 발행 옵션
    "comment_checkbox_label": "label[for='publish-option-comment']",
    "comment_checkbox": "#publish-option-comment",

    # 예약발행 옵션
    "schedule_radio_label": "label[for='radio_time2']",
    "date_input": "input.input_date__QmA0s",
    "hour_select": "select.hour_option__J_heO",
    "minute_select": "select.minute_option__Vb3xB",
    "datepicker_next_month": "button.ui-datepicker-next",
    "datepicker_year": ".ui-datepicker-year",
    "datepicker_month": ".ui-datepicker-month",
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
        self.stop_requested = False  # 중지 요청 플래그
        self.auto_generated_images: List[str] = []  # 자동 생성된 임시 이미지

        # 캡차 풀이용 Gemini 초기화
        self.gemini_model = None
        self._init_gemini()

    def _init_gemini(self):
        """캡차 풀이용 Gemini 초기화 (실패해도 발행에 영향 없음)"""
        try:
            config_path = "config.json"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                api_key = config.get('gemini_api', {}).get('api_key')
                if api_key:
                    genai.configure(api_key=api_key)
                    self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        except:
            # Gemini 없어도 발행은 가능, 캡차만 수동 필요
            self.gemini_model = None

    def request_stop(self):
        """중지 요청 - 브라우저 강제 종료"""
        self.stop_requested = True
        self.log("중지 요청됨 - 브라우저 종료 중...")
        try:
            self.close_browser()
        except:
            pass

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
        """텍스트 입력 - 헤드리스 모드에서는 keyboard.type 사용"""
        if self.headless:
            # 헤드리스 모드: 클립보드가 작동하지 않으므로 직접 타이핑
            self.page.keyboard.type(text, delay=10)
        else:
            # 일반 모드: 클립보드 붙여넣기 (더 빠름)
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

    def detect_captcha(self) -> bool:
        """캡차 존재 여부 확인"""
        try:
            # 캡차 입력창 확인 (타임아웃 짧게)
            captcha_input = self.page.locator("input#captcha, input[name='captcha']")
            if captcha_input.count() > 0:
                return True

            # 캡차 이미지 확인
            captcha_img = self.page.locator("#captchaimg, .captcha_image, img[alt*='captcha']")
            if captcha_img.count() > 0:
                return True

            # 캡차 질문 텍스트 확인 (간단한 텍스트 검색)
            try:
                body_text = self.page.locator("body").inner_text(timeout=3000)
                if "정답을 입력해주세요" in body_text or "자동입력 방지" in body_text:
                    return True
            except:
                pass

            return False
        except:
            return False

    def solve_captcha(self, password: str = "") -> bool:
        """AI로 캡차 풀이 시도

        Args:
            password: 비밀번호 (캡차 풀이 후 재입력 필요시)

        Returns:
            bool: 캡차 풀이 성공 여부
        """
        if not self.gemini_model:
            self.log("Gemini 모델이 초기화되지 않아 캡차 풀이 불가")
            return False

        self._captcha_password = password  # 비밀번호 임시 저장

        try:
            self.log("캡차 감지됨 - AI 풀이 시도...")

            # 1. 질문 텍스트 추출 (빨간색 글씨)
            question = ""
            try:
                page_text = self.page.inner_text("body")

                # 다양한 질문 패턴
                patterns = [
                    r'(가장\s*가격이\s*[싼비][^?]*\?)',
                    r'(가장\s*[싼비싸][^?]*가격[^?]*\?)',
                    r'(총[^?]*몇\s*개[^?]*\?)',
                    r'(총[^?]*얼마[^?]*\?)',
                    r'([가-힣]+의\s*가격은[^?]*\?)',
                    r'([가-힣]+\s*제품의[^?]*\?)',
                    r'(한\s*개\s*당\s*가격[^?]*\?)',
                    r'(몇\s*개[^?]*있[^?]*\?)',
                ]

                for pattern in patterns:
                    match = re.search(pattern, page_text)
                    if match:
                        question = match.group(0)
                        break

                # 패턴으로 못 찾으면 "?" 포함된 문장 찾기
                if not question:
                    sentences = re.findall(r'[^.!?\n]*\?', page_text)
                    for s in sentences:
                        if any(kw in s for kw in ['가격', '얼마', '물건', '제품', '몇']):
                            question = s.strip()
                            break

            except Exception as e:
                self.log(f"질문 추출 실패: {e}")

            self.log(f"캡차 질문: {question if question else '(이미지에서 직접 확인)'}")

            # 2. 전체 페이지 스크린샷 (질문+이미지 함께 캡처)
            captcha_path = "captcha_temp.png"
            self.page.screenshot(path=captcha_path)

            # 3. Gemini로 풀이
            img = Image.open(captcha_path)

            # 질문이 추출되었으면 해당 질문 사용, 아니면 이미지에서 찾도록
            if question:
                prompt = f"""이 네이버 로그인 캡차 이미지에서 질문에 답하세요.

질문: {question}

규칙:
- 답만 간결하게 (단위, 설명, 마침표 없이)
- 숫자면 숫자만 (예: 700)
- 텍스트면 텍스트만"""
            else:
                prompt = """이 네이버 로그인 캡차 이미지를 보세요.
이미지에 영수증/표와 빨간색 질문이 있습니다.
빨간색 질문을 읽고, 영수증/표를 분석해서 답을 구하세요.

규칙:
- 답만 간결하게 (단위, 설명, 마침표 없이)
- 숫자면 숫자만 (예: 700)
- 텍스트면 텍스트만"""

            response = self.gemini_model.generate_content([prompt, img])
            answer = response.text.strip()

            # 불필요한 문자 제거
            answer = answer.replace("원", "").replace("개", "").replace(".", "").strip()

            self.log(f"캡차 답변: {answer}")

            # 4. 답 입력 (type()으로 한 글자씩 입력 - 봇 감지 우회)
            # 다양한 캡차 입력창 셀렉터 시도
            captcha_selectors = [
                "input[placeholder*='정답']",
                "input#captcha",
                "input[name='captcha']",
                "input.input_captcha",
                "#captcha",
            ]
            captcha_input = None
            for selector in captcha_selectors:
                loc = self.page.locator(selector)
                if loc.count() > 0:
                    captcha_input = loc.first
                    self.log(f"캡차 입력창 발견: {selector}")
                    break

            if not captcha_input:
                # 모든 input 태그 중 빈 것 찾기
                all_inputs = self.page.locator("input[type='text'], input:not([type])")
                for i in range(all_inputs.count()):
                    inp = all_inputs.nth(i)
                    placeholder = inp.get_attribute("placeholder") or ""
                    if "정답" in placeholder or "입력" in placeholder:
                        captcha_input = inp
                        self.log(f"캡차 입력창 발견 (placeholder: {placeholder})")
                        break

            if captcha_input:
                # JavaScript로 직접 값 설정 (봇 탐지 우회)
                # 답변의 특수문자 이스케이프 처리
                answer_escaped = (answer
                    .replace('\\', '\\\\')
                    .replace('"', '\\"')
                    .replace("'", "\\'")
                    .replace('\n', '\\n'))
                self.page.evaluate(f'''
                    const captchaInput = document.querySelector("input[placeholder*='정답']");
                    if (captchaInput) {{
                        captchaInput.value = "{answer_escaped}";
                        captchaInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        captchaInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                ''')
                self.log(f"캡차 답 입력: {answer}")
                self._random_delay(0.3, 0.5)

                # 비밀번호도 JavaScript로 입력
                if self._captcha_password:
                    pw_escaped = self._captcha_password.replace("\\", "\\\\").replace("'", "\\'")
                    self.page.evaluate(f'''
                        const pwInput = document.querySelector("#pw");
                        if (pwInput) {{
                            pwInput.value = '{pw_escaped}';
                            pwInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            pwInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    ''')
                    self.log("비밀번호 재입력 완료")
                    self._random_delay(0.3, 0.5)

                # 로그인 버튼 다시 클릭
                self.page.click(SELECTORS["login_button"])
                self._random_delay(2, 3)

                # 디버깅용으로 마지막 캡차 이미지 보존 (captcha_last.png)
                try:
                    import shutil
                    shutil.copy(captcha_path, "captcha_last.png")
                    os.remove(captcha_path)
                except:
                    pass

                return True
            else:
                self.log("캡차 입력창을 찾을 수 없음")
                return False

        except Exception as e:
            self.log(f"캡차 풀이 오류: {e}")
            return False

    def check_account_protection(self) -> Dict:
        """아이디 보호조치(잠금) 상태 확인

        Returns:
            dict: {is_protected: bool, reason: str}
        """
        try:
            current_url = self.page.url

            # URL 기반 보호조치 감지
            protection_urls = [
                "protect",
                "security",
                "restriction"
            ]
            for url_indicator in protection_urls:
                if url_indicator in current_url.lower():
                    self.log(f"[경고] 보호조치 URL 감지: {current_url}")
                    return {'is_protected': True, 'reason': f'보호조치 URL: {current_url}'}

            # 페이지 콘텐츠 감지
            page_content = self.page.content()

            # 보호조치 키워드 확인
            protection_indicators = [
                "보호 조치",
                "보호조치",
                "비정상적인 활동이 감지되어",
                "스팸성 홍보활동",
                "서비스 이용이 제한"
            ]

            for indicator in protection_indicators:
                if indicator in page_content:
                    self.log(f"[경고] 아이디 보호조치 감지: {indicator}")
                    return {'is_protected': True, 'reason': indicator}

            return {'is_protected': False, 'reason': ''}

        except Exception as e:
            self.log(f"보호조치 확인 오류: {e}")
            return {'is_protected': False, 'reason': ''}

    def login_with_credentials(self, naver_id: str, naver_pw: str) -> Dict:
        """아이디/비밀번호로 로그인

        Args:
            naver_id: 네이버 아이디
            naver_pw: 네이버 비밀번호

        Returns:
            dict: {success: bool, protected: bool, reason: str}
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

            self._random_delay(2, 3)

            # 보호조치 확인
            protection = self.check_account_protection()
            if protection['is_protected']:
                self.is_logged_in = False
                return {'success': False, 'protected': True, 'reason': protection['reason']}

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

                return {'success': True, 'protected': False, 'reason': ''}

            except:
                current_url = self.page.url
                self.log(f"로그인 확인 중... URL: {current_url}")

                # 다시 보호조치 확인
                protection = self.check_account_protection()
                if protection['is_protected']:
                    return {'success': False, 'protected': True, 'reason': protection['reason']}

                if "nid.naver.com" in current_url:
                    # 캡차 감지 및 풀이 시도
                    if self.detect_captcha():
                        self.log("캡차 감지됨")

                        # 최대 3번 캡차 풀이 시도
                        for attempt in range(3):
                            self.log(f"캡차 풀이 시도 {attempt + 1}/3")

                            if self.solve_captcha(password=naver_pw):
                                # 로그인 성공 여부 확인
                                self._random_delay(2, 3)
                                try:
                                    self.page.wait_for_url(
                                        lambda url: "nid.naver.com" not in url,
                                        timeout=10000
                                    )
                                    self.is_logged_in = True
                                    self.log("캡차 풀이 성공 - 로그인 완료!")
                                    self.save_cookies()
                                    return {'success': True, 'protected': False, 'reason': ''}
                                except:
                                    # 여전히 로그인 페이지면 캡차 틀렸을 수 있음
                                    if not self.detect_captcha():
                                        # 캡차가 없으면 다른 문제
                                        break
                                    self.log("캡차 답이 틀린 것 같음, 재시도...")
                            else:
                                break

                        self.log("캡차 풀이 실패")
                        return {'success': False, 'protected': False, 'reason': '캡차 풀이 실패'}

                    # 캡차도 아니면 인증정보 문제
                    try:
                        self.page.screenshot(path="debug_login_failed.png")
                        self.log("디버그 스크린샷 저장: debug_login_failed.png")
                    except:
                        pass
                    self.log("로그인 실패 - 잘못된 인증정보")
                    return {'success': False, 'protected': False, 'reason': '잘못된 인증정보'}
                else:
                    self.is_logged_in = True
                    self.save_cookies()
                    return {'success': True, 'protected': False, 'reason': ''}

        except Exception as e:
            self.log(f"로그인 오류: {e}")
            return {'success': False, 'protected': False, 'reason': str(e)}

    def login_with_cookies(self) -> Dict:
        """저장된 쿠키로 로그인 시도

        Returns:
            dict: {success: bool, protected: bool, reason: str}
        """
        if not self.load_cookies():
            return {'success': False, 'protected': False, 'reason': '쿠키 파일 없음'}

        self.log("쿠키로 로그인 확인 중...")

        # 쿠키 적용을 위해 네이버 도메인 먼저 방문
        self.page.goto("https://www.naver.com")
        self._random_delay(1, 2)

        # 글쓰기 페이지로 직접 이동하여 로그인 확인
        self.page.goto(URLS["blog_write"])
        self._random_delay(2, 3)

        # 보호조치 확인
        protection = self.check_account_protection()
        if protection['is_protected']:
            self.is_logged_in = False
            return {'success': False, 'protected': True, 'reason': protection['reason']}

        # 로그인 상태 확인 - 글쓰기 에디터가 로드되는지 확인
        try:
            # 로그인 페이지로 리다이렉트되면 실패
            current_url = self.page.url
            if "nidlogin" in current_url or "nid.naver.com" in current_url:
                self.log("쿠키 만료 - 로그인 페이지로 리다이렉트됨")
                return {'success': False, 'protected': False, 'reason': '쿠키 만료'}

            # 에디터 iframe이 로드되면 성공
            self.page.wait_for_selector(SELECTORS["main_frame"], timeout=10000)
            self.is_logged_in = True
            self.log("쿠키 로그인 성공!")
            return {'success': True, 'protected': False, 'reason': ''}
        except:
            self.log("쿠키 만료 - 재로그인 필요")
            return {'success': False, 'protected': False, 'reason': '쿠키 만료'}

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
        scheduled_time: str = None,
        progress_callback: Callable[[str, int], None] = None,
        auto_generate_images: bool = False
    ) -> Dict:
        """블로그 글 발행 (즉시 또는 예약)

        Args:
            title: 글 제목
            content: 글 내용 (이미지 마커 포함 가능: {img:1}, {img:1-5})
            images: 이미지 파일 경로 리스트 (선택)
            scheduled_time: 예약발행 시간 (None/'즉시발행' = 즉시, 'YYYY-MM-DD HH:MM' = 예약)
                           예약 시간이 현재 시간보다 이전이면 즉시 발행
            progress_callback: 진행 상황 콜백 (메시지, 퍼센트)
            auto_generate_images: 이미지 자동 생성 여부 (기본값: False)
                                 True이면 마커 기반 이미지 자동 생성:
                                 - 1번 이미지: 항상 제목 이미지
                                 - 2번~ 이미지: 단락 첫 문장 이미지
                                 - 단락 부족 시 초과 마커 자동 제거

        Returns:
            발행 결과 딕셔너리 {success: bool, url: str, error: str, is_scheduled: bool}
        """
        if not self.is_logged_in:
            return {'success': False, 'error': '로그인되지 않음', 'url': '', 'is_scheduled': False}

        def update_progress(msg: str, pct: int):
            self.log(msg)
            if progress_callback:
                progress_callback(msg, pct)

        # 자동 이미지 생성
        if auto_generate_images and HAS_TEXT_IMAGE_GENERATOR and not images:
            update_progress("이미지 자동 생성 중...", 3)
            try:
                content, self.auto_generated_images = generate_auto_images_for_publish(title, content)
                images = self.auto_generated_images
                self.log(f"자동 생성 이미지: {len(images)}개")
            except Exception as e:
                self.log(f"이미지 자동 생성 실패 (무시): {e}")

        try:
            # 이미 글쓰기 페이지에 있는지 확인 (쿠키 로그인 후)
            current_url = self.page.url
            if "GoBlogWrite" not in current_url and "blog.naver.com" not in current_url:
                update_progress("글쓰기 페이지로 이동 중...", 5)
                self.page.goto(URLS["blog_write"])
                self._random_delay(3, 5)
            else:
                # 이미 글쓰기 페이지면 새로고침
                update_progress("글쓰기 페이지 새로고침...", 5)
                self.page.goto(URLS["blog_write"])
                self._random_delay(2, 3)

            update_progress("에디터 로딩 대기 중...", 10)

            # iframe 확인 - 새 에디터는 iframe 없이 직접 페이지에 로드됨
            try:
                iframe_count = self.page.locator(SELECTORS["main_frame"]).count()
                if iframe_count > 0:
                    frame = self.page.frame_locator(SELECTORS["main_frame"])
                    self.log("iframe 모드로 에디터 접근")
                else:
                    # iframe이 없으면 page 자체에서 찾기 (새 에디터)
                    frame = self.page
                    self.log("직접 페이지 모드로 에디터 접근")

                # 에디터 로드 확인 - 제목 영역이 보이는지 확인 (30초로 증가 - 느린 네트워크 대응)
                frame.locator(SELECTORS["title_area"]).wait_for(state="visible", timeout=30000)
                update_progress("에디터 준비 완료", 15)
            except Exception as e:
                return {'success': False, 'error': f'에디터 로드 실패: {e}', 'url': '', 'is_scheduled': False}

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
                return {'success': False, 'error': f'제목 입력 실패: {e}', 'url': '', 'is_scheduled': False}

            # 본문으로 이동
            self._random_delay(0.5, 1)

            # 본문 입력
            update_progress("본문 입력 중...", 40)
            try:
                content_locator = frame.locator(SELECTORS["content_area"])
                content_locator.click()
                self._random_delay(0.3, 0.7)

                if images:
                    if self.headless:
                        # 헤드리스 모드: file input 방식으로 이미지 업로드
                        update_progress("본문 + 이미지 입력 중 (헤드리스)...", 45)
                        self._input_content_with_images_headless(content, images, update_progress, frame)
                    elif HAS_WIN32_CLIPBOARD:
                        # 일반 모드: 클립보드 붙여넣기 방식
                        update_progress("본문 + 이미지 입력 중...", 45)
                        self._input_content_with_images(content, images, update_progress)
                    else:
                        # 클립보드 미지원 -> 마커 제거 후 텍스트만 입력
                        self.log("클립보드 미지원: 이미지 삽입 불가, 텍스트만 입력")
                        processed_content = self._remove_image_markers(content)
                        self._input_long_text(processed_content)
                else:
                    # 이미지 없음 -> 마커 제거 후 텍스트만 입력
                    processed_content = self._remove_image_markers(content)
                    self._input_long_text(processed_content)

                update_progress("본문 입력 완료", 70)
            except Exception as e:
                return {'success': False, 'error': f'본문 입력 실패: {e}', 'url': '', 'is_scheduled': False}

            self._random_delay(2, 4)

            # 발행 버튼 클릭
            update_progress("발행 버튼 클릭 중...", 80)
            try:
                publish_btn = frame.locator(SELECTORS["publish_button"])
                publish_btn.wait_for(state="visible", timeout=10000)
                self._random_delay(1, 2)
                publish_btn.click()
                update_progress("발행 버튼 클릭 완료", 85)
            except Exception as e:
                return {'success': False, 'error': f'발행 버튼 클릭 실패: {e}', 'url': '', 'is_scheduled': False}

            self._random_delay(3, 5)  # 발행 팝업 로딩 대기 (기존 1-2초 -> 3-5초)

            # 예약발행 여부 결정
            is_scheduled = False
            if scheduled_time and scheduled_time != '즉시발행':
                # 예약 시간 파싱
                try:
                    scheduled_dt = datetime.strptime(scheduled_time, "%Y-%m-%d %H:%M")
                    now = datetime.now()

                    # 예약 시간이 현재보다 미래인 경우에만 예약발행
                    if scheduled_dt > now:
                        is_scheduled = True
                        update_progress(f"예약발행 설정 중... ({scheduled_time})", 86)
                        try:
                            self._set_scheduled_publish(frame, scheduled_dt)
                            self.log(f"예약발행 시간 설정: {scheduled_time}")
                        except Exception as e:
                            self.log(f"예약발행 설정 실패, 즉시 발행으로 전환: {e}")
                            is_scheduled = False
                    else:
                        self.log(f"예약 시간({scheduled_time})이 현재 시간보다 이전, 즉시 발행")
                except ValueError as e:
                    self.log(f"예약 시간 파싱 실패 ({scheduled_time}), 즉시 발행: {e}")

            # 댓글 허용 끄기
            update_progress("발행 옵션 설정 중...", 87)
            try:
                self._disable_comment_option(frame)
            except Exception as e:
                self.log(f"댓글 옵션 설정 실패 (무시): {e}")

            self._random_delay(1, 2)

            # 발행 확인 버튼 클릭 (iframe 내부에 있음)
            update_progress("발행 확인 중...", 90)
            try:
                # 발행 팝업은 iframe 내부에 있음
                confirm_btn = frame.locator(SELECTORS["publish_confirm"])
                confirm_btn.wait_for(state="visible", timeout=15000)
                self._random_delay(1, 2)

                # 헤드리스 모드: JavaScript 클릭 사용
                if self.headless:
                    self.log("헤드리스 모드: 발행 확인 버튼 클릭 시도...")
                    try:
                        # iframe 내부에서 JavaScript 클릭
                        if hasattr(frame, 'evaluate'):
                            # frame이 FrameLocator인 경우
                            frame.locator(SELECTORS["publish_confirm"]).evaluate('el => el.click()')
                        else:
                            # frame이 Page인 경우
                            frame.evaluate(f'''
                                document.querySelector("{SELECTORS["publish_confirm"]}").click();
                            ''')
                        self.log("발행 확인 버튼 클릭 완료 (JS)")
                    except Exception as js_err:
                        # JavaScript 실패시 force 클릭 시도
                        self.log(f"JS 클릭 실패, force 클릭 시도: {js_err}")
                        confirm_btn.click(force=True)
                        self.log("발행 확인 버튼 클릭 완료 (force)")
                else:
                    confirm_btn.click()
                    self.log("발행 확인 버튼 클릭 완료")

                update_progress("발행 확인 버튼 클릭", 95)
            except Exception as e:
                return {'success': False, 'error': f'발행 확인 실패: {e}', 'url': '', 'is_scheduled': is_scheduled}

            # 발행 완료 대기
            update_progress("발행 완료 대기 중...", 98)
            try:
                # 예약발행인 경우 다른 처리
                if is_scheduled:
                    # 예약발행: 글쓰기 페이지에서 벗어나면 성공
                    def is_not_write_page(url):
                        # 글쓰기 페이지들 제외
                        if "GoBlogWrite" in url:
                            return False
                        if "Redirect=Write" in url:
                            return False
                        if "nid.naver.com" in url:
                            return False
                        return True

                    try:
                        self.page.wait_for_url(is_not_write_page, timeout=30000)
                        self._random_delay(1, 2)
                        current_url = self.page.url
                        self.log(f"예약발행 후 현재 URL: {current_url}")

                        update_progress("예약발행 완료!", 100)
                        return {
                            'success': True,
                            'url': current_url,
                            'error': '',
                            'is_scheduled': True
                        }
                    except:
                        current_url = self.page.url
                        self.log(f"예약발행 타임아웃, 현재 URL: {current_url}")
                        # 아직 글쓰기 페이지면 실패
                        if "GoBlogWrite" in current_url or "Redirect=Write" in current_url:
                            return {
                                'success': False,
                                'error': '예약발행 실패 - 글쓰기 페이지에서 벗어나지 못함',
                                'url': '',
                                'is_scheduled': True
                            }
                        else:
                            return {
                                'success': True,
                                'url': current_url,
                                'error': '',
                                'is_scheduled': True
                            }

                # 즉시발행인 경우
                def is_post_url(url):
                    # Redirect URL 제외 (blog.naver.com/아이디?Redirect=Write 등)
                    if "Redirect=" in url:
                        return False
                    # 쿼리 파라미터가 있는 블로그 메인 URL 제외
                    if re.search(r'blog\.naver\.com/[^/]+\?', url):
                        return False
                    # 글쓰기 페이지 제외
                    if "GoBlogWrite" in url:
                        return False
                    # 로그인 페이지 제외
                    if "nid.naver.com" in url:
                        return False
                    # 실제 포스트 URL 확인
                    if "PostView" in url:
                        return True
                    # 숫자 ID가 있는 블로그 URL (blog.naver.com/userid/12345)
                    if re.search(r'blog\.naver\.com/[^/]+/\d+', url):
                        return True
                    # 블로그 홈으로 리다이렉트된 경우도 성공으로 처리
                    if "BlogHome" in url:
                        return True
                    if "section.blog.naver.com" in url and "Redirect" not in url:
                        return True
                    return False

                # 발행 완료 대기 - 여러 방법으로 URL 확인
                published_url = None

                # 방법 1: 일정 시간 대기 후 URL 확인 (발행 처리 시간 고려)
                self._random_delay(3, 5)

                # 현재 페이지 URL 먼저 확인
                current_url = self.page.url
                self.log(f"발행 후 현재 URL: {current_url}")
                if is_post_url(current_url):
                    published_url = current_url
                    self.log("현재 탭에서 발행 URL 확인됨")

                # 방법 2: 새 탭 확인
                if not published_url:
                    all_pages = self.context.pages
                    self.log(f"열린 탭 수: {len(all_pages)}")
                    for p in all_pages:
                        try:
                            p_url = p.url
                            if is_post_url(p_url):
                                published_url = p_url
                                self.log(f"새 탭에서 발행 URL 발견: {p_url}")
                                break
                        except:
                            continue

                # 방법 3: wait_for_url로 추가 대기
                if not published_url:
                    try:
                        self.page.wait_for_url(is_post_url, timeout=10000)
                        published_url = self.page.url
                        self.log(f"URL 변화 감지됨: {published_url}")
                    except:
                        self.log("URL 변화 감지 실패")

                if published_url:
                    self._random_delay(1, 2)
                    self.log(f"발행된 URL: {published_url}")
                    update_progress("발행 완료!", 100)
                    return {
                        'success': True,
                        'url': published_url,
                        'error': '',
                        'is_scheduled': is_scheduled
                    }
                else:
                    return {
                        'success': False,
                        'error': '발행 완료 URL 확인 실패',
                        'url': '',
                        'is_scheduled': is_scheduled
                    }

            except Exception as e:
                return {
                    'success': False,
                    'error': f'발행 완료 확인 실패: {e}',
                    'url': '',
                    'is_scheduled': is_scheduled
                }

        except Exception as e:
            self.log(f"발행 오류: {e}")
            return {'success': False, 'error': str(e), 'url': '', 'is_scheduled': False}

        finally:
            # 자동 생성된 임시 이미지 정리
            if self.auto_generated_images and HAS_TEXT_IMAGE_GENERATOR:
                try:
                    cleanup_temp_images(self.auto_generated_images)
                    self.auto_generated_images = []
                except:
                    pass

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

    def _disable_comment_option(self, frame):
        """댓글 허용 옵션 끄기 (항상 실행)"""
        try:
            # 댓글 체크박스 찾기
            checkbox = frame.locator(SELECTORS["comment_checkbox"])

            # 체크박스가 존재하는지 확인
            if checkbox.count() == 0:
                self.log("댓글 체크박스를 찾을 수 없음")
                return

            # 체크박스 상태 확인 (checked 속성)
            is_checked = checkbox.is_checked()

            if is_checked:
                # 체크되어 있으면 (댓글 허용 상태) -> 클릭하여 끄기
                label = frame.locator(SELECTORS["comment_checkbox_label"])
                if label.count() > 0:
                    label.click()
                    self._random_delay(0.3, 0.5)
                    self.log("댓글 허용 옵션 끔")
                else:
                    # 라벨이 없으면 체크박스 직접 클릭
                    checkbox.click()
                    self._random_delay(0.3, 0.5)
                    self.log("댓글 허용 옵션 끔 (직접 클릭)")
            else:
                self.log("댓글 허용 이미 꺼져있음")

        except Exception as e:
            self.log(f"댓글 옵션 설정 중 오류: {e}")

    def _set_scheduled_publish(self, frame, scheduled_dt: datetime):
        """
        예약발행 시간 설정

        Args:
            frame: iframe frame_locator
            scheduled_dt: 예약 시간 (datetime 객체)
        """
        # 1. 예약 라디오 버튼 클릭
        self.log("예약 라디오 버튼 클릭...")
        schedule_radio = frame.locator(SELECTORS["schedule_radio_label"])
        schedule_radio.wait_for(state="visible", timeout=5000)
        schedule_radio.click()
        self._random_delay(1, 2)

        # 2. 날짜 설정
        self._set_scheduled_date(frame, scheduled_dt)

        # 3. 시간/분 설정
        self._set_scheduled_time(frame, scheduled_dt.hour, scheduled_dt.minute)

    def _set_scheduled_date(self, frame, target_dt: datetime):
        """
        예약발행 날짜 설정 (달력 UI)

        Args:
            frame: iframe frame_locator
            target_dt: 목표 날짜 (datetime 객체)
        """
        self.log(f"날짜 설정: {target_dt.strftime('%Y-%m-%d')}")

        # 날짜 input 클릭 -> 달력 팝업 열기
        date_input = frame.locator(SELECTORS["date_input"])
        date_input.click()
        self._random_delay(0.5, 1.0)

        target_year = target_dt.year
        target_month = target_dt.month
        target_day = target_dt.day

        max_attempts = 12  # 최대 12개월 이동

        for _ in range(max_attempts):
            # 현재 달력의 년/월 확인
            try:
                current_year_elem = frame.locator(SELECTORS["datepicker_year"])
                current_month_elem = frame.locator(SELECTORS["datepicker_month"])

                current_year = int(current_year_elem.inner_text())
                current_month_text = current_month_elem.inner_text()
                # "12월" -> 12
                current_month = int(current_month_text.replace('월', ''))

                if current_year == target_year and current_month == target_month:
                    break

                # 다음 달로 이동
                next_btn = frame.locator(SELECTORS["datepicker_next_month"])
                if next_btn.count() > 0:
                    next_btn.click()
                    self._random_delay(0.3, 0.5)
                else:
                    self.log("다음달 버튼을 찾을 수 없음")
                    break

            except Exception as e:
                self.log(f"달력 탐색 오류: {e}")
                break

        # 날짜 버튼 클릭 (disabled 아닌 것)
        day_selector = "td:not(.ui-state-disabled) button.ui-state-default"
        day_buttons = frame.locator(day_selector)

        count = day_buttons.count()
        for i in range(count):
            btn = day_buttons.nth(i)
            btn_text = btn.inner_text().strip()
            if btn_text == str(target_day):
                self.log(f"날짜 {target_day}일 선택")
                btn.click()
                self._random_delay(0.3, 0.5)
                return

        self.log(f"날짜 {target_day}일을 찾을 수 없음")

    def _set_scheduled_time(self, frame, hour: int, minute: int):
        """
        예약발행 시간/분 설정 (select box)

        Args:
            frame: iframe frame_locator
            hour: 시간 (0-23)
            minute: 분 (0-59, 10분 단위로 반올림됨)
        """
        # 분은 10분 단위로 반올림 (네이버는 00, 10, 20, 30, 40, 50만 지원)
        rounded_minute = (minute // 10) * 10

        self.log(f"시간 설정: {hour:02d}:{rounded_minute:02d}")

        # 시간 선택
        hour_select = frame.locator(SELECTORS["hour_select"])
        hour_select.select_option(value=f"{hour:02d}")
        self._random_delay(0.3, 0.5)

        # 분 선택
        minute_select = frame.locator(SELECTORS["minute_select"])
        minute_select.select_option(value=f"{rounded_minute:02d}")
        self._random_delay(0.3, 0.5)

    def _input_long_text(self, text: str):
        """긴 텍스트 입력 (청크 단위)"""
        # 줄바꿈 기준으로 분할하여 입력
        lines = text.split('\n')

        for i, line in enumerate(lines):
            if line.strip():
                if self.headless:
                    # 헤드리스 모드: 클립보드 대신 직접 타이핑
                    self.page.keyboard.type(line, delay=5)
                else:
                    # 일반 모드: 클립보드 사용
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
        # 이미지 마커 패턴: {img:1}, {img:1-5}
        marker_pattern = r'\{img:(\d+)(?:-(\d+))?\}'

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

        self.log(f"이미지 마커 {len(markers)}개 발견, 사용 가능 이미지: {len(images)}개")

        # 마커가 이미지보다 많으면 초과 마커 제거
        # 이미지 인덱스는 1-based (img:1 = 첫 번째 이미지)
        result = content
        image_count = len(images)

        for marker in markers:
            # 마커 번호가 이미지 수를 초과하면 마커만 제거
            if marker['start'] > image_count:
                result = result.replace(marker['full_match'], '')
            else:
                # 마커는 그대로 유지 (나중에 본문 입력 시 이미지로 대체)
                pass

        return result

    def _input_content_with_images(
        self,
        content: str,
        images: List[str],
        update_progress
    ):
        """
        본문 입력 + 이미지 삽입 (마커 위치에 클립보드 붙여넣기)

        Args:
            content: 본문 내용 (이미지 마커 포함: {img:1}, {img:1-5})
            images: 이미지 파일 경로 리스트
            update_progress: 진행률 콜백
        """
        # 이미지 마커 패턴: {img:1}, {img:1-5}
        marker_pattern = r'\{img:(\d+)(?:-(\d+))?\}'

        image_count = len(images)
        inserted_images = 0

        # 마커 정보 수집 (위치와 범위)
        markers = []
        for match in re.finditer(marker_pattern, content):
            start_num = int(match.group(1))
            end_num = int(match.group(2)) if match.group(2) else start_num
            markers.append({
                'full_match': match.group(0),
                'start': start_num,
                'end': end_num,
                'pos': match.start()
            })

        if not markers:
            # 마커가 없으면 텍스트만 입력
            self._input_long_text(content)
            return

        # 본문을 마커 위치 기준으로 처리
        last_pos = 0
        for marker in markers:
            # 마커 앞의 텍스트 입력
            text_before = content[last_pos:marker['pos']]
            if text_before:
                lines = text_before.split('\n')
                for i, line in enumerate(lines):
                    if line.strip():
                        pyperclip.copy(line)
                        self._random_delay(0.1, 0.2)
                        self.page.keyboard.press("Control+v")
                        self._random_delay(0.1, 0.2)

                    if i < len(lines) - 1:
                        self.page.keyboard.press("Enter")
                        self._random_delay(0.03, 0.08)

            # 마커 위치에 이미지 삽입 (범위: start ~ end)
            # 연속 이미지는 공백 없이 바로 붙여넣기
            for idx, img_num in enumerate(range(marker['start'], marker['end'] + 1)):
                if img_num <= image_count:
                    img_path = images[img_num - 1]  # 1-based to 0-based

                    if os.path.exists(img_path):
                        # 첫 번째 이미지 앞에만 줄바꿈 추가
                        if idx == 0:
                            self.page.keyboard.press("Enter")
                            self._random_delay(0.2, 0.4)

                        # 이미지 삽입
                        inserted_images += 1
                        update_progress(f"이미지 {inserted_images} 삽입 중...", 50 + inserted_images * 3)

                        if self._insert_image_at_cursor(img_path):
                            self.log(f"이미지 {img_num} 삽입: {os.path.basename(img_path)}")
                        else:
                            self.log(f"이미지 {img_num} 삽입 실패")

                        self._random_delay(0.2, 0.4)

            last_pos = marker['pos'] + len(marker['full_match'])

        # 마지막 마커 뒤의 텍스트 입력
        remaining_text = content[last_pos:]
        if remaining_text:
            lines = remaining_text.split('\n')
            for i, line in enumerate(lines):
                if line.strip():
                    pyperclip.copy(line)
                    self._random_delay(0.1, 0.2)
                    self.page.keyboard.press("Control+v")
                    self._random_delay(0.1, 0.2)

                if i < len(lines) - 1:
                    self.page.keyboard.press("Enter")
                    self._random_delay(0.03, 0.08)

        self.log(f"총 {inserted_images}개 이미지 삽입 완료")

    def _input_content_with_images_headless(
        self,
        content: str,
        images: List[str],
        update_progress,
        frame
    ):
        """
        본문 입력 + 이미지 삽입 (헤드리스 모드용 - file input 방식)

        Args:
            content: 본문 내용 (이미지 마커 포함: {img:1}, {img:1-5})
            images: 이미지 파일 경로 리스트
            update_progress: 진행률 콜백
            frame: iframe 프레임 로케이터
        """
        # 이미지 마커 패턴: {img:1}, {img:1-5}
        marker_pattern = r'\{img:(\d+)(?:-(\d+))?\}'

        image_count = len(images)
        inserted_images = 0

        # 마커 정보 수집 (위치와 범위)
        markers = []
        for match in re.finditer(marker_pattern, content):
            start_num = int(match.group(1))
            end_num = int(match.group(2)) if match.group(2) else start_num
            markers.append({
                'full_match': match.group(0),
                'start': start_num,
                'end': end_num,
                'pos': match.start()
            })

        if not markers:
            # 마커가 없으면 텍스트만 입력
            self._input_long_text(content)
            return

        # 본문을 마커 위치 기준으로 처리
        last_pos = 0
        for marker in markers:
            # 마커 앞의 텍스트 입력
            text_before = content[last_pos:marker['pos']]
            if text_before:
                lines = text_before.split('\n')
                for i, line in enumerate(lines):
                    if line.strip():
                        # 헤드리스 모드에서는 insert_text 사용 (type보다 훨씬 빠름)
                        self.page.keyboard.insert_text(line)
                        self._random_delay(0.02, 0.05)

                    if i < len(lines) - 1:
                        self.page.keyboard.press("Enter")
                        self._random_delay(0.02, 0.05)

            # 마커 위치에 이미지 삽입 (file input 방식)
            for idx, img_num in enumerate(range(marker['start'], marker['end'] + 1)):
                if img_num <= image_count:
                    img_path = images[img_num - 1]  # 1-based to 0-based

                    if os.path.exists(img_path):
                        # 첫 번째 이미지 앞에만 줄바꿈 추가
                        if idx == 0:
                            self.page.keyboard.press("Enter")
                            self._random_delay(0.2, 0.4)

                        # 이미지 삽입
                        inserted_images += 1
                        update_progress(f"이미지 {inserted_images} 삽입 중...", 50 + inserted_images * 3)

                        if self._insert_image_via_file_input(img_path, frame):
                            self.log(f"이미지 {img_num} 삽입: {os.path.basename(img_path)}")
                        else:
                            self.log(f"이미지 {img_num} 삽입 실패")

                        self._random_delay(0.3, 0.6)

            last_pos = marker['pos'] + len(marker['full_match'])

        # 마지막 마커 뒤의 텍스트 입력
        remaining_text = content[last_pos:]
        if remaining_text:
            lines = remaining_text.split('\n')
            for i, line in enumerate(lines):
                if line.strip():
                    self.page.keyboard.insert_text(line)
                    self._random_delay(0.02, 0.05)

                if i < len(lines) - 1:
                    self.page.keyboard.press("Enter")
                    self._random_delay(0.02, 0.05)

        self.log(f"총 {inserted_images}개 이미지 삽입 완료 (헤드리스)")

    def _insert_image_via_file_input(self, image_path: str, frame) -> bool:
        """
        file input을 통한 이미지 삽입 (헤드리스 모드용)

        Args:
            image_path: 이미지 파일 경로
            frame: iframe 프레임 로케이터

        Returns:
            성공 여부
        """
        try:
            abs_path = os.path.abspath(image_path)

            # file input이 이미 있는지 확인
            file_input = frame.locator('input[type="file"]')
            input_count = file_input.count()

            if input_count == 0:
                # file input이 없으면 사진 버튼 클릭
                photo_btn = frame.locator('button[data-name="image"]')
                if photo_btn.count() > 0:
                    photo_btn.first.click(force=True)
                    self._random_delay(1.5, 2.5)

                    # file input 다시 찾기
                    file_input = frame.locator('input[type="file"]')
                    input_count = file_input.count()

            if input_count > 0:
                # 파일 설정
                file_input.first.set_input_files(abs_path)
                self._random_delay(3, 5)  # 업로드 완료 대기

                # 이미지 컴포넌트 확인
                img_components = frame.locator('.se-component-image, .se-image-resource')
                if img_components.count() > 0:
                    return True
                else:
                    self.log("이미지 컴포넌트가 생성되지 않음")
                    return True  # 업로드는 됐을 수 있음
            else:
                self.log("file input을 찾을 수 없음")
                return False

        except Exception as e:
            self.log(f"file input 이미지 삽입 오류: {e}")
            return False

    def _remove_image_markers(self, content: str) -> str:
        """이미지 마커 제거"""
        pattern = r'\{img:\d+(?:-\d+)?\}'
        return re.sub(pattern, '', content)

    def _copy_image_to_clipboard(self, image_path: str) -> bool:
        """
        이미지를 클립보드에 복사

        Args:
            image_path: 이미지 파일 경로

        Returns:
            성공 여부
        """
        if not HAS_WIN32_CLIPBOARD:
            self.log("Windows 클립보드 지원 불가 (pywin32/Pillow 필요)")
            return False

        try:
            # 이미지 열기
            image = Image.open(image_path)

            # RGBA -> RGB 변환 (투명 배경 처리)
            if image.mode == 'RGBA':
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background

            # BMP 형식으로 변환 (클립보드용)
            output = io.BytesIO()
            image.convert('RGB').save(output, 'BMP')
            data = output.getvalue()[14:]  # BMP 헤더 제외

            # 클립보드에 복사
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            finally:
                win32clipboard.CloseClipboard()

            return True

        except Exception as e:
            self.log(f"클립보드 복사 실패: {e}")
            return False

    def _paste_image_from_clipboard(self) -> bool:
        """
        클립보드의 이미지를 에디터에 붙여넣기

        Returns:
            성공 여부
        """
        try:
            self.page.keyboard.press("Control+v")
            self._random_delay(1.5, 2.5)  # 이미지 업로드 대기
            return True
        except Exception as e:
            self.log(f"이미지 붙여넣기 실패: {e}")
            return False

    def _insert_image_at_cursor(self, image_path: str) -> bool:
        """
        현재 커서 위치에 이미지 삽입

        Args:
            image_path: 이미지 파일 경로

        Returns:
            성공 여부
        """
        if not os.path.exists(image_path):
            self.log(f"이미지 파일 없음: {image_path}")
            return False

        # 클립보드에 이미지 복사
        if not self._copy_image_to_clipboard(image_path):
            return False

        # 붙여넣기
        return self._paste_image_from_clipboard()

    def publish_multiple(
        self,
        posts: List[Dict],
        progress_callback: Callable[[int, int, str], None] = None,
        stop_flag: Callable[[], bool] = None
    ) -> List[Dict]:
        """여러 글 연속 발행

        Args:
            posts: 발행할 글 리스트 [{'title': str, 'content': str, 'images': list, 'scheduled_time': str}, ...]
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
                images=post.get('images', []),
                scheduled_time=post.get('scheduled_time'),
                auto_generate_images=post.get('auto_generate_images', False)
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
