"""
네이버 블로그 에디터 HTML 컴포넌트 생성

발행봇에서 마커({hr}, {quote:텍스트}, {table:...})를
네이버 에디터 HTML 컴포넌트로 변환할 때 사용
"""

import uuid
import re
from typing import List, Tuple, Optional


def generate_uuid():
    """SE 컴포넌트용 UUID 생성"""
    return f"SE-{uuid.uuid4()}"


def get_horizontal_line_html():
    """구분선 HTML"""
    comp_id = generate_uuid()
    return f'''<div class="se-component se-horizontalLine se-l-line1" id="{comp_id}" data-compid="{comp_id}" data-a11y-title="구분선"><div class="se-component-content"><div class="se-section se-section-horizontalLine se-l-line1 se-section-align-left"><div class="se-module se-module-horizontalLine __se-unit"><hr class="se-hr"></div></div></div></div>'''


def get_quotation_html(text: str):
    """인용구 HTML (기본 스타일)"""
    comp_id = generate_uuid()
    quote_module_id = generate_uuid()
    quote_para_id = generate_uuid()
    quote_span_id = generate_uuid()
    cite_module_id = generate_uuid()
    cite_para_id = generate_uuid()
    cite_span_id = generate_uuid()

    return f'''<div class="se-component se-quotation se-l-default" id="{comp_id}" data-compid="{comp_id}" data-a11y-title="인용구"><div class="se-component-content"><div class="se-section se-section-quotation se-l-default se-section-align-left __se-unit"><div class="se-quotation-container"><div id="{quote_module_id}" class="se-module se-module-text __se-unit se-quote"><p id="{quote_para_id}" class="se-text-paragraph se-text-paragraph-align-center" style="line-height: 1.8;"><span id="{quote_span_id}" class="se-ff-nanummyeongjo se-fs19 __se-node" style="color: rgb(0, 0, 0);"><i>{text}</i></span></p></div><div id="{cite_module_id}" class="se-module se-module-text __se-unit se-is-empty se-cite"><p id="{cite_para_id}" class="se-text-paragraph se-text-paragraph-align-center" style="line-height: 1.5;"><span id="{cite_span_id}" class="se-ff-nanumgothic se-fs13 __se-node" style="color: rgb(119, 119, 119);"></span></p></div></div></div></div></div>'''


def get_table_html(rows: int = 3, cols: int = 3, cell_data: Optional[List[List[str]]] = None):
    """표 HTML

    Args:
        rows: 행 수
        cols: 열 수
        cell_data: 2D 리스트로 셀 데이터 (없으면 빈 셀)
    """
    comp_id = generate_uuid()
    cell_width = round(100 / cols)
    tbody_html = ""

    for r in range(rows):
        row_id = generate_uuid()
        cells_html = ""
        for c in range(cols):
            cell_id = generate_uuid()
            text_id = generate_uuid()
            para_id = generate_uuid()
            span_id = generate_uuid()

            if cell_data and r < len(cell_data) and c < len(cell_data[r]):
                cell_text = cell_data[r][c]
                empty_class = ""
            else:
                cell_text = ""
                empty_class = " se-is-empty"

            cells_html += f'''<td id="{cell_id}" colspan="1" rowspan="1" class="__se-unit se-cell" style="width: {cell_width}%; height: 43px;"><div id="{text_id}" class="se-module se-module-text{empty_class}"><p id="{para_id}" class="se-text-paragraph se-text-paragraph-align-left" style="line-height: 1.6;"><span id="{span_id}" class="se-ff-nanumgothic se-fs15 __se-node" style="color: rgb(0, 0, 0);">{cell_text}</span></p></div></td>'''
        tbody_html += f'<tr class="se-tr" id="{row_id}">{cells_html}</tr>'

    return f'''<div class="se-component se-table se-l-default" id="{comp_id}" data-compid="{comp_id}" data-a11y-title="표"><div class="se-component-content"><div class="se-section se-section-table se-l-default se-section-align-left" style="width: 100%;"><div class="se-table-container"><table class="se-table-content"><tbody>{tbody_html}</tbody></table></div></div></div></div>'''


def parse_table_marker(marker_content: str) -> Tuple[int, int, Optional[List[List[str]]]]:
    """표 마커 파싱

    Args:
        marker_content: 마커 내용
            - "3x4" 형식 (빈 표)
            - "셀1<C>셀2<R>셀3<C>셀4" 형식 (새 구분자)
            - "헤더1,헤더2|데이터1,데이터2" 형식 (레거시)

    Returns:
        (rows, cols, cell_data)
    """
    # 패턴 1: "3x4" 형식 (빈 표)
    size_match = re.match(r'^(\d+)x(\d+)$', marker_content.strip())
    if size_match:
        rows = int(size_match.group(1))
        cols = int(size_match.group(2))
        return (rows, cols, None)

    # 패턴 2: 새 구분자 "<C>", "<R>" 형식
    if '<R>' in marker_content or '<C>' in marker_content:
        rows_data = marker_content.split('<R>')
        cell_data = []
        max_cols = 0
        for row_str in rows_data:
            cells = [c.strip() for c in row_str.split('<C>')]
            cell_data.append(cells)
            max_cols = max(max_cols, len(cells))

        return (len(cell_data), max_cols, cell_data)

    # 패턴 3: 레거시 ",", "|" 형식 (하위 호환)
    if '|' in marker_content or ',' in marker_content:
        rows_data = marker_content.split('|')
        cell_data = []
        max_cols = 0
        for row_str in rows_data:
            cells = [c.strip() for c in row_str.split(',')]
            # 이스케이프된 전각 문자 복원
            cells = [c.replace('，', ',').replace('｜', '|') for c in cells]
            cell_data.append(cells)
            max_cols = max(max_cols, len(cells))

        return (len(cell_data), max_cols, cell_data)

    # 기본값
    return (3, 3, None)


def parse_markdown_table(table_text: str) -> Tuple[int, int, List[List[str]]]:
    """마크다운 표 파싱

    Args:
        table_text: 마크다운 표 텍스트
        예: | 헤더1 | 헤더2 |
            | 데이터1 | 데이터2 |

    Returns:
        (rows, cols, cell_data)
    """
    lines = [l.strip() for l in table_text.strip().split('\n') if l.strip()]
    cell_data = []

    for line in lines:
        # | 로 시작하고 끝나면 제거
        if line.startswith('|'):
            line = line[1:]
        if line.endswith('|'):
            line = line[:-1]

        # --- 구분자 행 건너뛰기
        if re.match(r'^[\s\-|]+$', line):
            continue

        cells = [c.strip() for c in line.split('|')]
        if cells:
            cell_data.append(cells)

    if not cell_data:
        return (3, 3, None)

    rows = len(cell_data)
    cols = max(len(row) for row in cell_data)

    return (rows, cols, cell_data)


class ComponentMarkerProcessor:
    """컴포넌트 마커 처리기"""

    # 마커 패턴
    HR_PATTERN = r'\{hr\}'
    QUOTE_PATTERN = r'\{quote:([^}]+)\}'
    TABLE_PATTERN = r'\{table:([^}]+)\}'
    MARKDOWN_TABLE_PATTERN = r'(\|[^\n]+\|\n?)+'

    @classmethod
    def find_all_markers(cls, content: str) -> List[dict]:
        """모든 컴포넌트 마커 찾기

        Returns:
            [{'type': 'hr'|'quote'|'table', 'match': str, 'start': int, 'end': int, 'data': ...}, ...]
        """
        markers = []

        # 구분선 마커
        for match in re.finditer(cls.HR_PATTERN, content):
            markers.append({
                'type': 'hr',
                'match': match.group(0),
                'start': match.start(),
                'end': match.end(),
                'data': None
            })

        # 인용구 마커
        for match in re.finditer(cls.QUOTE_PATTERN, content):
            markers.append({
                'type': 'quote',
                'match': match.group(0),
                'start': match.start(),
                'end': match.end(),
                'data': match.group(1)  # 인용구 텍스트
            })

        # 표 마커
        for match in re.finditer(cls.TABLE_PATTERN, content):
            markers.append({
                'type': 'table',
                'match': match.group(0),
                'start': match.start(),
                'end': match.end(),
                'data': match.group(1)  # 표 데이터
            })

        # 마크다운 표 (| 로 시작하는 연속 행)
        for match in re.finditer(cls.MARKDOWN_TABLE_PATTERN, content):
            table_text = match.group(0)
            # 최소 2행 이상이어야 표로 인식
            if table_text.count('\n') >= 1 or table_text.count('|') >= 3:
                markers.append({
                    'type': 'markdown_table',
                    'match': match.group(0),
                    'start': match.start(),
                    'end': match.end(),
                    'data': table_text
                })

        # 위치순 정렬
        markers.sort(key=lambda x: x['start'])

        return markers

    @classmethod
    def get_component_html(cls, marker: dict) -> str:
        """마커에 해당하는 HTML 컴포넌트 생성"""
        if marker['type'] == 'hr':
            return get_horizontal_line_html()

        elif marker['type'] == 'quote':
            return get_quotation_html(marker['data'])

        elif marker['type'] == 'table':
            rows, cols, cell_data = parse_table_marker(marker['data'])
            return get_table_html(rows, cols, cell_data)

        elif marker['type'] == 'markdown_table':
            rows, cols, cell_data = parse_markdown_table(marker['data'])
            return get_table_html(rows, cols, cell_data)

        return ''

    @classmethod
    def remove_markers(cls, content: str) -> str:
        """모든 컴포넌트 마커 제거"""
        content = re.sub(cls.HR_PATTERN, '', content)
        content = re.sub(cls.QUOTE_PATTERN, '', content)
        content = re.sub(cls.TABLE_PATTERN, '', content)
        content = re.sub(cls.MARKDOWN_TABLE_PATTERN, '', content)
        return content
