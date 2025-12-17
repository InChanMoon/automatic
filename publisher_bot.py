"""
네이버 블로그 자동 발행봇 - Publisher Bot
컴팩트 UI 버전
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import random
from datetime import datetime
import os
import uuid

from src.sheets.content_manager_v3 import ContentManagerV3
from src.sheets.account_manager import AccountManager
from src.sheets.publish_settings_manager import PublishSettingsManager
from src.publisher.naver_blog_publisher import NaverBlogPublisher
from src.drive.image_manager import DriveImageManager


class PublisherBot:
    """발행봇 메인 클래스"""

    def __init__(self, root):
        self.root = root
        self.root.title("네이버 블로그 발행봇")
        self.root.geometry("750x450")
        self.root.configure(bg='#f0f0f0')

        # 봇 ID (동시성 제어용)
        self.bot_id = f"bot_{uuid.uuid4().hex[:8]}"

        # 매니저 초기화
        self.content_mgr = ContentManagerV3()
        self.account_mgr = AccountManager()
        self.settings_mgr = PublishSettingsManager()

        # 이미지 매니저 초기화
        try:
            self.image_mgr = DriveImageManager()
            if not self.image_mgr.test_connection():
                self.image_mgr = None
        except:
            self.image_mgr = None

        # 상태
        self.publishing = False
        self.stop_requested = False
        self.group_checkboxes = {}
        self.stats = {'published': 0, 'failed': 0}

        self.setup_ui()
        self.refresh_all_data()

    def setup_ui(self):
        """UI 구성"""
        # 상단 컨트롤
        top = tk.Frame(self.root, bg='#f0f0f0')
        top.pack(fill='x', padx=6, pady=4)

        # 버튼들 (작은 크기)
        self.start_btn = tk.Button(top, text="▶시작", command=self.start_publishing,
                                   bg='#4CAF50', fg='white', font=('맑은 고딕', 8, 'bold'),
                                   relief='flat', padx=8, pady=2)
        self.start_btn.pack(side='left', padx=1)

        self.stop_btn = tk.Button(top, text="■중지", command=self.stop_publishing,
                                  bg='#f44336', fg='white', font=('맑은 고딕', 8, 'bold'),
                                  relief='flat', padx=8, pady=2, state='disabled')
        self.stop_btn.pack(side='left', padx=1)

        tk.Button(top, text="새로고침", command=self.refresh_all_data,
                 bg='#2196F3', fg='white', font=('맑은 고딕', 8),
                 relief='flat', padx=6, pady=2).pack(side='left', padx=1)

        tk.Button(top, text="잠금해제", command=self.force_release_locks,
                 bg='#FF9800', fg='white', font=('맑은 고딕', 8),
                 relief='flat', padx=6, pady=2).pack(side='left', padx=1)

        # 헤드리스 옵션
        self.headless_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="헤드리스", variable=self.headless_var).pack(side='left', padx=6)

        # 상태 표시
        self.status_label = tk.Label(top, text="대기중", bg='#f0f0f0', fg='#666',
                                    font=('맑은 고딕', 8, 'bold'))
        self.status_label.pack(side='right', padx=3)

        tk.Label(top, text=f"ID:{self.bot_id[-6:]}", bg='#f0f0f0', fg='#999',
                font=('맑은 고딕', 7)).pack(side='right', padx=3)

        # 메인 영역 (좌: 그룹, 우: 로그)
        main = tk.PanedWindow(self.root, orient='horizontal', bg='#f0f0f0', sashwidth=3)
        main.pack(fill='both', expand=True, padx=6, pady=3)

        # 좌측: 그룹 목록
        left = tk.Frame(main, bg='white')
        main.add(left, width=200)

        # 그룹 헤더
        header = tk.Frame(left, bg='white')
        header.pack(fill='x', padx=3, pady=2)

        self.select_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(header, text="전체", variable=self.select_all_var,
                       command=self.toggle_select_all).pack(side='left')
        self.count_label = tk.Label(header, text="(0)", bg='white', fg='#666', font=('맑은 고딕', 7))
        self.count_label.pack(side='left', padx=3)

        # 그룹 트리뷰 (컴팩트)
        tree_frame = tk.Frame(left, bg='white')
        tree_frame.pack(fill='both', expand=True, padx=2, pady=2)

        # 스타일 설정 (행 색상)
        style = ttk.Style()
        style.configure('Compact.Treeview', rowheight=20, font=('맑은 고딕', 8))
        style.configure('Compact.Treeview.Heading', font=('맑은 고딕', 8, 'bold'))

        cols = ('sel', 'group', 'wait', 'today', 'per_acc')
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings',
                                 height=12, style='Compact.Treeview')

        self.tree.heading('sel', text='')
        self.tree.heading('group', text='그룹')
        self.tree.heading('wait', text='대기')
        self.tree.heading('today', text='발행')
        self.tree.heading('per_acc', text='계정당')

        self.tree.column('sel', width=25, anchor='center', stretch=False)
        self.tree.column('group', width=55, stretch=True)
        self.tree.column('wait', width=35, anchor='center', stretch=False)
        self.tree.column('today', width=35, anchor='center', stretch=False)
        self.tree.column('per_acc', width=50, anchor='center', stretch=False)

        # 행 색상 태그 설정
        self.tree.tag_configure('available', background='#e8f5e9')
        self.tree.tag_configure('locked', background='#ffebee')

        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self.tree.bind('<ButtonRelease-1>', self.on_tree_click)
        self.tree.bind('<Double-1>', self.on_tree_double_click)

        # 우측: 로그
        right = tk.Frame(main, bg='white')
        main.add(right)

        # 로그 헤더 (삭제 버튼)
        log_header = tk.Frame(right, bg='white')
        log_header.pack(fill='x', padx=2, pady=1)
        tk.Button(log_header, text="로그삭제", command=self.clear_log,
                 bg='#666', fg='white', font=('맑은 고딕', 7),
                 relief='flat', padx=4, pady=0).pack(side='right')

        self.log_text = scrolledtext.ScrolledText(right, font=('Consolas', 8),
                                                  wrap='word', bg='#1a1a1a', fg='#ccc')
        self.log_text.pack(fill='both', expand=True, padx=2, pady=2)

        # 하단 상태바
        bottom = tk.Frame(self.root, bg='#333', height=18)
        bottom.pack(fill='x')
        bottom.pack_propagate(False)

        self.stats_label = tk.Label(bottom, text="성공:0 실패:0", bg='#333', fg='#aaa',
                                   font=('맑은 고딕', 7))
        self.stats_label.pack(side='right', padx=8)

    def log(self, msg, level='info'):
        """로그 출력"""
        ts = datetime.now().strftime("%H:%M:%S")
        colors = {'info': '#ccc', 'success': '#4CAF50', 'error': '#f44336', 'warning': '#FF9800'}
        print(f"[{ts}] {msg}")
        try:
            if self.root.winfo_exists():
                self.log_text.insert('end', f"[{ts}] {msg}\n", level)
                self.log_text.tag_config(level, foreground=colors.get(level, '#ccc'))
                self.log_text.see('end')
        except:
            pass

    def clear_log(self):
        """로그 삭제"""
        self.log_text.delete('1.0', 'end')

    def toggle_select_all(self):
        """전체 선택"""
        val = self.select_all_var.get()
        for v in self.group_checkboxes.values():
            v.set(val)
        self.update_tree_checks()
        self.update_count()

    def on_tree_click(self, e):
        """트리 클릭 - 체크박스만 처리"""
        col = self.tree.identify_column(e.x)
        item = self.tree.identify_row(e.y)

        if not item:
            return

        vals = self.tree.item(item)['values']
        if not vals:
            return

        grp = vals[1]

        # 첫번째 컬럼 (체크박스)만 처리
        if col == '#1':
            if grp in self.group_checkboxes:
                self.group_checkboxes[grp].set(not self.group_checkboxes[grp].get())
                self.update_tree_checks()
                self.update_count()

    def on_tree_double_click(self, e):
        """더블클릭 - 상세 설정"""
        col = self.tree.identify_column(e.x)
        if col == '#1':  # 체크박스 컬럼은 무시
            return
        sel = self.tree.selection()
        if sel:
            grp = self.tree.item(sel[0])['values'][1]
            self.open_group_settings(grp)

    def update_tree_checks(self):
        """트리 체크박스만 업데이트"""
        for item in self.tree.get_children():
            vals = list(self.tree.item(item)['values'])
            grp = vals[1]
            if grp in self.group_checkboxes:
                vals[0] = "☑" if self.group_checkboxes[grp].get() else "☐"
                self.tree.item(item, values=vals)

    def update_count(self):
        """선택 수 업데이트"""
        cnt = sum(1 for v in self.group_checkboxes.values() if v.get())
        self.count_label.config(text=f"({cnt})")

    def refresh_all_data(self):
        """데이터 새로고침"""
        self.log("새로고침...")
        self.settings_mgr.sync_with_account_groups()

        old = {k: v.get() for k, v in self.group_checkboxes.items()}
        self.tree.delete(*self.tree.get_children())
        self.group_checkboxes.clear()

        groups = self.account_mgr.get_account_groups()
        settings = self.settings_mgr.get_all_settings()

        for grp in groups:
            contents = self.content_mgr.get_ready_contents_by_group(grp)
            setting = settings.get(grp, {})

            locked, _ = self.settings_mgr.is_locked(grp)
            tag = 'locked' if locked else 'available'

            var = tk.BooleanVar(value=old.get(grp, False))
            self.group_checkboxes[grp] = var

            self.tree.insert('', 'end', values=(
                "☑" if var.get() else "☐",
                grp,
                len(contents),
                setting.get('today_count', 0),
                setting.get('posts_per_account', 5)
            ), tags=(tag,))

        self.update_count()
        self.log("새로고침 완료", 'success')

    def force_release_locks(self):
        """잠금 해제"""
        selected = [k for k, v in self.group_checkboxes.items() if v.get()]
        if not selected:
            messagebox.showinfo("알림", "그룹을 선택하세요")
            return
        for grp in selected:
            self.settings_mgr.force_release_lock(grp)
            self.log(f"[{grp}] 잠금해제", 'success')
        self.refresh_all_data()

    def open_group_settings(self, group_name):
        """그룹 상세 설정 다이얼로그"""
        dlg = tk.Toplevel(self.root)
        dlg.title(f"{group_name}")
        dlg.configure(bg='white')
        dlg.transient(self.root)
        dlg.grab_set()

        # 메인 창 중앙에 위치
        dlg.update_idletasks()
        w, h = 280, 250
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")

        setting = self.settings_mgr.get_setting(group_name)
        if not setting:
            dlg.destroy()
            return

        f = tk.Frame(dlg, bg='white', padx=10, pady=8)
        f.pack(fill='both', expand=True)

        # 계정 선택
        acc_frame = tk.Frame(f, bg='white')
        acc_frame.pack(fill='x', pady=2)
        tk.Label(acc_frame, text="계정:", bg='white', width=10, anchor='w', font=('맑은 고딕', 8)).pack(side='left')

        accounts = self.account_mgr.get_accounts_by_group(group_name)
        acc_ids = [a['account_id'] for a in accounts]
        acc_var = tk.StringVar(value=setting['account'] or (acc_ids[0] if acc_ids else ''))
        ttk.Combobox(acc_frame, textvariable=acc_var, values=acc_ids, width=14, font=('맑은 고딕', 8)).pack(side='left')

        # 계정당 발행수
        ppa_frame = tk.Frame(f, bg='white')
        ppa_frame.pack(fill='x', pady=2)
        tk.Label(ppa_frame, text="계정당발행:", bg='white', width=10, anchor='w', font=('맑은 고딕', 8)).pack(side='left')
        ppa_var = tk.StringVar(value=str(setting['posts_per_account']))
        tk.Spinbox(ppa_frame, from_=1, to=999, width=6, textvariable=ppa_var,
                  font=('맑은 고딕', 8), justify='center').pack(side='left')

        # 현재 발행수
        cur_frame = tk.Frame(f, bg='white')
        cur_frame.pack(fill='x', pady=2)
        tk.Label(cur_frame, text="현재발행:", bg='white', width=10, anchor='w', font=('맑은 고딕', 8)).pack(side='left')
        tk.Label(cur_frame, text=f"{setting['account_post_count']}개",
                bg='white', font=('맑은 고딕', 8)).pack(side='left')

        # 오늘발행
        today_frame = tk.Frame(f, bg='white')
        today_frame.pack(fill='x', pady=2)
        tk.Label(today_frame, text="오늘발행:", bg='white', width=10, anchor='w', font=('맑은 고딕', 8)).pack(side='left')
        tk.Label(today_frame, text=f"{setting['today_count']}개", bg='white', font=('맑은 고딕', 8)).pack(side='left')

        # 잠금상태
        lock_frame = tk.Frame(f, bg='white')
        lock_frame.pack(fill='x', pady=2)
        tk.Label(lock_frame, text="잠금:", bg='white', width=10, anchor='w', font=('맑은 고딕', 8)).pack(side='left')
        locked, locker = self.settings_mgr.is_locked(group_name)
        if locked:
            tk.Label(lock_frame, text=f"잠금({locker[:6]})", bg='white', fg='#f44336', font=('맑은 고딕', 8)).pack(side='left')
            tk.Button(lock_frame, text="해제", command=lambda: self._release_and_reload(group_name, dlg),
                     bg='#FF9800', fg='white', font=('맑은 고딕', 7), relief='flat', padx=4).pack(side='left', padx=3)
        else:
            tk.Label(lock_frame, text="사용가능", bg='white', fg='#4CAF50', font=('맑은 고딕', 8)).pack(side='left')

        tk.Frame(f, bg='#ddd', height=1).pack(fill='x', pady=5)

        # 리셋 버튼들
        reset_frame = tk.Frame(f, bg='white')
        reset_frame.pack(fill='x', pady=2)
        tk.Button(reset_frame, text="오늘발행 리셋", command=lambda: self._reset_today(group_name, dlg),
                 bg='#9C27B0', fg='white', font=('맑은 고딕', 7), relief='flat', padx=4).pack(side='left')
        tk.Button(reset_frame, text="계정발행 리셋", command=lambda: self._reset_account(group_name, dlg),
                 bg='#607D8B', fg='white', font=('맑은 고딕', 7), relief='flat', padx=4).pack(side='left', padx=3)

        tk.Frame(f, bg='#ddd', height=1).pack(fill='x', pady=5)

        # 저장/닫기 버튼
        btn_frame = tk.Frame(f, bg='white')
        btn_frame.pack()

        def save():
            try:
                new_ppa = int(ppa_var.get())
                if new_ppa < 1:
                    new_ppa = 1
                self.settings_mgr.update_setting(group_name, account=acc_var.get(), posts_per_account=new_ppa)
                self.log(f"[{group_name}] 설정저장", 'success')
                self.refresh_all_data()
                dlg.destroy()
            except Exception as e:
                messagebox.showerror("오류", str(e))

        tk.Button(btn_frame, text="저장", command=save, bg='#4CAF50', fg='white',
                 font=('맑은 고딕', 8), relief='flat', padx=10).pack(side='left', padx=2)
        tk.Button(btn_frame, text="닫기", command=dlg.destroy, bg='#666', fg='white',
                 font=('맑은 고딕', 8), relief='flat', padx=10).pack(side='left', padx=2)

    def _release_and_reload(self, grp, dlg):
        self.settings_mgr.force_release_lock(grp)
        dlg.destroy()
        self.refresh_all_data()
        self.open_group_settings(grp)

    def _reset_today(self, grp, dlg):
        self.settings_mgr.update_setting(grp, today_count=0)
        self.log(f"[{grp}] 오늘발행 리셋", 'success')
        dlg.destroy()
        self.refresh_all_data()

    def _reset_account(self, grp, dlg):
        self.settings_mgr.update_setting(grp, account_post_count=0)
        self.log(f"[{grp}] 계정발행 리셋", 'success')
        dlg.destroy()
        self.refresh_all_data()

    def start_publishing(self):
        """발행 시작"""
        selected = [k for k, v in self.group_checkboxes.items() if v.get()]
        if not selected:
            messagebox.showwarning("알림", "그룹을 선택하세요")
            return

        self.publishing = True
        self.stop_requested = False
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_label.config(text="발행중", fg='#4CAF50')

        threading.Thread(target=self.publish_loop, args=(selected,), daemon=True).start()

    def stop_publishing(self):
        """발행 중지"""
        self.stop_requested = True
        self.log("중지 요청...", 'warning')

    def publish_loop(self, groups):
        """발행 루프"""
        self.log(f"시작: {', '.join(groups)}", 'success')

        try:
            while not self.stop_requested:
                published = False

                for grp in groups:
                    if self.stop_requested:
                        break

                    # 잠금 획득
                    if not self.settings_mgr.acquire_lock(grp, self.bot_id):
                        continue

                    try:
                        # 계정 전환 체크
                        if self.settings_mgr.should_switch_account(grp):
                            setting = self.settings_mgr.get_setting(grp)
                            cur = setting.get('account', '')
                            accs = [a['account_id'] for a in self.account_mgr.get_accounts_by_group(grp)]
                            if cur in accs:
                                nxt = accs[(accs.index(cur) + 1) % len(accs)]
                            else:
                                nxt = accs[0] if accs else None
                            if nxt:
                                self.settings_mgr.switch_to_next_account(grp, nxt)
                                self.log(f"[{grp}] 계정전환: {nxt}", 'warning')

                        # 계정 확인
                        setting = self.settings_mgr.get_setting(grp)
                        acc_id = setting.get('account', '')
                        if not acc_id:
                            acc = self.account_mgr.get_available_account(grp)
                            if acc:
                                acc_id = acc['account_id']
                                self.settings_mgr.update_setting(grp, account=acc_id)
                        else:
                            acc = self.account_mgr.get_account_by_id(grp, acc_id)

                        if not acc:
                            continue

                        # 콘텐츠 확인
                        contents = self.content_mgr.get_ready_contents_by_group(grp)
                        if not contents:
                            continue

                        content = contents[0]
                        success = self.publish_one(grp, acc, content)

                        if success:
                            published = True
                            self.stats['published'] += 1
                        else:
                            self.stats['failed'] += 1

                        self.root.after(0, lambda: self.stats_label.config(
                            text=f"성공:{self.stats['published']} 실패:{self.stats['failed']}"))
                        self.root.after(0, self.refresh_all_data)

                        if not self.stop_requested:
                            wait = random.randint(3, 8)
                            self.log(f"{wait}초 대기...")
                            self._wait(wait)

                    finally:
                        self.settings_mgr.release_lock(grp, self.bot_id)

                if not published and not self.stop_requested:
                    self.log("대기중... (30초)")
                    self._wait(30)

        finally:
            for grp in groups:
                try:
                    self.settings_mgr.release_lock(grp, self.bot_id)
                except:
                    pass
            self.root.after(0, self._on_stop)

    def _wait(self, sec):
        for _ in range(sec):
            if self.stop_requested:
                break
            time.sleep(1)

    def _on_stop(self):
        self.publishing = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_label.config(text="대기중", fg='#666')
        self.log("중지됨", 'warning')

    def _count_markers(self, content):
        import re
        pattern = r'\{img:(\d+)(?:-(\d+))?\}'
        mx = 0
        for m in re.finditer(pattern, content):
            s, e = int(m.group(1)), int(m.group(2)) if m.group(2) else int(m.group(1))
            mx = max(mx, s, e)
        return mx

    def publish_one(self, grp, acc, content):
        """단일 발행"""
        self.log(f"[{grp}] 발행: {content['title'][:20]}...")

        pub = None
        try:
            self.content_mgr.mark_as_publishing(content['sheet_name'], content['row_num'])

            # 이미지
            images = []
            cnt = self._count_markers(content['content'])
            if cnt > 0 and self.image_mgr:
                kw = content.get('keyword', '')
                if kw:
                    images = self.image_mgr.get_images_for_post(kw, cnt)

            # 발행
            pub = NaverBlogPublisher(headless=self.headless_var.get())
            pub.set_log_callback(lambda m: self.log(f"  {m}"))
            pub.start_browser()

            cookie = f"cookies/{acc['account_id']}_cookies.json"
            os.makedirs('cookies', exist_ok=True)
            pub.cookie_path = cookie

            logged = False
            if os.path.exists(cookie):
                logged = pub.login_with_cookies()
            if not logged:
                logged = pub.login_with_credentials(acc['account_id'], acc['password'])
            if not logged:
                raise Exception("로그인 실패")

            result = pub.publish_post(
                title=content['title'],
                content=content['content'],
                images=images,
                scheduled_time=content.get('scheduled_time')
            )

            if result['success']:
                self.content_mgr.mark_as_published(content['sheet_name'], content['row_num'],
                    published_url=result.get('url', ''), account_id=acc['account_id'])
                self.account_mgr.increment_usage(grp, acc['account_id'])
                self.settings_mgr.increment_today_count(grp)
                self.log(f"[{grp}] 성공!", 'success')
                return True
            else:
                self.content_mgr.mark_as_failed(content['sheet_name'], content['row_num'])
                self.log(f"[{grp}] 실패: {result['error']}", 'error')
                return False

        except Exception as e:
            self.log(f"[{grp}] 오류: {e}", 'error')
            try:
                self.content_mgr.mark_as_failed(content['sheet_name'], content['row_num'])
            except:
                pass
            return False
        finally:
            if pub:
                try:
                    pub.close_browser()
                except:
                    pass


def main():
    root = tk.Tk()
    PublisherBot(root)
    root.mainloop()


if __name__ == "__main__":
    main()
