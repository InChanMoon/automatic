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
from datetime import datetime

from src.sheets.license_manager import LicenseManager
from src.sheets.content_manager_v2 import ContentManagerV2
from src.content.multi_ai_generator import MultiAIGenerator
from src.crawler.naver_blog_crawler import NaverBlogCrawler
from src.utils.naver_html_generator import NaverHTMLGenerator


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

        # 변수
        self.generating = False
        self.stop_requested = False
        self.current_license = None
        self.editing_content_id = None

        # GUI 구성
        self.create_widgets()

        # 라이선스 자동 로드
        self.load_saved_license()

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
        left_frame = tk.Frame(main_container, bg='#f5f5f5', width=580)
        left_frame.pack(side='left', fill='both', padx=(0, 10))
        left_frame.pack_propagate(False)

        # 오른쪽: 콘텐츠 리스트 + 수정
        right_frame = tk.Frame(main_container, bg='#f5f5f5')
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))

        # === 왼쪽 영역 ===
        self.create_license_section(left_frame)
        self.create_input_section(left_frame)

        # === 오른쪽 영역 ===
        self.create_content_management_section(right_frame)

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

        # 탭 1: URL 리라이팅
        url_tab = tk.Frame(notebook, bg='white')
        notebook.add(url_tab, text="  URL 리라이팅  ")
        self.create_url_tab(url_tab)

        # 탭 2: 프롬프트 작성
        prompt_tab = tk.Frame(notebook, bg='white')
        notebook.add(prompt_tab, text="  프롬프트 작성  ")
        self.create_prompt_tab(prompt_tab)

    def create_url_tab(self, parent):
        """URL 리라이팅 탭 (스크롤 없이)"""
        main_frame = tk.Frame(parent, bg='white', padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)

        # URL 입력
        tk.Label(main_frame, text="블로그 URL:", bg='white',
                font=('맑은 고딕', 9)).pack(anchor='w')

        url_row = tk.Frame(main_frame, bg='white')
        url_row.pack(fill='x', pady=(3, 8))

        self.url_entry = tk.Entry(url_row, font=('맑은 고딕', 9), width=45)
        self.url_entry.pack(side='left', padx=(0, 5))

        tk.Button(url_row, text="가져오기", command=self.fetch_from_url,
                 bg='#2196F3', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=10).pack(side='left')

        # RSS 키워드
        rss_row = tk.Frame(main_frame, bg='white')
        rss_row.pack(fill='x', pady=(0, 8))

        tk.Label(rss_row, text="RSS 키워드:", bg='white',
                font=('맑은 고딕', 8), fg='#666').pack(side='left', padx=(0, 5))

        self.rss_keyword_entry = tk.Entry(rss_row, font=('맑은 고딕', 9), width=20)
        self.rss_keyword_entry.pack(side='left')

        # 미리보기
        tk.Label(main_frame, text="가져온 글:", bg='white',
                font=('맑은 고딕', 9)).pack(anchor='w')

        self.url_preview = scrolledtext.ScrolledText(main_frame, height=6,
                                                     font=('맑은 고딕', 9),
                                                     wrap='word', state='disabled')
        self.url_preview.pack(fill='x', pady=(3, 8))

        # 추가 지시사항
        tk.Label(main_frame, text="추가 지시사항:", bg='white',
                font=('맑은 고딕', 9)).pack(anchor='w')

        self.custom_prompt_url = scrolledtext.ScrolledText(main_frame, height=2,
                                                          font=('맑은 고딕', 9),
                                                          wrap='word')
        self.custom_prompt_url.pack(fill='x', pady=(3, 8))

        # 옵션
        option_frame = tk.LabelFrame(main_frame, text=" 옵션 ", bg='white',
                                    font=('맑은 고딕', 9), padx=8, pady=5)
        option_frame.pack(fill='x', pady=(0, 8))

        opt_row = tk.Frame(option_frame, bg='white')
        opt_row.pack(fill='x')

        tk.Label(opt_row, text="생성:", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.url_count_var = tk.StringVar(value='1')
        tk.Spinbox(opt_row, from_=1, to=50, width=4, textvariable=self.url_count_var,
                  font=('맑은 고딕', 9)).pack(side='left', padx=(3, 8))

        tk.Label(opt_row, text="AI:", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.ai_var_url = tk.StringVar(value='gemini')
        tk.Radiobutton(opt_row, text="Gemini", variable=self.ai_var_url,
                      value='gemini', bg='white', font=('맑은 고딕', 8)).pack(side='left')
        tk.Radiobutton(opt_row, text="Claude", variable=self.ai_var_url,
                      value='claude', bg='white', font=('맑은 고딕', 8)).pack(side='left')

        opt_row2 = tk.Frame(option_frame, bg='white')
        opt_row2.pack(fill='x', pady=(5, 0))

        tk.Label(opt_row2, text="계정그룹:", bg='white', font=('맑은 고딕', 9)).pack(side='left')
        self.url_account_group_var = tk.StringVar(value='')
        self.url_account_group_combo = ttk.Combobox(opt_row2, textvariable=self.url_account_group_var,
                                                    state='readonly', width=15, font=('맑은 고딕', 9))
        self.url_account_group_combo['values'] = ['(선택안함)']
        self.url_account_group_combo.set('(선택안함)')
        self.url_account_group_combo.pack(side='left', padx=(5, 0))

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
        tk.Label(main_frame, text="프롬프트 (필수):", bg='white',
                font=('맑은 고딕', 9, 'bold')).pack(anchor='w')

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
        self.ai_var_prompt = tk.StringVar(value='gemini')
        tk.Radiobutton(opt_row2, text="Gemini", variable=self.ai_var_prompt,
                      value='gemini', bg='white', font=('맑은 고딕', 8)).pack(side='left')
        tk.Radiobutton(opt_row2, text="Claude", variable=self.ai_var_prompt,
                      value='claude', bg='white', font=('맑은 고딕', 8)).pack(side='left')

        # 이미지 마커 옵션
        img_frame = tk.LabelFrame(main_frame, text=" 이미지 마커 ", bg='white',
                                 font=('맑은 고딕', 9), padx=8, pady=5)
        img_frame.pack(fill='x', pady=(0, 8))

        img_row1 = tk.Frame(img_frame, bg='white')
        img_row1.pack(fill='x')

        self.auto_image_var = tk.BooleanVar(value=False)
        tk.Checkbutton(img_row1, text="자동 생성", variable=self.auto_image_var,
                      bg='white', font=('맑은 고딕', 9),
                      command=self.toggle_image_options).pack(side='left')

        tk.Label(img_row1, text="개수:", bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(10, 3))
        self.image_count_var = tk.StringVar(value='3')
        self.img_count_spinbox = tk.Spinbox(img_row1, from_=1, to=10, width=3,
                                           textvariable=self.image_count_var,
                                           font=('맑은 고딕', 9), state='disabled')
        self.img_count_spinbox.pack(side='left')

        tk.Label(img_row1, text="위치:", bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(10, 3))
        self.custom_image_pos = tk.Entry(img_row1, width=15, font=('맑은 고딕', 9), state='disabled')
        self.custom_image_pos.pack(side='left')

        tk.Label(img_frame, text="예: [image01]=1개, [image01:05]=1~5번",
                bg='white', fg='#888', font=('맑은 고딕', 8)).pack(anchor='w')

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
            self.custom_image_pos.config(state='normal')
        else:
            self.img_count_spinbox.config(state='disabled')
            self.custom_image_pos.config(state='disabled')

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

    def create_content_list_tab(self, parent):
        """콘텐츠 목록 탭"""
        filter_frame = tk.Frame(parent, bg='white')
        filter_frame.pack(fill='x', padx=10, pady=10)

        tk.Label(filter_frame, text="상태:", bg='white', font=('맑은 고딕', 9)).pack(side='left')

        self.status_filter = ttk.Combobox(filter_frame, values=['전체', '대기', '발행 중', '발행 완료'],
                                         state='readonly', width=10, font=('맑은 고딕', 9))
        self.status_filter.set('전체')
        self.status_filter.pack(side='left', padx=(5, 10))
        self.status_filter.bind('<<ComboboxSelected>>', lambda e: self.refresh_content_list())

        tk.Button(filter_frame, text="🔄 새로고침", command=self.refresh_content_list,
                 bg='#2196F3', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=10).pack(side='left')

        tk.Button(filter_frame, text="🗑️ 삭제", command=self.delete_content,
                 bg='#F44336', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=10).pack(side='right')

        tk.Button(filter_frame, text="✏️ 수정", command=self.open_edit_tab,
                 bg='#FFC107', fg='white', font=('맑은 고딕', 9, 'bold'),
                 relief='flat', cursor='hand2', padx=10).pack(side='right', padx=(0, 5))

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

        columns = ('ID', '키워드', '제목', '상태', 'AI모델', '생성일')
        self.content_tree = ttk.Treeview(tree_container, columns=columns, show='headings',
                                        yscrollcommand=scrollbar_y.set,
                                        xscrollcommand=scrollbar_x.set, height=20)

        self.content_tree.heading('ID', text='ID')
        self.content_tree.heading('키워드', text='키워드')
        self.content_tree.heading('제목', text='제목')
        self.content_tree.heading('상태', text='상태')
        self.content_tree.heading('AI모델', text='AI모델')
        self.content_tree.heading('생성일', text='생성일')

        self.content_tree.column('ID', width=150, minwidth=100)
        self.content_tree.column('키워드', width=100, minwidth=80)
        self.content_tree.column('제목', width=300, minwidth=150)
        self.content_tree.column('상태', width=60, minwidth=50)
        self.content_tree.column('AI모델', width=100, minwidth=80)
        self.content_tree.column('생성일', width=120, minwidth=100)

        self.content_tree.pack(fill='both', expand=True)
        scrollbar_y.config(command=self.content_tree.yview)
        scrollbar_x.config(command=self.content_tree.xview)

        self.content_tree.bind('<Double-1>', lambda e: self.open_edit_tab())

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
        marker = f"[image{num:02d}]"
        self.edit_content_text.insert('insert', marker)

    def add_range_marker(self):
        """연속 이미지 마커 추가"""
        s = int(self.range_start_var.get())
        e = int(self.range_end_var.get())
        marker = f"[image{s:02d}:{e:02d}]"
        self.edit_content_text.insert('insert', marker)

    def remove_all_markers(self):
        """모든 이미지 마커 제거"""
        content = self.edit_content_text.get('1.0', 'end')
        if not re.search(r'\[image\d+(?::\d+)?\]', content):
            self.show_info("제거할 이미지 마커가 없습니다")
            return

        if messagebox.askyesno("확인", "모든 이미지 마커를 제거하시겠습니까?"):
            cleaned = re.sub(r'\[image\d+(?::\d+)?\]\s*', '', content)
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

    def fetch_from_url(self):
        """URL에서 글 가져오기"""
        url = self.url_entry.get().strip()
        rss_keyword = self.rss_keyword_entry.get().strip()

        if not url:
            self.show_error("블로그 URL을 입력하세요")
            return

        self.show_working("블로그에서 글을 가져오는 중...")

        def fetch_thread():
            try:
                if '/' in url.split('blog.naver.com/')[-1] and len(url.split('/')[-1]) > 5:
                    result = self.crawler.parse_blog_post(url)
                    content = f"[제목] {result['title']}\n\n{result['content_with_markers']}"
                else:
                    if not rss_keyword:
                        raise Exception("RSS 검색 키워드를 입력하세요")

                    blog_id = self.crawler.get_blog_id_from_url(url)
                    if not blog_id:
                        raise Exception("유효한 네이버 블로그 URL이 아닙니다")

                    self.root.after(0, lambda: self.show_working(f"RSS에서 '{rss_keyword}' 검색 중..."))

                    post = self.crawler.find_post_by_keyword(blog_id, rss_keyword)
                    if not post:
                        raise Exception(f"'{rss_keyword}'가 제목에 포함된 글을 찾을 수 없습니다")

                    result = self.crawler.parse_blog_post(post['link'])
                    content = f"[제목] {result['title']}\n\n{result['content_with_markers']}"

                self.root.after(0, lambda: self.url_preview.config(state='normal'))
                self.root.after(0, lambda: self.url_preview.delete('1.0', 'end'))
                self.root.after(0, lambda: self.url_preview.insert('1.0', content))
                self.root.after(0, lambda: self.url_preview.config(state='disabled'))
                self.root.after(0, lambda: self.show_success("글 가져오기 완료!"))

            except Exception as e:
                self.root.after(0, lambda: self.show_error(f"가져오기 실패: {str(e)[:50]}"))

        threading.Thread(target=fetch_thread, daemon=True).start()

    def get_ai_instruction_suffix(self, char_limit='800'):
        """AI 지시사항 접미사"""
        return f"""

[중요 지시사항]
1. 글자 수: {char_limit}자 내외로 작성해주세요.
2. 서식 금지: 제목이나 본문에 절대로 **, ##, ###, # 같은 마크다운 서식을 사용하지 마세요.
3. 글 자체를 읽기 좋게 자연스럽게 작성해주세요. 굵은 글씨나 헤더 대신 문단 구분으로 가독성을 높여주세요.
4. 제목은 간결하고 명확하게, 본문은 자연스럽고 읽기 좋게 작성해주세요."""

    def start_url_generation(self):
        """URL 리라이팅 생성 시작"""
        if not self.current_license:
            self.show_error("먼저 라이선스를 확인하세요")
            return

        original = self.url_preview.get('1.0', 'end').strip()
        if not original:
            self.show_error("먼저 글을 가져오세요")
            return

        try:
            count = int(self.url_count_var.get())
            if count < 1:
                raise ValueError()
        except ValueError:
            self.show_error("유효한 생성 개수를 입력하세요")
            return

        remaining = self.current_license['api_limit'] - self.current_license['api_usage']
        if count > remaining:
            self.show_error(f"남은 사용량({remaining}개)보다 많이 생성할 수 없습니다")
            return

        custom_prompt = self.custom_prompt_url.get('1.0', 'end').strip()
        ai_type = self.ai_var_url.get()
        keyword = self.rss_keyword_entry.get().strip() or "키워드없음"
        account_group = self.url_account_group_var.get()
        if account_group == '(선택안함)':
            self.show_error("계정그룹을 선택하세요")
            return

        self.generating = True
        self.stop_requested = False
        self.url_start_btn.config(state='disabled', bg='#999')
        self.url_stop_btn.config(state='normal', bg='#F44336')

        ai_name = "Gemini 2.5 Flash" if ai_type == 'gemini' else "Claude 3.5 Sonnet"

        def generate_thread():
            success_count = 0
            fail_count = 0

            for i in range(count):
                if self.stop_requested:
                    break

                self.root.after(0, lambda idx=i, sc=success_count: self.show_working(
                    f"[{idx+1}/{count}] {ai_name} 리라이팅 중... (성공: {sc}개)"
                ))

                try:
                    generator = MultiAIGenerator(ai_type=ai_type)

                    if custom_prompt:
                        full_prompt = f"{custom_prompt}\n\n(#{i+1}번째 글 - 이전과 다른 관점으로){self.get_ai_instruction_suffix()}"
                    else:
                        full_prompt = f"전문적이고 신뢰감 있는 말투로 리라이팅해주세요.\n(#{i+1}번째 글){self.get_ai_instruction_suffix()}"

                    result = generator.generate_with_custom_prompt(
                        user_prompt=full_prompt,
                        original_text=original
                    )

                    self.content_mgr.add_content(
                        keyword=keyword,
                        title=result['title'],
                        content=result['content'],
                        license_key=self.current_license['license_key'],
                        ai_model=ai_name,
                        account_group=account_group
                    )

                    self.license_mgr.increment_api_usage(self.current_license['license_key'])
                    success_count += 1

                    self.root.after(0, self.refresh_content_list)

                except Exception as e:
                    fail_count += 1
                    print(f"❌ 생성 실패 #{i+1}: {e}")

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
        custom_image_pos = self.custom_image_pos.get().strip() if auto_image else ""
        account_group = self.prompt_account_group_var.get()
        if account_group == '(선택안함)':
            self.show_error("계정그룹을 선택하세요")
            return

        self.generating = True
        self.stop_requested = False
        self.prompt_start_btn.config(state='disabled', bg='#999')
        self.prompt_stop_btn.config(state='normal', bg='#F44336')

        ai_name = "Gemini 2.5 Flash" if ai_type == 'gemini' else "Claude 3.5 Sonnet"

        def generate_thread():
            success_count = 0
            fail_count = 0

            for i in range(count):
                if self.stop_requested:
                    self.root.after(0, lambda sc=success_count, fc=fail_count: self.show_info(
                        f"중지됨 - 성공: {sc}개, 실패: {fc}개"
                    ))
                    break

                self.root.after(0, lambda idx=i, sc=success_count: self.show_working(
                    f"[{idx+1}/{count}] {ai_name} 글 생성 중... (성공: {sc}개)"
                ))

                try:
                    generator = MultiAIGenerator(ai_type=ai_type)

                    image_instruction = ""
                    if auto_image:
                        if custom_image_pos:
                            image_instruction = f"\n\n이미지 마커 위치: {custom_image_pos} 형식으로 본문에 이미지 마커를 넣어주세요."
                        else:
                            image_instruction = f"\n\n본문 중간중간에 [image01], [image02] 형식으로 {image_count}개의 이미지 마커를 적절히 배치해주세요."

                    full_prompt = f"{prompt}\n\n(#{i+1}번째 글 - 이전과 다른 관점, 다른 구성으로){self.get_ai_instruction_suffix(char_limit)}{image_instruction}"

                    result = generator.generate_with_custom_prompt(
                        user_prompt=full_prompt,
                        original_text=None
                    )

                    self.content_mgr.add_content(
                        keyword=keyword,
                        title=result['title'],
                        content=result['content'],
                        license_key=self.current_license['license_key'],
                        ai_model=ai_name,
                        account_group=account_group
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
        content_id = item['values'][0] if item['values'] else None

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
            status_map = {
                '전체': None,
                '대기': 'ready',
                '발행 중': 'publishing',
                '발행 완료': 'published'
            }

            filter_status = status_map.get(status_filter)

            for content in contents:
                if filter_status and content['status'] != filter_status:
                    continue

                status_kr = {
                    'ready': '대기',
                    'publishing': '발행 중',
                    'published': '완료'
                }.get(content['status'], content['status'])

                created_time = content['created_time']
                if len(created_time) > 16:
                    created_time = created_time[:16]

                self.content_tree.insert('', 0, values=(
                    content['content_id'],
                    content['keyword'],
                    content['title'][:45] + '...' if len(content['title']) > 45 else content['title'],
                    status_kr,
                    content.get('ai_model', ''),
                    created_time
                ))

        except Exception as e:
            print(f"❌ 콘텐츠 목록 새로고침 실패: {e}")

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
        content_id = item['values'][0] if item['values'] else None

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


def main():
    """메인 함수"""
    root = tk.Tk()
    app = ContentCreatorProV3(root)
    root.mainloop()


if __name__ == "__main__":
    main()
