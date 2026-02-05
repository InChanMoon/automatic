"""
네이버 블로그 공유봇 - Share Bot
블로그 글을 여러 계정으로 공유(스크랩)하는 자동화 프로그램
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import json
import os
from datetime import datetime

import keyboard
import requests

from src.share.share_engine import ShareEngine
from src.share.rss_monitor import RSSMonitor
from src.ui.theme import Theme


class ShareBot:
    """공유봇 메인 클래스"""

    VERSION = "1.0"
    CONFIG_FILE = "share_config.json"
    IP_SETTINGS_FILE = "ip_settings.json"

    def __init__(self, root):
        self.root = root
        self.root.title(f"블로그 공유봇 v{self.VERSION}")
        self.root.geometry("950x700")
        self.root.configure(bg=Theme.BG_MAIN)

        # 엔진
        self.engine: ShareEngine = None

        # RSS 모니터 (여러 블로그 지원)
        self.rss_monitor = RSSMonitor(interval_minutes=30)
        self.rss_monitor.on_log = lambda msg: self.log(msg, 'info')
        self.rss_monitor.on_new_posts = self.on_new_posts_detected

        # 상태
        self.is_running = False

        # IP 설정
        self.ip_change_enabled = tk.BooleanVar(value=False)
        self.ip_hotkey = tk.StringVar(value="")
        self.ip_wait_time = tk.IntVar(value=3)

        # 옵션
        self.headless_var = tk.BooleanVar(value=False)
        self.post_interval_min = tk.IntVar(value=5)
        self.post_interval_max = tk.IntVar(value=15)
        self.account_interval_min = tk.IntVar(value=30)
        self.account_interval_max = tk.IntVar(value=60)
        self.rss_interval = tk.IntVar(value=30)
        self.rss_enabled = tk.BooleanVar(value=False)

        self.setup_ui()
        self.load_config()
        self.load_ip_settings()

    def setup_ui(self):
        """UI 구성"""
        # ===== 상단 컨트롤 =====
        top = tk.Frame(self.root, bg=Theme.BG_MAIN)
        top.pack(fill='x', padx=8, pady=4)

        # 시작/중지 버튼
        self.start_btn = tk.Button(top, text="▶ 공유 시작", command=self.start_sharing,
                                   bg=Theme.COLOR_SUCCESS, fg='white', font=Theme.FONT_SMALL_BOLD,
                                   relief='flat', padx=12, pady=3)
        self.start_btn.pack(side='left', padx=2)

        self.stop_btn = tk.Button(top, text="■ 중지", command=self.stop_sharing,
                                  bg=Theme.COLOR_ERROR, fg='white', font=Theme.FONT_SMALL_BOLD,
                                  relief='flat', padx=12, pady=3, state='disabled')
        self.stop_btn.pack(side='left', padx=2)

        # 헤드리스 옵션
        ttk.Checkbutton(top, text="헤드리스", variable=self.headless_var).pack(side='left', padx=8)

        # IP 변경 옵션
        ttk.Checkbutton(top, text="IP변경", variable=self.ip_change_enabled).pack(side='left')
        tk.Button(top, text="⚙", command=self.open_ip_settings,
                 bg=Theme.COLOR_GRAY, fg='white', font=Theme.FONT_TINY,
                 relief='flat', padx=4, pady=1).pack(side='left', padx=2)

        # 상태 표시
        self.status_label = tk.Label(top, text="대기 중", bg=Theme.BG_MAIN, fg=Theme.FG_TEXT_LIGHT,
                                     font=Theme.FONT_SMALL_BOLD)
        self.status_label.pack(side='right', padx=5)

        # ===== 메인 영역 =====
        main = tk.PanedWindow(self.root, orient='horizontal', bg=Theme.BG_MAIN, sashwidth=4)
        main.pack(fill='both', expand=True, padx=8, pady=4)

        # 좌측 패널 (계정 + 공유 대상)
        left = tk.Frame(main, bg=Theme.BG_WHITE)
        main.add(left, width=450)

        # 우측 패널 (로그)
        right = tk.Frame(main, bg=Theme.BG_WHITE)
        main.add(right, width=450)

        self.setup_left_panel(left)
        self.setup_right_panel(right)

        # ===== 하단 진행 상황 =====
        self.setup_progress_bar()

    def setup_left_panel(self, parent):
        """좌측 패널: 계정 + 공유대상"""
        # ===== 계정 입력 영역 =====
        account_frame = tk.LabelFrame(parent, text="계정 목록 (id,pw 형식, 줄바꿈 구분)",
                                      bg=Theme.BG_WHITE, font=Theme.FONT_SMALL_BOLD)
        account_frame.pack(fill='both', expand=True, padx=5, pady=5)

        self.account_text = scrolledtext.ScrolledText(account_frame, height=8,
                                                       font=('Consolas', 9), wrap='none')
        self.account_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.account_text.insert('1.0', "# 형식: 아이디,비밀번호 (줄바꿈으로 구분)\n# 예시:\n# user001,password123\n# user002,pass456\n")

        # ===== 공유 대상 URL 입력 영역 =====
        url_frame = tk.LabelFrame(parent, text="공유할 글 URL (줄바꿈 구분)",
                                  bg=Theme.BG_WHITE, font=Theme.FONT_SMALL_BOLD)
        url_frame.pack(fill='both', expand=True, padx=5, pady=5)

        self.url_text = scrolledtext.ScrolledText(url_frame, height=6,
                                                   font=('Consolas', 9), wrap='none')
        self.url_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.url_text.insert('1.0', "# 공유할 블로그 글 URL을 줄바꿈으로 구분하여 입력\n# 예시:\n# https://blog.naver.com/user123/223456789\n")

        # ===== RSS 모니터링 영역 =====
        rss_frame = tk.LabelFrame(parent, text="RSS 모니터링 (여러 블로그 ID, 줄바꿈 구분)",
                                  bg=Theme.BG_WHITE, font=Theme.FONT_SMALL_BOLD)
        rss_frame.pack(fill='x', padx=5, pady=5)

        rss_top = tk.Frame(rss_frame, bg=Theme.BG_WHITE)
        rss_top.pack(fill='x', padx=5, pady=3)

        ttk.Checkbutton(rss_top, text="RSS 모니터링 활성화", variable=self.rss_enabled).pack(side='left')

        tk.Label(rss_top, text="간격:", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL).pack(side='left', padx=(10, 2))
        tk.Spinbox(rss_top, from_=5, to=120, width=4, textvariable=self.rss_interval,
                  font=Theme.FONT_SMALL, justify='center').pack(side='left')
        tk.Label(rss_top, text="분", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL).pack(side='left', padx=2)

        tk.Button(rss_top, text="RSS 확인", command=self.check_rss_now,
                 bg=Theme.COLOR_INFO, fg='white', font=Theme.FONT_TINY,
                 relief='flat', padx=6).pack(side='right', padx=5)

        self.rss_text = scrolledtext.ScrolledText(rss_frame, height=3,
                                                   font=('Consolas', 9), wrap='none')
        self.rss_text.pack(fill='x', padx=5, pady=5)
        self.rss_text.insert('1.0', "# 모니터링할 블로그 ID (줄바꿈 구분)\n# 예시: sunny12221\n")

        # ===== 간격 설정 =====
        interval_frame = tk.Frame(parent, bg=Theme.BG_WHITE)
        interval_frame.pack(fill='x', padx=5, pady=5)

        tk.Label(interval_frame, text="글 간격:", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL).pack(side='left')
        tk.Spinbox(interval_frame, from_=1, to=60, width=3, textvariable=self.post_interval_min,
                  font=Theme.FONT_SMALL, justify='center').pack(side='left', padx=2)
        tk.Label(interval_frame, text="~", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL).pack(side='left')
        tk.Spinbox(interval_frame, from_=1, to=120, width=3, textvariable=self.post_interval_max,
                  font=Theme.FONT_SMALL, justify='center').pack(side='left', padx=2)
        tk.Label(interval_frame, text="초", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL).pack(side='left', padx=(0, 15))

        tk.Label(interval_frame, text="계정 간격:", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL).pack(side='left')
        tk.Spinbox(interval_frame, from_=10, to=300, width=3, textvariable=self.account_interval_min,
                  font=Theme.FONT_SMALL, justify='center').pack(side='left', padx=2)
        tk.Label(interval_frame, text="~", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL).pack(side='left')
        tk.Spinbox(interval_frame, from_=10, to=600, width=3, textvariable=self.account_interval_max,
                  font=Theme.FONT_SMALL, justify='center').pack(side='left', padx=2)
        tk.Label(interval_frame, text="초", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL).pack(side='left')

    def setup_right_panel(self, parent):
        """우측 패널: 로그"""
        # 로그 헤더
        log_header = tk.Frame(parent, bg=Theme.BG_WHITE)
        log_header.pack(fill='x', padx=5, pady=3)

        tk.Label(log_header, text="로그", bg=Theme.BG_WHITE, font=Theme.FONT_SMALL_BOLD).pack(side='left')
        tk.Button(log_header, text="지우기", command=self.clear_log,
                 bg=Theme.COLOR_GRAY, fg='white', font=Theme.FONT_TINY,
                 relief='flat', padx=6).pack(side='right')

        # 로그 텍스트
        self.log_text = scrolledtext.ScrolledText(parent, height=25,
                                                   font=Theme.FONT_LOG, wrap='word',
                                                   bg=Theme.BG_DARK, fg=Theme.FG_TEXT_DARK)
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)

        # 로그 태그 설정
        self.log_text.tag_config('info', foreground=Theme.FG_TEXT_DARK)
        self.log_text.tag_config('success', foreground=Theme.COLOR_SUCCESS)
        self.log_text.tag_config('error', foreground=Theme.COLOR_ERROR)
        self.log_text.tag_config('warning', foreground=Theme.COLOR_WARNING)

    def setup_progress_bar(self):
        """하단 진행 상황 바"""
        bottom = tk.Frame(self.root, bg=Theme.BG_WHITE)
        bottom.pack(fill='x', padx=8, pady=4)

        # 진행 상태 라벨
        stats_frame = tk.Frame(bottom, bg=Theme.BG_WHITE)
        stats_frame.pack(fill='x', padx=5, pady=3)

        self.progress_account = tk.Label(stats_frame, text="계정: -/-", bg=Theme.BG_WHITE,
                                        font=Theme.FONT_SMALL)
        self.progress_account.pack(side='left', padx=10)

        self.progress_post = tk.Label(stats_frame, text="글: -/-", bg=Theme.BG_WHITE,
                                     font=Theme.FONT_SMALL)
        self.progress_post.pack(side='left', padx=10)

        self.progress_stats = tk.Label(stats_frame, text="공유: 0 / 건너뜀: 0 / 실패: 0", bg=Theme.BG_WHITE,
                                      font=Theme.FONT_SMALL)
        self.progress_stats.pack(side='left', padx=10)

        # 프로그레스 바
        self.progress_bar = ttk.Progressbar(bottom, mode='determinate', length=400)
        self.progress_bar.pack(fill='x', padx=5, pady=3)

    # ==================== 설정 저장/로드 ====================

    def load_config(self):
        """설정 로드"""
        config_path = os.path.join(os.path.dirname(__file__), self.CONFIG_FILE)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 계정
                if 'accounts' in data:
                    self.account_text.delete('1.0', 'end')
                    self.account_text.insert('1.0', data['accounts'])

                # URL
                if 'urls' in data:
                    self.url_text.delete('1.0', 'end')
                    self.url_text.insert('1.0', data['urls'])

                # RSS 블로그 ID
                if 'rss_blogs' in data:
                    self.rss_text.delete('1.0', 'end')
                    self.rss_text.insert('1.0', data['rss_blogs'])

                # 옵션
                self.headless_var.set(data.get('headless', False))
                self.post_interval_min.set(data.get('post_interval_min', 5))
                self.post_interval_max.set(data.get('post_interval_max', 15))
                self.account_interval_min.set(data.get('account_interval_min', 30))
                self.account_interval_max.set(data.get('account_interval_max', 60))
                self.rss_interval.set(data.get('rss_interval', 30))
                self.rss_enabled.set(data.get('rss_enabled', False))

                self.log("설정 로드됨", 'success')
            except Exception as e:
                self.log(f"설정 로드 실패: {e}", 'error')

    def save_config(self):
        """설정 저장"""
        config_path = os.path.join(os.path.dirname(__file__), self.CONFIG_FILE)
        data = {
            'accounts': self.account_text.get('1.0', 'end').strip(),
            'urls': self.url_text.get('1.0', 'end').strip(),
            'rss_blogs': self.rss_text.get('1.0', 'end').strip(),
            'headless': self.headless_var.get(),
            'post_interval_min': self.post_interval_min.get(),
            'post_interval_max': self.post_interval_max.get(),
            'account_interval_min': self.account_interval_min.get(),
            'account_interval_max': self.account_interval_max.get(),
            'rss_interval': self.rss_interval.get(),
            'rss_enabled': self.rss_enabled.get(),
        }
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"설정 저장 실패: {e}", 'error')

    # ==================== IP 변경 관련 ====================

    def load_ip_settings(self):
        """IP 설정 로드"""
        config_path = os.path.join(os.path.dirname(__file__), self.IP_SETTINGS_FILE)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.ip_hotkey.set(data.get('hotkey', ''))
                    self.ip_wait_time.set(data.get('wait_time', 3))
                    self.ip_change_enabled.set(data.get('enabled', False))
            except:
                pass

    def save_ip_settings(self):
        """IP 설정 저장"""
        config_path = os.path.join(os.path.dirname(__file__), self.IP_SETTINGS_FILE)
        data = {
            'hotkey': self.ip_hotkey.get(),
            'wait_time': self.ip_wait_time.get(),
            'enabled': self.ip_change_enabled.get()
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_current_ip(self) -> str:
        """현재 IP 조회"""
        try:
            resp = requests.get('https://api.ip.pe.kr/', timeout=10)
            return resp.text.strip()
        except Exception as e:
            self.log(f"IP 조회 실패: {e}", 'error')
            return ""

    def change_ip(self) -> bool:
        """IP 변경 실행 (핫키 전송 → 대기 → 변경 확인)"""
        hotkey = self.ip_hotkey.get()
        if not hotkey:
            self.log("IP 핫키가 설정되지 않음", 'warning')
            return False

        # 변경 전 IP
        old_ip = self.get_current_ip()
        if not old_ip:
            return False
        self.log(f"현재 IP: {old_ip}", 'info')

        # 핫키 전송
        try:
            keyboard.send(hotkey)
            self.log(f"IP 변경 핫키 전송: {hotkey}", 'info')
        except Exception as e:
            self.log(f"핫키 전송 실패: {e}", 'error')
            return False

        # 대기 (1초 간격으로 체크)
        wait = self.ip_wait_time.get()
        self.log(f"IP 변경 대기 중... (최대 {wait}초)", 'info')

        new_ip = old_ip
        for i in range(wait):
            time.sleep(1)
            new_ip = self.get_current_ip()
            if new_ip and new_ip != old_ip:
                self.log(f"IP 변경 성공: {old_ip} → {new_ip} ({i+1}초)", 'success')
                return True

        self.log(f"IP 변경 안됨 (동일: {new_ip})", 'warning')
        return False

    def open_ip_settings(self):
        """IP 설정 다이얼로그"""
        dlg = tk.Toplevel(self.root)
        dlg.title("IP 변경 설정")
        dlg.configure(bg='white')
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(False, False)

        f = tk.Frame(dlg, bg='white', padx=15, pady=10)
        f.pack(fill='both', expand=True)

        # 핫키 설정
        hk_frame = tk.Frame(f, bg='white')
        hk_frame.pack(fill='x', pady=3)
        tk.Label(hk_frame, text="핫키:", bg='white', width=10, anchor='w', font=Theme.FONT_NORMAL).pack(side='left')
        hk_entry = tk.Entry(hk_frame, textvariable=self.ip_hotkey, width=20, font=Theme.FONT_NORMAL)
        hk_entry.pack(side='left')
        tk.Label(hk_frame, text="(예: ctrl+shift+f5)", bg='white', fg='#888', font=Theme.FONT_SMALL).pack(side='left', padx=5)

        # 대기 시간
        wait_frame = tk.Frame(f, bg='white')
        wait_frame.pack(fill='x', pady=3)
        tk.Label(wait_frame, text="대기시간:", bg='white', width=10, anchor='w', font=Theme.FONT_NORMAL).pack(side='left')
        tk.Spinbox(wait_frame, from_=1, to=30, width=5, textvariable=self.ip_wait_time,
                  font=Theme.FONT_NORMAL, justify='center').pack(side='left')
        tk.Label(wait_frame, text="초", bg='white', font=Theme.FONT_NORMAL).pack(side='left', padx=3)

        # 현재 IP 표시
        ip_frame = tk.Frame(f, bg='white')
        ip_frame.pack(fill='x', pady=3)
        tk.Label(ip_frame, text="현재 IP:", bg='white', width=10, anchor='w', font=Theme.FONT_NORMAL).pack(side='left')
        ip_label = tk.Label(ip_frame, text="조회 중...", bg='white', fg=Theme.COLOR_INFO, font=Theme.FONT_NORMAL)
        ip_label.pack(side='left')

        def refresh_ip():
            ip_label.config(text="조회 중...")
            def do_refresh():
                ip = self.get_current_ip()
                dlg.after(0, lambda: ip_label.config(text=ip or "조회 실패"))
            threading.Thread(target=do_refresh, daemon=True).start()

        tk.Button(ip_frame, text="새로고침", command=refresh_ip,
                 bg=Theme.COLOR_INFO, fg='white', font=Theme.FONT_TINY, relief='flat', padx=4).pack(side='left', padx=5)

        refresh_ip()

        tk.Frame(f, bg='#ddd', height=1).pack(fill='x', pady=8)

        # 버튼
        btn_frame = tk.Frame(f, bg='white')
        btn_frame.pack(pady=3)

        def test_change():
            def do_test():
                result = self.change_ip()
                dlg.after(0, refresh_ip)
                if result:
                    dlg.after(0, lambda: messagebox.showinfo("성공", "IP가 변경되었습니다"))
                else:
                    dlg.after(0, lambda: messagebox.showwarning("실패", "IP 변경에 실패했습니다"))
            threading.Thread(target=do_test, daemon=True).start()

        def save_and_close():
            self.save_ip_settings()
            self.log("IP 설정 저장됨", 'success')
            dlg.destroy()

        tk.Button(btn_frame, text="테스트", command=test_change,
                 bg=Theme.COLOR_WARNING, fg='white', font=Theme.FONT_NORMAL, relief='flat', padx=10).pack(side='left', padx=3)
        tk.Button(btn_frame, text="저장", command=save_and_close,
                 bg=Theme.COLOR_SUCCESS, fg='white', font=Theme.FONT_NORMAL, relief='flat', padx=10).pack(side='left', padx=3)
        tk.Button(btn_frame, text="닫기", command=dlg.destroy,
                 bg=Theme.COLOR_GRAY, fg='white', font=Theme.FONT_NORMAL, relief='flat', padx=10).pack(side='left', padx=3)

        # 다이얼로그 중앙 배치
        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dlg.winfo_reqwidth()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dlg.winfo_reqheight()) // 2
        dlg.geometry(f"+{x}+{y}")

    # ==================== 데이터 파싱 ====================

    def parse_accounts(self) -> list:
        """계정 텍스트 파싱 -> [{'id': str, 'pw': str}, ...]"""
        accounts = []
        text = self.account_text.get('1.0', 'end').strip()

        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # 구분자: 쉼표 또는 탭
            if ',' in line:
                parts = line.split(',', 1)
            elif '\t' in line:
                parts = line.split('\t', 1)
            else:
                continue

            if len(parts) == 2:
                account_id = parts[0].strip()
                password = parts[1].strip()
                if account_id and password:
                    accounts.append({'id': account_id, 'pw': password})

        return accounts

    def parse_urls(self) -> list:
        """URL 텍스트 파싱 -> [url, ...]"""
        urls = []
        text = self.url_text.get('1.0', 'end').strip()

        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # URL 형식 체크 (간단하게)
            if 'blog.naver.com' in line or line.startswith('http'):
                urls.append(line)

        return urls

    def parse_rss_blogs(self) -> list:
        """RSS 블로그 ID 파싱 -> [blog_id, ...]"""
        blogs = []
        text = self.rss_text.get('1.0', 'end').strip()

        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # URL이면 ID 추출
            if 'blog.naver.com' in line:
                blog_id = self.rss_monitor.get_blog_id_from_url(line)
                if blog_id:
                    blogs.append(blog_id)
            else:
                # 그냥 ID
                blogs.append(line)

        return blogs

    # ==================== RSS 모니터링 ====================

    def check_rss_now(self):
        """RSS 즉시 확인"""
        blog_ids = self.parse_rss_blogs()
        if not blog_ids:
            messagebox.showwarning("경고", "모니터링할 블로그 ID가 없습니다")
            return

        self.log(f"RSS 확인 중... ({len(blog_ids)}개 블로그)", 'info')

        def do_check():
            # 블로그 ID 등록
            self.rss_monitor.clear_blogs()
            for blog_id in blog_ids:
                self.rss_monitor.add_blog(blog_id)

            # 확인
            posts = self.rss_monitor.check_once()

            # 결과 표시
            if posts:
                self.root.after(0, lambda: self.show_rss_results(posts))
            else:
                self.root.after(0, lambda: self.log("RSS에서 글을 찾지 못함", 'warning'))

        threading.Thread(target=do_check, daemon=True).start()

    def show_rss_results(self, posts: list):
        """RSS 결과를 URL 텍스트에 추가할지 확인"""
        if not posts:
            return

        msg = f"{len(posts)}개의 글을 찾았습니다.\n\n"
        for i, post in enumerate(posts[:5]):  # 최대 5개 표시
            msg += f"{i+1}. {post['title'][:30]}...\n"
        if len(posts) > 5:
            msg += f"\n... 외 {len(posts) - 5}개"

        msg += "\n\n공유 대상에 추가하시겠습니까?"

        if messagebox.askyesno("RSS 결과", msg):
            # 기존 URL에 추가
            current = self.url_text.get('1.0', 'end').strip()
            new_urls = '\n'.join([post['link'] for post in posts])

            if current and not current.endswith('\n'):
                current += '\n'

            self.url_text.delete('1.0', 'end')
            self.url_text.insert('1.0', current + new_urls)
            self.log(f"{len(posts)}개 URL 추가됨", 'success')

    def on_new_posts_detected(self, posts: list):
        """새 글 감지 콜백 (RSS 모니터링 중)"""
        self.root.after(0, lambda: self.show_rss_results(posts))

    def start_rss_monitoring(self):
        """RSS 모니터링 시작"""
        blog_ids = self.parse_rss_blogs()
        if not blog_ids:
            return

        self.rss_monitor.interval = self.rss_interval.get()
        self.rss_monitor.clear_blogs()
        for blog_id in blog_ids:
            self.rss_monitor.add_blog(blog_id)

        self.rss_monitor.start_monitoring()
        self.log(f"RSS 모니터링 시작 ({len(blog_ids)}개 블로그, {self.rss_interval.get()}분 간격)", 'success')

    def stop_rss_monitoring(self):
        """RSS 모니터링 중지"""
        self.rss_monitor.stop_monitoring()

    # ==================== 공유 시작/중지 ====================

    def start_sharing(self):
        """공유 시작"""
        if self.is_running:
            return

        # 데이터 파싱
        accounts = self.parse_accounts()
        urls = self.parse_urls()

        if not accounts:
            messagebox.showwarning("경고", "계정을 입력하세요\n형식: 아이디,비밀번호")
            return

        if not urls:
            messagebox.showwarning("경고", "공유할 URL을 입력하세요")
            return

        # 설정 저장
        self.save_config()

        # 확인
        if not messagebox.askyesno("확인",
            f"계정 {len(accounts)}개로 {len(urls)}개 글을 공유합니다.\n\n"
            f"헤드리스: {'예' if self.headless_var.get() else '아니오'}\n"
            f"IP 변경: {'예' if self.ip_change_enabled.get() else '아니오'}\n\n"
            "시작하시겠습니까?"):
            return

        self.is_running = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_label.config(text="공유 중...", fg=Theme.COLOR_SUCCESS)

        self.log("=== 공유 시작 ===", 'success')
        self.log(f"계정: {len(accounts)}개, 글: {len(urls)}개", 'info')

        # RSS 모니터링 시작 (활성화된 경우)
        if self.rss_enabled.get():
            self.start_rss_monitoring()

        # 엔진 생성 및 시작
        self.engine = ShareEngine(headless=self.headless_var.get())
        self.engine.log_callback = lambda msg: self.root.after(0, lambda: self.log(msg, 'info'))
        self.engine.progress_callback = lambda p: self.root.after(0, lambda: self.update_progress(p))

        if self.ip_change_enabled.get():
            self.engine.ip_change_callback = self.change_ip

        # 공유 시작
        self.engine.start_sharing(
            accounts=accounts,
            post_urls=urls,
            post_interval=(self.post_interval_min.get(), self.post_interval_max.get()),
            account_interval=(self.account_interval_min.get(), self.account_interval_max.get()),
            ip_change_enabled=self.ip_change_enabled.get()
        )

        # 완료 대기 스레드
        def wait_for_complete():
            while self.engine and self.engine.is_running:
                time.sleep(0.5)
            self.root.after(0, self.on_sharing_complete)

        threading.Thread(target=wait_for_complete, daemon=True).start()

    def stop_sharing(self):
        """공유 중지"""
        if self.engine:
            self.engine.request_stop()
            self.log("중지 요청됨...", 'warning')
            self.status_label.config(text="중지 중...", fg=Theme.COLOR_WARNING)

        self.stop_rss_monitoring()

    def on_sharing_complete(self):
        """공유 완료 후 처리"""
        self.is_running = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_label.config(text="완료", fg=Theme.COLOR_INFO)
        self.log("=== 공유 완료 ===", 'success')

        self.stop_rss_monitoring()

    def update_progress(self, progress: dict):
        """진행 상황 업데이트"""
        current_account = progress.get('current_account', '-')
        current_account_idx = progress.get('current_account_index', 0)
        total_accounts = progress.get('total_accounts', 0)
        current_post_idx = progress.get('current_post_index', 0)
        total_posts = progress.get('total_posts', 0)
        shared = progress.get('shared_posts', 0)
        skipped = progress.get('skipped_posts', 0)
        failed = progress.get('failed_posts', 0)

        self.progress_account.config(text=f"계정: {current_account} ({current_account_idx}/{total_accounts})")
        self.progress_post.config(text=f"글: {current_post_idx}/{total_posts}")
        self.progress_stats.config(text=f"공유: {shared} / 건너뜀: {skipped} / 실패: {failed}")

        # 프로그레스 바
        total_ops = total_accounts * total_posts
        completed_ops = (current_account_idx - 1) * total_posts + current_post_idx
        if total_ops > 0:
            percent = (completed_ops / total_ops) * 100
            self.progress_bar['value'] = percent

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
    app = ShareBot(root)

    # 종료 시 설정 저장
    def on_close():
        app.save_config()
        app.stop_rss_monitoring()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
