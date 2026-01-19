"""
네이버 블로그 콘텐츠 생성기 PRO v3.0

대량 원고 자동 생성 + 실시간 리스트 업데이트 + 멈춤 기능
이미지 마커 지원 + 글자 수 제한
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import json
import re
from datetime import datetime, timedelta
import calendar

from src.sheets.license_manager import LicenseManager
from src.sheets.content_manager_v2 import ContentManagerV2
from src.content.gemini_generator import GeminiGenerator
from src.content.gpt_generator import GPTGenerator
from src.crawler.naver_blog_crawler import NaverBlogCrawler
from src.utils.naver_html_generator import NaverHTMLGenerator
from src.drive.image_manager import DriveImageManager


# URL 리라이팅 기본 프롬프트
DEFAULT_REWRITE_PROMPT = """글을 제공할건데, 글의 문단 및 구조는 비교하기 쉽게 그대로 제공해주고, 글의 말투 어미를 동일하게 바꾸는데, 조금 길게 바꿔주고, 조사도 중간중간 많이 바꿔줘."""

# 프롬프트 작성 탭 기본 지시사항
DEFAULT_PROMPT_INSTRUCTION = """[출력 형식]
제목: (여기에 제목)

본문:
(여기에 본문)

[글 구조 - SEO]
- 제목: 키워드 포함, 30자 이내
- 서론: 키워드 포함
- 본론: 소제목 2-3개로 구분
- 결론: 요약
- 글자 수: {char_limit}자 내외

[서식 마커]
- {{quote:인용문}}: 핵심 문장 강조
- {{table:A<C>B<R>C<C>D}}: 비교/정리 표 (<C>=열, <R>=행)
- {{hr}}: 섹션 구분선

[규칙]
1. 마크다운(**, ##, #) 절대 금지
2. 인용구/표를 적절히 활용
3. 키워드 자연스럽게 3-5회 포함
4. 제목과 본문만 출력"""


class ContentCreatorProV3:
    """프로 콘텐츠 생성기 v3.0"""

    def __init__(self, root):
        self.root = root
        self.root.title("네이버 블로그 콘텐츠 생성기 PRO v3.0")
        self.root.geometry("1400x900")
        self.root.resizable(True, True)
        self.root.configure(bg='#f5f5f5')

        # 스타일 설정
        self.setup_styles()

        # 매니저 초기화
        self.license_mgr = LicenseManager()
        self.content_mgr = ContentManagerV2()
        self.crawler = NaverBlogCrawler()
        self.html_generator = NaverHTMLGenerator()
        self.generator = None

        # 이미지 매니저 (폴더 목록용)
        try:
            self.image_mgr = DriveImageManager()
            self.image_folders = []  # 캐시
        except Exception:
            self.image_mgr = None
            self.image_folders = []

        # 변수
        self.generating = False
        self.custom_prompt_instruction = None  # 커스텀 지시사항 (None이면 기본값 사용)
        self.stop_requested = False
        self.current_license = None
        self.editing_content_id = None

        # GUI 구성
        self.create_widgets()

        # 라이선스 자동 로드
        self.load_saved_license()

        # 이미지 폴더 목록 로드
        self.root.after(500, self.refresh_image_folders)

    def show_working(self, message):
        """작업 중 상태 표시"""
        self.progress_bar.pack(side='left', padx=(0, 10))
        self.progress_bar.start(10)
        self.progress_label.config(text=f"⏳ {message}", bg='#FFF3CD', fg='#856404')
        self.root.update_idletasks()

    def show_success(self, message):
        """성공 상태 표시"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.progress_label.config(text=f"✅ {message}", bg='#D4EDDA', fg='#155724')

    def show_error(self, message):
        """에러 상태 표시"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.progress_label.config(text=f"❌ {message}", bg='#F8D7DA', fg='#721C24')

    def show_info(self, message):
        """정보 상태 표시"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.progress_label.config(text=f"ℹ️ {message}", bg='#D1ECF1', fg='#0C5460')

    def setup_styles(self):
        """스타일 설정"""
        style = ttk.Style()
        style.theme_use('clam')

    def create_widgets(self):
        """위젯 생성"""
        # 메인 컨테이너
        main_container = tk.Frame(self.root, bg='#f5f5f5')
        main_container.pack(fill='both', expand=True, padx=15, pady=15)

        # 왼쪽: 입력 영역
        self.left_frame = tk.Frame(main_container, bg='#f5f5f5', width=500)
        self.left_frame.pack(side='left', fill='both', padx=(0, 10))
        self.left_frame.pack_propagate(False)

        # 오른쪽: 콘텐츠 리스트 + 수정 (접기/펼치기 가능)
        self.right_frame = tk.Frame(main_container, bg='#f5f5f5')
        self.right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
        self.right_panel_visible = True  # 오른쪽 패널 표시 상태

        # === 왼쪽 영역 ===
        # 상단 헤더 (토글 버튼 포함)
        left_header = tk.Frame(self.left_frame, bg='#f5f5f5')
        left_header.pack(fill='x', pady=(0, 5))

        self.toggle_btn = tk.Button(left_header, text="◀ 콘텐츠 목록",
                                    command=self.toggle_right_panel,
                                    bg='#607D8B', fg='white', font=('맑은 고딕', 9, 'bold'),
                                    relief='flat', cursor='hand2', padx=10)
        self.toggle_btn.pack(side='right')

        self.create_license_section(self.left_frame)
        self.create_input_section(self.left_frame)

        # === 오른쪽 영역 ===
        self.create_content_management_section(self.right_frame)

        # 하단: 상태 표시
        status_frame = tk.Frame(self.root, bg='#f5f5f5')
        status_frame.pack(side='bottom', fill='x', pady=(10, 5), padx=15)

        self.progress_bar = ttk.Progressbar(status_frame, mode='indeterminate', length=200)
        self.progress_bar.pack(side='left', padx=(0, 10))
        self.progress_bar.pack_forget()

        self.progress_label = tk.Label(status_frame, text="", bg='#f5f5f5',
                                      font=('맑은 고딕', 10, 'bold'), fg='#666',
                                      padx=10, pady=5)
        self.progress_label.pack(side='left', fill='x', expand=True)

    def create_license_section(self, parent):
        """라이선스 섹션"""
        card = tk.LabelFrame(parent, text="  🔑 라이선스  ", bg='white',
                           font=('맑은 고딕', 10, 'bold'), padx=15, pady=8)
        card.pack(fill='x', pady=(0, 10))

        input_frame = tk.Frame(card, bg='white')
        input_frame.pack(fill='x')

        tk.Label(input_frame, text="키:", bg='white',
                font=('맑은 고딕', 9)).pack(side='left', padx=(0, 5))

        self.license_entry = tk.Entry(input_frame, font=('맑은 고딕', 9), width=28)
        self.license_entry.pack(side='left', padx=(0, 5))

        tk.Button(input_frame, text="확인", command=self.verify_license,
                 bg='#4CAF50', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=8).pack(side='left', padx=(0, 10))

        self.usage_label = tk.Label(input_frame, text="", bg='white',
                                   font=('맑은 고딕', 9, 'bold'), fg='#888')
        self.usage_label.pack(side='left')

    def create_input_section(self, parent):
        """입력 섹션"""
        card = tk.LabelFrame(parent, text="  📝 콘텐츠 생성  ", bg='white',
                           font=('맑은 고딕', 10, 'bold'), padx=10, pady=10)
        card.pack(fill='both', expand=True)

        notebook = ttk.Notebook(card)
        notebook.pack(fill='both', expand=True)

        # 탭 1: URL 리라이팅 (기본)
        url_tab = tk.Frame(notebook, bg='white')
        notebook.add(url_tab, text="  URL 리라이팅  ")
        self.create_url_tab(url_tab)

        # 탭 2: 프롬프트 작성
        prompt_tab = tk.Frame(notebook, bg='white')
        notebook.add(prompt_tab, text="  프롬프트 작성  ")
        self.create_prompt_tab(prompt_tab)

        # 탭 3: 직접 작성
        direct_tab = tk.Frame(notebook, bg='white')
        notebook.add(direct_tab, text="  직접 작성  ")
        self.create_direct_input_tab(direct_tab)

    def create_direct_input_tab(self, parent):
        """직접 입력 탭 - AI 없이 원고 직접 등록"""
        main_frame = tk.Frame(parent, bg='white', padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)

        # 안내
        tk.Label(main_frame, text="💡 AI 없이 직접 원고를 입력하여 등록합니다",
                bg='#E8F5E9', fg='#2E7D32', font=('맑은 고딕', 9), padx=8, pady=4).pack(fill='x', pady=(0, 8))

        # 키워드 + 계정 그룹
        row1 = tk.Frame(main_frame, bg='white')
        row1.pack(fill='x', pady=(0, 8))

        tk.Label(row1, text="키워드:", bg='white', font=('맑은 고딕', 9, 'bold')).pack(side='left')
        self.direct_keyword_entry = tk.Entry(row1, font=('맑은 고딕', 9), width=20)
        self.direct_keyword_entry.pack(side='left', padx=(5, 15))

        tk.Label(row1, text="계정그룹:", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.direct_account_group_var = tk.StringVar(value='')
        self.direct_account_group_combo = ttk.Combobox(row1, textvariable=self.direct_account_group_var,
                                                       state='readonly', width=15, font=('맑은 고딕', 9))
        self.direct_account_group_combo['values'] = ['(선택안함)']
        self.direct_account_group_combo.set('(선택안함)')
        self.direct_account_group_combo.pack(side='left', padx=(5, 0))

        # 제목
        row2 = tk.Frame(main_frame, bg='white')
        row2.pack(fill='x', pady=(0, 8))

        tk.Label(row2, text="제목:", bg='white', font=('맑은 고딕', 9, 'bold')).pack(side='left')
        self.direct_title_entry = tk.Entry(row2, font=('맑은 고딕', 9), width=55)
        self.direct_title_entry.pack(side='left', padx=(5, 0), fill='x', expand=True)

        # 본문
        tk.Label(main_frame, text="본문:", bg='white', font=('맑은 고딕', 9, 'bold')).pack(anchor='w')

        self.direct_content_text = scrolledtext.ScrolledText(main_frame, height=8,
                                                              font=('맑은 고딕', 9), wrap='word')
        self.direct_content_text.pack(fill='both', expand=True, pady=(3, 8))

        # 이미지 마커 버튼들
        marker_frame = tk.Frame(main_frame, bg='white')
        marker_frame.pack(fill='x', pady=(0, 8))

        tk.Label(marker_frame, text="이미지 마커:", bg='white', font=('맑은 고딕', 9)).pack(side='left')

        tk.Label(marker_frame, text="단일", bg='white', font=('맑은 고딕', 8), fg='#666').pack(side='left', padx=(10, 3))
        self.direct_single_marker_var = tk.StringVar(value='1')
        tk.Spinbox(marker_frame, from_=1, to=20, width=3, textvariable=self.direct_single_marker_var,
                  font=('맑은 고딕', 9)).pack(side='left')
        tk.Button(marker_frame, text="추가", command=self.add_direct_single_marker,
                 bg='#9C27B0', fg='white', font=('맑은 고딕', 8),
                 relief='flat', padx=8).pack(side='left', padx=(3, 10))

        tk.Label(marker_frame, text="연속", bg='white', font=('맑은 고딕', 8), fg='#666').pack(side='left')
        self.direct_range_start_var = tk.StringVar(value='1')
        self.direct_range_end_var = tk.StringVar(value='5')
        tk.Spinbox(marker_frame, from_=1, to=20, width=3, textvariable=self.direct_range_start_var,
                  font=('맑은 고딕', 9)).pack(side='left', padx=(3, 0))
        tk.Label(marker_frame, text="~", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        tk.Spinbox(marker_frame, from_=1, to=20, width=3, textvariable=self.direct_range_end_var,
                  font=('맑은 고딕', 9)).pack(side='left')
        tk.Button(marker_frame, text="추가", command=self.add_direct_range_marker,
                 bg='#673AB7', fg='white', font=('맑은 고딕', 8),
                 relief='flat', padx=8).pack(side='left', padx=(3, 0))

        # 예약발행 옵션
        schedule_frame = tk.LabelFrame(main_frame, text=" 예약발행 ", bg='white',
                                       font=('맑은 고딕', 9), padx=8, pady=5)
        schedule_frame.pack(fill='x', pady=(0, 8))

        schedule_row = tk.Frame(schedule_frame, bg='white')
        schedule_row.pack(fill='x')

        self.direct_schedule_var = tk.BooleanVar(value=False)
        tk.Checkbutton(schedule_row, text="예약발행", variable=self.direct_schedule_var,
                      bg='white', font=('맑은 고딕', 9),
                      command=self.toggle_direct_schedule).pack(side='left')

        tk.Label(schedule_row, text="시간:", bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(10, 3))
        self.direct_date_var = tk.StringVar()
        self.direct_date_combo = ttk.Combobox(schedule_row, textvariable=self.direct_date_var,
                                               state='disabled', width=12, font=('맑은 고딕', 9))
        self.direct_date_combo.pack(side='left')

        self.direct_hour_var = tk.StringVar(value='09')
        self.direct_hour_combo = ttk.Combobox(schedule_row, textvariable=self.direct_hour_var,
                                               state='disabled', width=4, font=('맑은 고딕', 9))
        self.direct_hour_combo['values'] = [f'{i:02d}' for i in range(24)]
        self.direct_hour_combo.pack(side='left', padx=(3, 0))

        tk.Label(schedule_row, text=":", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.direct_minute_var = tk.StringVar(value='00')
        self.direct_minute_combo = ttk.Combobox(schedule_row, textvariable=self.direct_minute_var,
                                                 state='disabled', width=4, font=('맑은 고딕', 9))
        self.direct_minute_combo['values'] = [f'{i:02d}' for i in range(0, 60, 10)]
        self.direct_minute_combo.pack(side='left')

        # 직접 입력 탭 날짜 콤보박스 초기화
        self._init_direct_date_combo()

        # 버튼
        btn_frame = tk.Frame(main_frame, bg='white')
        btn_frame.pack(fill='x', pady=(5, 0))

        self.direct_register_btn = tk.Button(btn_frame, text="📥 등록",
                                             command=self.register_direct_content,
                                             bg='#4CAF50', fg='white', font=('맑은 고딕', 10, 'bold'),
                                             relief='flat', cursor='hand2', padx=15, pady=6)
        self.direct_register_btn.pack(side='left', padx=(0, 5))

        tk.Button(btn_frame, text="🗑️ 초기화", command=self.clear_direct_input,
                 bg='#FF9800', fg='white', font=('맑은 고딕', 10, 'bold'),
                 relief='flat', cursor='hand2', padx=15, pady=6).pack(side='left')

    def add_direct_single_marker(self):
        """직접 입력 탭 - 단일 이미지 마커 추가"""
        num = int(self.direct_single_marker_var.get())
        marker = f"{{img:{num}}}"
        self.direct_content_text.insert('insert', marker)

    def add_direct_range_marker(self):
        """직접 입력 탭 - 연속 이미지 마커 추가"""
        s = int(self.direct_range_start_var.get())
        e = int(self.direct_range_end_var.get())
        marker = f"{{img:{s}-{e}}}"
        self.direct_content_text.insert('insert', marker)

    def _init_direct_date_combo(self):
        """직접 입력 탭 날짜/시간 콤보박스 초기화"""
        dates = self._get_date_list()
        self.direct_date_combo['values'] = dates

        rounded_date, rounded_hour, rounded_min = self._get_rounded_time()

        if rounded_date not in dates:
            dates.insert(0, rounded_date)
            self.direct_date_combo['values'] = dates

        self.direct_date_combo.set(rounded_date)
        self.direct_hour_var.set(rounded_hour)
        self.direct_minute_var.set(rounded_min)

    def toggle_direct_schedule(self):
        """직접 입력 탭 예약발행 토글"""
        if self.direct_schedule_var.get():
            self.direct_date_combo.config(state='readonly')
            self.direct_hour_combo.config(state='readonly')
            self.direct_minute_combo.config(state='readonly')
        else:
            self.direct_date_combo.config(state='disabled')
            self.direct_hour_combo.config(state='disabled')
            self.direct_minute_combo.config(state='disabled')

    def get_direct_scheduled_time(self):
        """직접 입력 탭에서 예약발행 시간 가져오기"""
        if not self.direct_schedule_var.get():
            return '즉시발행'

        date = self.direct_date_var.get()
        hour = int(self.direct_hour_var.get())
        minute = int(self.direct_minute_var.get())

        return f"{date} {hour:02d}:{minute:02d}"

    def clear_direct_input(self):
        """직접 입력 폼 초기화"""
        self.direct_keyword_entry.delete(0, 'end')
        self.direct_title_entry.delete(0, 'end')
        self.direct_content_text.delete('1.0', 'end')
        self.direct_schedule_var.set(False)
        self.toggle_direct_schedule()
        self._init_direct_date_combo()
        self.show_info("입력 폼이 초기화되었습니다")

    def register_direct_content(self):
        """직접 입력 콘텐츠 등록"""
        if not self.current_license:
            self.show_error("먼저 라이선스를 확인하세요")
            return

        keyword = self.direct_keyword_entry.get().strip()
        if not keyword:
            self.show_error("키워드를 입력하세요")
            return

        title = self.direct_title_entry.get().strip()
        if not title:
            self.show_error("제목을 입력하세요")
            return

        content = self.direct_content_text.get('1.0', 'end').strip()
        if not content:
            self.show_error("본문을 입력하세요")
            return

        account_group = self.direct_account_group_var.get()
        if account_group == '(선택안함)':
            self.show_error("계정그룹을 선택하세요")
            return

        scheduled_time = self.get_direct_scheduled_time()

        try:
            self.show_working("콘텐츠 등록 중...")

            self.content_mgr.add_content(
                keyword=keyword,
                title=title,
                content=content,
                license_key=self.current_license['license_key'],
                account_group=account_group,
                scheduled_time=scheduled_time
            )

            self.show_success("콘텐츠가 등록되었습니다!")
            self.refresh_content_list()

            # 입력 폼 초기화 (키워드와 계정그룹 유지)
            self.direct_title_entry.delete(0, 'end')
            self.direct_content_text.delete('1.0', 'end')

        except Exception as e:
            self.show_error(f"등록 실패: {str(e)[:30]}")

    def create_url_tab(self, parent):
        """URL 리라이팅 탭 (다중 링크 지원)"""
        main_frame = tk.Frame(parent, bg='white', padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)

        # 키워드
        kw_frame = tk.Frame(main_frame, bg='white')
        kw_frame.pack(fill='x', pady=(0, 8))

        tk.Label(kw_frame, text="키워드:", bg='white',
                font=('맑은 고딕', 9, 'bold')).pack(side='left')
        self.rss_keyword_entry = tk.Entry(kw_frame, font=('맑은 고딕', 9), width=25)
        self.rss_keyword_entry.pack(side='left', padx=(5, 10))
        tk.Label(kw_frame, text="※ RSS 검색용", bg='white',
                font=('맑은 고딕', 8), fg='#888').pack(side='left')

        # 이미지폴더 선택
        img_folder_frame = tk.Frame(main_frame, bg='white')
        img_folder_frame.pack(fill='x', pady=(0, 8))

        tk.Label(img_folder_frame, text="이미지폴더", bg='white',
                font=('맑은 고딕', 9, 'bold')).pack(side='left')
        tk.Label(img_folder_frame, text="*", bg='white',
                font=('맑은 고딕', 9, 'bold'), fg='#f44336').pack(side='left')
        tk.Label(img_folder_frame, text=":", bg='white',
                font=('맑은 고딕', 9, 'bold')).pack(side='left')
        self.url_image_folder_var = tk.StringVar(value='자동생성')
        self.url_image_folder_combo = ttk.Combobox(img_folder_frame, textvariable=self.url_image_folder_var,
                                                    state='readonly', width=20, font=('맑은 고딕', 9))
        self.url_image_folder_combo['values'] = ['자동생성', '(로딩중...)']
        self.url_image_folder_combo.set('자동생성')
        self.url_image_folder_combo.pack(side='left', padx=(5, 5))

        tk.Button(img_folder_frame, text="새로고침", command=self.refresh_image_folders,
                 bg='#607D8B', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=8, pady=2).pack(side='left')

        tk.Label(img_folder_frame, text="※ Drive 이미지 폴더", bg='white',
                font=('맑은 고딕', 8), fg='#888').pack(side='left', padx=(10, 0))

        # RSS 검색 섹션
        rss_frame = tk.LabelFrame(main_frame, text=" RSS 검색 (선택) ", bg='white',
                                  font=('맑은 고딕', 9), padx=8, pady=5)
        rss_frame.pack(fill='x', pady=(0, 8))

        rss_row = tk.Frame(rss_frame, bg='white')
        rss_row.pack(fill='x')

        tk.Label(rss_row, text="블로그 URL:", bg='white',
                font=('맑은 고딕', 9)).pack(side='left')
        self.url_entry = tk.Entry(rss_row, font=('맑은 고딕', 9), width=35)
        self.url_entry.pack(side='left', padx=(5, 5))

        tk.Button(rss_row, text="🔍 검색", command=self.search_rss_links,
                 bg='#2196F3', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=10).pack(side='left')

        tk.Label(rss_frame, text="※ 키워드로 RSS 검색 후 링크 목록에 추가됩니다", bg='white',
                font=('맑은 고딕', 8), fg='#888').pack(anchor='w', pady=(3, 0))

        # 링크 목록 (통합 텍스트 영역)
        link_frame = tk.Frame(main_frame, bg='white')
        link_frame.pack(fill='x', pady=(0, 8))

        tk.Label(link_frame, text="링크 목록 (한 줄에 하나씩, 자유롭게 편집 가능):", bg='white',
                font=('맑은 고딕', 9)).pack(anchor='w')

        self.url_links_text = scrolledtext.ScrolledText(link_frame, height=4,
                                                        font=('맑은 고딕', 9),
                                                        wrap='none')
        self.url_links_text.pack(fill='x', pady=(3, 0))

        # 커스텀 프롬프트
        prompt_label_frame = tk.Frame(main_frame, bg='white')
        prompt_label_frame.pack(fill='x')
        tk.Label(prompt_label_frame, text="커스텀 프롬프트 (선택):", bg='white',
                font=('맑은 고딕', 9)).pack(side='left')
        tk.Button(prompt_label_frame, text="기본값", command=self.show_default_prompt_popup,
                 bg='#607D8B', fg='white', font=('맑은 고딕', 8), relief='flat',
                 padx=6, cursor='hand2').pack(side='left', padx=(5, 0))

        self.custom_prompt_url = scrolledtext.ScrolledText(main_frame, height=2,
                                                          font=('맑은 고딕', 9),
                                                          wrap='word')
        self.custom_prompt_url.pack(fill='x', pady=(3, 8))

        # 기존 호환용 (url_preview 제거, 새 로직에서 직접 처리)
        self.url_preview = None

        # 옵션
        option_frame = tk.LabelFrame(main_frame, text=" 옵션 ", bg='white',
                                    font=('맑은 고딕', 9), padx=8, pady=5)
        option_frame.pack(fill='x', pady=(0, 8))

        opt_row = tk.Frame(option_frame, bg='white')
        opt_row.pack(fill='x')

        tk.Label(opt_row, text="링크당 생성:", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.url_count_var = tk.StringVar(value='1')
        tk.Spinbox(opt_row, from_=1, to=10, width=3, textvariable=self.url_count_var,
                  font=('맑은 고딕', 9)).pack(side='left', padx=(3, 8))

        tk.Label(opt_row, text="AI:", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.ai_var_url = tk.StringVar(value='gpt')
        tk.Radiobutton(opt_row, text="GPT", variable=self.ai_var_url,
                      value='gpt', bg='white', font=('맑은 고딕', 8)).pack(side='left')
        tk.Radiobutton(opt_row, text="Gemini", variable=self.ai_var_url,
                      value='gemini', bg='white', font=('맑은 고딕', 8)).pack(side='left')

        opt_row2 = tk.Frame(option_frame, bg='white')
        opt_row2.pack(fill='x', pady=(5, 0))

        tk.Label(opt_row2, text="계정그룹:", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.url_account_group_var = tk.StringVar(value='')
        self.url_account_group_combo = ttk.Combobox(opt_row2, textvariable=self.url_account_group_var,
                                                    state='readonly', width=15, font=('맑은 고딕', 9))
        self.url_account_group_combo['values'] = ['(선택안함)']
        self.url_account_group_combo.set('(선택안함)')
        self.url_account_group_combo.pack(side='left', padx=(5, 0))

        # 예약발행 옵션
        schedule_frame = tk.LabelFrame(main_frame, text=" 예약발행 ", bg='white',
                                       font=('맑은 고딕', 9), padx=8, pady=5)
        schedule_frame.pack(fill='x', pady=(8, 8))

        schedule_row1 = tk.Frame(schedule_frame, bg='white')
        schedule_row1.pack(fill='x')

        self.url_schedule_var = tk.BooleanVar(value=False)
        tk.Checkbutton(schedule_row1, text="예약발행", variable=self.url_schedule_var,
                      bg='white', font=('맑은 고딕', 9),
                      command=self.toggle_url_schedule).pack(side='left')

        tk.Label(schedule_row1, text="시작:", bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(10, 3))
        self.url_date_var = tk.StringVar()
        self.url_date_combo = ttk.Combobox(schedule_row1, textvariable=self.url_date_var,
                                           state='disabled', width=12, font=('맑은 고딕', 9))
        self.url_date_combo.pack(side='left')

        self.url_hour_var = tk.StringVar(value='09')
        self.url_hour_combo = ttk.Combobox(schedule_row1, textvariable=self.url_hour_var,
                                           state='disabled', width=4, font=('맑은 고딕', 9))
        self.url_hour_combo['values'] = [f'{i:02d}' for i in range(24)]
        self.url_hour_combo.pack(side='left', padx=(3, 0))

        tk.Label(schedule_row1, text=":", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.url_minute_var = tk.StringVar(value='00')
        self.url_minute_combo = ttk.Combobox(schedule_row1, textvariable=self.url_minute_var,
                                             state='disabled', width=4, font=('맑은 고딕', 9))
        self.url_minute_combo['values'] = [f'{i:02d}' for i in range(0, 60, 10)]
        self.url_minute_combo.pack(side='left')

        # 간격 설정
        schedule_row2 = tk.Frame(schedule_frame, bg='white')
        schedule_row2.pack(fill='x', pady=(5, 0))

        tk.Label(schedule_row2, text="간격:", bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(85, 3))
        self.url_interval_hour_var = tk.StringVar(value='2')
        self.url_interval_hour_spin = tk.Spinbox(schedule_row2, from_=0, to=24, width=3,
                                                  textvariable=self.url_interval_hour_var,
                                                  font=('맑은 고딕', 9), state='disabled')
        self.url_interval_hour_spin.pack(side='left')
        tk.Label(schedule_row2, text="시간", bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(2, 5))

        self.url_interval_min_var = tk.StringVar(value='30')
        self.url_interval_min_spin = tk.Spinbox(schedule_row2, from_=0, to=50, width=3,
                                                 textvariable=self.url_interval_min_var,
                                                 font=('맑은 고딕', 9), state='disabled',
                                                 increment=10)
        self.url_interval_min_spin.pack(side='left')
        tk.Label(schedule_row2, text="분", bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(2, 0))

        # URL 탭 날짜/시간 콤보박스 초기화
        self._init_url_date_combo()

        # 버튼
        btn_frame = tk.Frame(main_frame, bg='white')
        btn_frame.pack(fill='x', pady=(5, 0))

        self.url_start_btn = tk.Button(btn_frame, text="🚀 생성 시작",
                                      command=self.start_url_generation,
                                      bg='#4CAF50', fg='white', font=('맑은 고딕', 10, 'bold'),
                                      relief='flat', cursor='hand2', padx=15, pady=6)
        self.url_start_btn.pack(side='left', padx=(0, 5))

        self.url_stop_btn = tk.Button(btn_frame, text="⏹ 멈춤",
                                     command=self.stop_generation,
                                     bg='#F44336', fg='white', font=('맑은 고딕', 10, 'bold'),
                                     relief='flat', cursor='hand2', padx=15, pady=6,
                                     state='disabled')
        self.url_stop_btn.pack(side='left')

    def create_prompt_tab(self, parent):
        """프롬프트 작성 탭 (스크롤 없이)"""
        main_frame = tk.Frame(parent, bg='white', padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)

        # 안내
        tk.Label(main_frame, text="💡 프롬프트로 AI가 새 글을 작성합니다",
                bg='#E3F2FD', fg='#1565C0', font=('맑은 고딕', 9), padx=8, pady=4).pack(fill='x', pady=(0, 8))

        # 프롬프트
        prompt_label_frame = tk.Frame(main_frame, bg='white')
        prompt_label_frame.pack(fill='x')
        tk.Label(prompt_label_frame, text="프롬프트 (필수):", bg='white',
                font=('맑은 고딕', 9, 'bold')).pack(side='left')
        tk.Button(prompt_label_frame, text="AI 지시사항", command=self.show_prompt_instruction_popup,
                 bg='#607D8B', fg='white', font=('맑은 고딕', 8), relief='flat',
                 padx=6, cursor='hand2').pack(side='left', padx=(5, 0))

        self.prompt_text = scrolledtext.ScrolledText(main_frame, height=4,
                                                    font=('맑은 고딕', 9), wrap='word')
        self.prompt_text.pack(fill='x', pady=(3, 8))

        # 키워드 + 계정 그룹
        kw_row = tk.Frame(main_frame, bg='white')
        kw_row.pack(fill='x', pady=(0, 8))

        tk.Label(kw_row, text="키워드:", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.prompt_keyword_entry = tk.Entry(kw_row, font=('맑은 고딕', 9), width=20)
        self.prompt_keyword_entry.pack(side='left', padx=(5, 15))

        tk.Label(kw_row, text="계정그룹:", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.prompt_account_group_var = tk.StringVar(value='')
        self.prompt_account_group_combo = ttk.Combobox(kw_row, textvariable=self.prompt_account_group_var,
                                                       state='readonly', width=15, font=('맑은 고딕', 9))
        self.prompt_account_group_combo['values'] = ['(선택안함)']
        self.prompt_account_group_combo.set('(선택안함)')
        self.prompt_account_group_combo.pack(side='left', padx=(5, 0))

        # 옵션
        option_frame = tk.LabelFrame(main_frame, text=" 옵션 ", bg='white',
                                    font=('맑은 고딕', 9), padx=8, pady=5)
        option_frame.pack(fill='x', pady=(0, 8))

        opt_row1 = tk.Frame(option_frame, bg='white')
        opt_row1.pack(fill='x', pady=(0, 3))

        tk.Label(opt_row1, text="생성:", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.prompt_count_var = tk.StringVar(value='1')
        tk.Spinbox(opt_row1, from_=1, to=50, width=4, textvariable=self.prompt_count_var,
                  font=('맑은 고딕', 9)).pack(side='left', padx=(3, 10))

        tk.Label(opt_row1, text="글자수:", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.char_limit_var = tk.StringVar(value='800')
        tk.Entry(opt_row1, textvariable=self.char_limit_var, width=5,
                font=('맑은 고딕', 9)).pack(side='left', padx=(3, 3))
        tk.Label(opt_row1, text="자", bg='white', font=('맑은 고딕', 9)).pack(side='left')

        opt_row2 = tk.Frame(option_frame, bg='white')
        opt_row2.pack(fill='x')

        tk.Label(opt_row2, text="AI:", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.ai_var_prompt = tk.StringVar(value='gpt')
        tk.Radiobutton(opt_row2, text="GPT", variable=self.ai_var_prompt,
                      value='gpt', bg='white', font=('맑은 고딕', 8)).pack(side='left')
        tk.Radiobutton(opt_row2, text="Gemini", variable=self.ai_var_prompt,
                      value='gemini', bg='white', font=('맑은 고딕', 8)).pack(side='left')

        # 이미지 마커 옵션
        img_frame = tk.LabelFrame(main_frame, text=" 이미지 마커 ", bg='white',
                                 font=('맑은 고딕', 9), padx=8, pady=5)
        img_frame.pack(fill='x', pady=(0, 8))

        img_row1 = tk.Frame(img_frame, bg='white')
        img_row1.pack(fill='x')

        self.auto_image_var = tk.BooleanVar(value=False)
        tk.Checkbutton(img_row1, text="이미지 마커", variable=self.auto_image_var,
                      bg='white', font=('맑은 고딕', 9),
                      command=self.toggle_image_options).pack(side='left')

        tk.Label(img_row1, text="개수:", bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(10, 3))
        self.image_count_var = tk.StringVar(value='5')
        self.img_count_spinbox = tk.Spinbox(img_row1, from_=1, to=20, width=3,
                                           textvariable=self.image_count_var,
                                           font=('맑은 고딕', 9), state='disabled')
        self.img_count_spinbox.pack(side='left')

        self.image_position_var = tk.StringVar(value='top')
        self.img_top_radio = tk.Radiobutton(img_row1, text="최상단 나열", variable=self.image_position_var,
                                           value='top', bg='white', font=('맑은 고딕', 9), state='disabled')
        self.img_top_radio.pack(side='left', padx=(10, 0))
        self.img_auto_radio = tk.Radiobutton(img_row1, text="적절히", variable=self.image_position_var,
                                            value='auto', bg='white', font=('맑은 고딕', 9), state='disabled')
        self.img_auto_radio.pack(side='left', padx=(5, 0))

        # 예약발행 옵션
        schedule_frame2 = tk.LabelFrame(main_frame, text=" 예약발행 ", bg='white',
                                        font=('맑은 고딕', 9), padx=8, pady=5)
        schedule_frame2.pack(fill='x', pady=(0, 8))

        schedule_row2_1 = tk.Frame(schedule_frame2, bg='white')
        schedule_row2_1.pack(fill='x')

        self.prompt_schedule_var = tk.BooleanVar(value=False)
        tk.Checkbutton(schedule_row2_1, text="예약발행", variable=self.prompt_schedule_var,
                      bg='white', font=('맑은 고딕', 9),
                      command=self.toggle_prompt_schedule).pack(side='left')

        tk.Label(schedule_row2_1, text="시작:", bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(10, 3))
        self.prompt_date_var = tk.StringVar()
        self.prompt_date_combo = ttk.Combobox(schedule_row2_1, textvariable=self.prompt_date_var,
                                              state='disabled', width=12, font=('맑은 고딕', 9))
        self.prompt_date_combo.pack(side='left')

        self.prompt_hour_var = tk.StringVar(value='09')
        self.prompt_hour_combo = ttk.Combobox(schedule_row2_1, textvariable=self.prompt_hour_var,
                                              state='disabled', width=4, font=('맑은 고딕', 9))
        self.prompt_hour_combo['values'] = [f'{i:02d}' for i in range(24)]
        self.prompt_hour_combo.pack(side='left', padx=(3, 0))

        tk.Label(schedule_row2_1, text=":", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.prompt_minute_var = tk.StringVar(value='00')
        self.prompt_minute_combo = ttk.Combobox(schedule_row2_1, textvariable=self.prompt_minute_var,
                                                state='disabled', width=4, font=('맑은 고딕', 9))
        self.prompt_minute_combo['values'] = [f'{i:02d}' for i in range(0, 60, 10)]
        self.prompt_minute_combo.pack(side='left')

        # 간격 설정
        schedule_row2_2 = tk.Frame(schedule_frame2, bg='white')
        schedule_row2_2.pack(fill='x', pady=(5, 0))

        tk.Label(schedule_row2_2, text="간격:", bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(85, 3))
        self.prompt_interval_hour_var = tk.StringVar(value='2')
        self.prompt_interval_hour_spin = tk.Spinbox(schedule_row2_2, from_=0, to=24, width=3,
                                                     textvariable=self.prompt_interval_hour_var,
                                                     font=('맑은 고딕', 9), state='disabled')
        self.prompt_interval_hour_spin.pack(side='left')
        tk.Label(schedule_row2_2, text="시간", bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(2, 5))

        self.prompt_interval_min_var = tk.StringVar(value='30')
        self.prompt_interval_min_spin = tk.Spinbox(schedule_row2_2, from_=0, to=50, width=3,
                                                    textvariable=self.prompt_interval_min_var,
                                                    font=('맑은 고딕', 9), state='disabled',
                                                    increment=10)
        self.prompt_interval_min_spin.pack(side='left')
        tk.Label(schedule_row2_2, text="분", bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(2, 0))

        # 프롬프트 탭 날짜/시간 콤보박스 초기화
        self._init_prompt_date_combo()

        # 버튼
        btn_frame = tk.Frame(main_frame, bg='white')
        btn_frame.pack(fill='x', pady=(5, 0))

        self.prompt_start_btn = tk.Button(btn_frame, text="🚀 생성 시작",
                                         command=self.start_prompt_generation,
                                         bg='#4CAF50', fg='white', font=('맑은 고딕', 10, 'bold'),
                                         relief='flat', cursor='hand2', padx=15, pady=6)
        self.prompt_start_btn.pack(side='left', padx=(0, 5))

        self.prompt_stop_btn = tk.Button(btn_frame, text="⏹ 멈춤",
                                        command=self.stop_generation,
                                        bg='#F44336', fg='white', font=('맑은 고딕', 10, 'bold'),
                                        relief='flat', cursor='hand2', padx=15, pady=6,
                                        state='disabled')
        self.prompt_stop_btn.pack(side='left')

    def toggle_image_options(self):
        """이미지 옵션 활성화/비활성화"""
        if self.auto_image_var.get():
            self.img_count_spinbox.config(state='normal')
            self.img_top_radio.config(state='normal')
            self.img_auto_radio.config(state='normal')
        else:
            self.img_count_spinbox.config(state='disabled')
            self.img_top_radio.config(state='disabled')
            self.img_auto_radio.config(state='disabled')

    def _get_date_list(self):
        """오늘부터 30일간의 날짜 리스트 생성"""
        dates = []
        today = datetime.now()
        for i in range(30):
            d = today + timedelta(days=i)
            dates.append(d.strftime('%Y-%m-%d'))
        return dates

    def _get_rounded_time(self):
        """
        현재 시간을 10분 단위로 올림 처리

        예: 16:23 -> 16:30, 23:55 -> 다음날 00:00

        Returns:
            tuple: (날짜 문자열, 시간 문자열, 분 문자열)
        """
        now = datetime.now()

        # 현재 분을 10분 단위로 올림
        current_min = now.minute
        if current_min % 10 == 0:
            # 이미 10분 단위면 그대로 (또는 10분 추가)
            rounded_min = current_min + 10
        else:
            # 10분 단위로 올림
            rounded_min = ((current_min // 10) + 1) * 10

        # 시간 조정
        extra_hours = rounded_min // 60
        rounded_min = rounded_min % 60

        rounded_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=extra_hours, minutes=rounded_min)

        return (
            rounded_time.strftime('%Y-%m-%d'),
            rounded_time.strftime('%H'),
            rounded_time.strftime('%M')
        )

    def _init_url_date_combo(self):
        """URL 탭 날짜/시간 콤보박스 초기화"""
        dates = self._get_date_list()
        self.url_date_combo['values'] = dates

        # 현재 시간 기준 10분 올림
        rounded_date, rounded_hour, rounded_min = self._get_rounded_time()

        # 날짜가 오늘이 아니면 (자정 넘김) 날짜 리스트에 추가
        if rounded_date not in dates:
            dates.insert(0, rounded_date)
            self.url_date_combo['values'] = dates

        self.url_date_combo.set(rounded_date)
        self.url_hour_var.set(rounded_hour)
        self.url_minute_var.set(rounded_min)

    def _init_prompt_date_combo(self):
        """프롬프트 탭 날짜/시간 콤보박스 초기화"""
        dates = self._get_date_list()
        self.prompt_date_combo['values'] = dates

        # 현재 시간 기준 10분 올림
        rounded_date, rounded_hour, rounded_min = self._get_rounded_time()

        # 날짜가 오늘이 아니면 (자정 넘김) 날짜 리스트에 추가
        if rounded_date not in dates:
            dates.insert(0, rounded_date)
            self.prompt_date_combo['values'] = dates

        self.prompt_date_combo.set(rounded_date)
        self.prompt_hour_var.set(rounded_hour)
        self.prompt_minute_var.set(rounded_min)

    def toggle_url_schedule(self):
        """URL 탭 예약발행 토글"""
        if self.url_schedule_var.get():
            self.url_date_combo.config(state='readonly')
            self.url_hour_combo.config(state='readonly')
            self.url_minute_combo.config(state='readonly')
            self.url_interval_hour_spin.config(state='normal')
            self.url_interval_min_spin.config(state='normal')
        else:
            self.url_date_combo.config(state='disabled')
            self.url_hour_combo.config(state='disabled')
            self.url_minute_combo.config(state='disabled')
            self.url_interval_hour_spin.config(state='disabled')
            self.url_interval_min_spin.config(state='disabled')

    def toggle_prompt_schedule(self):
        """프롬프트 탭 예약발행 토글"""
        if self.prompt_schedule_var.get():
            self.prompt_date_combo.config(state='readonly')
            self.prompt_hour_combo.config(state='readonly')
            self.prompt_minute_combo.config(state='readonly')
            self.prompt_interval_hour_spin.config(state='normal')
            self.prompt_interval_min_spin.config(state='normal')
        else:
            self.prompt_date_combo.config(state='disabled')
            self.prompt_hour_combo.config(state='disabled')
            self.prompt_minute_combo.config(state='disabled')
            self.prompt_interval_hour_spin.config(state='disabled')
            self.prompt_interval_min_spin.config(state='disabled')

    def get_url_scheduled_time(self, index=0):
        """
        URL 탭에서 예약발행 시간 가져오기

        Args:
            index: 콘텐츠 순번 (0부터 시작). 시작시간 + (간격 * index)

        Returns:
            str: '즉시발행' 또는 'YYYY-MM-DD HH:MM' 형식
        """
        if not self.url_schedule_var.get():
            return '즉시발행'

        date = self.url_date_var.get()
        hour = int(self.url_hour_var.get())
        minute = int(self.url_minute_var.get())

        # 시작 시간 생성
        start_time = datetime.strptime(f"{date} {hour:02d}:{minute:02d}", '%Y-%m-%d %H:%M')

        # 간격 계산
        interval_hours = int(self.url_interval_hour_var.get())
        interval_mins = int(self.url_interval_min_var.get())
        interval = timedelta(hours=interval_hours, minutes=interval_mins)

        # 인덱스에 따른 시간 계산
        scheduled = start_time + (interval * index)

        return scheduled.strftime('%Y-%m-%d %H:%M')

    def get_prompt_scheduled_time(self, index=0):
        """
        프롬프트 탭에서 예약발행 시간 가져오기

        Args:
            index: 콘텐츠 순번 (0부터 시작). 시작시간 + (간격 * index)

        Returns:
            str: '즉시발행' 또는 'YYYY-MM-DD HH:MM' 형식
        """
        if not self.prompt_schedule_var.get():
            return '즉시발행'

        date = self.prompt_date_var.get()
        hour = int(self.prompt_hour_var.get())
        minute = int(self.prompt_minute_var.get())

        # 시작 시간 생성
        start_time = datetime.strptime(f"{date} {hour:02d}:{minute:02d}", '%Y-%m-%d %H:%M')

        # 간격 계산
        interval_hours = int(self.prompt_interval_hour_var.get())
        interval_mins = int(self.prompt_interval_min_var.get())
        interval = timedelta(hours=interval_hours, minutes=interval_mins)

        # 인덱스에 따른 시간 계산
        scheduled = start_time + (interval * index)

        return scheduled.strftime('%Y-%m-%d %H:%M')

    def create_content_management_section(self, parent):
        """콘텐츠 관리 섹션"""
        self.mgmt_notebook = ttk.Notebook(parent)
        self.mgmt_notebook.pack(fill='both', expand=True)

        # 탭 1: 콘텐츠 목록
        list_tab = tk.Frame(self.mgmt_notebook, bg='white')
        self.mgmt_notebook.add(list_tab, text="  📋 콘텐츠 목록  ")
        self.create_content_list_tab(list_tab)

        # 탭 2: 원고 수정
        edit_tab = tk.Frame(self.mgmt_notebook, bg='white')
        self.mgmt_notebook.add(edit_tab, text="  ✏️ 원고 수정  ")
        self.create_edit_tab(edit_tab)

    def show_default_prompt_popup(self):
        """기본 프롬프트 팝업 표시"""
        popup = tk.Toplevel(self.root)
        popup.title("기본 리라이팅 프롬프트")
        popup.geometry("500x300")
        popup.resizable(True, True)
        popup.configure(bg='white')
        popup.transient(self.root)
        popup.grab_set()

        # 설명
        tk.Label(popup, text="프롬프트를 입력하지 않으면 아래 기본값이 사용됩니다.\n수정 후 '적용' 버튼을 누르면 입력창에 복사됩니다.",
                bg='white', font=('맑은 고딕', 9), fg='#666', justify='left').pack(anchor='w', padx=15, pady=(15, 10))

        # 프롬프트 텍스트
        prompt_text = scrolledtext.ScrolledText(popup, font=('맑은 고딕', 10), wrap='word', height=10)
        prompt_text.pack(fill='both', expand=True, padx=15, pady=(0, 10))
        prompt_text.insert('1.0', DEFAULT_REWRITE_PROMPT)

        # 버튼
        btn_frame = tk.Frame(popup, bg='white')
        btn_frame.pack(fill='x', padx=15, pady=(0, 15))

        def apply_prompt():
            text = prompt_text.get('1.0', 'end').strip()
            self.custom_prompt_url.delete('1.0', 'end')
            self.custom_prompt_url.insert('1.0', text)
            popup.destroy()

        tk.Button(btn_frame, text="적용", command=apply_prompt,
                 bg='#4CAF50', fg='white', font=('맑은 고딕', 10, 'bold'),
                 relief='flat', padx=20, cursor='hand2').pack(side='left')
        tk.Button(btn_frame, text="취소", command=popup.destroy,
                 bg='#666', fg='white', font=('맑은 고딕', 10),
                 relief='flat', padx=20, cursor='hand2').pack(side='left', padx=(10, 0))

    def show_prompt_instruction_popup(self):
        """프롬프트 작성 탭 AI 지시사항 팝업"""
        popup = tk.Toplevel(self.root)
        popup.title("AI 지시사항 설정")
        popup.geometry("550x450")
        popup.resizable(True, True)
        popup.configure(bg='white')
        popup.transient(self.root)
        popup.grab_set()

        # 설명
        tk.Label(popup, text="프롬프트 뒤에 자동으로 추가되는 AI 지시사항입니다.\n{char_limit}는 글자수 설정값으로 자동 치환됩니다.",
                bg='white', font=('맑은 고딕', 9), fg='#666', justify='left').pack(anchor='w', padx=15, pady=(15, 10))

        # 현재 지시사항 표시
        current_instruction = self.custom_prompt_instruction if self.custom_prompt_instruction else DEFAULT_PROMPT_INSTRUCTION

        instruction_text = scrolledtext.ScrolledText(popup, font=('맑은 고딕', 10), wrap='word', height=15)
        instruction_text.pack(fill='both', expand=True, padx=15, pady=(0, 10))
        instruction_text.insert('1.0', current_instruction)

        # 버튼
        btn_frame = tk.Frame(popup, bg='white')
        btn_frame.pack(fill='x', padx=15, pady=(0, 15))

        def apply_instruction():
            text = instruction_text.get('1.0', 'end').strip()
            self.custom_prompt_instruction = text if text else None
            popup.destroy()
            self.show_success("AI 지시사항이 적용되었습니다")

        def reset_to_default():
            instruction_text.delete('1.0', 'end')
            instruction_text.insert('1.0', DEFAULT_PROMPT_INSTRUCTION)

        tk.Button(btn_frame, text="적용", command=apply_instruction,
                 bg='#4CAF50', fg='white', font=('맑은 고딕', 10, 'bold'),
                 relief='flat', padx=20, cursor='hand2').pack(side='left')
        tk.Button(btn_frame, text="기본값 복원", command=reset_to_default,
                 bg='#FF9800', fg='white', font=('맑은 고딕', 10),
                 relief='flat', padx=15, cursor='hand2').pack(side='left', padx=(10, 0))
        tk.Button(btn_frame, text="취소", command=popup.destroy,
                 bg='#666', fg='white', font=('맑은 고딕', 10),
                 relief='flat', padx=20, cursor='hand2').pack(side='left', padx=(10, 0))

    def toggle_right_panel(self):
        """오른쪽 패널 접기/펼치기 (창 크기 조절)"""
        if self.right_panel_visible:
            # 접기 - 오른쪽 패널 숨기고 창 크기 줄이기
            self.right_frame.pack_forget()
            self.toggle_btn.config(text="콘텐츠 목록 ▶")
            self.root.geometry("600x900")
        else:
            # 펼치기 - 오른쪽 패널 보이고 창 크기 키우기
            self.right_frame.pack(side='right', fill='both', expand=True)
            self.toggle_btn.config(text="◀ 콘텐츠 목록")
            self.root.geometry("1400x900")

        self.right_panel_visible = not self.right_panel_visible

    def create_content_list_tab(self, parent):
        """콘텐츠 목록 탭"""
        filter_frame = tk.Frame(parent, bg='white')
        filter_frame.pack(fill='x', padx=10, pady=10)

        tk.Label(filter_frame, text="상태:", bg='white', font=('맑은 고딕', 9)).pack(side='left')

        self.status_filter = ttk.Combobox(filter_frame, values=['전체', '대기', '발행 중', '발행 완료'],
                                         state='readonly', width=10, font=('맑은 고딕', 9))
        self.status_filter.set('대기')  # 기본값: 대기
        self.status_filter.pack(side='left', padx=(5, 10))
        self.status_filter.bind('<<ComboboxSelected>>', lambda e: self.refresh_content_list())

        tk.Button(filter_frame, text="🔄 새로고침", command=self.refresh_content_list,
                 bg='#2196F3', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=10).pack(side='left')

        # 상태 토글 버튼 (draft ↔ ready)
        tk.Button(filter_frame, text="선택 토글", command=self.toggle_selected_status,
                 bg='#9C27B0', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=8).pack(side='left', padx=(5, 0))
        tk.Button(filter_frame, text="전체→대기", command=self.set_all_to_ready,
                 bg='#4CAF50', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=8).pack(side='left', padx=(5, 0))
        tk.Button(filter_frame, text="전체→초안", command=self.set_all_to_draft,
                 bg='#03A9F4', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=8).pack(side='left', padx=(5, 0))

        tk.Button(filter_frame, text="🗑️ 삭제", command=self.delete_content,
                 bg='#F44336', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=10).pack(side='right')

        tk.Button(filter_frame, text="✏️ 수정", command=self.open_edit_tab,
                 bg='#FFC107', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=10).pack(side='right', padx=(0, 5))

        # 상태 색상 범례
        legend_frame = tk.Frame(filter_frame, bg='white')
        legend_frame.pack(side='left', padx=(15, 0))

        tk.Label(legend_frame, text="●", fg='#03A9F4', bg='white', font=('맑은 고딕', 8)).pack(side='left')
        tk.Label(legend_frame, text="초안", bg='white', font=('맑은 고딕', 8), fg='#666').pack(side='left', padx=(0, 6))
        tk.Label(legend_frame, text="●", fg='#4CAF50', bg='white', font=('맑은 고딕', 8)).pack(side='left')
        tk.Label(legend_frame, text="대기", bg='white', font=('맑은 고딕', 8), fg='#666').pack(side='left', padx=(0, 6))
        tk.Label(legend_frame, text="●", fg='#FF9800', bg='white', font=('맑은 고딕', 8)).pack(side='left')
        tk.Label(legend_frame, text="발행중", bg='white', font=('맑은 고딕', 8), fg='#666').pack(side='left', padx=(0, 6))
        tk.Label(legend_frame, text="●", fg='#9E9E9E', bg='white', font=('맑은 고딕', 8)).pack(side='left')
        tk.Label(legend_frame, text="완료", bg='white', font=('맑은 고딕', 8), fg='#666').pack(side='left')

        # 리스트
        list_frame = tk.Frame(parent, bg='white')
        list_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # 스크롤바 프레임
        tree_container = tk.Frame(list_frame, bg='white')
        tree_container.pack(fill='both', expand=True)

        scrollbar_y = tk.Scrollbar(tree_container, orient='vertical')
        scrollbar_y.pack(side='right', fill='y')

        scrollbar_x = tk.Scrollbar(tree_container, orient='horizontal')
        scrollbar_x.pack(side='bottom', fill='x')

        # 컬럼: No, 그룹, 키워드, 제목, 상태, 예약시간, 생성시간, 보기, content_id(숨김)
        columns = ('No', '그룹', '키워드', '제목', '상태', '예약시간', '생성시간', '보기', 'content_id')
        self.content_tree = ttk.Treeview(tree_container, columns=columns, show='headings',
                                        yscrollcommand=scrollbar_y.set,
                                        xscrollcommand=scrollbar_x.set, height=20)

        self.content_tree.heading('No', text='No')
        self.content_tree.heading('그룹', text='그룹')
        self.content_tree.heading('키워드', text='키워드')
        self.content_tree.heading('제목', text='제목')
        self.content_tree.heading('상태', text='상태')
        self.content_tree.heading('예약시간', text='예약시간')
        self.content_tree.heading('생성시간', text='생성시간')
        self.content_tree.heading('보기', text='보기')
        self.content_tree.heading('content_id', text='')

        self.content_tree.column('No', width=35, minwidth=30, anchor='center')
        self.content_tree.column('그룹', width=50, minwidth=40)
        self.content_tree.column('키워드', width=80, minwidth=60)
        self.content_tree.column('제목', width=200, minwidth=120)
        self.content_tree.column('상태', width=45, minwidth=40, anchor='center')
        self.content_tree.column('예약시간', width=110, minwidth=90)
        self.content_tree.column('생성시간', width=110, minwidth=90)
        self.content_tree.column('보기', width=40, minwidth=40, anchor='center')
        self.content_tree.column('content_id', width=0, minwidth=0, stretch=False)

        # 상태별 색상 태그 정의
        self.content_tree.tag_configure('draft', foreground='#03A9F4')      # 하늘색
        self.content_tree.tag_configure('ready', foreground='#4CAF50')      # 녹색
        self.content_tree.tag_configure('publishing', foreground='#FF9800') # 주황
        self.content_tree.tag_configure('published', foreground='#9E9E9E')  # 회색
        self.content_tree.tag_configure('failed', foreground='#F44336')     # 빨강

        self.content_tree.pack(fill='both', expand=True)
        scrollbar_y.config(command=self.content_tree.yview)
        scrollbar_x.config(command=self.content_tree.xview)

        self.content_tree.bind('<Double-1>', lambda e: self.open_edit_tab())
        self.content_tree.bind('<ButtonRelease-1>', self.on_tree_click)

    def create_edit_tab(self, parent):
        """원고 수정 탭"""
        info_frame = tk.Frame(parent, bg='#FFF3CD')
        info_frame.pack(fill='x', padx=10, pady=10)

        self.edit_info_label = tk.Label(info_frame, text="수정할 원고를 목록에서 선택하세요",
                                       bg='#FFF3CD', fg='#856404',
                                       font=('맑은 고딕', 9), padx=10, pady=5)
        self.edit_info_label.pack(fill='x')

        form_frame = tk.Frame(parent, bg='white')
        form_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # 키워드 + 제목
        row1 = tk.Frame(form_frame, bg='white')
        row1.pack(fill='x', pady=(0, 8))

        tk.Label(row1, text="키워드:", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.edit_keyword_entry = tk.Entry(row1, font=('맑은 고딕', 9), width=15)
        self.edit_keyword_entry.pack(side='left', padx=(5, 15))

        tk.Label(row1, text="제목:", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.edit_title_entry = tk.Entry(row1, font=('맑은 고딕', 9), width=50)
        self.edit_title_entry.pack(side='left', padx=(5, 0), fill='x', expand=True)

        # 본문
        tk.Label(form_frame, text="본문:", bg='white', font=('맑은 고딕', 9)).pack(anchor='w')

        self.edit_content_text = scrolledtext.ScrolledText(form_frame, height=18,
                                                          font=('맑은 고딕', 9), wrap='word')
        self.edit_content_text.pack(fill='both', expand=True, pady=(3, 8))

        # 이미지 마커 버튼들 (인라인)
        marker_frame = tk.Frame(form_frame, bg='white')
        marker_frame.pack(fill='x', pady=(0, 8))

        tk.Label(marker_frame, text="이미지 마커:", bg='white', font=('맑은 고딕', 9)).pack(side='left')

        tk.Label(marker_frame, text="단일", bg='white', font=('맑은 고딕', 8), fg='#666').pack(side='left', padx=(10, 3))
        self.single_marker_var = tk.StringVar(value='1')
        tk.Spinbox(marker_frame, from_=1, to=20, width=3, textvariable=self.single_marker_var,
                  font=('맑은 고딕', 9)).pack(side='left')
        tk.Button(marker_frame, text="추가", command=self.add_single_marker,
                 bg='#9C27B0', fg='white', font=('맑은 고딕', 8),
                 relief='flat', padx=8).pack(side='left', padx=(3, 10))

        tk.Label(marker_frame, text="연속", bg='white', font=('맑은 고딕', 8), fg='#666').pack(side='left')
        self.range_start_var = tk.StringVar(value='1')
        self.range_end_var = tk.StringVar(value='5')
        tk.Spinbox(marker_frame, from_=1, to=20, width=3, textvariable=self.range_start_var,
                  font=('맑은 고딕', 9)).pack(side='left', padx=(3, 0))
        tk.Label(marker_frame, text="~", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        tk.Spinbox(marker_frame, from_=1, to=20, width=3, textvariable=self.range_end_var,
                  font=('맑은 고딕', 9)).pack(side='left')
        tk.Button(marker_frame, text="추가", command=self.add_range_marker,
                 bg='#673AB7', fg='white', font=('맑은 고딕', 8),
                 relief='flat', padx=8).pack(side='left', padx=(3, 10))

        tk.Button(marker_frame, text="🗑️ 마커 삭제", command=self.remove_all_markers,
                 bg='#FF9800', fg='white', font=('맑은 고딕', 8),
                 relief='flat', padx=8).pack(side='right')

        # 버튼
        btn_frame = tk.Frame(form_frame, bg='white')
        btn_frame.pack(fill='x')

        tk.Button(btn_frame, text="← 목록으로", command=self.back_to_list,
                 bg='#999', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=12).pack(side='left')

        tk.Button(btn_frame, text="💾 저장", command=self.save_edit,
                 bg='#4CAF50', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=15).pack(side='right')

    def add_single_marker(self):
        """단일 이미지 마커 추가"""
        num = int(self.single_marker_var.get())
        marker = f"{{img:{num}}}"
        self.edit_content_text.insert('insert', marker)

    def add_range_marker(self):
        """연속 이미지 마커 추가"""
        s = int(self.range_start_var.get())
        e = int(self.range_end_var.get())
        marker = f"{{img:{s}-{e}}}"
        self.edit_content_text.insert('insert', marker)

    def remove_all_markers(self):
        """모든 이미지 마커 제거"""
        content = self.edit_content_text.get('1.0', 'end')
        # {img:N} 또는 {img:N-M} 형식 검색
        if not re.search(r'\{img:\d+(?:-\d+)?\}', content):
            self.show_info("제거할 이미지 마커가 없습니다")
            return

        if messagebox.askyesno("확인", "모든 이미지 마커를 제거하시겠습니까?"):
            cleaned = re.sub(r'\{img:\d+(?:-\d+)?\}\s*', '', content)
            self.edit_content_text.delete('1.0', 'end')
            self.edit_content_text.insert('1.0', cleaned.strip())
            self.show_success("이미지 마커가 제거되었습니다")

    # ========== 기능 메서드 ==========

    def verify_license(self):
        """라이선스 확인"""
        license_key = self.license_entry.get().strip()

        if not license_key:
            messagebox.showerror("오류", "라이선스 키를 입력하세요")
            return

        validation = self.license_mgr.validate_license(license_key)

        if not validation['valid']:
            messagebox.showerror("오류", f"유효하지 않은 라이선스\n\n{validation['message']}")
            return

        if not validation['can_use_api']:
            messagebox.showwarning("경고", f"API 사용 한도 초과\n\n{validation['message']}")

        info = self.license_mgr.get_license_info(license_key)

        if not info:
            messagebox.showerror("오류", "라이선스 정보를 가져올 수 없습니다")
            return

        self.current_license = {
            'license_key': license_key,
            'user_email': info['user_email'],
            'tier': 'admin' if info['is_admin'] == 'TRUE' else 'user',
            'api_usage': validation['api_usage'],
            'api_limit': validation['api_limit'],
            'is_active': True
        }

        usage = validation['api_usage']
        limit = validation['api_limit']
        remaining = limit - usage

        color = '#4CAF50' if remaining > 20 else '#FF9800' if remaining > 5 else '#F44336'

        self.usage_label.config(
            text=f"✅ {remaining}/{limit}",
            fg=color
        )

        self.save_license(license_key)
        self.refresh_content_list()
        self.load_account_groups()

    def load_account_groups(self):
        """계정 그룹 목록 로딩 (시트에서 '계정_' 으로 시작하는 탭들)"""
        try:
            groups = self.content_mgr.get_account_groups()

            # 콤보박스 업데이트
            combo_values = ['(선택안함)'] + groups

            self.direct_account_group_combo['values'] = combo_values
            self.url_account_group_combo['values'] = combo_values
            self.prompt_account_group_combo['values'] = combo_values

        except Exception as e:
            print(f"계정그룹 로딩 실패: {e}")

    def load_saved_license(self):
        """저장된 라이선스 로드"""
        try:
            with open('license.json', 'r') as f:
                data = json.load(f)
                self.license_entry.insert(0, data.get('key', ''))
                if data.get('key'):
                    self.verify_license()
        except:
            pass

    def save_license(self, key):
        """라이선스 저장"""
        try:
            with open('license.json', 'w') as f:
                json.dump({'key': key}, f)
        except:
            pass

    def refresh_image_folders(self):
        """Drive 이미지 폴더 목록 새로고침"""
        if not self.image_mgr:
            # Drive 연결 실패해도 자동생성은 사용 가능
            self.url_image_folder_combo['values'] = ['자동생성']
            self.url_image_folder_combo.set('자동생성')
            return

        def load_folders():
            try:
                folders = self.image_mgr.get_all_keyword_folders()
                self.image_folders = folders

                def update_combo():
                    # "자동생성"을 맨 앞에 추가
                    all_options = ['자동생성'] + (folders if folders else [])
                    self.url_image_folder_combo['values'] = all_options
                    self.url_image_folder_combo.set('자동생성')  # 기본값

                self.root.after(0, update_combo)

            except Exception as e:
                def show_error():
                    # 로딩 실패해도 자동생성은 사용 가능
                    self.url_image_folder_combo['values'] = ['자동생성']
                    self.url_image_folder_combo.set('자동생성')
                    print(f"이미지 폴더 로딩 실패: {e}")

                self.root.after(0, show_error)

        threading.Thread(target=load_folders, daemon=True).start()

    def search_rss_links(self):
        """RSS에서 키워드로 다중 링크 검색"""
        url = self.url_entry.get().strip()
        keyword = self.rss_keyword_entry.get().strip()

        if not url:
            self.show_error("블로그 URL을 입력하세요")
            return

        if not keyword:
            self.show_error("키워드를 입력하세요")
            return

        self.show_working(f"RSS에서 '{keyword}' 검색 중...")

        def search_thread():
            try:
                blog_id = self.crawler.get_blog_id_from_url(url)
                if not blog_id:
                    raise Exception("유효한 네이버 블로그 URL이 아닙니다")

                posts = self.crawler.find_posts_by_keyword(blog_id, keyword)
                if not posts:
                    raise Exception(f"'{keyword}'가 제목에 포함된 글을 찾을 수 없습니다")

                # 링크 목록에 추가
                def add_links():
                    current = self.url_links_text.get('1.0', 'end').strip()
                    new_links = '\n'.join([post['link'] for post in posts])
                    if current:
                        self.url_links_text.insert('end', '\n' + new_links)
                    else:
                        self.url_links_text.insert('1.0', new_links)
                    self.show_success(f"{len(posts)}개 링크 추가됨")

                self.root.after(0, add_links)

            except Exception as e:
                self.root.after(0, lambda: self.show_error(f"검색 실패: {str(e)[:50]}"))

        threading.Thread(target=search_thread, daemon=True).start()

    def get_ai_instruction_suffix(self, char_limit='800'):
        """AI 지시사항 접미사"""
        # 커스텀 지시사항이 있으면 사용, 없으면 기본값
        template = self.custom_prompt_instruction if self.custom_prompt_instruction else DEFAULT_PROMPT_INSTRUCTION
        return "\n\n" + template.format(char_limit=char_limit)

    def start_url_generation(self):
        """URL 리라이팅 생성 시작 (다중 링크 지원)"""
        if not self.current_license:
            self.show_error("먼저 라이선스를 확인하세요")
            return

        # 키워드 (선택)
        keyword = self.rss_keyword_entry.get().strip()

        # 이미지폴더 체크 (필수)
        image_folder = self.url_image_folder_var.get()
        if not image_folder or image_folder in ['(로딩중...)', '(폴더 없음)', '(Drive 연결 실패)', '(로딩 실패)']:
            self.show_error("이미지폴더를 선택하세요")
            return

        # 링크 목록 파싱
        links_text = self.url_links_text.get('1.0', 'end').strip()
        if not links_text:
            self.show_error("링크를 입력하세요")
            return

        links = [line.strip() for line in links_text.split('\n') if line.strip()]
        if not links:
            self.show_error("유효한 링크가 없습니다")
            return

        try:
            per_link_count = int(self.url_count_var.get())
            if per_link_count < 1:
                raise ValueError()
        except ValueError:
            self.show_error("유효한 링크당 생성 개수를 입력하세요")
            return

        total_count = len(links) * per_link_count
        remaining = self.current_license['api_limit'] - self.current_license['api_usage']
        if total_count > remaining:
            self.show_error(f"남은 사용량({remaining}개)보다 많이 생성할 수 없습니다 (필요: {total_count}개)")
            return

        custom_prompt = self.custom_prompt_url.get('1.0', 'end').strip()
        ai_type = self.ai_var_url.get()
        account_group = self.url_account_group_var.get()
        if account_group == '(선택안함)':
            self.show_error("계정그룹을 선택하세요")
            return

        self.generating = True
        self.stop_requested = False
        self.url_start_btn.config(state='disabled', bg='#999')
        self.url_stop_btn.config(state='normal', bg='#F44336')

        if ai_type == 'gemini':
            ai_name = "Gemini 2.5 Flash"
        elif ai_type == 'gpt':
            ai_name = "GPT-4o mini"
        else:
            ai_name = "Claude 3.5 Sonnet"

        def generate_thread():
            success_count = 0
            fail_count = 0
            content_index = 0  # 전체 콘텐츠 인덱스 (예약시간 계산용)

            for link_idx, link in enumerate(links):
                if self.stop_requested:
                    break

                # 1. 링크에서 글 가져오기
                self.root.after(0, lambda idx=link_idx: self.show_working(
                    f"[링크 {idx+1}/{len(links)}] 글 가져오는 중..."
                ))

                try:
                    result = self.crawler.parse_blog_post(link)
                    original = f"[제목] {result['title']}\n\n{result['content_with_markers']}"
                except Exception as e:
                    fail_count += per_link_count
                    print(f"❌ 링크 가져오기 실패 ({link}): {e}")
                    continue

                # 2. 링크당 per_link_count개 생성
                for i in range(per_link_count):
                    if self.stop_requested:
                        break

                    # 각 콘텐츠별 예약 시간 계산 (전체 인덱스 기반)
                    scheduled_time = self.get_url_scheduled_time(index=content_index)

                    self.root.after(0, lambda lidx=link_idx, idx=i, sc=success_count, st=scheduled_time: self.show_working(
                        f"[링크 {lidx+1}/{len(links)}] [{idx+1}/{per_link_count}] {ai_name} 리라이팅 중... (성공: {sc}개)" +
                        (f" 예약: {st}" if st != '즉시발행' else "")
                    ))

                    try:
                        if ai_type == 'gpt':
                            generator = GPTGenerator()
                        else:
                            generator = GeminiGenerator()

                        if custom_prompt:
                            full_prompt = f"""{custom_prompt}
{{img:숫자}}가 적힌 부분은 그대로 유지해야해.
(#{i+1}번째 글 - 이전과 다른 관점으로)

[중요 지시사항]
1. 키워드 보호: '{keyword}'는 절대 번역, 음역, 괄호 추가 금지. 원문 철자 그대로 사용.
   - 잘못된 예: jefferies → 제프리스, jefferies(제프리스), Jefferies
   - 올바른 예: jefferies → jefferies (대소문자, 철자 동일하게 유지)
2. 제목 수정: 원본 제목의 핵심 구조와 키워드는 유지하고, 일부 조사나 부가 단어만 변경.
3. 서식 금지: 제목이나 본문에 절대로 **, ##, ###, # 같은 마크다운 서식 사용 금지.
4. 본문은 읽기 좋게 자연스럽게 작성. 문단 구분이나 표 형태 활용."""
                        else:
                            full_prompt = f"""글을 제공할건데, 글의 문단 및 구조는 비교하기 쉽게 그대로 제공해주고, 글의 말투 어미를 동일하게 바꾸는데, 조금 길게 바꿔주고, 조사도 중간중간 많이 바꿔줘. {{img:숫자}}가 적힌 부분은 그대로 유지해야해.
(#{i+1}번째 글)

[중요 지시사항]
1. 키워드 보호: '{keyword}'는 절대 번역, 음역, 괄호 추가 금지. 원문 철자 그대로 사용.
   - 잘못된 예: jefferies → 제프리스, jefferies(제프리스), Jefferies
   - 올바른 예: jefferies → jefferies (대소문자, 철자 동일하게 유지)
2. 제목 수정: 원본 제목의 핵심 구조와 키워드는 유지하고, 일부 조사나 부가 단어만 변경.
3. 서식 금지: 제목이나 본문에 절대로 **, ##, ###, # 같은 마크다운 서식 사용 금지.
4. 본문은 읽기 좋게 자연스럽게 작성. 문단 구분이나 표 형태 활용."""

                        gen_result = generator.generate_with_custom_prompt(
                            user_prompt=full_prompt,
                            original_text=original
                        )

                        self.content_mgr.add_content(
                            keyword=image_folder,  # 이미지폴더를 keyword로 저장 (발행봇 호환)
                            title=gen_result['title'],
                            content=gen_result['content'],
                            license_key=self.current_license['license_key'],
                            account_group=account_group,
                            scheduled_time=scheduled_time
                        )

                        self.license_mgr.increment_api_usage(self.current_license['license_key'])
                        success_count += 1
                        content_index += 1

                        self.root.after(0, self.refresh_content_list)

                    except Exception as e:
                        fail_count += 1
                        content_index += 1
                        print(f"❌ 생성 실패 (링크 {link_idx+1}, #{i+1}): {e}")

            self.root.after(0, lambda: self._generation_complete(success_count, fail_count, 'url'))

        threading.Thread(target=generate_thread, daemon=True).start()

    def start_prompt_generation(self):
        """프롬프트 기반 생성 시작"""
        if not self.current_license:
            self.show_error("먼저 라이선스를 확인하세요")
            return

        prompt = self.prompt_text.get('1.0', 'end').strip()
        if not prompt:
            self.show_error("프롬프트를 입력하세요")
            return

        keyword = self.prompt_keyword_entry.get().strip()
        if not keyword:
            self.show_error("키워드를 입력하세요")
            return

        try:
            count = int(self.prompt_count_var.get())
            if count < 1:
                raise ValueError()
        except ValueError:
            self.show_error("유효한 생성 개수를 입력하세요")
            return

        remaining = self.current_license['api_limit'] - self.current_license['api_usage']
        if count > remaining:
            self.show_error(f"남은 사용량({remaining}개)보다 많이 생성할 수 없습니다")
            return

        char_limit = self.char_limit_var.get().strip() or '800'
        ai_type = self.ai_var_prompt.get()

        auto_image = self.auto_image_var.get()
        image_count = int(self.image_count_var.get()) if auto_image else 0
        image_position = self.image_position_var.get() if auto_image else ""  # 'top' or 'auto'
        account_group = self.prompt_account_group_var.get()
        if account_group == '(선택안함)':
            self.show_error("계정그룹을 선택하세요")
            return

        self.generating = True
        self.stop_requested = False
        self.prompt_start_btn.config(state='disabled', bg='#999')
        self.prompt_stop_btn.config(state='normal', bg='#F44336')

        if ai_type == 'gemini':
            ai_name = "Gemini 2.5 Flash"
        elif ai_type == 'gpt':
            ai_name = "GPT-4o mini"
        else:
            ai_name = "Claude 3.5 Sonnet"

        def generate_thread():
            success_count = 0
            fail_count = 0

            for i in range(count):
                if self.stop_requested:
                    self.root.after(0, lambda sc=success_count, fc=fail_count: self.show_info(
                        f"중지됨 - 성공: {sc}개, 실패: {fc}개"
                    ))
                    break

                # 각 콘텐츠별 예약 시간 계산 (인덱스 기반)
                scheduled_time = self.get_prompt_scheduled_time(index=i)

                self.root.after(0, lambda idx=i, sc=success_count, st=scheduled_time: self.show_working(
                    f"[{idx+1}/{count}] {ai_name} 글 생성 중... (성공: {sc}개)" + (f" 예약: {st}" if st != '즉시발행' else "")
                ))

                try:
                    if ai_type == 'gpt':
                        generator = GPTGenerator()
                    else:
                        generator = GeminiGenerator()

                    image_instruction = ""
                    if auto_image and image_position == 'auto':
                        # 적절히: AI에게 위치 결정 맡김
                        image_instruction = f"\n\n본문에 어울리게 이미지 위치를 {{img:1}}, {{img:2}} 형식으로 최대 {image_count}개로 넣어줘."

                    full_prompt = f"{prompt}\n\n(#{i+1}번째 글 - 이전과 다른 관점, 다른 구성으로){self.get_ai_instruction_suffix(char_limit)}{image_instruction}"

                    result = generator.generate_with_custom_prompt(
                        user_prompt=full_prompt,
                        original_text=None
                    )

                    # 최상단 나열: 본문 맨 앞에 이미지 마커 삽입
                    content = result['content']
                    if auto_image and image_position == 'top':
                        content = f"{{img:1-{image_count}}}\n\n{content}"

                    self.content_mgr.add_content(
                        keyword=keyword,
                        title=result['title'],
                        content=content,
                        license_key=self.current_license['license_key'],
                        account_group=account_group,
                        scheduled_time=scheduled_time
                    )

                    self.license_mgr.increment_api_usage(self.current_license['license_key'])
                    success_count += 1

                    self.root.after(0, self.refresh_content_list)

                except Exception as e:
                    fail_count += 1
                    print(f"❌ 생성 실패 #{i+1}: {e}")

            self.root.after(0, lambda: self._generation_complete(success_count, fail_count, 'prompt'))

        threading.Thread(target=generate_thread, daemon=True).start()

    def _generation_complete(self, success_count, fail_count, mode):
        """생성 완료 처리"""
        self.generating = False
        self.stop_requested = False

        if mode == 'url':
            self.url_start_btn.config(state='normal', bg='#4CAF50')
            self.url_stop_btn.config(state='disabled', bg='#999')
        else:
            self.prompt_start_btn.config(state='normal', bg='#4CAF50')
            self.prompt_stop_btn.config(state='disabled', bg='#999')

        if fail_count == 0:
            self.show_success(f"생성 완료! {success_count}개 등록됨")
        else:
            self.show_info(f"생성 완료 - 성공: {success_count}, 실패: {fail_count}")

        self.verify_license()

    def stop_generation(self):
        """생성 중지"""
        if self.generating:
            self.stop_requested = True
            self.url_stop_btn.config(state='disabled')
            self.prompt_stop_btn.config(state='disabled')
            self.show_info("중지 요청 중...")

    def open_edit_tab(self):
        """수정 탭 열기"""
        selected = self.content_tree.selection()
        if not selected:
            self.show_error("수정할 항목을 선택하세요")
            return

        if not self.current_license:
            self.show_error("먼저 라이선스를 확인하세요")
            return

        item = self.content_tree.item(selected[0])
        content_id = item['values'][7] if item['values'] and len(item['values']) > 7 else None

        if not content_id:
            self.show_error("콘텐츠 ID를 찾을 수 없습니다")
            return

        content_data = self.content_mgr.get_content_by_id(
            content_id,
            license_key=self.current_license['license_key']
        )

        if not content_data:
            self.show_error("콘텐츠를 찾을 수 없습니다")
            return

        self.edit_keyword_entry.delete(0, 'end')
        self.edit_keyword_entry.insert(0, content_data['keyword'])

        self.edit_title_entry.delete(0, 'end')
        self.edit_title_entry.insert(0, content_data['title'])

        self.edit_content_text.delete('1.0', 'end')
        self.edit_content_text.insert('1.0', content_data['content'])

        self.editing_content_id = content_id

        self.edit_info_label.config(
            text=f"수정 중: {content_id} | 키워드: {content_data['keyword']}",
            bg='#D4EDDA', fg='#155724'
        )

        self.mgmt_notebook.select(1)

    def back_to_list(self):
        """목록 탭으로 돌아가기"""
        self.mgmt_notebook.select(0)

    def save_edit(self):
        """편집 내용 저장"""
        if not self.editing_content_id:
            self.show_error("편집 중인 콘텐츠가 없습니다")
            return

        keyword = self.edit_keyword_entry.get().strip()
        title = self.edit_title_entry.get().strip()
        content = self.edit_content_text.get('1.0', 'end').strip()

        if not keyword or not title or not content:
            self.show_error("모든 필드를 입력하세요")
            return

        is_admin = self.current_license.get('tier', '') == 'admin'

        try:
            success = self.content_mgr.update_content(
                content_id=self.editing_content_id,
                keyword=keyword,
                title=title,
                content=content,
                license_key=self.current_license['license_key'],
                is_admin=is_admin
            )

            if success:
                self.show_success("콘텐츠가 수정되었습니다")
                self.refresh_content_list()
                self.back_to_list()
            else:
                self.show_error("수정 권한이 없거나 오류 발생")

        except Exception as e:
            self.show_error(f"수정 실패: {str(e)[:30]}")

    def refresh_content_list(self):
        """콘텐츠 목록 새로고침"""
        if not self.current_license:
            return

        self.content_tree.delete(*self.content_tree.get_children())

        try:
            is_admin = self.current_license.get('tier', '') == 'admin'
            license_key = self.current_license['license_key']

            contents = self.content_mgr.get_all_contents(
                license_key=license_key,
                is_admin=is_admin
            )

            status_filter = self.status_filter.get()

            # 생성시간 기준 오름차순 정렬 (오래된 것 위, 최신 아래)
            contents_sorted = sorted(contents, key=lambda x: x.get('created_time', ''))

            row_num = 0
            for content in contents_sorted:
                status = content['status']

                # 필터 적용
                if status_filter == '대기':
                    # 대기: draft + ready 둘 다 표시
                    if status not in ('draft', 'ready'):
                        continue
                elif status_filter == '발행 중':
                    if status != 'publishing':
                        continue
                elif status_filter == '발행 완료':
                    if status != 'published':
                        continue
                # '전체'는 필터 없음

                row_num += 1

                # 예약시간 표시
                scheduled = content.get('scheduled_time', '즉시발행')

                # 생성시간 표시
                created_time = content.get('created_time', '')
                if len(created_time) > 16:
                    created_time = created_time[:16]

                # 발행글 링크 버튼 (published 상태에서만 '보기' 표시)
                view_btn = '보기' if status == 'published' and content.get('published_url') else ''

                # 상태 표시 텍스트
                status_text = {'draft': '초안', 'ready': '대기', 'publishing': '발행중', 'published': '완료', 'failed': '실패'}.get(status, status)

                self.content_tree.insert('', 'end', values=(
                    row_num,
                    content.get('account_group', ''),
                    content['keyword'],
                    content['title'][:35] + '...' if len(content['title']) > 35 else content['title'],
                    status_text,
                    scheduled,
                    created_time,
                    view_btn,
                    content['content_id']  # 숨김 컬럼
                ), tags=(status,))

        except Exception as e:
            print(f"❌ 콘텐츠 목록 새로고침 실패: {e}")

    def on_tree_click(self, event):
        """트리뷰 클릭 이벤트 - 발행글 보기 버튼 처리"""
        region = self.content_tree.identify_region(event.x, event.y)
        if region != 'cell':
            return

        column = self.content_tree.identify_column(event.x)
        item = self.content_tree.identify_row(event.y)

        if not item:
            return

        # 보기 컬럼 클릭 (#8 = 8번째 컬럼)
        if column == '#8':
            values = self.content_tree.item(item, 'values')
            if values and values[7] == '보기':
                content_id = values[8]  # 숨김 컬럼에서 ID 가져오기
                self._open_published_url(content_id)

    def _open_published_url(self, content_id):
        """발행된 글 URL 열기"""
        if not self.current_license:
            return

        content_data = self.content_mgr.get_content_by_id(
            content_id,
            license_key=self.current_license['license_key']
        )

        if content_data and content_data.get('published_url'):
            import webbrowser
            webbrowser.open(content_data['published_url'])
        else:
            self.show_info("발행 URL이 없습니다")

    def delete_content(self):
        """콘텐츠 삭제"""
        selected = self.content_tree.selection()
        if not selected:
            self.show_error("삭제할 항목을 선택하세요")
            return

        if not self.current_license:
            self.show_error("먼저 라이선스를 확인하세요")
            return

        if not messagebox.askyesno("확인", "정말 삭제하시겠습니까?\n\n삭제된 콘텐츠는 복구할 수 없습니다."):
            return

        item = self.content_tree.item(selected[0])
        content_id = item['values'][8] if item['values'] and len(item['values']) > 8 else None

        if not content_id:
            self.show_error("콘텐츠 ID를 찾을 수 없습니다")
            return

        is_admin = self.current_license.get('tier', '') == 'admin'

        try:
            success = self.content_mgr.delete_content(
                content_id=content_id,
                license_key=self.current_license['license_key'],
                is_admin=is_admin
            )

            if success:
                self.show_success("콘텐츠가 삭제되었습니다")
                self.refresh_content_list()
            else:
                self.show_error("삭제 권한이 없거나 오류 발생")

        except Exception as e:
            self.show_error(f"삭제 실패: {str(e)[:30]}")

    def toggle_selected_status(self):
        """선택된 항목의 상태 토글 (draft ↔ ready)"""
        selected = self.content_tree.selection()
        if not selected:
            self.show_error("토글할 항목을 선택하세요")
            return

        if not self.current_license:
            return

        is_admin = self.current_license.get('tier', '') == 'admin'

        for item_id in selected:
            item = self.content_tree.item(item_id)
            values = item['values']
            if not values or len(values) < 9:
                continue

            content_id = values[8]  # content_id
            current_status_text = values[4]  # 상태 텍스트 (초안/대기)

            # draft ↔ ready 토글
            if current_status_text == '초안':
                new_status = 'ready'
            elif current_status_text == '대기':
                new_status = 'draft'
            else:
                continue  # 다른 상태는 토글 안함

            try:
                self.content_mgr.update_content_status(
                    content_id=content_id,
                    status=new_status,
                    license_key=self.current_license['license_key']
                )
            except:
                pass

        self.refresh_content_list()

    def set_all_to_ready(self):
        """현재 보이는 draft 항목 전체를 ready로 변경"""
        if not self.current_license:
            return

        is_admin = self.current_license.get('tier', '') == 'admin'
        count = 0

        for item_id in self.content_tree.get_children():
            item = self.content_tree.item(item_id)
            values = item['values']
            if not values or len(values) < 9:
                continue

            content_id = values[8]
            current_status_text = values[4]

            if current_status_text == '초안':
                try:
                    self.content_mgr.update_content_status(
                        content_id=content_id,
                        status='ready',
                        license_key=self.current_license['license_key']
                    )
                    count += 1
                except:
                    pass

        self.refresh_content_list()
        if count > 0:
            self.show_success(f"{count}개 → 대기 상태로 변경")

    def set_all_to_draft(self):
        """현재 보이는 ready 항목 전체를 draft로 변경"""
        if not self.current_license:
            return

        count = 0

        for item_id in self.content_tree.get_children():
            item = self.content_tree.item(item_id)
            values = item['values']
            if not values or len(values) < 9:
                continue

            content_id = values[8]
            current_status_text = values[4]

            if current_status_text == '대기':
                try:
                    self.content_mgr.update_content_status(
                        content_id=content_id,
                        status='draft',
                        license_key=self.current_license['license_key']
                    )
                    count += 1
                except:
                    pass

        self.refresh_content_list()
        if count > 0:
            self.show_success(f"{count}개 → 초안 상태로 변경")


def main():
    """메인 함수"""
    root = tk.Tk()
    app = ContentCreatorProV3(root)
    root.mainloop()


if __name__ == "__main__":
    main()
