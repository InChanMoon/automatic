"""
콘텐츠 파싱 유틸리티

제목/본문 파싱, 이미지 마커 처리 등 공통 기능
"""

import re
from typing import Dict, List, Tuple


def parse_title_and_content(text: str) -> Dict[str, str]:
    """
    AI 생성 텍스트에서 제목과 본문 분리

    Args:
        text: "제목: xxx\n본문: yyy" 형식의 텍스트

    Returns:
        dict: {'title': str, 'content': str}
    """
    lines = text.strip().split('\n')

    title = ''
    content_lines = []
    in_content = False
    title_line_idx = -1

    for idx, line in enumerate(lines):
        if line.startswith('제목:'):
            title = line.replace('제목:', '').strip()
            title_line_idx = idx
        elif line.startswith('본문:'):
            in_content = True
        elif in_content:
            content_lines.append(line)

    content = '\n'.join(content_lines).strip()

    # 제목이 추출되지 않은 경우 첫 줄 사용
    if not title and lines:
        title = lines[0]

    # 본문이 추출되지 않은 경우
    if not content:
        filtered_lines = []
        for idx, line in enumerate(lines):
            if idx == title_line_idx:
                continue
            if line.strip().startswith('제목:') or line.strip() == '본문:':
                continue
            filtered_lines.append(line)
        content = '\n'.join(filtered_lines).strip()

    # 그래도 없으면 전체 텍스트
    if not content:
        content = text

    return {'title': title, 'content': content}


def extract_image_markers(content: str) -> List[Dict]:
    """
    본문에서 이미지 마커 추출

    Args:
        content: 이미지 마커가 포함된 본문 ({img:1}, {img:1-5})

    Returns:
        list: [{'full_match': str, 'start': int, 'end': int, 'pos': int}, ...]
    """
    marker_pattern = r'\{img:(\d+)(?:-(\d+))?\}'
    markers = []

    for match in re.finditer(marker_pattern, content):
        start_num = int(match.group(1))
        end_num = int(match.group(2)) if match.group(2) else start_num
        markers.append({
            'full_match': match.group(0),
            'start': start_num,
            'end': end_num,
            'pos': match.start()
        })

    return markers


def remove_image_markers(content: str) -> str:
    """
    본문에서 이미지 마커 제거

    Args:
        content: 이미지 마커가 포함된 본문

    Returns:
        str: 마커가 제거된 본문
    """
    pattern = r'\{img:\d+(?:-\d+)?\}'
    return re.sub(pattern, '', content)


def safe_int(value, default: int = 0) -> int:
    """
    안전한 int 변환

    Args:
        value: 변환할 값
        default: 변환 실패 시 기본값

    Returns:
        int: 변환된 정수 또는 기본값
    """
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def escape_js_string(s: str) -> str:
    """
    JavaScript 문자열 이스케이프

    Args:
        s: 원본 문자열

    Returns:
        str: 이스케이프된 문자열
    """
    if not s:
        return ''
    return (s
            .replace('\\', '\\\\')
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace('\n', '\\n')
            .replace('\r', '\\r'))
