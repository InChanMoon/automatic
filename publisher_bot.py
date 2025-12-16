"""
네이버 블로그 자동 발행봇 - Publisher Bot

관리자 전용 발행봇:
- 그룹별 발행대기 콘텐츠 자동 발행
- 계정 로테이션 및 일일 한도 관리
- 발행 간격 및 시간대 설정
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import random
from datetime import datetime
import json
import os

from src.sheets.content_manager_v3 import ContentManagerV3
from src.sheets.account_manager import AccountManager
from src.sheets.publish_settings_manager import PublishSettingsManager
from src.publisher.naver_blog_publisher import NaverBlogPublisher


class PublisherBot:
    """발행봇 메인 클래스"""

    def __init__(self, root):
        self.root = root
        self.root.title("네이버 블로그 발행봇 - 관리자 전용")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f5f5f5')

        # 매니저 초기화
        self.content_mgr = ContentManagerV3()
        self.account_mgr = AccountManager()
        self.settings_mgr = PublishSettingsManager()

        # 발행 상태
        self.publishing = False
        self.stop_requested = False
        self.publisher = None

        # 통계
        self.stats = {
            'total_published': 0,
            'total_failed': 0,
            'session_start': None
        }

        # UI 구성
        self.setup_ui()

        # 초기 데이터 로드
        self.refresh_all_data()

    def setup_ui(self):
        """UI 구성"""
        # 메인 컨테이너
        main_container = tk.Frame(self.root, bg='#f5f5f5')
        main_container.pack(fill='both', expand=True, padx=10, pady=10)

        # 상단: 제어 패널
        self.create_control_panel(main_container)

        # 중앙: 정보 패널
        middle_frame = tk.Frame(main_container, bg='#f5f5f5')
        middle_frame.pack(fill='both', expand=True, pady=(10, 0))

        # 좌측: 그룹별 현황
        left_frame = tk.Frame(middle_frame, bg='#f5f5f5')
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        self.create_group_panel(left_frame)

        # 우측: 발행 로그
        right_frame = tk.Frame(middle_frame, bg='#f5f5f5')
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        self.create_log_panel(right_frame)

        # 하단: 상태바
        self.create_status_bar(main_container)

    def create_control_panel(self, parent):
        """제어 패널"""
        card = tk.LabelFrame(parent, text="  발행 제어  ", bg='white',
                            font=('맑은 고딕', 11, 'bold'), padx=15, pady=10)
        card.pack(fill='x')

        # 버튼 행
        btn_frame = tk.Frame(card, bg='white')
        btn_frame.pack(fill='x')

        self.start_btn = tk.Button(btn_frame, text="발행 시작",
                                   command=self.start_publishing,
                                   bg='#4CAF50', fg='white',
                                   font=('맑은 고딕', 11, 'bold'),
                                   relief='flat', cursor='hand2',
                                   padx=20, pady=8)
        self.start_btn.pack(side='left', padx=(0, 10))

        self.stop_btn = tk.Button(btn_frame, text="발행 중지",
                                  command=self.stop_publishing,
                                  bg='#F44336', fg='white',
                                  font=('맑은 고딕', 11, 'bold'),
                                  relief='flat', cursor='hand2',
                                  padx=20, pady=8, state='disabled')
        self.stop_btn.pack(side='left', padx=(0, 10))

        tk.Button(btn_frame, text="새로고침",
                 command=self.refresh_all_data,
                 bg='#2196F3', fg='white',
                 font=('맑은 고딕', 10, 'bold'),
                 relief='flat', cursor='hand2',
                 padx=15, pady=8).pack(side='left', padx=(0, 10))

        tk.Button(btn_frame, text="일일 카운트 리셋",
                 command=self.reset_daily_counts,
                 bg='#FF9800', fg='white',
                 font=('맑은 고딕', 10, 'bold'),
                 relief='flat', cursor='hand2',
                 padx=15, pady=8).pack(side='left')

        # 발행 현황
        status_frame = tk.Frame(btn_frame, bg='white')
        status_frame.pack(side='right')

        self.publish_status_label = tk.Label(status_frame,
                                            text="대기 중",
                                            bg='white',
                                            font=('맑은 고딕', 12, 'bold'),
                                            fg='#666')
        self.publish_status_label.pack(side='right')

        # 옵션 행
        opt_frame = tk.Frame(card, bg='white')
        opt_frame.pack(fill='x', pady=(10, 0))

        tk.Label(opt_frame, text="헤드리스 모드:", bg='white',
                font=('맑은 고딕', 9)).pack(side='left')
        self.headless_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_frame, variable=self.headless_var).pack(side='left', padx=(5, 20))

        tk.Label(opt_frame, text="활성 그룹만:", bg='white',
                font=('맑은 고딕', 9)).pack(side='left')
        self.active_only_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, variable=self.active_only_var).pack(side='left')

    def create_group_panel(self, parent):
        """그룹별 현황 패널"""
        card = tk.LabelFrame(parent, text="  그룹별 현황  ", bg='white',
                            font=('맑은 고딕', 11, 'bold'), padx=10, pady=10)
        card.pack(fill='both', expand=True)

        # 트리뷰
        columns = ('그룹', '대기', '계정', '용량', '상태', '발행')
        self.group_tree = ttk.Treeview(card, columns=columns, show='headings', height=12)

        self.group_tree.heading('그룹', text='그룹')
        self.group_tree.heading('대기', text='대기 콘텐츠')
        self.group_tree.heading('계정', text='활성 계정')
        self.group_tree.heading('용량', text='남은 용량')
        self.group_tree.heading('상태', text='발행 상태')
        self.group_tree.heading('발행', text='오늘 발행')

        self.group_tree.column('그룹', width=100)
        self.group_tree.column('대기', width=80)
        self.group_tree.column('계정', width=80)
        self.group_tree.column('용량', width=80)
        self.group_tree.column('상태', width=80)
        self.group_tree.column('발행', width=80)

        scrollbar = ttk.Scrollbar(card, orient='vertical', command=self.group_tree.yview)
        self.group_tree.configure(yscrollcommand=scrollbar.set)

        self.group_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # 더블클릭으로 설정 편집
        self.group_tree.bind('<Double-1>', self.edit_group_settings)

    def create_log_panel(self, parent):
        """발행 로그 패널"""
        card = tk.LabelFrame(parent, text="  발행 로그  ", bg='white',
                            font=('맑은 고딕', 11, 'bold'), padx=10, pady=10)
        card.pack(fill='both', expand=True)

        self.log_text = scrolledtext.ScrolledText(card, height=20,
                                                  font=('Consolas', 9),
                                                  wrap='word', bg='#1e1e1e', fg='#d4d4d4')
        self.log_text.pack(fill='both', expand=True)

        # 로그 클리어 버튼
        tk.Button(card, text="로그 지우기",
                 command=lambda: self.log_text.delete(1.0, 'end'),
                 bg='#666', fg='white',
                 font=('맑은 고딕', 8),
                 relief='flat').pack(anchor='e', pady=(5, 0))

    def create_status_bar(self, parent):
        """상태바"""
        status_frame = tk.Frame(parent, bg='#333', height=30)
        status_frame.pack(fill='x', pady=(10, 0))
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(status_frame, text="준비됨",
                                    bg='#333', fg='white',
                                    font=('맑은 고딕', 9),
                                    padx=10)
        self.status_label.pack(side='left', fill='y')

        # 통계 표시
        self.stats_label = tk.Label(status_frame,
                                   text="오늘 발행: 0개 | 성공: 0개 | 실패: 0개",
                                   bg='#333', fg='#aaa',
                                   font=('맑은 고딕', 9),
                                   padx=10)
        self.stats_label.pack(side='right', fill='y')

    def log(self, message, level='info'):
        """로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        colors = {
            'info': '#d4d4d4',
            'success': '#4CAF50',
            'error': '#F44336',
            'warning': '#FF9800'
        }

        self.log_text.insert('end', f"[{timestamp}] ", 'timestamp')
        self.log_text.insert('end', f"{message}\n", level)

        self.log_text.tag_config('timestamp', foreground='#888')
        self.log_text.tag_config(level, foreground=colors.get(level, '#d4d4d4'))

        self.log_text.see('end')

    def refresh_all_data(self):
        """모든 데이터 새로고침"""
        self.log("데이터 새로고침 중...")

        # 설정 동기화 (새 계정 그룹 있으면 기본 설정 생성)
        self.settings_mgr.sync_with_account_groups()

        # 그룹 트리뷰 업데이트
        self.group_tree.delete(*self.group_tree.get_children())

        groups = self.account_mgr.get_account_groups()
        settings = self.settings_mgr.get_all_settings()

        for group in groups:
            # 대기 콘텐츠 수
            contents = self.content_mgr.get_ready_contents_by_group(group)
            content_count = len(contents)

            # 계정 통계
            acc_stats = self.account_mgr.get_group_stats(group)

            # 발행 설정
            setting = settings.get(group, {})
            can_publish, _ = self.settings_mgr.can_publish(group)

            status = "활성" if setting.get('enabled', False) else "비활성"
            if not can_publish and setting.get('enabled', False):
                status = "한도/시간"

            self.group_tree.insert('', 'end', values=(
                group,
                content_count,
                acc_stats['active'],
                acc_stats['remaining_capacity'],
                status,
                setting.get('today_count', 0)
            ))

        self.log("데이터 새로고침 완료", 'success')
        self.update_status("준비됨")

    def reset_daily_counts(self):
        """일일 카운트 리셋"""
        if not messagebox.askyesno("확인", "모든 그룹의 일일 발행 카운트를 리셋하시겠습니까?"):
            return

        # 계정 카운트 리셋
        acc_reset = self.account_mgr.reset_daily_counts()

        # 설정 카운트 리셋
        setting_reset = self.settings_mgr.reset_all_today_counts()

        self.log(f"일일 카운트 리셋 완료 (계정: {acc_reset}개, 설정: {setting_reset}개)", 'success')
        self.refresh_all_data()

    def edit_group_settings(self, event):
        """그룹 설정 편집 (더블클릭)"""
        selection = self.group_tree.selection()
        if not selection:
            return

        item = self.group_tree.item(selection[0])
        group_name = item['values'][0]

        # 설정 편집 창 열기
        self.open_settings_dialog(group_name)

    def open_settings_dialog(self, group_name):
        """설정 편집 다이얼로그"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"발행 설정 - {group_name}")
        dialog.geometry("400x400")
        dialog.configure(bg='white')
        dialog.transient(self.root)
        dialog.grab_set()

        setting = self.settings_mgr.get_setting(group_name)
        if not setting:
            messagebox.showerror("오류", "설정을 찾을 수 없습니다.")
            dialog.destroy()
            return

        # 폼
        frame = tk.Frame(dialog, bg='white', padx=20, pady=20)
        frame.pack(fill='both', expand=True)

        row = 0

        # 활성화
        tk.Label(frame, text="발행 활성화:", bg='white',
                font=('맑은 고딕', 10)).grid(row=row, column=0, sticky='w', pady=5)
        enabled_var = tk.BooleanVar(value=setting['enabled'])
        ttk.Checkbutton(frame, variable=enabled_var).grid(row=row, column=1, sticky='w')
        row += 1

        # 발행 간격
        tk.Label(frame, text="최소 간격(초):", bg='white',
                font=('맑은 고딕', 10)).grid(row=row, column=0, sticky='w', pady=5)
        interval_min_var = tk.StringVar(value=str(setting['interval_min']))
        tk.Entry(frame, textvariable=interval_min_var, width=10).grid(row=row, column=1, sticky='w')
        row += 1

        tk.Label(frame, text="최대 간격(초):", bg='white',
                font=('맑은 고딕', 10)).grid(row=row, column=0, sticky='w', pady=5)
        interval_max_var = tk.StringVar(value=str(setting['interval_max']))
        tk.Entry(frame, textvariable=interval_max_var, width=10).grid(row=row, column=1, sticky='w')
        row += 1

        # 일일 한도
        tk.Label(frame, text="일일 한도:", bg='white',
                font=('맑은 고딕', 10)).grid(row=row, column=0, sticky='w', pady=5)
        daily_limit_var = tk.StringVar(value=str(setting['daily_limit']))
        tk.Entry(frame, textvariable=daily_limit_var, width=10).grid(row=row, column=1, sticky='w')
        row += 1

        # 발행 시간대
        tk.Label(frame, text="시작 시간(0-23):", bg='white',
                font=('맑은 고딕', 10)).grid(row=row, column=0, sticky='w', pady=5)
        start_hour_var = tk.StringVar(value=str(setting['start_hour']))
        tk.Entry(frame, textvariable=start_hour_var, width=10).grid(row=row, column=1, sticky='w')
        row += 1

        tk.Label(frame, text="종료 시간(1-24):", bg='white',
                font=('맑은 고딕', 10)).grid(row=row, column=0, sticky='w', pady=5)
        end_hour_var = tk.StringVar(value=str(setting['end_hour']))
        tk.Entry(frame, textvariable=end_hour_var, width=10).grid(row=row, column=1, sticky='w')
        row += 1

        # 버튼
        btn_frame = tk.Frame(frame, bg='white')
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)

        def save_settings():
            try:
                self.settings_mgr.update_setting(
                    group_name,
                    enabled=enabled_var.get(),
                    interval_min=int(interval_min_var.get()),
                    interval_max=int(interval_max_var.get()),
                    daily_limit=int(daily_limit_var.get()),
                    start_hour=int(start_hour_var.get()),
                    end_hour=int(end_hour_var.get())
                )
                self.log(f"[{group_name}] 설정 저장 완료", 'success')
                self.refresh_all_data()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("오류", f"저장 실패: {e}")

        tk.Button(btn_frame, text="저장", command=save_settings,
                 bg='#4CAF50', fg='white',
                 font=('맑은 고딕', 10, 'bold'),
                 relief='flat', padx=20).pack(side='left', padx=5)

        tk.Button(btn_frame, text="취소", command=dialog.destroy,
                 bg='#666', fg='white',
                 font=('맑은 고딕', 10),
                 relief='flat', padx=20).pack(side='left', padx=5)

    def update_status(self, message):
        """상태바 업데이트"""
        self.status_label.config(text=message)

    def update_stats(self):
        """통계 업데이트"""
        self.stats_label.config(
            text=f"오늘 발행: {self.stats['total_published'] + self.stats['total_failed']}개 | "
                 f"성공: {self.stats['total_published']}개 | "
                 f"실패: {self.stats['total_failed']}개"
        )

    def start_publishing(self):
        """발행 시작"""
        if self.publishing:
            return

        self.publishing = True
        self.stop_requested = False
        self.stats['session_start'] = datetime.now()

        self.start_btn.config(state='disabled', bg='#999')
        self.stop_btn.config(state='normal', bg='#F44336')
        self.publish_status_label.config(text="발행 중...", fg='#4CAF50')

        # 발행 스레드 시작
        thread = threading.Thread(target=self.publishing_loop, daemon=True)
        thread.start()

    def stop_publishing(self):
        """발행 중지"""
        self.stop_requested = True
        self.log("발행 중지 요청됨...", 'warning')
        self.update_status("중지 중...")

    def publishing_loop(self):
        """발행 루프"""
        self.log("=" * 40)
        self.log("발행봇 시작", 'success')
        self.log("=" * 40)

        while not self.stop_requested:
            try:
                # 발행 가능한 그룹 확인
                published_any = False

                groups = self.account_mgr.get_account_groups()
                if self.active_only_var.get():
                    groups = [g for g in groups if self.settings_mgr.get_setting(g).get('enabled', False)]

                for group in groups:
                    if self.stop_requested:
                        break

                    # 발행 가능 확인
                    can_publish, reason = self.settings_mgr.can_publish(group)
                    if not can_publish:
                        continue

                    # 사용 가능한 계정 확인
                    account = self.account_mgr.get_available_account(group)
                    if not account:
                        self.log(f"[{group}] 사용 가능한 계정 없음", 'warning')
                        continue

                    # 발행 대기 콘텐츠 확인
                    contents = self.content_mgr.get_ready_contents_by_group(group)
                    if not contents:
                        continue

                    content = contents[0]  # 가장 오래된 콘텐츠

                    # 발행 시도
                    self.root.after(0, lambda g=group, c=content: self.update_status(
                        f"[{g}] 발행 중: {c['title'][:20]}..."
                    ))

                    success = self.publish_single(group, account, content)

                    if success:
                        published_any = True
                        self.stats['total_published'] += 1
                    else:
                        self.stats['total_failed'] += 1

                    self.root.after(0, self.update_stats)
                    self.root.after(0, self.refresh_all_data)

                    # 발행 간격 대기
                    if not self.stop_requested:
                        setting = self.settings_mgr.get_setting(group)
                        interval = random.randint(
                            setting['interval_min'],
                            setting['interval_max']
                        )
                        self.log(f"다음 발행까지 {interval}초 대기...")
                        self.wait_with_check(interval)

                # 발행할 게 없으면 잠시 대기
                if not published_any and not self.stop_requested:
                    self.log("발행 대기 중... (30초 후 재확인)")
                    self.wait_with_check(30)

            except Exception as e:
                self.log(f"발행 루프 오류: {e}", 'error')
                if not self.stop_requested:
                    self.wait_with_check(10)

        # 종료 처리
        self.root.after(0, self.on_publishing_stopped)

    def wait_with_check(self, seconds):
        """중지 요청 체크하며 대기"""
        for _ in range(seconds):
            if self.stop_requested:
                break
            time.sleep(1)

    def publish_single(self, group, account, content):
        """단일 콘텐츠 발행"""
        self.log(f"[{group}] 발행 시작: {content['title'][:30]}...")
        self.log(f"  계정: {account['account_id']}")

        publisher = None  # finally에서 사용하기 위해 미리 선언

        try:
            # 발행 중 상태로 변경
            self.content_mgr.mark_as_publishing(
                content['sheet_name'],
                content['row_num']
            )

            # 발행기 초기화
            publisher = NaverBlogPublisher(headless=self.headless_var.get())
            publisher.set_log_callback(lambda msg: self.log(f"  {msg}"))
            publisher.start_browser()

            # 쿠키 파일명 (계정별)
            cookie_file = f"cookies/{account['account_id']}_cookies.json"
            os.makedirs('cookies', exist_ok=True)
            publisher.cookie_path = cookie_file

            # 로그인 시도
            logged_in = False
            if os.path.exists(cookie_file):
                logged_in = publisher.login_with_cookies()

            if not logged_in:
                logged_in = publisher.login_with_credentials(
                    account['account_id'],
                    account['password']
                )

            if not logged_in:
                raise Exception("로그인 실패")

            # 발행
            result = publisher.publish_post(
                title=content['title'],
                content=content['content']
            )

            if result['success']:
                # 발행 완료 처리 - URL과 계정 정보 함께 저장
                self.content_mgr.mark_as_published(
                    content['sheet_name'],
                    content['row_num'],
                    published_url=result.get('url', ''),
                    account_id=account['account_id']
                )
                self.account_mgr.increment_usage(group, account['account_id'])
                self.settings_mgr.increment_today_count(group)

                self.log(f"[{group}] 발행 성공!", 'success')
                self.log(f"  URL: {result['url']}")
                return True
            else:
                # 발행 실패
                self.content_mgr.mark_as_failed(
                    content['sheet_name'],
                    content['row_num']
                )
                self.log(f"[{group}] 발행 실패: {result['error']}", 'error')
                return False

        except Exception as e:
            self.log(f"[{group}] 발행 오류: {e}", 'error')
            import traceback
            self.log(f"  상세: {traceback.format_exc()}", 'error')

            # 실패 상태로 변경
            try:
                self.content_mgr.mark_as_failed(
                    content['sheet_name'],
                    content['row_num']
                )
            except:
                pass

            return False

        finally:
            # 브라우저 안전하게 종료
            if publisher:
                try:
                    publisher.close_browser()
                except Exception as e:
                    self.log(f"  브라우저 종료 오류: {e}", 'warning')

    def on_publishing_stopped(self):
        """발행 중지 후 처리"""
        self.publishing = False
        self.stop_requested = False

        self.start_btn.config(state='normal', bg='#4CAF50')
        self.stop_btn.config(state='disabled', bg='#999')
        self.publish_status_label.config(text="대기 중", fg='#666')

        self.log("=" * 40)
        self.log("발행봇 중지됨", 'warning')
        self.log(f"세션 통계 - 성공: {self.stats['total_published']}개, "
                f"실패: {self.stats['total_failed']}개")
        self.log("=" * 40)

        self.update_status("준비됨")


def main():
    """메인 함수"""
    root = tk.Tk()
    app = PublisherBot(root)
    root.mainloop()


if __name__ == "__main__":
    main()
