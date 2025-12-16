"""
네이버 블로그 에디터용 HTML 생성기

텍스트를 네이버 블로그 에디터에 붙여넣기 가능한 HTML로 변환
"""

import re
import uuid
from html import escape


class NaverHTMLGenerator:
    """네이버 블로그 에디터 HTML 생성기"""

    def __init__(self):
        pass

    def generate_id(self):
        """고유 ID 생성"""
        return f"SE-{uuid.uuid4()}"

    def text_to_naver_html(self, text):
        """
        일반 텍스트를 네이버 블로그 HTML로 변환

        지원:
        - 일반 문단
        - **굵게**, *기울임*, _밑줄_
        - > 인용문
        - | 표 |
        - • 리스트
        - [이미지N] 마커
        """
        lines = text.strip().split('\n')
        components = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # 빈 줄 건너뛰기
            if not line.strip():
                i += 1
                continue

            # 인용문 (> 시작)
            if line.strip().startswith('>'):
                quote_lines = []
                while i < len(lines) and lines[i].strip().startswith('>'):
                    quote_lines.append(lines[i].strip()[1:].strip())
                    i += 1
                components.append(self._create_quotation('\n'.join(quote_lines)))
                continue

            # 표 (| 시작)
            if line.strip().startswith('|'):
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    table_lines.append(lines[i].strip())
                    i += 1
                components.append(self._create_table(table_lines))
                continue

            # 리스트 (• 시작)
            if line.strip().startswith('•'):
                list_items = []
                while i < len(lines) and lines[i].strip().startswith('•'):
                    list_items.append(lines[i].strip()[1:].strip())
                    i += 1
                components.append(self._create_list(list_items))
                continue

            # 이미지 마커 [이미지N]
            if re.match(r'^\[이미지\d+\]$', line.strip()):
                components.append(self._create_image_placeholder(line.strip()))
                i += 1
                continue

            # 일반 문단
            components.append(self._create_paragraph(line.strip()))
            i += 1

        return '\n'.join(components)

    def _apply_styles(self, text):
        """마크다운 스타일을 HTML로 변환"""
        # **굵게**
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        # *기울임*
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        # _밑줄_
        text = re.sub(r'_(.+?)_', r'<u>\1</u>', text)

        return text

    def _create_paragraph(self, text):
        """일반 문단 HTML 생성"""
        comp_id = self.generate_id()
        p_id = self.generate_id()
        span_id = self.generate_id()

        styled_text = self._apply_styles(escape(text))

        return f'''<div class="se-component se-text se-l-default" id="{comp_id}">
    <div class="se-component-content">
        <div class="se-section se-section-text se-l-default">
            <div class="se-module se-module-text">
                <p class="se-text-paragraph se-text-paragraph-align-" style="" id="{p_id}">
                    <span class="se-fs-fs16 se-ff-" id="{span_id}">{styled_text}</span>
                </p>
            </div>
        </div>
    </div>
</div>'''

    def _create_quotation(self, text):
        """인용문 HTML 생성"""
        comp_id = self.generate_id()
        p_id = self.generate_id()
        span_id = self.generate_id()

        styled_text = self._apply_styles(escape(text))
        # 줄바꿈 처리
        styled_text = styled_text.replace('\n', '</span></p><p class="se-text-paragraph se-text-paragraph-align-center" style="" id="' + self.generate_id() + '"><span class="se-fs-fs16 se-ff-" id="' + self.generate_id() + '">')

        return f'''<div class="se-component se-quotation se-l-default" id="{comp_id}">
    <div class="se-component-content">
        <div class="se-section se-section-quotation se-l-default">
            <blockquote class="se-quotation-container">
                <div class="se-module se-module-text se-quote">
                    <p class="se-text-paragraph se-text-paragraph-align-center" style="" id="{p_id}">
                        <span class="se-fs-fs16 se-ff-" id="{span_id}"><i>{styled_text}</i></span>
                    </p>
                </div>
            </blockquote>
        </div>
    </div>
</div>'''

    def _create_table(self, lines):
        """표 HTML 생성"""
        comp_id = self.generate_id()

        rows = []
        for line in lines:
            # | 셀1 | 셀2 | -> ['셀1', '셀2']
            cells = [c.strip() for c in line.split('|') if c.strip()]

            cell_html = ''
            for cell in cells:
                cell_id = self.generate_id()
                p_id = self.generate_id()
                span_id = self.generate_id()
                styled_cell = self._apply_styles(escape(cell))

                cell_html += f'''<td class="se-cell" colspan="1" rowspan="1" style="width: {100 // len(cells):.2f}%; height: 40.0px;">
                    <div class="se-module se-module-text">
                        <p class="se-text-paragraph se-text-paragraph-align-center" style="" id="{p_id}">
                            <span class="se-fs-" id="{span_id}"><b>{styled_cell}</b></span>
                        </p>
                    </div>
                </td>'''

            rows.append(f'<tr class="se-tr">{cell_html}</tr>')

        rows_html = '\n'.join(rows)
        col_count = len([c.strip() for c in lines[0].split('|') if c.strip()]) if lines else 3

        return f'''<div class="se-component se-table se-l-table_layout1" id="{comp_id}">
    <div class="se-component-content">
        <div class="se-section se-section-table se-l-table_layout1 se-section-align-center" style="width: 100.0%;">
            <div class="se-table-container">
                <table class="se-table-content" style="">
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <script type="text/data" class="__se_module_data" data-module='{{"type":"v2_table", "id" : "{comp_id}", "data": {{ "columnCount" : "{col_count}" }}}}'></script>
</div>'''

    def _create_list(self, items):
        """리스트 HTML 생성"""
        comp_id = self.generate_id()

        list_items = ''
        for item in items:
            li_id = self.generate_id()
            p_id = self.generate_id()
            span_id = self.generate_id()
            styled_item = self._apply_styles(escape(item))

            list_items += f'''<li class="se-text-list-item" id="{li_id}">
                <p class="se-text-paragraph se-text-paragraph-align-" style="" id="{p_id}">
                    <span class="se-fs-fs16 se-ff-" id="{span_id}">{styled_item}</span>
                </p>
            </li>'''

        return f'''<div class="se-component se-text se-l-default" id="{comp_id}">
    <div class="se-component-content">
        <div class="se-section se-section-text se-l-default">
            <div class="se-module se-module-text">
                <ul class="se-text-list se-text-list-type-bullet-disc">
                    {list_items}
                </ul>
            </div>
        </div>
    </div>
</div>'''

    def _create_image_placeholder(self, marker):
        """이미지 플레이스홀더 (참고용 - 실제 이미지는 별도 업로드 필요)"""
        comp_id = self.generate_id()
        p_id = self.generate_id()
        span_id = self.generate_id()

        return f'''<div class="se-component se-text se-l-default" id="{comp_id}">
    <div class="se-component-content">
        <div class="se-section se-section-text se-l-default">
            <div class="se-module se-module-text">
                <p class="se-text-paragraph se-text-paragraph-align-center" style="" id="{p_id}">
                    <span class="se-fs-fs16 se-ff-" id="{span_id}" style="color: #999;">{escape(marker)}</span>
                </p>
            </div>
        </div>
    </div>
</div>'''


# 테스트
if __name__ == '__main__':
    generator = NaverHTMLGenerator()

    test_text = """안녕하세요 **굵은 글씨**와 *기울임*입니다.

> 이것은 인용문입니다
> 두 번째 줄

| 구분 | 설명 |
| 항목1 | 내용1 |
| 항목2 | 내용2 |

• 리스트 항목 1
• 리스트 항목 2
• 리스트 항목 3

[이미지1]

마지막 문단입니다."""

    html = generator.text_to_naver_html(test_text)
    print(html)
