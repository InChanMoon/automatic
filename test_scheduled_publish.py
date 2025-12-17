"""
예약발행 테스트 프로그램

네이버 블로그 예약발행 기능 테스트:
1. 로그인
2. 글쓰기 페이지 이동
3. 제목/본문 입력
4. 발행 버튼 클릭
5. 예약 라디오 선택
6. 날짜/시간 설정
7. 발행 확인
"""

import time
import re
from datetime import datetime, timedelta

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import pyperclip

# 계정 정보 가져오기
import sys
sys.path.insert(0, '.')
from src.sheets.account_manager import AccountManager


class ScheduledPublishTest:
    """예약발행 테스트 클래스"""

    # 셀렉터
    SELECTORS = {
        # 로그인
        "id_input": "#id",
        "pw_input": "#pw",
        "login_button": "#log\\.login",

        # 글쓰기
        "main_frame": "#mainFrame",
        "draft_popup_cancel": "button.se-popup-button-cancel",
        "title_area": ".se-section-documentTitle",
        "content_area": ".se-section-text",
        "publish_button": "button[data-click-area='tpb.publish']",

        # 발행 옵션
        "schedule_radio_label": "label[for='radio_time2']",
        "date_input": "input.input_date__QmA0s",
        "hour_select": "select.hour_option__J_heO",
        "minute_select": "select.minute_option__Vb3xB",
        "publish_confirm": "button[data-testid='seOnePublishBtn']",

        # 달력
        "datepicker_next_month": "button.ui-datepicker-next",
        "datepicker_year": ".ui-datepicker-year",
        "datepicker_month": ".ui-datepicker-month",
    }

    URLS = {
        "login": "https://nid.naver.com/nidlogin.login",
        "blog_write": "https://blog.naver.com/GoBlogWrite.naver",
    }

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def log(self, msg):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")

    def start_browser(self):
        """브라우저 시작"""
        self.log("브라우저 시작...")

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--lang=ko-KR",
                "--window-size=1920,1080",
            ]
        )

        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )

        self.page = self.context.new_page()
        stealth_sync(self.page)

        self.log("브라우저 시작 완료")

    def close_browser(self):
        """브라우저 종료"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.log("브라우저 종료")

    def _random_delay(self, min_sec=0.3, max_sec=1.0):
        """랜덤 딜레이"""
        import random
        time.sleep(random.uniform(min_sec, max_sec))

    def _paste_text(self, text):
        """클립보드 붙여넣기"""
        pyperclip.copy(text)
        self._random_delay(0.2, 0.4)
        self.page.keyboard.press("Control+v")
        self._random_delay(0.2, 0.4)

    def login(self, naver_id, naver_pw):
        """네이버 로그인"""
        self.log(f"로그인 시도: {naver_id}")

        self.page.goto(self.URLS["login"])
        self._random_delay(2, 3)

        # 아이디 입력
        self.page.wait_for_selector(self.SELECTORS["id_input"], timeout=10000)
        self.page.click(self.SELECTORS["id_input"])
        self._paste_text(naver_id)

        # 비밀번호 입력
        self.page.click(self.SELECTORS["pw_input"])
        self._paste_text(naver_pw)

        # 로그인 버튼
        self._random_delay(0.5, 1.0)
        self.page.click(self.SELECTORS["login_button"])

        # 로그인 확인
        try:
            self.page.wait_for_url(
                lambda url: "nid.naver.com" not in url,
                timeout=15000
            )
            self.log("로그인 성공!")
            return True
        except:
            self.log("로그인 실패 - 캡차 또는 인증 필요")
            return False

    def go_to_write_page(self):
        """글쓰기 페이지 이동"""
        self.log("글쓰기 페이지로 이동...")

        self.page.goto(self.URLS["blog_write"])
        self._random_delay(3, 5)

        # iframe 대기
        self.page.wait_for_selector(self.SELECTORS["main_frame"], timeout=20000)
        self.log("글쓰기 페이지 로드 완료")

        return self.page.frame_locator(self.SELECTORS["main_frame"])

    def close_popups(self, frame):
        """팝업 닫기"""
        try:
            cancel_btn = frame.locator(self.SELECTORS["draft_popup_cancel"])
            if cancel_btn.count() > 0:
                cancel_btn.click()
                self.log("임시저장 팝업 닫기")
                self._random_delay(0.5, 1.0)
        except:
            pass

    def write_content(self, frame, title, content):
        """제목/본문 입력"""
        self.log(f"제목 입력: {title[:30]}...")

        # 제목 입력
        title_locator = frame.locator(self.SELECTORS["title_area"])
        title_locator.click()
        self._random_delay(0.3, 0.5)
        self._paste_text(title)

        self._random_delay(0.5, 1.0)

        # 본문 입력
        self.log("본문 입력...")
        content_locator = frame.locator(self.SELECTORS["content_area"])
        content_locator.click()
        self._random_delay(0.3, 0.5)

        # 줄바꿈 단위로 입력
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip():
                pyperclip.copy(line)
                self._random_delay(0.05, 0.1)
                self.page.keyboard.press("Control+v")

            if i < len(lines) - 1:
                self.page.keyboard.press("Enter")
                self._random_delay(0.03, 0.05)

        self.log("본문 입력 완료")

    def click_publish_button(self, frame):
        """발행 버튼 클릭 (옵션 팝업 열기)"""
        self.log("발행 버튼 클릭...")

        publish_btn = frame.locator(self.SELECTORS["publish_button"])
        publish_btn.wait_for(state="visible", timeout=10000)
        self._random_delay(1, 2)
        publish_btn.click()

        self._random_delay(2, 3)
        self.log("발행 옵션 팝업 열림")

    def set_scheduled_time(self, frame, target_datetime):
        """
        예약 시간 설정

        Args:
            frame: iframe frame_locator
            target_datetime: datetime 객체 또는 "2025-12-20 14:30" 문자열
        """
        # datetime 파싱
        if isinstance(target_datetime, str):
            target_dt = datetime.strptime(target_datetime, "%Y-%m-%d %H:%M")
        else:
            target_dt = target_datetime

        self.log(f"예약 시간 설정: {target_dt.strftime('%Y-%m-%d %H:%M')}")

        # 1. 예약 라디오 버튼 클릭
        self.log("예약 라디오 버튼 클릭...")
        schedule_radio = frame.locator(self.SELECTORS["schedule_radio_label"])
        schedule_radio.wait_for(state="visible", timeout=5000)
        schedule_radio.click()
        self._random_delay(1, 2)

        # 2. 날짜 설정
        self._set_date(frame, target_dt)

        # 3. 시간 설정
        self._set_time(frame, target_dt.hour, target_dt.minute)

        self.log("예약 시간 설정 완료")

    def _set_date(self, frame, target_dt):
        """날짜 설정 (달력 UI)"""
        self.log(f"날짜 설정: {target_dt.strftime('%Y-%m-%d')}")

        # 날짜 input 클릭 -> 달력 팝업 열기
        date_input = frame.locator(self.SELECTORS["date_input"])
        date_input.click()
        self._random_delay(0.5, 1.0)

        # 현재 달력의 년/월 확인하고 목표 월까지 이동
        target_year = target_dt.year
        target_month = target_dt.month
        target_day = target_dt.day

        max_attempts = 12  # 최대 12개월 이동

        for _ in range(max_attempts):
            # 현재 달력의 년/월 확인
            try:
                current_year_elem = frame.locator(self.SELECTORS["datepicker_year"])
                current_month_elem = frame.locator(self.SELECTORS["datepicker_month"])

                current_year = int(current_year_elem.inner_text())
                current_month_text = current_month_elem.inner_text()
                # "12월" -> 12
                current_month = int(current_month_text.replace('월', ''))

                self.log(f"현재 달력: {current_year}년 {current_month}월")

                if current_year == target_year and current_month == target_month:
                    break

                # 다음 달로 이동
                next_btn = frame.locator(self.SELECTORS["datepicker_next_month"])
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
        # td:not(.ui-state-disabled) button 중 텍스트가 target_day인 것
        day_selector = f"td:not(.ui-state-disabled) button.ui-state-default"
        day_buttons = frame.locator(day_selector)

        count = day_buttons.count()
        self.log(f"선택 가능한 날짜: {count}개")

        for i in range(count):
            btn = day_buttons.nth(i)
            btn_text = btn.inner_text().strip()
            if btn_text == str(target_day):
                self.log(f"날짜 {target_day}일 클릭")
                btn.click()
                self._random_delay(0.3, 0.5)
                return

        self.log(f"날짜 {target_day}일을 찾을 수 없음 (과거 날짜이거나 범위 초과)")

    def _set_time(self, frame, hour, minute):
        """시간/분 설정 (select box)"""
        self.log(f"시간 설정: {hour:02d}:{minute:02d}")

        # 시간 선택
        hour_select = frame.locator(self.SELECTORS["hour_select"])
        hour_select.select_option(value=f"{hour:02d}")
        self._random_delay(0.3, 0.5)

        # 분 선택 (10분 단위로 반올림)
        # 네이버는 00, 10, 20, 30, 40, 50만 지원
        rounded_minute = (minute // 10) * 10

        minute_select = frame.locator(self.SELECTORS["minute_select"])
        minute_select.select_option(value=f"{rounded_minute:02d}")
        self._random_delay(0.3, 0.5)

        self.log(f"시간 선택 완료: {hour:02d}:{rounded_minute:02d}")

    def confirm_publish(self, frame):
        """발행 확인 버튼 클릭"""
        self.log("발행 확인 버튼 클릭...")

        confirm_btn = frame.locator(self.SELECTORS["publish_confirm"])
        confirm_btn.wait_for(state="visible", timeout=10000)
        self._random_delay(1, 2)
        confirm_btn.click()

        self.log("발행 확인 완료")

    def run_test(self, naver_id, naver_pw, scheduled_time=None):
        """
        전체 테스트 실행

        Args:
            naver_id: 네이버 ID
            naver_pw: 네이버 비밀번호
            scheduled_time: 예약 시간 (None이면 현재 + 1시간)
        """
        try:
            self.start_browser()

            # 로그인
            if not self.login(naver_id, naver_pw):
                self.log("로그인 실패로 테스트 중단")
                input("수동 로그인 후 Enter를 눌러주세요...")

            self._random_delay(2, 3)

            # 글쓰기 페이지
            frame = self.go_to_write_page()
            self._random_delay(1, 2)

            # 팝업 닫기
            self.close_popups(frame)

            # 테스트 글 작성
            test_title = f"[테스트] 예약발행 테스트 - {datetime.now().strftime('%H:%M:%S')}"
            test_content = """이것은 예약발행 테스트 글입니다.

자동으로 예약 시간이 설정되어야 합니다.

테스트 완료 후 삭제해주세요."""

            self.write_content(frame, test_title, test_content)
            self._random_delay(2, 3)

            # 발행 버튼 클릭
            self.click_publish_button(frame)

            # 예약 시간 설정
            if scheduled_time is None:
                # 기본: 현재 + 1시간
                scheduled_time = datetime.now() + timedelta(hours=1)

            self.set_scheduled_time(frame, scheduled_time)

            # 발행 확인은 수동으로 (테스트이므로)
            self.log("=" * 50)
            self.log("예약 시간 설정 완료!")
            self.log("발행 확인 버튼을 수동으로 클릭하거나,")
            self.log("Enter를 눌러 자동 발행을 진행합니다.")
            self.log("=" * 50)

            user_input = input("Enter to confirm, 'n' to skip: ")

            if user_input.lower() != 'n':
                self.confirm_publish(frame)
                self._random_delay(3, 5)
                self.log(f"현재 URL: {self.page.url}")

            self.log("테스트 완료!")
            input("브라우저를 닫으려면 Enter...")

        except Exception as e:
            self.log(f"테스트 오류: {e}")
            import traceback
            traceback.print_exc()
            input("오류 확인 후 Enter...")

        finally:
            self.close_browser()


def main():
    """메인 함수"""
    print("=" * 60)
    print("네이버 블로그 예약발행 테스트")
    print("=" * 60)

    # 계정 정보 가져오기 (현금화 그룹)
    account_manager = AccountManager()
    accounts = account_manager.get_accounts_by_group('현금화', active_only=True)

    if not accounts:
        print("현금화 그룹에 활성 계정이 없습니다.")
        return

    # 첫 번째 계정 사용
    account = accounts[0]
    naver_id = account['account_id']
    naver_pw = account['password']

    print(f"\n사용할 계정: {naver_id}")
    print(f"비밀번호: {'*' * len(naver_pw)}")

    # 예약 시간 입력
    print("\n예약 시간 입력 (Enter = 현재 + 1시간)")
    print("형식: YYYY-MM-DD HH:MM (예: 2025-12-20 14:30)")
    time_input = input("예약 시간: ").strip()

    if time_input:
        try:
            scheduled_time = datetime.strptime(time_input, "%Y-%m-%d %H:%M")
        except:
            print("잘못된 형식입니다. 기본값 사용 (현재 + 1시간)")
            scheduled_time = None
    else:
        scheduled_time = None

    # 테스트 실행
    tester = ScheduledPublishTest()
    tester.run_test(naver_id, naver_pw, scheduled_time)


if __name__ == '__main__':
    main()
