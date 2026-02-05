"""
네이버 블로그 공유봇 V2

키워드 검색 기반 블로그 공유 자동화 프로그램
- 자동 로그인 (공유계정 첫 번째)
- 키워드 검색 → 블로그 탭 → 최신순 → 우리 글 필터링
- 수집 모드: 일정 시간 수집 후 일괄 공유
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set

import keyboard
import requests

from src.share.share_engine import ShareEngine
from src.share.naver_search_crawler import NaverSearchCrawler
from src.sheets.share_manager import ShareManager
from src.ui.theme import Theme


class ShareBotV2:
    """공유봇 V2 - 수집 모드 + 일괄 공유"""

    VERSION = "2.1"
    CONFIG_FILE = "share_config_v2.json"
    IP_SETTINGS_FILE = "ip_settings.json"

    def __init__(self, root):
        self.root = root
        self.root.title(f"블로그 공유봇 v{self.VERSION}")
        self.root.geometry("1200x850")
        self.root.configure(bg=Theme.BG_MAIN)

        # 매니저
        self.share_mgr: Optional[ShareManager] = None
        self.share_accounts: List[Dict] = []  # 공유계정 목록

        # 크롤러/엔진 (브라우저 세션 유지)
        self.crawler: Optional[NaverSearchCrawler] = None
        self.engine: Optional[ShareEngine] = None

        # 상태
        self.is_running = False
        self.is_collecting = False  # 수집 모드 활성화
        self.stop_requested = False

        # 검색 결과
        self.current_keyword = ""
        self.current_posts: List[Dict] = []
        self.post_selections: Dict[int, tk.BooleanVar] = {}
        self.known_links: Set[str] = set()  # 이미 처리한 링크

        # 수집된 링크 (일괄 공유용)
        self.collected_links: List[Dict] = []  # {'keyword': str, 'link': str, 'title': str, 'blog_id': str}
        self.collection_start_time: Optional[datetime] = None

        # 설정 변수
        self.search_account_id = tk.StringVar()
        self.search_account_pw = tk.StringVar()
        self.headless_var = tk.BooleanVar(value=False)
        self.target_group = tk.StringVar(value="소액결제현금화")
        self.monitor_interval = tk.IntVar(value=60)  # 모니터링 간격 (초)
        self.collection_duration = tk.IntVar(value=30)  # 수집 시간 (분)

        # IP 변경 설정
        self.ip_change_enabled = tk.BooleanVar(value=False)
        self.ip_hotkey = tk.StringVar(value="")
        self.ip_wait_time = tk.IntVar(value=3)

        # 신고 사유 설정
        self.report_reason = tk.StringVar(value="illegal")  # "illegal" 또는 "spam"

        # 통계
        self.stats = {
            'searched': 0,
            'filtered': 0,
            'collected': 0,
            'shared': 0,
            'reported': 0,
            'skipped': 0,
            'failed': 0,
        }

        self.setup_ui()
        self.load_config()
        self.load_ip_settings()
        self.init_managers()

    def init_managers(self):
        """매니저 초기화 및 자동 로그인 준비"""
        def do_init():
            try:
                self.share_mgr = ShareManager()
                self.root.after(0, lambda: self.log("시트 매니저 초기화 완료", 'success'))

                # 타겟 그룹 목록 로드
                groups = self.share_mgr.get_account_groups()
                if groups:
                    self.root.after(0, lambda: self.update_group_combo(groups))

                # 공유계정 목록 로드
                self.share_accounts = self.share_mgr.get_share_accounts()
                if self.share_accounts:
                    self.root.after(0, lambda: self.update_account_info())
                    self.root.after(0, lambda: self.log(f"공유계정 {len(self.share_accounts)}개 로드됨", 'info'))

            except Exception as e:
                self.root.after(0, lambda: self.log(f"초기화 오류: {e}", 'error'))

        threading.Thread(target=do_init, daemon=True).start()

    def update_group_combo(self, groups: List[str]):
        """타겟 그룹 콤보박스 업데이트"""
        self.group_combo['values'] = groups
        if groups and not self.target_group.get():
            self.target_group.set(groups[0])

    def update_account_info(self):
        """검색 계정 정보 업데이트 (첫 번째 계정 자동 선택)"""
        if self.share_accounts:
            first_acc = self.share_accounts[0]
            self.search_account_id.set(first_acc['id'])
            self.search_account_pw.set(first_acc['pw'])
            self.search_account_label.config(text=f"검색 계정: {first_acc['id']}")

    # ==================== UI 구성 ====================

    def setup_ui(self):
        """UI 구성"""
        self._setup_top_bar()
        self._setup_main_area()
        self._setup_status_bar()

    def _setup_top_bar(self):
        """상단 컨트롤 바"""
        top = tk.Frame(self.root, bg=Theme.BG_MAIN)
        top.pack(fill='x', padx=8, pady=4)

        # === 검색 계정 (자동 선택됨) ===
        acc_frame = tk.LabelFrame(top, text="검색 계정 (자동)", bg=Theme.BG_MAIN, font=Theme.FONT_SMALL_BOLD)
        acc_frame.pack(side='left', padx=5, pady=2)

        self.search_account_label = tk.Label(acc_frame, text="로딩 중...", bg=Theme.BG_MAIN,
                                              font=Theme.FONT_SMALL)
        self.search_account_label.pack(side='left', padx=5)

        # 로그인 버튼
        self.login_btn = tk.Button(acc_frame, text="로그인", command=self.do_login,
                                   bg=Theme.COLOR_INFO, fg='white', font=Theme.FONT_SMALL,
                                   relief='flat', padx=8)
        self.login_btn.pack(side='left', padx=5)

        self.login_status = tk.Label(acc_frame, text="미로그인", bg=Theme.BG_MAIN,
                                     fg=Theme.COLOR_ERROR, font=Theme.FONT_SMALL_BOLD)
        self.login_status.pack(side='left', padx=5)

        # === 타겟 그룹 ===
        group_frame = tk.LabelFrame(top, text="타겟 그룹", bg=Theme.BG_MAIN, font=Theme.FONT_SMALL_BOLD)
        group_frame.pack(side='left', padx=5, pady=2)

        self.group_combo = ttk.Combobox(group_frame, textvariable=self.target_group,
                                        width=15, state='readonly', font=Theme.FONT_SMALL)
        self.group_combo.pack(side='left', padx=5, pady=2)

        # === 옵션 ===
        opt_frame = tk.LabelFrame(top, text="옵션", bg=Theme.BG_MAIN, font=Theme.FONT_SMALL_BOLD)
        opt_frame.pack(side='left', padx=5, pady=2)

        ttk.Checkbutton(opt_frame, text="헤드리스", variable=self.headless_var).pack(side='left', padx=3)
        ttk.Checkbutton(opt_frame, text="IP변경", variable=self.ip_change_enabled).pack(side='left', padx=3)
        tk.Button(opt_frame, text="⚙", command=self.open_ip_settings,
                  bg=Theme.COLOR_GRAY, fg='white', font=Theme.FONT_TINY,
                  relief='flat', padx=3).pack(side='left')

        # === 상태 ===
        self.status_label = tk.Label(top, text="대기 중", bg=Theme.BG_MAIN, fg=Theme.FG_TEXT_LIGHT,
                                     font=Theme.FONT_SMALL_BOLD)
        self.status_label.pack(side='right', padx=10)

    def _setup_main_area(self):
        """메인 영역"""
        main = tk.PanedWindow(self.root, orient='horizontal', bg=Theme.BG_MAIN, sashwidth=4)
        main.pack(fill='both', expand=True, padx=8, pady=4)

        # 좌측: 검색 + 결과
        left = tk.Frame(main, bg=Theme.BG_WHITE)
        main.add(left, width=600)

        # 우측: 로그
        right = tk.Frame(main, bg=Theme.BG_WHITE)
        main.add(right, width=500)

        self._setup_left_panel(left)
        self._setup_right_panel(right)

    def _setup_left_panel(self, parent):
        """좌측 패널"""
        # === 검색 영역 ===
        search_frame = tk.LabelFrame(parent, text="키워드 검색", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL_BOLD)
        search_frame.pack(fill='x', padx=5, pady=5)

        # 키워드 입력
        kw_row = tk.Frame(search_frame, bg=Theme.BG_WHITE)
        kw_row.pack(fill='x', padx=5, pady=5)

        self.keyword_entry = tk.Entry(kw_row, font=('맑은 고딕', 11), width=30)
        self.keyword_entry.pack(side='left', fill='x', expand=True)
        self.keyword_entry.bind('<Return>', lambda e: self.do_search())

        tk.Button(kw_row, text="🔍 검색", command=self.do_search,
                  bg=Theme.COLOR_INFO, fg='white', font=Theme.FONT_SMALL_BOLD,
                  relief='flat', padx=10).pack(side='left', padx=5)

        # === 수집 모드 설정 ===
        collect_frame = tk.LabelFrame(parent, text="수집 모드", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL_BOLD)
        collect_frame.pack(fill='x', padx=5, pady=5)

        # 설정 행
        setting_row = tk.Frame(collect_frame, bg=Theme.BG_WHITE)
        setting_row.pack(fill='x', padx=5, pady=3)

        tk.Label(setting_row, text="수집 시간:", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL).pack(side='left')
        tk.Spinbox(setting_row, from_=5, to=120, width=5, textvariable=self.collection_duration,
                   font=Theme.FONT_SMALL, justify='center').pack(side='left', padx=2)
        tk.Label(setting_row, text="분", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL).pack(side='left', padx=(0, 15))

        tk.Label(setting_row, text="모니터링 간격:", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL).pack(side='left')
        tk.Spinbox(setting_row, from_=30, to=300, width=5, textvariable=self.monitor_interval,
                   font=Theme.FONT_SMALL, justify='center').pack(side='left', padx=2)
        tk.Label(setting_row, text="초", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL).pack(side='left')

        # 버튼 행
        btn_row = tk.Frame(collect_frame, bg=Theme.BG_WHITE)
        btn_row.pack(fill='x', padx=5, pady=5)

        self.collect_btn = tk.Button(btn_row, text="▶ 수집 시작", command=self.start_collection,
                                     bg=Theme.COLOR_SUCCESS, fg='white', font=Theme.FONT_SMALL_BOLD,
                                     relief='flat', padx=15)
        self.collect_btn.pack(side='left', padx=5)

        self.stop_collect_btn = tk.Button(btn_row, text="■ 수집 중지", command=self.stop_collection,
                                          bg=Theme.COLOR_ERROR, fg='white', font=Theme.FONT_SMALL_BOLD,
                                          relief='flat', padx=10, state='disabled')
        self.stop_collect_btn.pack(side='left', padx=5)

        # 수집 상태 표시
        self.collect_status_label = tk.Label(btn_row, text="", bg=Theme.BG_WHITE,
                                              font=Theme.FONT_SMALL, fg=Theme.FG_TEXT_LIGHT)
        self.collect_status_label.pack(side='left', padx=10)

        # 남은 시간 표시
        self.time_remaining_label = tk.Label(btn_row, text="", bg=Theme.BG_WHITE,
                                              font=Theme.FONT_SMALL_BOLD, fg=Theme.COLOR_INFO)
        self.time_remaining_label.pack(side='right', padx=5)

        # === 수집된 링크 ===
        result_frame = tk.LabelFrame(parent, text="수집된 링크", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL_BOLD)
        result_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # 헤더
        result_header = tk.Frame(result_frame, bg=Theme.BG_WHITE)
        result_header.pack(fill='x', padx=5, pady=2)

        self.collected_count_label = tk.Label(result_header, text="수집: 0개", bg=Theme.BG_WHITE,
                                               font=Theme.FONT_SMALL, fg=Theme.FG_TEXT_LIGHT)
        self.collected_count_label.pack(side='left')

        tk.Button(result_header, text="목록 초기화", command=self.clear_collected_links,
                  bg=Theme.COLOR_GRAY, fg='white', font=Theme.FONT_TINY,
                  relief='flat', padx=6).pack(side='right')

        # 트리뷰
        cols = ('keyword', 'title', 'blog_id', 'status')
        self.result_tree = ttk.Treeview(result_frame, columns=cols, show='headings', height=15)

        self.result_tree.heading('keyword', text='키워드')
        self.result_tree.heading('title', text='제목')
        self.result_tree.heading('blog_id', text='블로그ID')
        self.result_tree.heading('status', text='상태')

        self.result_tree.column('keyword', width=100)
        self.result_tree.column('title', width=280)
        self.result_tree.column('blog_id', width=100)
        self.result_tree.column('status', width=80, anchor='center')

        vsb = ttk.Scrollbar(result_frame, orient='vertical', command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=vsb.set)

        self.result_tree.pack(side='left', fill='both', expand=True, padx=(5, 0), pady=5)
        vsb.pack(side='right', fill='y', pady=5, padx=(0, 5))

        self.result_tree.tag_configure('pending', foreground=Theme.FG_TEXT)
        self.result_tree.tag_configure('processing', foreground=Theme.COLOR_WARNING)
        self.result_tree.tag_configure('done', foreground=Theme.COLOR_SUCCESS)

        # === 일괄 공유/신고 버튼 ===
        btn_frame = tk.Frame(parent, bg=Theme.BG_WHITE)
        btn_frame.pack(fill='x', padx=5, pady=5)

        self.share_btn = tk.Button(btn_frame, text="▶ 일괄 공유", command=self.start_batch_sharing,
                                   bg=Theme.COLOR_SUCCESS, fg='white', font=Theme.FONT_SMALL_BOLD,
                                   relief='flat', padx=12, pady=5)
        self.share_btn.pack(side='left', padx=3)

        self.report_btn = tk.Button(btn_frame, text="⚠ 일괄 신고", command=self.start_batch_reporting,
                                    bg=Theme.COLOR_WARNING, fg='white', font=Theme.FONT_SMALL_BOLD,
                                    relief='flat', padx=12, pady=5)
        self.report_btn.pack(side='left', padx=3)

        # 신고 사유 선택
        reason_frame = tk.Frame(btn_frame, bg=Theme.BG_WHITE)
        reason_frame.pack(side='left', padx=10)
        tk.Radiobutton(reason_frame, text="불법정보", variable=self.report_reason, value="illegal",
                       bg=Theme.BG_WHITE, font=Theme.FONT_TINY).pack(side='left')
        tk.Radiobutton(reason_frame, text="스팸홍보", variable=self.report_reason, value="spam",
                       bg=Theme.BG_WHITE, font=Theme.FONT_TINY).pack(side='left')

        self.stop_btn = tk.Button(btn_frame, text="■ 중지", command=self.stop_all,
                                  bg=Theme.COLOR_ERROR, fg='white', font=Theme.FONT_SMALL_BOLD,
                                  relief='flat', padx=12, pady=5, state='disabled')
        self.stop_btn.pack(side='left', padx=3)

        tk.Button(btn_frame, text="브라우저 종료", command=self.close_browsers,
                  bg=Theme.COLOR_GRAY, fg='white', font=Theme.FONT_SMALL,
                  relief='flat', padx=10).pack(side='right', padx=5)

    def _setup_right_panel(self, parent):
        """우측 패널: 로그"""
        log_header = tk.Frame(parent, bg=Theme.BG_WHITE)
        log_header.pack(fill='x', padx=5, pady=3)

        tk.Label(log_header, text="로그", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL_BOLD).pack(side='left')
        tk.Button(log_header, text="지우기", command=self.clear_log,
                  bg=Theme.COLOR_GRAY, fg='white', font=Theme.FONT_TINY,
                  relief='flat', padx=6).pack(side='right')

        self.log_text = scrolledtext.ScrolledText(parent, font=Theme.FONT_LOG, wrap='word',
                                                   bg=Theme.BG_DARK, fg=Theme.FG_TEXT_DARK)
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)

        self.log_text.tag_config('info', foreground=Theme.FG_TEXT_DARK)
        self.log_text.tag_config('success', foreground=Theme.COLOR_SUCCESS)
        self.log_text.tag_config('error', foreground=Theme.COLOR_ERROR)
        self.log_text.tag_config('warning', foreground=Theme.COLOR_WARNING)

    def _setup_status_bar(self):
        """하단 상태 바"""
        bottom = tk.Frame(self.root, bg=Theme.BG_WHITE)
        bottom.pack(fill='x', padx=8, pady=4)

        stats_frame = tk.Frame(bottom, bg=Theme.BG_WHITE)
        stats_frame.pack(fill='x', padx=5, pady=3)

        self.stats_label = tk.Label(stats_frame,
                                    text="검색: 0 | 필터링: 0 | 공유: 0 | 건너뜀: 0 | 실패: 0",
                                    bg=Theme.BG_WHITE, font=Theme.FONT_SMALL)
        self.stats_label.pack(side='left', padx=10)

        self.current_task_label = tk.Label(stats_frame, text="", bg=Theme.BG_WHITE,
                                           font=Theme.FONT_SMALL, fg=Theme.FG_TEXT_LIGHT)
        self.current_task_label.pack(side='right', padx=10)

        self.progress_bar = ttk.Progressbar(bottom, mode='determinate', length=400)
        self.progress_bar.pack(fill='x', padx=5, pady=3)

    # ==================== 로그인 (공유계정 첫 번째 자동 사용) ====================

    def do_login(self):
        """로그인 실행 (공유계정 첫 번째)"""
        if not self.share_accounts:
            messagebox.showwarning("경고", "공유계정을 로드하지 못했습니다")
            return

        account_id = self.search_account_id.get()
        account_pw = self.search_account_pw.get()

        if not account_id or not account_pw:
            messagebox.showwarning("경고", "계정 정보가 없습니다")
            return

        self.log(f"로그인 시도: {account_id}")
        self.login_btn.config(state='disabled')
        self.login_status.config(text="로그인 중...", fg=Theme.COLOR_WARNING)

        def do_login_thread():
            try:
                # 크롤러 생성 및 시작
                self.crawler = NaverSearchCrawler(headless=self.headless_var.get())
                self.crawler.log_callback = lambda msg: self.root.after(0, lambda: self.log(msg))
                self.crawler.start_browser()

                # 로그인
                result = self.crawler.login(account_id, account_pw)

                if result['success']:
                    self.root.after(0, lambda: self.login_status.config(text=f"로그인됨", fg=Theme.COLOR_SUCCESS))
                    self.root.after(0, lambda: self.log(f"로그인 성공: {account_id}", 'success'))
                else:
                    self.root.after(0, lambda: self.login_status.config(text="로그인 실패", fg=Theme.COLOR_ERROR))
                    self.root.after(0, lambda: self.log(f"로그인 실패: {result['reason']}", 'error'))
                    self.crawler.close_browser()
                    self.crawler = None

            except Exception as e:
                self.root.after(0, lambda: self.log(f"로그인 오류: {e}", 'error'))
                self.root.after(0, lambda: self.login_status.config(text="로그인 오류", fg=Theme.COLOR_ERROR))

            finally:
                self.root.after(0, lambda: self.login_btn.config(state='normal'))

        threading.Thread(target=do_login_thread, daemon=True).start()

    # ==================== 검색 (단일) ====================

    def do_search(self):
        """단일 검색 실행 (수집 목록에 추가)"""
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showwarning("경고", "키워드를 입력하세요")
            return

        if not self.crawler or not self.crawler.is_logged_in:
            messagebox.showwarning("경고", "먼저 로그인하세요")
            return

        if not self.share_mgr:
            messagebox.showwarning("경고", "초기화 중입니다")
            return

        self.log(f"검색: {keyword}")
        self.status_label.config(text="검색 중...", fg=Theme.COLOR_INFO)

        def do_search_thread():
            try:
                # 검색 실행 (블로그 탭 + 최신순)
                posts = self.crawler.search_and_collect(keyword, max_results=30)
                self.stats['searched'] += len(posts)
                self.root.after(0, lambda: self.log(f"검색 결과: {len(posts)}개"))

                # 타겟 그룹 계정 가져오기
                target_group = self.target_group.get()
                target_ids = self.share_mgr.get_target_account_ids(target_group)

                # 우리 글 필터링
                our_posts = self.crawler.filter_by_account_ids(posts, target_ids)
                self.stats['filtered'] += len(our_posts)
                self.root.after(0, lambda: self.log(f"우리 글: {len(our_posts)}개", 'success'))

                # 새 글만 수집 목록에 추가
                new_count = 0
                for post in our_posts:
                    link = post['link']
                    if link not in self.known_links:
                        self.known_links.add(link)

                        # 이미 시트에 있는 링크 제외
                        if not self.share_mgr.is_link_shared(link):
                            self.collected_links.append({
                                'keyword': keyword,
                                'link': link,
                                'title': post['title'],
                                'blog_id': post['blog_id'],
                                'status': 'pending'
                            })
                            new_count += 1

                if new_count > 0:
                    self.stats['collected'] += new_count
                    self.root.after(0, lambda: self.log(f"새 글 수집: {new_count}개", 'success'))
                    self.root.after(0, self._update_collected_tree)

                self.root.after(0, lambda: self.status_label.config(text="검색 완료", fg=Theme.COLOR_SUCCESS))
                self.root.after(0, self._update_stats_label)

            except Exception as e:
                self.root.after(0, lambda: self.log(f"검색 오류: {e}", 'error'))
                self.root.after(0, lambda: self.status_label.config(text="검색 오류", fg=Theme.COLOR_ERROR))

        threading.Thread(target=do_search_thread, daemon=True).start()

    def _update_collected_tree(self):
        """수집된 링크 트리뷰 업데이트"""
        self.result_tree.delete(*self.result_tree.get_children())

        for i, item in enumerate(self.collected_links):
            title = item['title'][:35] + "..." if len(item['title']) > 35 else item['title']

            status_text = {'pending': '대기', 'processing': '처리중', 'done': '완료'}.get(item['status'], item['status'])

            self.result_tree.insert('', 'end', iid=str(i), values=(
                item['keyword'],
                title,
                item['blog_id'],
                status_text
            ), tags=(item['status'],))

        self.collected_count_label.config(text=f"수집: {len(self.collected_links)}개")

    def clear_collected_links(self):
        """수집 목록 초기화"""
        if self.collected_links and not messagebox.askyesno("확인", "수집된 링크를 모두 삭제하시겠습니까?"):
            return

        self.collected_links = []
        self.known_links = set()
        self.stats['collected'] = 0
        self._update_collected_tree()
        self._update_stats_label()
        self.log("수집 목록 초기화됨")

    # ==================== 수집 모드 ====================

    def start_collection(self):
        """수집 시작 (지정 시간 동안 검색 + 수집)"""
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showwarning("경고", "키워드를 입력하세요")
            return

        if not self.crawler or not self.crawler.is_logged_in:
            messagebox.showwarning("경고", "먼저 로그인하세요")
            return

        if not self.share_mgr:
            messagebox.showwarning("경고", "초기화 중입니다")
            return

        self.is_collecting = True
        self.stop_requested = False
        self.collection_start_time = datetime.now()
        self.current_keyword = keyword

        self.collect_btn.config(state='disabled')
        self.stop_collect_btn.config(state='normal')
        self.collect_status_label.config(text=f"수집 중: {keyword}")

        duration = self.collection_duration.get()
        self.log(f"=== 수집 시작 ===", 'success')
        self.log(f"키워드: {keyword}, 수집 시간: {duration}분, 간격: {self.monitor_interval.get()}초")

        threading.Thread(target=self._collection_loop, daemon=True).start()
        self._update_time_remaining()

    def stop_collection(self):
        """수집 중지"""
        self.is_collecting = False
        self.stop_requested = True
        self._on_collection_complete()

    def _on_collection_complete(self):
        """수집 완료 처리"""
        self.collect_btn.config(state='normal')
        self.stop_collect_btn.config(state='disabled')
        self.collect_status_label.config(text="")
        self.time_remaining_label.config(text="")
        self.log(f"=== 수집 완료 ===", 'success')
        self.log(f"총 수집: {len(self.collected_links)}개 링크")

    def _update_time_remaining(self):
        """남은 시간 업데이트"""
        if not self.is_collecting or not self.collection_start_time:
            return

        duration = self.collection_duration.get()
        end_time = self.collection_start_time + timedelta(minutes=duration)
        remaining = end_time - datetime.now()

        if remaining.total_seconds() <= 0:
            return

        mins = int(remaining.total_seconds() // 60)
        secs = int(remaining.total_seconds() % 60)
        self.time_remaining_label.config(text=f"남은 시간: {mins:02d}:{secs:02d}")

        # 1초마다 업데이트
        self.root.after(1000, self._update_time_remaining)

    def _collection_loop(self):
        """수집 루프"""
        keyword = self.current_keyword
        interval = self.monitor_interval.get()
        duration_minutes = self.collection_duration.get()
        end_time = self.collection_start_time + timedelta(minutes=duration_minutes)

        # 첫 검색
        self._do_collection_search(keyword)

        while self.is_collecting and not self.stop_requested:
            # 시간 체크
            if datetime.now() >= end_time:
                self.root.after(0, lambda: self.log("수집 시간 종료", 'info'))
                break

            # 대기
            for _ in range(interval):
                if not self.is_collecting or self.stop_requested:
                    break
                time.sleep(1)

            if not self.is_collecting or self.stop_requested:
                break

            # 새로고침 후 수집
            try:
                self.root.after(0, lambda: self.status_label.config(text="새로고침...", fg=Theme.COLOR_INFO))
                self.crawler.refresh_results()
                self._do_collection_search(keyword, refresh=True)
            except Exception as e:
                self.root.after(0, lambda: self.log(f"수집 오류: {e}", 'error'))

        self.is_collecting = False
        self.root.after(0, self._on_collection_complete)

    def _do_collection_search(self, keyword: str, refresh: bool = False):
        """수집용 검색 (필터링 + 수집)"""
        try:
            if not refresh:
                # 첫 검색
                posts = self.crawler.search_and_collect(keyword, max_results=50)
            else:
                # 새로고침 후 링크 수집
                posts = self.crawler.collect_blog_links(max_results=50)

            self.stats['searched'] += len(posts)

            # 타겟 계정 필터링
            target_ids = self.share_mgr.get_target_account_ids(self.target_group.get())
            our_posts = self.crawler.filter_by_account_ids(posts, target_ids)
            self.stats['filtered'] += len(our_posts)

            # 새 글만 수집
            new_count = 0
            for post in our_posts:
                link = post['link']
                if link not in self.known_links:
                    self.known_links.add(link)

                    # 이미 시트에 있는 링크 제외
                    if not self.share_mgr.is_link_shared(link):
                        self.collected_links.append({
                            'keyword': keyword,
                            'link': link,
                            'title': post['title'],
                            'blog_id': post['blog_id'],
                            'status': 'pending'
                        })
                        new_count += 1

            if new_count > 0:
                self.stats['collected'] += new_count
                self.root.after(0, lambda: self.log(f"새 글 수집: {new_count}개", 'success'))
                self.root.after(0, self._update_collected_tree)
                self.root.after(0, self._update_stats_label)

            self.root.after(0, lambda: self.status_label.config(text=f"수집 중 ({len(self.collected_links)}개)", fg=Theme.COLOR_SUCCESS))

        except Exception as e:
            self.root.after(0, lambda: self.log(f"검색 오류: {e}", 'error'))

    # ==================== 일괄 공유 ====================

    def start_batch_sharing(self):
        """일괄 공유 시작 (계정별로 모든 링크 공유)"""
        if not self.collected_links:
            messagebox.showwarning("경고", "수집된 링크가 없습니다")
            return

        if not self.share_accounts:
            messagebox.showwarning("경고", "공유계정을 로드하지 못했습니다")
            return

        pending_links = [l for l in self.collected_links if l['status'] == 'pending']
        if not pending_links:
            messagebox.showinfo("안내", "처리할 링크가 없습니다 (모두 완료됨)")
            return

        if not messagebox.askyesno("확인",
            f"수집된 {len(pending_links)}개 링크를 {len(self.share_accounts)}개 계정으로 공유합니다.\n\n"
            f"워크플로우:\n"
            f"1번 계정 → 모든 링크 공유 → IP 변경 →\n"
            f"2번 계정 → 모든 링크 공유 → IP 변경 → ...\n\n"
            f"시작하시겠습니까?"):
            return

        self.is_running = True
        self.stop_requested = False
        self.share_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.collect_btn.config(state='disabled')
        self.status_label.config(text="일괄 공유 중...", fg=Theme.COLOR_SUCCESS)

        self.stats['shared'] = 0
        self.stats['skipped'] = 0
        self.stats['failed'] = 0

        self.log("=== 일괄 공유 시작 ===", 'success')
        self.log(f"링크: {len(pending_links)}개, 계정: {len(self.share_accounts)}개")

        threading.Thread(target=self._batch_sharing_loop, daemon=True).start()

    def _batch_sharing_loop(self):
        """
        일괄 공유 루프

        워크플로우:
        계정1 → [링크1, 링크2, 링크3, ...] → IP 변경
        계정2 → [링크1, 링크2, 링크3, ...] → IP 변경
        ...
        """
        pending_links = [l for l in self.collected_links if l['status'] == 'pending']

        try:
            total_accounts = len(self.share_accounts)

            for acc_idx, account in enumerate(self.share_accounts):
                if self.stop_requested:
                    break

                account_id = account['id']
                account_pw = account['pw']

                self.root.after(0, lambda aid=account_id, idx=acc_idx:
                    self.log(f"\n[{idx+1}/{total_accounts}] 계정: {aid}", 'info'))
                self.root.after(0, lambda aid=account_id:
                    self.current_task_label.config(text=f"계정: {aid}"))

                # 엔진 시작 및 로그인
                engine = ShareEngine(headless=self.headless_var.get())
                engine.start_browser()

                login_result = engine.login(account_id, account_pw)
                if not login_result['success']:
                    self.root.after(0, lambda aid=account_id, r=login_result:
                        self.log(f"[{aid}] 로그인 실패: {r['reason']}", 'error'))
                    engine.close_browser()
                    continue

                self.root.after(0, lambda aid=account_id:
                    self.log(f"[{aid}] 로그인 성공", 'success'))

                # 이 계정으로 모든 링크 공유
                for link_idx, link_item in enumerate(pending_links):
                    if self.stop_requested:
                        break

                    link = link_item['link']
                    keyword = link_item['keyword']

                    # 이미 이 계정으로 공유한 링크인지 확인
                    shared_accounts = self.share_mgr.get_shared_accounts_for_link(link)
                    if account_id in shared_accounts:
                        self.root.after(0, lambda aid=account_id:
                            self.log(f"  - 이미 공유함, 건너뜀"))
                        self.stats['skipped'] += 1
                        continue

                    # 링크가 시트에 없으면 추가
                    if not self.share_mgr.is_link_shared(link):
                        self.share_mgr.add_shared_link(keyword, link)

                    # 공유 실행
                    self.root.after(0, lambda l=link[:40]:
                        self.status_label.config(text=f"공유 중: {l}..."))

                    share_result = engine.share_post(link)

                    if share_result['success']:
                        self.share_mgr.add_shared_account_to_link(link, account_id)
                        self.root.after(0, lambda:
                            self.log(f"  - 공유 성공", 'success'))
                        self.stats['shared'] += 1
                    else:
                        self.root.after(0, lambda r=share_result:
                            self.log(f"  - 공유 실패: {r['reason']}", 'error'))
                        self.stats['failed'] += 1

                    self.root.after(0, self._update_stats_label)

                    # 짧은 대기 (연속 공유 간)
                    time.sleep(1)

                # 브라우저 종료
                engine.close_browser()

                # IP 변경 (마지막 계정 제외)
                if self.ip_change_enabled.get() and acc_idx < total_accounts - 1:
                    self.root.after(0, lambda: self.log("IP 변경 중...", 'info'))
                    if self.change_ip():
                        self.root.after(0, lambda: self.log("IP 변경 완료", 'success'))
                    else:
                        self.root.after(0, lambda: self.log("IP 변경 실패", 'warning'))
                    time.sleep(2)  # IP 안정화 대기

            # 완료된 링크 상태 업데이트
            for link_item in pending_links:
                link_item['status'] = 'done'

            self.root.after(0, self._update_collected_tree)
            self.root.after(0, lambda: self.log("\n=== 일괄 공유 완료 ===", 'success'))

        except Exception as e:
            self.root.after(0, lambda: self.log(f"공유 오류: {e}", 'error'))

        finally:
            self.root.after(0, self._on_sharing_complete)

    def _on_sharing_complete(self):
        """공유 완료"""
        self.is_running = False
        self.share_btn.config(state='normal')
        self.report_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.collect_btn.config(state='normal')
        self.status_label.config(text="완료", fg=Theme.COLOR_INFO)
        self.current_task_label.config(text="")

    # ==================== 일괄 신고 ====================

    def start_batch_reporting(self):
        """일괄 신고 시작 (계정별로 모든 링크 신고)"""
        if not self.collected_links:
            messagebox.showwarning("경고", "수집된 링크가 없습니다")
            return

        if not self.share_accounts:
            messagebox.showwarning("경고", "공유계정을 로드하지 못했습니다")
            return

        pending_links = [l for l in self.collected_links if l['status'] == 'pending']
        if not pending_links:
            messagebox.showinfo("안내", "처리할 링크가 없습니다 (모두 완료됨)")
            return

        reason_text = "불법정보" if self.report_reason.get() == "illegal" else "스팸홍보"

        if not messagebox.askyesno("확인",
            f"수집된 {len(pending_links)}개 링크를 {len(self.share_accounts)}개 계정으로 신고합니다.\n\n"
            f"신고 사유: {reason_text}\n\n"
            f"워크플로우:\n"
            f"1번 계정 → 모든 링크 신고 → IP 변경 →\n"
            f"2번 계정 → 모든 링크 신고 → IP 변경 → ...\n\n"
            f"시작하시겠습니까?"):
            return

        self.is_running = True
        self.stop_requested = False
        self.share_btn.config(state='disabled')
        self.report_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.collect_btn.config(state='disabled')
        self.status_label.config(text="일괄 신고 중...", fg=Theme.COLOR_WARNING)

        self.stats['reported'] = 0
        self.stats['skipped'] = 0
        self.stats['failed'] = 0

        self.log("=== 일괄 신고 시작 ===", 'warning')
        self.log(f"링크: {len(pending_links)}개, 계정: {len(self.share_accounts)}개, 사유: {reason_text}")

        threading.Thread(target=self._batch_reporting_loop, daemon=True).start()

    def _batch_reporting_loop(self):
        """
        일괄 신고 루프

        워크플로우:
        계정1 → [링크1, 링크2, 링크3, ...] 신고 → IP 변경
        계정2 → [링크1, 링크2, 링크3, ...] 신고 → IP 변경
        ...
        """
        pending_links = [l for l in self.collected_links if l['status'] == 'pending']
        reason = self.report_reason.get()

        try:
            total_accounts = len(self.share_accounts)

            for acc_idx, account in enumerate(self.share_accounts):
                if self.stop_requested:
                    break

                account_id = account['id']
                account_pw = account['pw']

                self.root.after(0, lambda aid=account_id, idx=acc_idx:
                    self.log(f"\n[{idx+1}/{total_accounts}] 계정: {aid}", 'info'))
                self.root.after(0, lambda aid=account_id:
                    self.current_task_label.config(text=f"계정: {aid}"))

                # 엔진 시작 및 로그인
                engine = ShareEngine(headless=self.headless_var.get())
                engine.start_browser()

                login_result = engine.login(account_id, account_pw)
                if not login_result['success']:
                    self.root.after(0, lambda aid=account_id, r=login_result:
                        self.log(f"[{aid}] 로그인 실패: {r['reason']}", 'error'))
                    engine.close_browser()
                    continue

                self.root.after(0, lambda aid=account_id:
                    self.log(f"[{aid}] 로그인 성공", 'success'))

                # 이 계정으로 모든 링크 신고
                for link_idx, link_item in enumerate(pending_links):
                    if self.stop_requested:
                        break

                    link = link_item['link']
                    keyword = link_item['keyword']

                    # 이미 이 계정으로 신고한 링크인지 확인
                    reported_accounts = self.share_mgr.get_reported_accounts_for_link(link)
                    if account_id in reported_accounts:
                        self.root.after(0, lambda:
                            self.log(f"  - 이미 신고함, 건너뜀"))
                        self.stats['skipped'] += 1
                        continue

                    # 링크가 시트에 없으면 추가
                    if not self.share_mgr.is_link_reported(link):
                        self.share_mgr.add_reported_link(keyword, link)

                    # 신고 실행
                    self.root.after(0, lambda l=link[:40]:
                        self.status_label.config(text=f"신고 중: {l}..."))

                    report_result = engine.report_post(link, reason)

                    if report_result['success']:
                        if report_result.get('already_reported'):
                            self.root.after(0, lambda:
                                self.log(f"  - 이미 신고된 글", 'warning'))
                            self.stats['skipped'] += 1
                        else:
                            self.share_mgr.add_reported_account_to_link(link, account_id)
                            self.root.after(0, lambda:
                                self.log(f"  - 신고 성공", 'success'))
                            self.stats['reported'] += 1
                    else:
                        self.root.after(0, lambda r=report_result:
                            self.log(f"  - 신고 실패: {r['reason']}", 'error'))
                        self.stats['failed'] += 1

                    self.root.after(0, self._update_stats_label)

                    # 짧은 대기 (연속 신고 간)
                    time.sleep(1)

                # 브라우저 종료
                engine.close_browser()

                # IP 변경 (마지막 계정 제외)
                if self.ip_change_enabled.get() and acc_idx < total_accounts - 1:
                    self.root.after(0, lambda: self.log("IP 변경 중...", 'info'))
                    if self.change_ip():
                        self.root.after(0, lambda: self.log("IP 변경 완료", 'success'))
                    else:
                        self.root.after(0, lambda: self.log("IP 변경 실패", 'warning'))
                    time.sleep(2)  # IP 안정화 대기

            # 완료된 링크 상태 업데이트
            for link_item in pending_links:
                link_item['status'] = 'done'

            self.root.after(0, self._update_collected_tree)
            self.root.after(0, lambda: self.log("\n=== 일괄 신고 완료 ===", 'success'))

        except Exception as e:
            self.root.after(0, lambda: self.log(f"신고 오류: {e}", 'error'))

        finally:
            self.root.after(0, self._on_sharing_complete)

    def _update_stats_label(self):
        """통계 업데이트"""
        self.stats_label.config(
            text=f"검색: {self.stats['searched']} | "
                 f"수집: {self.stats['collected']} | "
                 f"공유: {self.stats['shared']} | "
                 f"신고: {self.stats['reported']} | "
                 f"건너뜀: {self.stats['skipped']} | "
                 f"실패: {self.stats['failed']}"
        )

    def stop_all(self):
        """모든 작업 중지"""
        self.stop_requested = True
        self.is_running = False
        self.is_collecting = False
        self.log("모든 작업 중지됨", 'warning')

    def close_browsers(self):
        """모든 브라우저 종료"""
        if self.crawler:
            self.crawler.close_browser()
            self.crawler = None
        if self.engine:
            self.engine.close_browser()
            self.engine = None

        self.login_status.config(text="미로그인", fg=Theme.COLOR_ERROR)
        self.log("브라우저 종료됨", 'info')

    # ==================== IP 변경 ====================

    def load_ip_settings(self):
        """IP 설정 로드"""
        path = os.path.join(os.path.dirname(__file__), self.IP_SETTINGS_FILE)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.ip_hotkey.set(data.get('hotkey', ''))
                    self.ip_wait_time.set(data.get('wait_time', 3))
                    self.ip_change_enabled.set(data.get('enabled', False))
            except:
                pass

    def save_ip_settings(self):
        """IP 설정 저장"""
        path = os.path.join(os.path.dirname(__file__), self.IP_SETTINGS_FILE)
        data = {
            'hotkey': self.ip_hotkey.get(),
            'wait_time': self.ip_wait_time.get(),
            'enabled': self.ip_change_enabled.get()
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_current_ip(self) -> str:
        """현재 IP 조회"""
        try:
            resp = requests.get('https://api.ip.pe.kr/', timeout=10)
            return resp.text.strip()
        except:
            return ""

    def change_ip(self) -> bool:
        """IP 변경"""
        hotkey = self.ip_hotkey.get()
        if not hotkey:
            return False

        old_ip = self.get_current_ip()
        if not old_ip:
            return False

        try:
            keyboard.send(hotkey)
            self.log(f"IP 변경 핫키 전송: {hotkey}")
        except Exception as e:
            self.log(f"핫키 전송 실패: {e}", 'error')
            return False

        wait = self.ip_wait_time.get()
        for i in range(wait):
            time.sleep(1)
            new_ip = self.get_current_ip()
            if new_ip and new_ip != old_ip:
                self.log(f"IP 변경: {old_ip} → {new_ip}", 'success')
                return True

        return False

    def open_ip_settings(self):
        """IP 설정 다이얼로그"""
        dlg = tk.Toplevel(self.root)
        dlg.title("IP 변경 설정")
        dlg.configure(bg='white')
        dlg.transient(self.root)
        dlg.grab_set()

        f = tk.Frame(dlg, bg='white', padx=15, pady=10)
        f.pack(fill='both', expand=True)

        # 핫키
        row1 = tk.Frame(f, bg='white')
        row1.pack(fill='x', pady=3)
        tk.Label(row1, text="핫키:", bg='white', width=10, anchor='w').pack(side='left')
        tk.Entry(row1, textvariable=self.ip_hotkey, width=20).pack(side='left')

        # 대기시간
        row2 = tk.Frame(f, bg='white')
        row2.pack(fill='x', pady=3)
        tk.Label(row2, text="대기시간:", bg='white', width=10, anchor='w').pack(side='left')
        tk.Spinbox(row2, from_=1, to=30, width=5, textvariable=self.ip_wait_time).pack(side='left')
        tk.Label(row2, text="초", bg='white').pack(side='left')

        # 버튼
        btn_frame = tk.Frame(f, bg='white')
        btn_frame.pack(pady=10)

        def save_and_close():
            self.save_ip_settings()
            dlg.destroy()

        tk.Button(btn_frame, text="저장", command=save_and_close,
                  bg=Theme.COLOR_SUCCESS, fg='white').pack(side='left', padx=5)
        tk.Button(btn_frame, text="닫기", command=dlg.destroy,
                  bg=Theme.COLOR_GRAY, fg='white').pack(side='left', padx=5)

    # ==================== 설정 ====================

    def load_config(self):
        """설정 로드"""
        path = os.path.join(os.path.dirname(__file__), self.CONFIG_FILE)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.headless_var.set(data.get('headless', False))
                self.target_group.set(data.get('target_group', '소액결제현금화'))
                self.monitor_interval.set(data.get('monitor_interval', 60))
                self.collection_duration.set(data.get('collection_duration', 30))

                if 'last_keyword' in data:
                    self.keyword_entry.insert(0, data['last_keyword'])

            except:
                pass

    def save_config(self):
        """설정 저장"""
        path = os.path.join(os.path.dirname(__file__), self.CONFIG_FILE)
        data = {
            'headless': self.headless_var.get(),
            'target_group': self.target_group.get(),
            'monitor_interval': self.monitor_interval.get(),
            'collection_duration': self.collection_duration.get(),
            'last_keyword': self.keyword_entry.get().strip(),
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass

    # ==================== 로그 ====================

    def log(self, message: str, level: str = 'info'):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        self.log_text.insert('end', log_msg, level)
        self.log_text.see('end')

    def clear_log(self):
        """로그 지우기"""
        self.log_text.delete('1.0', 'end')


def main():
    root = tk.Tk()
    app = ShareBotV2(root)

    def on_close():
        app.save_config()
        app.close_browsers()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
