"""
콘텐츠 생성기 GUI

키워드별 맞춤 프롬프트 작성 및 콘텐츠 생성
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json

from src.sheets.license_manager import LicenseManager
from src.sheets.content_manager import ContentManager
from src.content.advanced_generator import AdvancedContentGenerator


class ContentCreatorGUI:
    """콘텐츠 생성기 GUI 클래스"""

    def __init__(self, root):
        self.root = root
        self.root.title("네이버 블로그 콘텐츠 생성기")
        self.root.geometry("900x700")

        # 매니저 초기화
        self.license_mgr = LicenseManager()
        self.content_mgr = ContentManager()
        self.generator = AdvancedContentGenerator()

        # GUI 구성
        self.create_widgets()

    def create_widgets(self):
        """위젯 생성"""

        # ===== 상단: 라이선스 입력 =====
        license_frame = ttk.LabelFrame(self.root, text="라이선스", padding=10)
        license_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(license_frame, text="라이선스 키:").pack(side='left', padx=5)
        self.license_entry = ttk.Entry(license_frame, width=30)
        self.license_entry.pack(side='left', padx=5)
        self.license_entry.insert(0, "LICENSE-ADMIN")

        ttk.Button(license_frame, text="검증", command=self.validate_license).pack(side='left', padx=5)

        self.license_status = ttk.Label(license_frame, text="", foreground="gray")
        self.license_status.pack(side='left', padx=10)

        # ===== 탭 =====
        tab_control = ttk.Notebook(self.root)

        # 탭 1: 리라이팅
        self.tab_rewrite = ttk.Frame(tab_control)
        tab_control.add(self.tab_rewrite, text='리라이팅 (원본 글 수정)')

        # 탭 2: 새로 작성
        self.tab_new = ttk.Frame(tab_control)
        tab_control.add(self.tab_new, text='새로 작성')

        # 탭 3: 사용자 정의 프롬프트
        self.tab_custom = ttk.Frame(tab_control)
        tab_control.add(self.tab_custom, text='사용자 정의 프롬프트')

        tab_control.pack(expand=1, fill='both', padx=10, pady=5)

        # ===== 탭 1: 리라이팅 =====
        self.create_rewrite_tab()

        # ===== 탭 2: 새로 작성 =====
        self.create_new_tab()

        # ===== 탭 3: 사용자 정의 =====
        self.create_custom_tab()

        # ===== 하단: 결과 =====
        result_frame = ttk.LabelFrame(self.root, text="생성된 콘텐츠", padding=10)
        result_frame.pack(fill='both', expand=True, padx=10, pady=5)

        ttk.Label(result_frame, text="제목:").pack(anchor='w')
        self.result_title = ttk.Entry(result_frame, width=80)
        self.result_title.pack(fill='x', pady=5)

        ttk.Label(result_frame, text="본문:").pack(anchor='w')
        self.result_content = scrolledtext.ScrolledText(result_frame, height=10, wrap='word')
        self.result_content.pack(fill='both', expand=True, pady=5)

        # 저장 버튼
        button_frame = ttk.Frame(result_frame)
        button_frame.pack(fill='x', pady=5)

        ttk.Button(button_frame, text="Sheets에 저장 (발행 대기)", command=self.save_to_sheets).pack(side='left', padx=5)
        ttk.Button(button_frame, text="클립보드 복사", command=self.copy_to_clipboard).pack(side='left', padx=5)

    def create_rewrite_tab(self):
        """리라이팅 탭 생성"""
        # 키워드
        ttk.Label(self.tab_rewrite, text="키워드:").pack(anchor='w', padx=10, pady=(10, 0))
        self.rewrite_keyword = ttk.Entry(self.tab_rewrite, width=50)
        self.rewrite_keyword.pack(fill='x', padx=10, pady=5)
        self.rewrite_keyword.insert(0, "yatpor 사기")

        # 말투 지시
        ttk.Label(self.tab_rewrite, text="말투 지시 (선택):").pack(anchor='w', padx=10)
        self.rewrite_tone = ttk.Combobox(self.tab_rewrite, width=47, values=[
            "자연스럽고 읽기 쉬운 말투로",
            "친근한 말투로",
            "전문적인 말투로",
            "격식 있는 말투로",
            "가벼운 말투로"
        ])
        self.rewrite_tone.pack(fill='x', padx=10, pady=5)
        self.rewrite_tone.current(0)

        # 원본 글
        ttk.Label(self.tab_rewrite, text="원본 글:").pack(anchor='w', padx=10)
        self.rewrite_original = scrolledtext.ScrolledText(self.tab_rewrite, height=15, wrap='word')
        self.rewrite_original.pack(fill='both', expand=True, padx=10, pady=5)

        # 생성 버튼
        ttk.Button(self.tab_rewrite, text="리라이팅 생성", command=self.generate_rewrite).pack(pady=10)

    def create_new_tab(self):
        """새로 작성 탭 생성"""
        # 키워드
        ttk.Label(self.tab_new, text="키워드:").pack(anchor='w', padx=10, pady=(10, 0))
        self.new_keyword = ttk.Entry(self.tab_new, width=50)
        self.new_keyword.pack(fill='x', padx=10, pady=5)
        self.new_keyword.insert(0, "소액결제현금화")

        # 템플릿 선택
        ttk.Label(self.tab_new, text="템플릿:").pack(anchor='w', padx=10)

        template_frame = ttk.Frame(self.tab_new)
        template_frame.pack(fill='x', padx=10, pady=5)

        self.template_var = tk.StringVar(value='default')

        templates = [
            ('기본 설명', 'default'),
            ('장단점', 'pros_cons'),
            ('SEO 최적화', 'seo'),
            ('소제목 포함', 'with_subtitles'),
            ('가이드 형식', 'guide')
        ]

        for i, (label, value) in enumerate(templates):
            ttk.Radiobutton(template_frame, text=label, value=value, variable=self.template_var).grid(row=i//3, column=i%3, sticky='w', padx=5, pady=2)

        # 미리보기
        ttk.Label(self.tab_new, text="프롬프트 미리보기:").pack(anchor='w', padx=10, pady=(10, 0))
        self.new_preview = scrolledtext.ScrolledText(self.tab_new, height=8, wrap='word', state='disabled', bg='#f0f0f0')
        self.new_preview.pack(fill='x', padx=10, pady=5)

        # 템플릿 변경 시 미리보기 업데이트
        self.template_var.trace('w', self.update_template_preview)
        self.update_template_preview()

        # 생성 버튼
        ttk.Button(self.tab_new, text="콘텐츠 생성", command=self.generate_new).pack(pady=10)

    def create_custom_tab(self):
        """사용자 정의 프롬프트 탭 생성"""
        # 키워드
        ttk.Label(self.tab_custom, text="키워드:").pack(anchor='w', padx=10, pady=(10, 0))
        self.custom_keyword = ttk.Entry(self.tab_custom, width=50)
        self.custom_keyword.pack(fill='x', padx=10, pady=5)

        # 원본 글 (선택)
        ttk.Label(self.tab_custom, text="원본 글 (리라이팅 시 제공, 새로 작성 시 비워두기):").pack(anchor='w', padx=10)
        self.custom_original = scrolledtext.ScrolledText(self.tab_custom, height=8, wrap='word')
        self.custom_original.pack(fill='x', padx=10, pady=5)

        # 사용자 프롬프트
        ttk.Label(self.tab_custom, text="프롬프트 (자유롭게 작성):").pack(anchor='w', padx=10)
        self.custom_prompt = scrolledtext.ScrolledText(self.tab_custom, height=10, wrap='word')
        self.custom_prompt.pack(fill='both', expand=True, padx=10, pady=5)

        # 예시 프롬프트
        example_text = """예시 프롬프트:
- 글을 제공할건데, 글의 문단 및 구조는 비교하기 쉽게 동일하게 제공하고, 글의 말투어미는 동일한 어미로 새로이 다르게 수정해주고, 말투 어미는 조금 길게 수정해주고, 글의 조사도 중간중간 수정해줘
- 휴대폰 소액결제 현금화의 장단점을 1000자 내외로 써줘
- 소액결제현금화를 설명하는 SEO 용도의 글을 1000자 내외로 작성해줘"""
        self.custom_prompt.insert('1.0', example_text)

        # 생성 버튼
        ttk.Button(self.tab_custom, text="콘텐츠 생성", command=self.generate_custom).pack(pady=10)

    def update_template_preview(self, *args):
        """템플릿 미리보기 업데이트"""
        keyword = self.new_keyword.get() or "[키워드]"
        template_type = self.template_var.get()

        templates = {
            'default': f"{keyword}를 설명하는 글을 1000자 내외로 써줘",
            'pros_cons': f"{keyword}의 장단점을 1000자 내외로 써줘. 장점 3개, 단점 3개 형식으로",
            'seo': f"{keyword}를 설명하는 SEO 용도의 글을 1000자 내외로 작성해줘. 키워드를 자연스럽게 여러 번 포함",
            'with_subtitles': f"{keyword}를 설명하는 글을 소제목 있는 형태로 1000자 내외로 써줘. 소제목은 ### 사용",
            'guide': f"{keyword} 완벽 가이드를 1000자 내외로 작성해줘. 초보자도 이해하기 쉽게"
        }

        preview = templates.get(template_type, templates['default'])

        self.new_preview.config(state='normal')
        self.new_preview.delete('1.0', 'end')
        self.new_preview.insert('1.0', preview)
        self.new_preview.config(state='disabled')

    def validate_license(self):
        """라이선스 검증"""
        license_key = self.license_entry.get().strip()

        if not license_key:
            messagebox.showerror("오류", "라이선스 키를 입력하세요")
            return

        validation = self.license_mgr.validate_license(license_key)

        if validation['valid']:
            self.license_status.config(text=f"✅ {validation['message']}", foreground="green")
        else:
            self.license_status.config(text=f"❌ {validation['message']}", foreground="red")
            messagebox.showerror("라이선스 오류", validation['message'])

    def generate_rewrite(self):
        """리라이팅 생성"""
        keyword = self.rewrite_keyword.get().strip()
        tone = self.rewrite_tone.get().strip()
        original = self.rewrite_original.get('1.0', 'end').strip()

        if not keyword or not original:
            messagebox.showerror("오류", "키워드와 원본 글을 입력하세요")
            return

        # 라이선스 검증
        if not self._check_license():
            return

        # 생성
        self.root.config(cursor="wait")
        self.root.update()

        result = self.generator.rewrite_article(original, tone)

        self.result_title.delete(0, 'end')
        self.result_title.insert(0, result['title'])

        self.result_content.delete('1.0', 'end')
        self.result_content.insert('1.0', result['content'])

        self.root.config(cursor="")

        # API 사용량 증가
        license_key = self.license_entry.get().strip()
        self.license_mgr.increment_api_usage(license_key)

        messagebox.showinfo("완료", "리라이팅이 완료되었습니다!")

    def generate_new(self):
        """새로 작성 생성"""
        keyword = self.new_keyword.get().strip()
        template_type = self.template_var.get()

        if not keyword:
            messagebox.showerror("오류", "키워드를 입력하세요")
            return

        # 라이선스 검증
        if not self._check_license():
            return

        # 생성
        self.root.config(cursor="wait")
        self.root.update()

        result = self.generator.generate_with_template(keyword, template_type)

        self.result_title.delete(0, 'end')
        self.result_title.insert(0, result['title'])

        self.result_content.delete('1.0', 'end')
        self.result_content.insert('1.0', result['content'])

        self.root.config(cursor="")

        # API 사용량 증가
        license_key = self.license_entry.get().strip()
        self.license_mgr.increment_api_usage(license_key)

        messagebox.showinfo("완료", "콘텐츠 생성이 완료되었습니다!")

    def generate_custom(self):
        """사용자 정의 프롬프트로 생성"""
        keyword = self.custom_keyword.get().strip()
        original = self.custom_original.get('1.0', 'end').strip()
        prompt = self.custom_prompt.get('1.0', 'end').strip()

        if not keyword or not prompt:
            messagebox.showerror("오류", "키워드와 프롬프트를 입력하세요")
            return

        # 라이선스 검증
        if not self._check_license():
            return

        # 생성
        self.root.config(cursor="wait")
        self.root.update()

        result = self.generator.generate_with_custom_prompt(prompt, original if original else None)

        self.result_title.delete(0, 'end')
        self.result_title.insert(0, result['title'])

        self.result_content.delete('1.0', 'end')
        self.result_content.insert('1.0', result['content'])

        self.root.config(cursor="")

        # API 사용량 증가
        license_key = self.license_entry.get().strip()
        self.license_mgr.increment_api_usage(license_key)

        messagebox.showinfo("완료", "콘텐츠 생성이 완료되었습니다!")

    def save_to_sheets(self):
        """Sheets에 저장"""
        title = self.result_title.get().strip()
        content = self.result_content.get('1.0', 'end').strip()
        license_key = self.license_entry.get().strip()

        # 현재 활성 탭의 키워드 가져오기
        current_tab = self.root.nametowidget(str(self.root.focus()))
        if 'rewrite' in str(current_tab):
            keyword = self.rewrite_keyword.get().strip()
        elif 'new' in str(current_tab):
            keyword = self.new_keyword.get().strip()
        else:
            keyword = self.custom_keyword.get().strip()

        if not title or not content or not keyword:
            messagebox.showerror("오류", "제목, 본문, 키워드가 필요합니다")
            return

        # 콘텐츠 관리자에 추가 (generated 상태로)
        row_num = self.content_mgr.add_keyword_request(keyword, license_key)
        self.content_mgr.update_generated_content(row_num, title, content)

        messagebox.showinfo("완료", f"Sheets에 저장되었습니다!\n키워드: {keyword}\n행: {row_num}")

    def copy_to_clipboard(self):
        """클립보드에 복사"""
        title = self.result_title.get().strip()
        content = self.result_content.get('1.0', 'end').strip()

        full_text = f"{title}\n\n{content}"

        self.root.clipboard_clear()
        self.root.clipboard_append(full_text)

        messagebox.showinfo("완료", "클립보드에 복사되었습니다!")

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
    app = ContentCreatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
