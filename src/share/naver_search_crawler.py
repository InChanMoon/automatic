"""
네이버 검색 크롤러 (Playwright 기반)

로그인 → 키워드 검색 → 블로그 탭 → 최신순 → 링크 수집
성인인증 필요 키워드도 검색 가능
"""

import re
import time
import random
from typing import List, Dict, Set, Optional, Callable, Tuple
from urllib.parse import urlparse, urlencode, quote
from datetime import datetime

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from playwright_stealth import stealth_sync


class NaverSearchCrawler:
    """네이버 모바일 검색 크롤러 (로그인 지원)"""

    # URL
    URLS = {
        "login": "https://nid.naver.com/nidlogin.login?svctype=262144",
        "search": "https://m.search.naver.com/search.naver",
    }

    # 셀렉터
    SELECTORS = {
        # 로그인
        "id_input": "#id",
        "pw_input": "#pw",
        "login_button": ".btn_login, #log\\.login, button[type='submit']",

        # 검색
        "search_input": "#query, input[name='query']",
        "search_button": ".bt_search, button[type='submit']",

        # 블로그 탭 (검색 결과 페이지)
        "blog_tab": "a[href*='where=blog'], a.tab_item[data-tab='blog'], div.flick_bx a:has-text('블로그')",

        # 최신순 정렬
        "sort_options": ".option_filter, .filter_area, .sp_nearch",
        "sort_latest": "a:has-text('최신순'), a[data-value='date'], button:has-text('최신순')",
        "sort_relevance": "a:has-text('관련도순'), a[data-value='sim']",

        # 블로그 검색 결과
        "blog_items": ".total_wrap, .blog_item, .list_info",
        "blog_link": "a[href*='blog.naver.com']",
        "blog_title": ".total_tit, .title_link, .tit",
    }

    # 태블릿 설정
    TABLET_VIEWPORT = {"width": 768, "height": 1024}
    TABLET_USER_AGENT = "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        self.is_logged_in = False
        self.current_account: Optional[str] = None

        # 현재 검색 상태
        self.current_keyword: Optional[str] = None
        self.is_blog_tab_active = False
        self.is_latest_sort = False

        # 로그 콜백
        self.log_callback: Optional[Callable[[str], None]] = None

    def log(self, message: str):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [Crawler] {message}"
        print(log_msg)
        if self.log_callback:
            self.log_callback(message)

    def _random_delay(self, min_sec: float = 0.5, max_sec: float = 1.5):
        """랜덤 지연"""
        time.sleep(random.uniform(min_sec, max_sec))

    def _click_with_offset(self, element, max_offset: int = 5):
        """요소 클릭 (랜덤 오프셋)"""
        try:
            box = element.bounding_box()
            if box:
                center_x = box['x'] + box['width'] / 2
                center_y = box['y'] + box['height'] / 2
                offset_x = random.randint(-max_offset, max_offset)
                offset_y = random.randint(-max_offset, max_offset)
                self.page.mouse.click(center_x + offset_x, center_y + offset_y)
            else:
                element.click()
        except:
            element.click()

    # ==================== 브라우저 관리 ====================

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
            ]
        )

        self.context = self.browser.new_context(
            viewport=self.TABLET_VIEWPORT,
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            user_agent=self.TABLET_USER_AGENT,
            is_mobile=True,
            has_touch=True,
        )

        self.page = self.context.new_page()
        stealth_sync(self.page)

        self.log("브라우저 시작 완료")

    def close_browser(self):
        """브라우저 종료"""
        try:
            if self.page:
                self.page.close()
                self.page = None
            if self.context:
                self.context.close()
                self.context = None
            if self.browser:
                self.browser.close()
                self.browser = None
            if self.playwright:
                self.playwright.stop()
                self.playwright = None

            self.is_logged_in = False
            self.current_account = None
            self.current_keyword = None
            self.is_blog_tab_active = False
            self.is_latest_sort = False

            self.log("브라우저 종료")
        except Exception as e:
            self.log(f"브라우저 종료 오류: {e}")

    # ==================== 로그인 ====================

    def login(self, account_id: str, password: str) -> Dict:
        """
        네이버 로그인

        Args:
            account_id: 네이버 아이디
            password: 비밀번호

        Returns:
            dict: {success: bool, reason: str}
        """
        if not self.page:
            self.start_browser()

        self.log(f"로그인 시도: {account_id}")

        try:
            self.page.goto(self.URLS["login"])
            self._random_delay(2, 3)

            # 아이디 입력
            self.page.wait_for_selector(self.SELECTORS["id_input"], timeout=15000)
            id_input = self.page.query_selector(self.SELECTORS["id_input"])
            self._click_with_offset(id_input)
            self._random_delay(0.3, 0.5)
            self.page.keyboard.type(account_id, delay=random.randint(50, 100))
            self._random_delay(0.3, 0.5)

            # 비밀번호 입력
            pw_input = self.page.query_selector(self.SELECTORS["pw_input"])
            self._click_with_offset(pw_input)
            self._random_delay(0.3, 0.5)
            self.page.keyboard.type(password, delay=random.randint(50, 100))
            self._random_delay(0.5, 1.0)

            # 로그인 버튼 클릭
            login_btn = self.page.query_selector(self.SELECTORS["login_button"])
            if login_btn:
                self._click_with_offset(login_btn)
            else:
                self.page.keyboard.press("Enter")

            self._random_delay(3, 5)

            # 로그인 성공 확인
            try:
                self.page.wait_for_url(
                    lambda url: "nid.naver.com" not in url,
                    timeout=15000
                )
                self.is_logged_in = True
                self.current_account = account_id
                self.log(f"로그인 성공: {account_id}")
                return {'success': True, 'reason': ''}

            except:
                # 캡차 또는 보호조치 확인
                if self._detect_captcha():
                    self.log("캡차 감지됨")
                    return {'success': False, 'reason': '캡차 필요'}

                if self._check_protection():
                    self.log("계정 보호조치 감지됨")
                    return {'success': False, 'reason': '계정 보호조치'}

                self.log("로그인 실패")
                return {'success': False, 'reason': '로그인 실패'}

        except Exception as e:
            self.log(f"로그인 오류: {e}")
            return {'success': False, 'reason': str(e)}

    def _detect_captcha(self) -> bool:
        """캡차 감지"""
        try:
            selectors = ["#captcha", "input[name='captcha']", "#captchaimg", ".captcha_wrap"]
            for sel in selectors:
                if self.page.query_selector(sel):
                    return True
            return False
        except:
            return False

    def _check_protection(self) -> bool:
        """계정 보호조치 감지"""
        try:
            url = self.page.url
            keywords = ['보호조치', '스팸', '제한', 'restrict', 'protect']
            if any(kw in url for kw in keywords):
                return True

            text = self.page.inner_text("body") if self.page.query_selector("body") else ""
            if any(kw in text for kw in ['보호조치', '스팸성', '계정 보호']):
                return True

            return False
        except:
            return False

    # ==================== 검색 ====================

    def search_keyword(self, keyword: str) -> bool:
        """
        키워드 검색 실행

        Args:
            keyword: 검색 키워드

        Returns:
            bool: 성공 여부
        """
        if not self.page:
            self.log("브라우저가 시작되지 않음")
            return False

        self.log(f"검색: {keyword}")

        try:
            # 검색 URL로 이동
            search_url = f"{self.URLS['search']}?query={quote(keyword)}"
            self.page.goto(search_url)
            self._random_delay(2, 3)

            self.page.wait_for_load_state("networkidle", timeout=15000)

            self.current_keyword = keyword
            self.is_blog_tab_active = False
            self.is_latest_sort = False

            self.log(f"검색 완료: {keyword}")
            return True

        except Exception as e:
            self.log(f"검색 오류: {e}")
            return False

    def click_blog_tab(self) -> bool:
        """
        블로그 탭 클릭

        Returns:
            bool: 성공 여부
        """
        self.log("블로그 탭 클릭 시도...")

        try:
            # 블로그 탭 찾기 (여러 셀렉터 시도)
            blog_tab_selectors = [
                "a[href*='where=blog']",
                "a.tab[data-tab='blog']",
                "div.flick_bx a:has-text('블로그')",
                "a:has-text('블로그')",
                "button:has-text('블로그')",
            ]

            blog_tab = None
            for selector in blog_tab_selectors:
                try:
                    elem = self.page.query_selector(selector)
                    if elem and elem.is_visible():
                        blog_tab = elem
                        break
                except:
                    continue

            if not blog_tab:
                # 스크롤해서 탭 찾기
                self.page.evaluate("window.scrollTo(0, 0)")
                self._random_delay(0.5, 1)

                for selector in blog_tab_selectors:
                    try:
                        elem = self.page.wait_for_selector(selector, timeout=3000)
                        if elem and elem.is_visible():
                            blog_tab = elem
                            break
                    except:
                        continue

            if not blog_tab:
                self.log("블로그 탭을 찾을 수 없음")
                return False

            self._click_with_offset(blog_tab)
            self._random_delay(2, 3)

            self.page.wait_for_load_state("networkidle", timeout=15000)
            self.is_blog_tab_active = True
            self.is_latest_sort = False  # 탭 이동하면 정렬 초기화

            self.log("블로그 탭 클릭 완료")
            return True

        except Exception as e:
            self.log(f"블로그 탭 클릭 오류: {e}")
            return False

    def click_latest_sort(self) -> bool:
        """
        최신순 정렬 클릭

        Returns:
            bool: 성공 여부
        """
        self.log("최신순 클릭 시도...")

        try:
            # 최신순 버튼 찾기 (여러 셀렉터 시도)
            latest_selectors = [
                "a:has-text('최신순')",
                "button:has-text('최신순')",
                "a[data-value='date']",
                ".option_filter a:nth-child(2)",
                "span:has-text('최신순')",
            ]

            latest_btn = None
            for selector in latest_selectors:
                try:
                    elem = self.page.query_selector(selector)
                    if elem and elem.is_visible():
                        latest_btn = elem
                        break
                except:
                    continue

            if not latest_btn:
                # 스크롤해서 찾기
                self.page.evaluate("window.scrollTo(0, 0)")
                self._random_delay(0.5, 1)

                for selector in latest_selectors:
                    try:
                        elem = self.page.wait_for_selector(selector, timeout=3000)
                        if elem and elem.is_visible():
                            latest_btn = elem
                            break
                    except:
                        continue

            if not latest_btn:
                self.log("최신순 버튼을 찾을 수 없음")
                return False

            self._click_with_offset(latest_btn)
            self._random_delay(2, 3)

            self.page.wait_for_load_state("networkidle", timeout=15000)
            self.is_latest_sort = True

            self.log("최신순 클릭 완료")
            return True

        except Exception as e:
            self.log(f"최신순 클릭 오류: {e}")
            return False

    def refresh_results(self) -> bool:
        """
        현재 검색 결과 새로고침 (최신순 유지)

        Returns:
            bool: 성공 여부
        """
        self.log("검색 결과 새로고침...")

        try:
            self.page.reload()
            self._random_delay(2, 3)
            self.page.wait_for_load_state("networkidle", timeout=15000)

            self.log("새로고침 완료")
            return True

        except Exception as e:
            self.log(f"새로고침 오류: {e}")
            return False

    # ==================== 결과 수집 ====================

    def collect_blog_links(self, max_results: int = 30) -> List[Dict]:
        """
        현재 페이지에서 블로그 링크 수집

        Args:
            max_results: 최대 수집 개수

        Returns:
            list: [{'title': str, 'link': str, 'blog_id': str, 'log_no': str}, ...]
        """
        self.log("블로그 링크 수집 중...")

        posts = []
        seen_links = set()

        try:
            # 스크롤해서 더 많은 결과 로드
            self._scroll_for_more_results(max_results)

            # 모든 블로그 링크 찾기
            links = self.page.query_selector_all('a[href*="blog.naver.com"]')

            for link in links:
                try:
                    href = link.get_attribute('href')
                    if not href or 'blog.naver.com' not in href:
                        continue

                    # URL 파싱
                    blog_id, log_no = self.extract_blog_id_from_url(href)
                    if not blog_id or not log_no:
                        continue

                    # 모바일 URL로 정규화
                    normalized_link = f"https://m.blog.naver.com/{blog_id}/{log_no}"

                    # 중복 제거
                    if normalized_link in seen_links:
                        continue
                    seen_links.add(normalized_link)

                    # 제목 추출
                    title = self._extract_title_from_link(link)

                    posts.append({
                        'title': title,
                        'link': normalized_link,
                        'blog_id': blog_id,
                        'log_no': log_no,
                    })

                    if len(posts) >= max_results:
                        break

                except Exception:
                    continue

            self.log(f"수집 완료: {len(posts)}개")

        except Exception as e:
            self.log(f"수집 오류: {e}")

        return posts

    def _scroll_for_more_results(self, target_count: int):
        """더 많은 결과를 위해 스크롤"""
        scroll_count = 0
        max_scrolls = 5

        while scroll_count < max_scrolls:
            links = self.page.query_selector_all('a[href*="blog.naver.com"]')
            if len(links) >= target_count:
                break

            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self._random_delay(1, 2)
            scroll_count += 1

    def _extract_title_from_link(self, link_element) -> str:
        """링크 요소에서 제목 추출"""
        try:
            title = link_element.inner_text()
            if title and len(title.strip()) > 3:
                return title.strip()

            parent = link_element.evaluate_handle("el => el.parentElement")
            if parent:
                title_elem = parent.query_selector('.title, .tit, .title_link, h3, h4')
                if title_elem:
                    return title_elem.inner_text().strip()
        except:
            pass

        return "(제목 없음)"

    def extract_blog_id_from_url(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        블로그 URL에서 blog_id와 log_no 추출

        Returns:
            tuple: (blog_id, log_no) 또는 (None, None)
        """
        try:
            # 쿼리 파라미터 방식
            if 'blogId=' in url and 'logNo=' in url:
                blog_id_match = re.search(r'blogId=([^&]+)', url)
                log_no_match = re.search(r'logNo=(\d+)', url)
                if blog_id_match and log_no_match:
                    return blog_id_match.group(1), log_no_match.group(1)

            # 경로 방식
            parsed = urlparse(url)
            if 'blog.naver.com' in parsed.netloc:
                path_parts = parsed.path.strip('/').split('/')
                if len(path_parts) >= 2:
                    blog_id = path_parts[0]
                    log_no = path_parts[1].split('?')[0]

                    if blog_id and log_no and log_no.isdigit():
                        return blog_id, log_no

            return None, None

        except Exception:
            return None, None

    def filter_by_account_ids(self, posts: List[Dict], account_ids: Set[str]) -> List[Dict]:
        """우리 계정의 글만 필터링"""
        return [post for post in posts if post.get('blog_id') in account_ids]

    # ==================== 통합 메서드 ====================

    def search_and_collect(
        self,
        keyword: str,
        max_results: int = 30
    ) -> List[Dict]:
        """
        검색 → 블로그 탭 → 최신순 → 수집 (통합)

        Args:
            keyword: 검색 키워드
            max_results: 최대 수집 개수

        Returns:
            list: 블로그 글 목록
        """
        # 1. 키워드 검색
        if not self.search_keyword(keyword):
            return []

        # 2. 블로그 탭 클릭
        if not self.click_blog_tab():
            return []

        # 3. 최신순 클릭
        if not self.click_latest_sort():
            self.log("최신순 클릭 실패 - 관련도순으로 진행")

        # 4. 링크 수집
        return self.collect_blog_links(max_results)


if __name__ == "__main__":
    # 테스트
    crawler = NaverSearchCrawler(headless=False)

    try:
        crawler.start_browser()

        # 테스트 계정으로 로그인 필요
        # login_result = crawler.login("your_id", "your_pw")
        # if not login_result['success']:
        #     print(f"로그인 실패: {login_result['reason']}")
        #     exit()

        # 검색 테스트
        keyword = "소액결제 현금화"
        print(f"\n검색어: {keyword}")
        print("-" * 50)

        posts = crawler.search_and_collect(keyword, max_results=10)

        for i, post in enumerate(posts, 1):
            print(f"{i}. {post['title'][:40]}")
            print(f"   블로그ID: {post['blog_id']}")
            print(f"   링크: {post['link']}")
            print()

        input("엔터를 누르면 종료합니다...")

    finally:
        crawler.close_browser()
