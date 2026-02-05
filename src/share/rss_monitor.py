"""
RSS 모니터링 모듈

블로그 RSS 피드를 주기적으로 확인하여 새 글을 감지합니다.
"""

import time
import threading
import xml.etree.ElementTree as ET
from typing import Callable, List, Dict, Set, Optional
from datetime import datetime
from urllib.parse import urlparse

import requests


class RSSMonitor:
    """RSS 피드 모니터링 클래스"""

    def __init__(self, interval_minutes: int = 30):
        """
        Args:
            interval_minutes: RSS 확인 간격 (분)
        """
        self.interval = interval_minutes
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None

        # 모니터링 대상 블로그들
        self.blog_ids: Set[str] = set()

        # 이미 처리한 글 URL (중복 방지)
        self.known_posts: Set[str] = set()

        # 콜백 함수
        self.on_new_posts: Optional[Callable[[List[Dict]], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None

        # HTTP 헤더
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def log(self, message: str):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [RSS] {message}"
        print(log_msg)
        if self.on_log:
            self.on_log(message)

    def add_blog(self, blog_id: str):
        """모니터링할 블로그 추가"""
        blog_id = blog_id.strip()
        if blog_id:
            self.blog_ids.add(blog_id)
            self.log(f"블로그 추가: {blog_id}")

    def remove_blog(self, blog_id: str):
        """블로그 제거"""
        self.blog_ids.discard(blog_id)
        self.log(f"블로그 제거: {blog_id}")

    def clear_blogs(self):
        """모든 블로그 제거"""
        self.blog_ids.clear()
        self.known_posts.clear()

    def get_blog_id_from_url(self, blog_url: str) -> Optional[str]:
        """
        블로그 URL에서 블로그 ID 추출

        예: https://blog.naver.com/sunny12221 -> sunny12221
        예: https://blog.naver.com/sunny12221/224107556066 -> sunny12221
        """
        try:
            parsed = urlparse(blog_url)
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 1 and path_parts[0]:
                return path_parts[0]
            return None
        except:
            return None

    def get_rss_feed(self, blog_id: str) -> List[Dict]:
        """
        RSS Atom 피드 가져오기

        Args:
            blog_id: 블로그 ID (예: sunny12221)

        Returns:
            list: [{'title': str, 'link': str, 'published': str}, ...]
        """
        rss_url = f"https://rss.blog.naver.com/{blog_id}.xml?atom=0.3"

        try:
            response = requests.get(rss_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            ns = {'atom': 'http://purl.org/atom/ns#'}

            entries = []
            for entry in root.findall('.//atom:entry', ns):
                title_elem = entry.find('atom:title', ns)
                link_elem = entry.find('atom:link', ns)
                issued_elem = entry.find('atom:issued', ns)

                if title_elem is not None and link_elem is not None:
                    link_text = link_elem.text or ''
                    link_text = link_text.split('?')[0]  # 쿼리 파라미터 제거

                    entries.append({
                        'title': title_elem.text or '',
                        'link': link_text,
                        'published': issued_elem.text if issued_elem is not None else '',
                        'blog_id': blog_id
                    })

            return entries

        except Exception as e:
            self.log(f"RSS 피드 가져오기 실패 ({blog_id}): {e}")
            if self.on_error:
                self.on_error(f"RSS 오류: {e}")
            return []

    def check_all_blogs(self) -> List[Dict]:
        """모든 블로그의 새 글 확인"""
        new_posts = []

        for blog_id in list(self.blog_ids):
            entries = self.get_rss_feed(blog_id)

            for entry in entries:
                link = entry['link']
                if link and link not in self.known_posts:
                    self.known_posts.add(link)
                    new_posts.append(entry)

        return new_posts

    def initialize_known_posts(self):
        """기존 글들을 known_posts에 등록 (초기화)"""
        self.log("기존 글 목록 초기화 중...")

        for blog_id in list(self.blog_ids):
            entries = self.get_rss_feed(blog_id)
            for entry in entries:
                if entry['link']:
                    self.known_posts.add(entry['link'])

        self.log(f"기존 글 {len(self.known_posts)}개 등록됨")

    def start_monitoring(self):
        """모니터링 시작 (백그라운드 스레드)"""
        if self.is_running:
            self.log("이미 모니터링 중입니다")
            return

        if not self.blog_ids:
            self.log("모니터링할 블로그가 없습니다")
            return

        self.is_running = True

        # 기존 글 초기화
        self.initialize_known_posts()

        # 백그라운드 스레드 시작
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        self.log(f"RSS 모니터링 시작 (간격: {self.interval}분)")

    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_running = False
        self.log("RSS 모니터링 중지됨")

    def _monitor_loop(self):
        """모니터링 루프 (백그라운드)"""
        while self.is_running:
            try:
                # 새 글 확인
                new_posts = self.check_all_blogs()

                if new_posts:
                    self.log(f"새 글 {len(new_posts)}개 발견!")
                    if self.on_new_posts:
                        self.on_new_posts(new_posts)

                # 대기
                for _ in range(self.interval * 60):
                    if not self.is_running:
                        break
                    time.sleep(1)

            except Exception as e:
                self.log(f"모니터링 오류: {e}")
                time.sleep(60)  # 오류 시 1분 대기

    def check_once(self) -> List[Dict]:
        """
        한 번만 RSS 확인 (수동 확인용)

        Returns:
            모든 글 목록 (새 글 여부 무관)
        """
        all_posts = []

        for blog_id in list(self.blog_ids):
            entries = self.get_rss_feed(blog_id)
            all_posts.extend(entries)

        return all_posts

    def get_posts_by_blog(self, blog_id: str) -> List[Dict]:
        """특정 블로그의 글 목록 가져오기"""
        return self.get_rss_feed(blog_id)
