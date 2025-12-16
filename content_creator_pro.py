"""
네이버 블로그 콘텐츠 생성기 PRO

고급 UX/UI, 웹 크롤링, 이미지 위치 지정, 멀티 AI 지원
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import json
import re
from urllib.parse import urlparse

from src.sheets.license_manager import LicenseManager
from src.sheets.content_manager import ContentManager
from src.content.multi_ai_generator import MultiAIGenerator
from src.crawler.naver_blog_crawler import NaverBlogCrawler


class ContentCreatorPro:
    """프로 콘텐츠 생성기"""

    def __init__(self, root):
        self.root = root
        self.root.title("네이버 블로그 콘텐츠 생성기 PRO v2.0")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f5f5f5')

        # 스타일 설정
        self.setup_styles()

        # 매니저 초기화
        self.license_mgr = LicenseManager()
        self.content_mgr = ContentManager()
        self.crawler = NaverBlogCrawler()

        # AI 생성기는 나중에 초기화 (AI 선택 후)
        self.generator = None

        # 변수
        self.generating = False
        self.image_markers = []  # [위치1, 위치2, ...]

        # GUI 구성
        self.create_widgets()

        # 라이선스 자동 로드
        self.auto_load_license()

    def setup_styles(self):
        """스타일 설정"""
        style = ttk.Style()
        style.theme_use('clam')

        # 버튼 스타일
        style.configure('Primary.TButton',
                       background='#0066cc',
                       foreground='white',
                       font=('맑은 고딕', 10, 'bold'),
                       padding=10)

        style.configure('Success.TButton',
                       background='#28a745',
                       foreground='white',
                       font=('맑은 고딕', 9),
                       padding=8)

        style.configure('Warning.TButton',
                       background='#ffc107',
                       foreground='black',
                       font=('맑은 고딕', 9),
                       padding=8)

        # 프레임 스타일
        style.configure('Card.TFrame',
                       background='white',
                       relief='flat',
                       borderwidth=1)

    def create_widgets(self):
        """위젯 생성"""

        # ===== 메인 컨테이너 =====
        main_container = tk.Frame(self.root, bg='#f5f5f5')
        main_container.pack(fill='both', expand=True, padx=20, pady=20)

        # ===== 좌측: 입력 영역 =====
        left_panel = tk.Frame(main_container, bg='#f5f5f5')
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 10))

        self.create_left_panel(left_panel)

        # ===== 우측: 결과 영역 =====
        right_panel = tk.Frame(main_container, bg='#f5f5f5')
        right_panel.pack(side='right', fill='both', expand=True, padx=(10, 0))

        self.create_right_panel(right_panel)

    def create_left_panel(self, parent):
        """좌측 패널 생성"""

        # ===== 1. 라이선스 카드 =====
        license_card = tk.LabelFrame(parent, text="  🔑 라이선스  ", bg='white',
                                     font=('맑은 고딕', 11, 'bold'), padx=15, pady=15)
        license_card.pack(fill='x', pady=(0, 15))

        license_inner = tk.Frame(license_card, bg='white')
        license_inner.pack(fill='x')

        tk.Label(license_inner, text="라이선스 키:", bg='white',
                font=('맑은 고딕', 9)).pack(side='left', padx=(0, 10))

        self.license_entry = tk.Entry(license_inner, width=25, font=('맑은 고딕', 10))
        self.license_entry.pack(side='left', padx=(0, 10))

        ttk.Button(license_inner, text="검증", command=self.validate_license,
                  style='Primary.TButton', width=8).pack(side='left')

        self.license_status = tk.Label(license_card, text="", bg='white',
                                       font=('맑은 고딕', 9), fg='gray')
        self.license_status.pack(anchor='w', pady=(10, 0))

        # ===== 2. 키워드 & AI 선택 =====
        keyword_card = tk.LabelFrame(parent, text="  📝 기본 설정  ", bg='white',
                                     font=('맑은 고딕', 11, 'bold'), padx=15, pady=15)
        keyword_card.pack(fill='x', pady=(0, 15))

        # 키워드
        kw_frame = tk.Frame(keyword_card, bg='white')
        kw_frame.pack(fill='x', pady=(0, 10))

        tk.Label(kw_frame, text="키워드:", bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(0, 10))
        self.keyword_entry = tk.Entry(kw_frame, width=40, font=('맑은 고딕', 10))
        self.keyword_entry.pack(side='left', fill='x', expand=True)

        # AI 선택
        ai_frame = tk.Frame(keyword_card, bg='white')
        ai_frame.pack(fill='x')

        tk.Label(ai_frame, text="AI 모델:", bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(0, 10))

        self.ai_var = tk.StringVar(value='gemini')
        tk.Radiobutton(ai_frame, text="Gemini 2.5 Flash", variable=self.ai_var, value='gemini',
                      bg='white', font=('맑은 고딕', 9)).pack(side='left', padx=(0, 20))
        tk.Radiobutton(ai_frame, text="Claude 3.5 Sonnet", variable=self.ai_var, value='claude',
                      bg='white', font=('맑은 고딕', 9)).pack(side='left')

        # ===== 3. 생성 모드 선택 =====
        mode_card = tk.LabelFrame(parent, text="  🎯 생성 모드  ", bg='white',
                                 font=('맑은 고딕', 11, 'bold'), padx=15, pady=15)
        mode_card.pack(fill='x', pady=(0, 15))

        self.mode_var = tk.StringVar(value='url')

        modes = [
            ('url', '🌐 URL에서 가져오기', '블로그 URL을 입력하면 자동으로 글을 가져와 리라이팅합니다'),
            ('text', '📄 텍스트 직접 입력', '원본 글을 직접 붙여넣어 리라이팅합니다'),
            ('new', '✨ 새로 작성', '키워드만으로 완전히 새로운 글을 생성합니다'),
            ('custom', '⚙️ 사용자 정의', '자유롭게 프롬프트를 작성합니다')
        ]

        for value, label, desc in modes:
            frame = tk.Frame(mode_card, bg='white')
            frame.pack(fill='x', pady=2)

            tk.Radiobutton(frame, text=label, variable=self.mode_var, value=value,
                          bg='white', font=('맑은 고딕', 9, 'bold'),
                          command=self.on_mode_change).pack(side='left')

            tk.Label(frame, text=desc, bg='white', font=('맑은 고딕', 8),
                    fg='gray').pack(side='left', padx=(10, 0))

        # ===== 4. 입력 영역 (동적) =====
        self.input_card = tk.LabelFrame(parent, text="  ✍️ 입력  ", bg='white',
                                       font=('맑은 고딕', 11, 'bold'), padx=15, pady=15)
        self.input_card.pack(fill='both', expand=True, pady=(0, 15))

        self.input_container = tk.Frame(self.input_card, bg='white')
        self.input_container.pack(fill='both', expand=True)

        # 초기 모드 설정
        self.on_mode_change()

        # ===== 5. 생성 버튼 =====
        button_frame = tk.Frame(parent, bg='#f5f5f5')
        button_frame.pack(fill='x')

        self.generate_btn = tk.Button(button_frame, text="🚀 콘텐츠 생성하기",
                                      command=self.generate_content,
                                      bg='#0066cc', fg='white',
                                      font=('맑은 고딕', 12, 'bold'),
                                      padx=20, pady=12, cursor='hand2',
                                      relief='flat')
        self.generate_btn.pack(fill='x')

        # 진행 상태
        self.progress_label = tk.Label(parent, text="", bg='#f5f5f5',
                                      font=('맑은 고딕', 9), fg='#0066cc')
        self.progress_label.pack(pady=(10, 0))

    def create_right_panel(self, parent):
        """우측 패널 생성"""

        # ===== 결과 카드 =====
        result_card = tk.LabelFrame(parent, text="  📄 생성된 콘텐츠  ", bg='white',
                                   font=('맑은 고딕', 11, 'bold'), padx=15, pady=15)
        result_card.pack(fill='both', expand=True)

        # 제목
        tk.Label(result_card, text="제목:", bg='white', font=('맑은 고딕', 9, 'bold')).pack(anchor='w', pady=(0, 5))
        self.result_title = tk.Entry(result_card, font=('맑은 고딕', 11), bg='#f9f9f9')
        self.result_title.pack(fill='x', pady=(0, 15))

        # 본문
        text_frame = tk.Frame(result_card, bg='white')
        text_frame.pack(fill='both', expand=True, pady=(0, 15))

        tk.Label(text_frame, text="본문:", bg='white', font=('맑은 고딕', 9, 'bold')).pack(anchor='w', pady=(0, 5))

        self.result_content = scrolledtext.ScrolledText(text_frame, wrap='word',
                                                        font=('맑은 고딕', 10),
                                                        bg='#f9f9f9', relief='flat',
                                                        padx=10, pady=10)
        self.result_content.pack(fill='both', expand=True)

        # 이미지 마커 관리
        marker_frame = tk.Frame(result_card, bg='white')
        marker_frame.pack(fill='x', pady=(0, 15))

        tk.Label(marker_frame, text="🖼️ 이미지 위치:", bg='white',
                font=('맑은 고딕', 9, 'bold')).pack(side='left', padx=(0, 10))

        ttk.Button(marker_frame, text="현재 위치에 삽입", command=self.insert_image_marker,
                  style='Warning.TButton').pack(side='left', padx=(0, 5))

        ttk.Button(marker_frame, text="마커 모두 제거", command=self.clear_image_markers,
                  style='Warning.TButton').pack(side='left')

        self.marker_info = tk.Label(marker_frame, text="이미지 마커: 0개", bg='white',
                                   font=('맑은 고딕', 8), fg='gray')
        self.marker_info.pack(side='left', padx=(15, 0))

        # 저장 버튼들
        save_frame = tk.Frame(result_card, bg='white')
        save_frame.pack(fill='x')

        ttk.Button(save_frame, text="✅ Sheets에 저장 (발행 대기)",
                  command=self.save_to_sheets, style='Success.TButton').pack(side='left', padx=(0, 10))

        ttk.Button(save_frame, text="📋 클립보드 복사",
                  command=self.copy_to_clipboard, style='Success.TButton').pack(side='left', padx=(0, 10))

        ttk.Button(save_frame, text="💾 파일로 저장",
                  command=self.save_to_file, style='Success.TButton').pack(side='left')

    def on_mode_change(self):
        """모드 변경 시 입력 영역 업데이트"""
        # 기존 위젯 제거
        for widget in self.input_container.winfo_children():
            widget.destroy()

        mode = self.mode_var.get()

        if mode == 'url':
            self.create_url_input()
        elif mode == 'text':
            self.create_text_input()
        elif mode == 'new':
            self.create_new_input()
        elif mode == 'custom':
            self.create_custom_input()

    def create_url_input(self):
        """URL 입력 모드"""
        tk.Label(self.input_container, text="블로그 URL:", bg='white',
                font=('맑은 고딕', 9)).pack(anchor='w', pady=(0, 5))

        url_frame = tk.Frame(self.input_container, bg='white')
        url_frame.pack(fill='x', pady=(0, 10))

        self.url_entry = tk.Entry(url_frame, font=('맑은 고딕', 10))
        self.url_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.url_entry.insert(0, "https://blog.naver.com/...")

        ttk.Button(url_frame, text="불러오기", command=self.fetch_from_url,
                  style='Primary.TButton', width=10).pack(side='left')

        tk.Label(self.input_container, text="말투 설정:", bg='white',
                font=('맑은 고딘', 9)).pack(anchor='w', pady=(10, 5))

        self.tone_combo = ttk.Combobox(self.input_container, values=[
            "자연스럽고 읽기 쉬운 말투로",
            "친근한 말투로",
            "전문적인 말투로",
            "격식 있는 말투로",
            "가벼운 말투로"
        ], state='readonly', font=('맑은 고딕', 9))
        self.tone_combo.pack(fill='x')
        self.tone_combo.current(0)

        tk.Label(self.input_container, text="가져온 글 미리보기:", bg='white',
                font=('맑은 고딕', 9)).pack(anchor='w', pady=(15, 5))

        self.url_preview = scrolledtext.ScrolledText(self.input_container, height=12,
                                                     wrap='word', font=('맑은 고딕', 9),
                                                     bg='#f9f9f9', state='disabled')
        self.url_preview.pack(fill='both', expand=True)

    def create_text_input(self):
        """텍스트 직접 입력 모드"""
        tk.Label(self.input_container, text="말투 설정:", bg='white',
                font=('맑은 고딕', 9)).pack(anchor='w', pady=(0, 5))

        self.text_tone_combo = ttk.Combobox(self.input_container, values=[
            "자연스럽고 읽기 쉬운 말투로",
            "친근한 말투로",
            "전문적인 말투로",
            "격식 있는 말투로",
            "가벼운 말투로"
        ], state='readonly', font=('맑은 고딕', 9))
        self.text_tone_combo.pack(fill='x', pady=(0, 10))
        self.text_tone_combo.current(0)

        tk.Label(self.input_container, text="원본 글:", bg='white',
                font=('맑은 고딕', 9)).pack(anchor='w', pady=(0, 5))

        self.text_input = scrolledtext.ScrolledText(self.input_container, height=15,
                                                    wrap='word', font=('맑은 고딕', 10),
                                                    bg='#f9f9f9')
        self.text_input.pack(fill='both', expand=True)

    def create_new_input(self):
        """새로 작성 모드"""
        tk.Label(self.input_container, text="템플릿 선택:", bg='white',
                font=('맑은 고딕', 9)).pack(anchor='w', pady=(0, 5))

        self.template_var = tk.StringVar(value='default')

        templates = [
            ('default', '기본 설명', '키워드를 설명하는 일반적인 글'),
            ('pros_cons', '장단점 분석', '장점 3개, 단점 3개 형식'),
            ('seo', 'SEO 최적화', '검색 엔진 최적화 글'),
            ('with_subtitles', '소제목 포함', '체계적인 구조의 글'),
            ('guide', '완벽 가이드', '초보자를 위한 상세 가이드')
        ]

        for value, label, desc in templates:
            frame = tk.Frame(self.input_container, bg='white')
            frame.pack(fill='x', pady=3)

            tk.Radiobutton(frame, text=label, variable=self.template_var, value=value,
                          bg='white', font=('맑은 고딕', 9),
                          command=self.update_new_preview).pack(side='left', padx=(0, 10))

            tk.Label(frame, text=desc, bg='white', font=('맑은 고딕', 8),
                    fg='gray').pack(side='left')

        tk.Label(self.input_container, text="프롬프트 미리보기:", bg='white',
                font=('맑은 고딕', 9)).pack(anchor='w', pady=(15, 5))

        self.new_preview = scrolledtext.ScrolledText(self.input_container, height=8,
                                                     wrap='word', font=('맑은 고딕', 9),
                                                     bg='#f0f0f0', state='disabled')
        self.new_preview.pack(fill='both', expand=True)

        self.update_new_preview()

    def create_custom_input(self):
        """사용자 정의 모드"""
        tk.Label(self.input_container, text="프롬프트 (자유롭게 작성):", bg='white',
                font=('맑은 고딕', 9)).pack(anchor='w', pady=(0, 5))

        self.custom_prompt = scrolledtext.ScrolledText(self.input_container, height=10,
                                                       wrap='word', font=('맑은 고딕', 10),
                                                       bg='#f9f9f9')
        self.custom_prompt.pack(fill='both', expand=True, pady=(0, 10))

        example = """예시:
- 휴대폰 소액결제 현금화의 장단점을 1000자 내외로 써줘
- 소액결제현금화를 설명하는 SEO 용도의 글을 1000자 내외로 작성해줘"""
        self.custom_prompt.insert('1.0', example)

        tk.Label(self.input_container, text="원본 글 (리라이팅 시 입력, 새로 작성 시 비워두기):",
                bg='white', font=('맑은 고딕', 9)).pack(anchor='w', pady=(10, 5))

        self.custom_original = scrolledtext.ScrolledText(self.input_container, height=8,
                                                         wrap='word', font=('맑은 고딕', 9),
                                                         bg='#f9f9f9')
        self.custom_original.pack(fill='both', expand=True)

    def update_new_preview(self):
        """새로 작성 모드 프롬프트 미리보기"""
        keyword = self.keyword_entry.get() or "[키워드]"
        template = self.template_var.get()

        templates = {
            'default': f"{keyword}를 설명하는 글을 1000자 내외로 써줘",
            'pros_cons': f"{keyword}의 장단점을 1000자 내외로 써줘. 장점 3개, 단점 3개 형식으로",
            'seo': f"{keyword}를 설명하는 SEO 용도의 글을 1000자 내외로 작성해줘. 키워드를 자연스럽게 여러 번 포함",
            'with_subtitles': f"{keyword}를 설명하는 글을 소제목 있는 형태로 1000자 내외로 써줘. 소제목은 ### 사용",
            'guide': f"{keyword} 완벽 가이드를 1000자 내외로 작성해줘. 초보자도 이해하기 쉽게"
        }

        preview = templates.get(template, templates['default'])

        self.new_preview.config(state='normal')
        self.new_preview.delete('1.0', 'end')
        self.new_preview.insert('1.0', preview)
        self.new_preview.config(state='disabled')

    def fetch_from_url(self):
        """URL에서 글 가져오기 (RSS + 직접 파싱)"""
        url = self.url_entry.get().strip()
        keyword = self.keyword_entry.get().strip()

        if not url or url == "https://blog.naver.com/...":
            messagebox.showerror("오류", "유효한 블로그 URL을 입력하세요")
            return

        self.progress_label.config(text="⏳ 블로그에서 글을 가져오는 중...")
        self.root.update()

        def fetch_thread():
            try:
                # URL 타입 감지
                # 1. 글 URL 직접 (예: https://blog.naver.com/sunny12221/224107556066)
                # 2. 블로그 홈 URL + 키워드 검색 (예: https://blog.naver.com/sunny12221)

                if '/' in url.split('blog.naver.com/')[-1] and len(url.split('/')[-1]) > 5:
                    # 직접 글 URL
                    result = self.crawler.parse_blog_post(url)

                    content = f"[제목] {result['title']}\n\n{result['content_with_markers']}"

                else:
                    # 블로그 홈 + 키워드 검색
                    if not keyword:
                        raise Exception("키워드를 입력하세요 (RSS에서 검색용)")

                    blog_id = self.crawler.get_blog_id_from_url(url)

                    if not blog_id:
                        raise Exception("유효한 네이버 블로그 URL이 아닙니다")

                    self.root.after(0, lambda: self.progress_label.config(text=f"🔍 RSS에서 '{keyword}' 검색 중..."))

                    post = self.crawler.find_post_by_keyword(blog_id, keyword)

                    if not post:
                        raise Exception(f"'{keyword}'가 제목에 포함된 글을 찾을 수 없습니다")

                    self.root.after(0, lambda: self.progress_label.config(text=f"📄 '{post['title']}' 파싱 중..."))

                    result = self.crawler.parse_blog_post(post['link'])

                    content = f"[제목] {result['title']}\n\n{result['content_with_markers']}"

                # 미리보기에 표시
                self.root.after(0, lambda: self.url_preview.config(state='normal'))
                self.root.after(0, lambda: self.url_preview.delete('1.0', 'end'))
                self.root.after(0, lambda: self.url_preview.insert('1.0', content))
                self.root.after(0, lambda: self.url_preview.config(state='disabled'))
                self.root.after(0, lambda: self.progress_label.config(text="✅ 글 가져오기 완료!"))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("오류", f"URL 가져오기 실패:\n{str(e)}"))
                self.root.after(0, lambda: self.progress_label.config(text=""))

        threading.Thread(target=fetch_thread, daemon=True).start()

    def generate_content(self):
        """콘텐츠 생성"""
        if self.generating:
            messagebox.showwarning("경고", "이미 생성 중입니다")
            return

        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showerror("오류", "키워드를 입력하세요")
            return

        # 라이선스 체크
        if not self._check_license():
            return

        mode = self.mode_var.get()
        ai_type = self.ai_var.get()

        # 버튼 비활성화
        self.generate_btn.config(state='disabled', text='🔄 생성 중...')
        self.generating = True

        ai_name = "Gemini 2.5 Flash" if ai_type == 'gemini' else "Claude 3.5 Sonnet"
        self.progress_label.config(text=f"⏳ {ai_name}가 콘텐츠를 생성하고 있습니다... 잠시만 기다려주세요")

        def generate_thread():
            try:
                # AI 생성기 초기화
                self.generator = MultiAIGenerator(ai_type=ai_type)

                result = None

                if mode == 'url' or mode == 'text':
                    # 리라이팅
                    if mode == 'url':
                        original = self.url_preview.get('1.0', 'end').strip()
                        tone = self.tone_combo.get()
                    else:
                        original = self.text_input.get('1.0', 'end').strip()
                        tone = self.text_tone_combo.get()

                    if not original:
                        raise Exception("원본 글이 없습니다")

                    result = self.generator.rewrite_article(original, tone)

                elif mode == 'new':
                    # 새로 작성
                    template = self.template_var.get()
                    result = self.generator.generate_with_template(keyword, template)

                elif mode == 'custom':
                    # 사용자 정의
                    prompt = self.custom_prompt.get('1.0', 'end').strip()
                    original = self.custom_original.get('1.0', 'end').strip()

                    if not prompt:
                        raise Exception("프롬프트를 입력하세요")

                    result = self.generator.generate_with_custom_prompt(prompt, original if original else None)

                # 결과 표시
                self.root.after(0, lambda: self.result_title.delete(0, 'end'))
                self.root.after(0, lambda: self.result_title.insert(0, result['title']))

                self.root.after(0, lambda: self.result_content.delete('1.0', 'end'))
                self.root.after(0, lambda: self.result_content.insert('1.0', result['content']))

                # API 사용량 증가
                license_key = self.license_entry.get().strip()
                self.license_mgr.increment_api_usage(license_key)

                self.root.after(0, lambda: self.progress_label.config(text=f"✅ 콘텐츠 생성 완료! (사용 모델: {ai_name})"))
                self.root.after(0, lambda: messagebox.showinfo("완료", f"콘텐츠 생성이 완료되었습니다!\n\n사용 모델: {ai_name}"))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("오류", f"생성 실패:\n{str(e)}"))
                self.root.after(0, lambda: self.progress_label.config(text=""))

            finally:
                self.generating = False
                self.root.after(0, lambda: self.generate_btn.config(state='normal', text='🚀 콘텐츠 생성하기'))

        threading.Thread(target=generate_thread, daemon=True).start()

    def insert_image_marker(self):
        """현재 커서 위치에 이미지 마커 삽입"""
        try:
            cursor_pos = self.result_content.index(tk.INSERT)
            marker_text = f"\n[이미지{len(self.image_markers) + 1}]\n"

            self.result_content.insert(cursor_pos, marker_text)
            self.image_markers.append(cursor_pos)

            self.marker_info.config(text=f"이미지 마커: {len(self.image_markers)}개")

        except Exception as e:
            messagebox.showerror("오류", f"마커 삽입 실패:\n{str(e)}")

    def clear_image_markers(self):
        """이미지 마커 모두 제거"""
        content = self.result_content.get('1.0', 'end')
        content = re.sub(r'\[이미지\d+\]', '', content)

        self.result_content.delete('1.0', 'end')
        self.result_content.insert('1.0', content)

        self.image_markers = []
        self.marker_info.config(text="이미지 마커: 0개")

    def save_to_sheets(self):
        """Sheets에 저장"""
        title = self.result_title.get().strip()
        content = self.result_content.get('1.0', 'end').strip()
        keyword = self.keyword_entry.get().strip()
        license_key = self.license_entry.get().strip()

        if not all([title, content, keyword]):
            messagebox.showerror("오류", "제목, 본문, 키워드가 필요합니다")
            return

        row_num = self.content_mgr.add_keyword_request(keyword, license_key)
        self.content_mgr.update_generated_content(row_num, title, content)

        messagebox.showinfo("완료", f"✅ Sheets에 저장되었습니다!\n\n키워드: {keyword}\n행: {row_num}\n상태: 발행 대기")

    def copy_to_clipboard(self):
        """클립보드에 복사"""
        title = self.result_title.get().strip()
        content = self.result_content.get('1.0', 'end').strip()

        full_text = f"{title}\n\n{content}"

        self.root.clipboard_clear()
        self.root.clipboard_append(full_text)

        messagebox.showinfo("완료", "클립보드에 복사되었습니다!")

    def save_to_file(self):
        """파일로 저장"""
        title = self.result_title.get().strip()
        content = self.result_content.get('1.0', 'end').strip()

        if not title or not content:
            messagebox.showerror("오류", "제목과 본문이 필요합니다")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("텍스트 파일", "*.txt"), ("마크다운 파일", "*.md"), ("모든 파일", "*.*")],
            initialfile=f"{title[:30]}.txt"
        )

        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"{title}\n\n{content}")

            messagebox.showinfo("완료", f"파일로 저장되었습니다:\n{filename}")

    def validate_license(self):
        """라이선스 검증"""
        license_key = self.license_entry.get().strip()

        if not license_key:
            messagebox.showerror("오류", "라이선스 키를 입력하세요")
            return

        validation = self.license_mgr.validate_license(license_key)

        if validation['valid']:
            self.license_status.config(text=f"✅ {validation['message']}", fg='#28a745')
        else:
            self.license_status.config(text=f"❌ {validation['message']}", fg='#dc3545')
            messagebox.showerror("라이선스 오류", validation['message'])

    def auto_load_license(self):
        """라이선스 자동 로드"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)

            if 'default_license' in config:
                self.license_entry.insert(0, config['default_license'])
            else:
                self.license_entry.insert(0, "LICENSE-ADMIN")

        except:
            self.license_entry.insert(0, "LICENSE-ADMIN")

    def _check_license(self):
        """라이선스 확인"""
        license_key = self.license_entry.get().strip()

        if not license_key:
            messagebox.showerror("오류", "라이선스 키를 입력하세요")
            return False

        validation = self.license_mgr.validate_license(license_key)

        if not validation['valid']:
            messagebox.showerror("라이선스 오류", validation['message'])
            return False

        if not validation['can_use_api']:
            messagebox.showerror("API 사용량 초과", validation['message'])
            return False

        return True


def main():
    """메인 함수"""
    root = tk.Tk()
    app = ContentCreatorPro(root)
    root.mainloop()


if __name__ == "__main__":
    main()
