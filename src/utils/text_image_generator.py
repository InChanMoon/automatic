# -*- coding: utf-8 -*-
"""
텍스트 → 이미지 변환 유틸리티
- 제목 이미지 생성 (항상)
- 단락 첫 문장 이미지 생성 (단락 구조 있을 때)
"""
from PIL import Image, ImageDraw, ImageFont
import os
import re
import random
import tempfile
from typing import List, Tuple, Optional


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """한글 폰트 로드"""
    font_paths = [
        "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/NanumGothicBold.ttf" if bold else "C:/Windows/Fonts/NanumGothic.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    return ImageFont.load_default()


# 색상 팔레트 (배경색, 강조색, 글자색, 보조색)
COLOR_PALETTES = [
    # 다크 계열 (밝은 글자)
    {"bg": "#1a1a2e", "accent": "#e94560", "text": "#FFFFFF", "sub": "#0f3460"},
    {"bg": "#16213e", "accent": "#e94560", "text": "#FFFFFF", "sub": "#0f3460"},
    {"bg": "#1f1f1f", "accent": "#ff6b6b", "text": "#FFFFFF", "sub": "#4ecdc4"},
    {"bg": "#2d3436", "accent": "#74b9ff", "text": "#FFFFFF", "sub": "#0984e3"},
    {"bg": "#192a56", "accent": "#f7dc6f", "text": "#FFFFFF", "sub": "#3498db"},
    # 라이트 계열 (어두운 글자)
    {"bg": "#f5f5f5", "accent": "#e94560", "text": "#333333", "sub": "#666666"},
    {"bg": "#fff9e6", "accent": "#ff9f43", "text": "#333333", "sub": "#ee5a24"},
    {"bg": "#e8f4f8", "accent": "#0984e3", "text": "#2d3436", "sub": "#74b9ff"},
]


def create_text_image(
    text: str,
    style: str = "random",
    width: int = 800,
    height: int = 200
) -> str:
    """
    텍스트를 이미지로 변환

    Args:
        text: 이미지에 넣을 텍스트
        style: 스타일 ("minimal", "quote", "random")
        width: 이미지 너비
        height: 이미지 높이

    Returns:
        생성된 이미지 파일 경로 (임시 파일)
    """
    if style == "random":
        style = random.choice(["minimal", "quote"])

    if style == "minimal":
        return _create_minimal_style(text, width, height)
    elif style == "quote":
        return _create_quote_style(text, width, height)
    else:
        return _create_minimal_style(text, width, height)


def _wrap_text(text: str, max_chars_per_line: int = 35) -> str:
    """텍스트를 적절한 위치에서 줄바꿈"""
    if len(text) <= max_chars_per_line:
        return text

    # 최대 2줄, 총 70자까지
    if len(text) > max_chars_per_line * 2:
        text = text[:max_chars_per_line * 2 - 3] + "..."

    # 중간 지점에서 공백/구두점 찾아서 줄바꿈
    mid = len(text) // 2

    # 중간 근처에서 줄바꿈 위치 찾기
    best_pos = mid
    for i in range(mid, max(0, mid - 10), -1):
        if text[i] in ' ,.:;!?':
            best_pos = i + 1
            break

    # 못 찾으면 중간에서 그냥 자르기
    if best_pos == mid:
        for i in range(mid, min(len(text), mid + 10)):
            if text[i] in ' ,.:;!?':
                best_pos = i + 1
                break

    line1 = text[:best_pos].strip()
    line2 = text[best_pos:].strip()

    return f"{line1}\n{line2}" if line2 else line1


def _create_minimal_style(text: str, width: int, height: int) -> str:
    """미니멀 스타일 이미지 생성"""
    # 밝거나 어두운 배경 랜덤
    is_dark = random.random() > 0.5
    if is_dark:
        bg_color = random.choice(["#1a1a1a", "#2d2d2d", "#1e272e"])
        text_color = "#FFFFFF"
        accent = random.choice(["#e94560", "#74b9ff", "#00b894", "#fdcb6e"])
    else:
        bg_color = random.choice(["#FFFFFF", "#f8f9fa", "#f1f2f6"])
        text_color = "#2d3436"
        accent = random.choice(["#e94560", "#0984e3", "#00b894", "#e17055"])

    # 2줄 텍스트를 위해 높이 조정
    actual_height = height + 50 if len(text) > 40 else height

    img = Image.new('RGB', (width, actual_height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # 심플한 테두리 또는 하단 라인
    if random.random() > 0.5:
        draw.rectangle([(0, 0), (width-1, actual_height-1)], outline=accent, width=3)
    else:
        draw.rectangle([(50, actual_height-20), (width-50, actual_height-16)], fill=accent)

    # 텍스트 줄바꿈 처리 (한 줄에 40자, 최대 80자)
    display_text = _wrap_text(text, 40)

    font = get_font(24, bold=True)  # 더 많은 글자를 위해 폰트 줄임
    bbox = draw.textbbox((0, 0), display_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (actual_height - text_height) // 2 - 5

    draw.text((x, y), display_text, font=font, fill=text_color, align='center')

    # 임시 파일로 저장
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    img.save(temp_file.name)
    return temp_file.name


def _create_quote_style(text: str, width: int, height: int) -> str:
    """인용문 스타일 이미지 생성"""
    # 라이트 계열 선택
    light_palettes = [p for p in COLOR_PALETTES if p["text"] == "#333333"]
    palette = random.choice(light_palettes) if light_palettes else COLOR_PALETTES[-1]

    # 2줄 텍스트를 위해 높이 조정
    actual_height = height + 50 if len(text) > 40 else height

    img = Image.new('RGB', (width, actual_height), color=palette["bg"])
    draw = ImageDraw.Draw(img)

    # 왼쪽 강조 바
    bar_width = random.randint(6, 10)
    draw.rectangle([(0, 0), (bar_width, actual_height)], fill=palette["accent"])

    # 큰 따옴표
    quote_font = get_font(50, bold=True)
    draw.text((25, 10), '"', font=quote_font, fill=palette["accent"])
    draw.text((width - 50, actual_height - 70), '"', font=quote_font, fill=palette["accent"])

    # 텍스트 줄바꿈 처리 (한 줄에 40자, 최대 80자)
    display_text = _wrap_text(text, 40)

    font = get_font(22)  # 더 많은 글자를 위해 폰트 줄임
    bbox = draw.textbbox((0, 0), display_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (actual_height - text_height) // 2

    draw.text((x, y), display_text, font=font, fill=palette["text"], align='center')

    # 임시 파일로 저장
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    img.save(temp_file.name)
    return temp_file.name


def create_title_image(title: str, width: int = 800, height: int = 400) -> str:
    """
    제목 이미지 생성 (썸네일 스타일)

    Args:
        title: 글 제목
        width: 이미지 너비
        height: 이미지 높이

    Returns:
        생성된 이미지 파일 경로 (임시 파일)
    """
    palette = random.choice(COLOR_PALETTES)

    img = Image.new('RGB', (width, height), color=palette["bg"])
    draw = ImageDraw.Draw(img)

    # 장식 요소들 랜덤 선택
    decorations = random.sample(["top_bar", "circles", "corner_lines", "dots"], k=random.randint(2, 3))

    if "top_bar" in decorations:
        bar_height = random.randint(6, 12)
        draw.rectangle([(0, 0), (width, bar_height)], fill=palette["accent"])

    if "circles" in decorations:
        for _ in range(random.randint(2, 4)):
            x = random.randint(30, width - 80)
            y = random.randint(30, height - 80)
            size = random.randint(30, 60)
            if random.random() > 0.5:
                draw.ellipse([(x, y), (x+size, y+size)], fill=palette["accent"])
            else:
                draw.ellipse([(x, y), (x+size, y+size)], outline=palette["accent"], width=3)

    if "corner_lines" in decorations:
        line_len = random.randint(50, 100)
        draw.line([(0, height-30), (line_len, height-30)], fill=palette["accent"], width=3)
        draw.line([(width-line_len, 30), (width, 30)], fill=palette["accent"], width=3)

    if "dots" in decorations:
        for _ in range(random.randint(5, 15)):
            x = random.randint(0, width)
            y = random.randint(0, height)
            r = random.randint(2, 5)
            draw.ellipse([(x-r, y-r), (x+r, y+r)], fill=palette["sub"])

    # 메인 텍스트 (제목) - 2줄로 줄바꿈
    display_text = _wrap_text(title, 25)  # 제목은 폰트가 크므로 25자에서 줄바꿈

    font = get_font(36, bold=True)  # 2줄을 위해 폰트 크기 줄임
    bbox = draw.textbbox((0, 0), display_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2 - 20

    # 그림자 효과
    draw.text((x+2, y+2), display_text, font=font, fill="#00000044", align='center')
    draw.text((x, y), display_text, font=font, fill=palette["text"], align='center')

    # 임시 파일로 저장
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    img.save(temp_file.name)
    return temp_file.name


def extract_first_sentence(paragraph: str) -> str:
    """단락에서 첫 문장 추출"""
    # 문장 종결 기호로 분리
    for end_char in ['.', '!', '?', '다.', '요.', '죠.']:
        if end_char in paragraph:
            idx = paragraph.index(end_char) + len(end_char)
            sentence = paragraph[:idx].strip()
            if len(sentence) > 10:  # 너무 짧으면 스킵
                return sentence

    # 종결 기호 없으면 앞부분 사용
    return paragraph[:50].strip() if len(paragraph) > 50 else paragraph.strip()


def has_paragraph_structure(content: str) -> bool:
    """
    단락 구조가 있는지 확인

    Args:
        content: 본문 내용

    Returns:
        단락 구조 여부 (2개 이상의 빈 줄로 구분된 단락이 있으면 True)
    """
    # 이미지 마커 제거
    import re
    clean_content = re.sub(r'\{img:\d+(?:-\d+)?\}', '', content)

    # 연속 줄바꿈으로 분리
    paragraphs = [p.strip() for p in clean_content.split('\n\n') if p.strip()]

    # 2개 이상의 단락이 있어야 단락 구조로 인정
    return len(paragraphs) >= 2


def parse_image_markers(content: str) -> Tuple[int, List[dict]]:
    """
    본문에서 이미지 마커를 파싱하여 필요한 이미지 개수 계산

    Args:
        content: 본문 내용

    Returns:
        (필요한 최대 이미지 번호, 마커 정보 리스트)
    """
    marker_pattern = r'\{img:(\d+)(?:-(\d+))?\}'
    markers = []
    max_img_num = 0

    for match in re.finditer(marker_pattern, content):
        start_num = int(match.group(1))
        end_num = int(match.group(2)) if match.group(2) else start_num

        markers.append({
            'full_match': match.group(0),
            'start': start_num,
            'end': end_num,
            'position': match.start()
        })

        max_img_num = max(max_img_num, end_num)

    return max_img_num, markers


def generate_images_from_markers(
    title: str,
    content: str
) -> Tuple[str, List[str]]:
    """
    마커 기반 이미지 자동 생성 (자동생성 옵션용)

    - 본문의 기존 마커를 파싱하여 필요한 이미지 개수 파악
    - 마커가 없으면 이미지 생성하지 않음 (본문 그대로 반환)
    - 1번 이미지: 제목 이미지
    - 2번~ 이미지: 단락 첫 문장 이미지 (단락 구조 있을 때)
    - 단락 부족 시 초과 마커 제거

    Args:
        title: 글 제목
        content: 본문 내용 (마커 포함: {img:1}, {img:1-5} 등)

    Returns:
        (수정된 본문, 이미지 경로 리스트)
    """
    # 1. 마커 파싱
    max_img_num, markers = parse_image_markers(content)

    # 마커가 없으면 이미지 생성하지 않음
    if max_img_num == 0:
        return content, []

    generated_images = []

    # 2. 1번 이미지: 제목 이미지
    title_img = create_title_image(title)
    generated_images.append(title_img)

    # 3. 2번~ 이미지: 단락 첫 문장 이미지
    if max_img_num >= 2:
        # 단락 구조 확인
        if has_paragraph_structure(content):
            # 마커 제거한 본문에서 단락 추출
            clean_content = re.sub(r'\{img:\d+(?:-\d+)?\}\s*', '', content)
            paragraphs = [p.strip() for p in clean_content.split('\n\n') if p.strip()]

            # 2번부터 필요한 만큼 이미지 생성
            for i in range(2, max_img_num + 1):
                para_idx = i - 2  # 2번 → 0번 단락, 3번 → 1번 단락...

                if para_idx < len(paragraphs):
                    # 단락에서 첫 문장 추출
                    first_sentence = extract_first_sentence(paragraphs[para_idx])
                    if first_sentence and len(first_sentence) > 10:
                        img_path = create_text_image(first_sentence, style="random")
                        generated_images.append(img_path)
                    else:
                        # 문장이 너무 짧으면 None 추가 (나중에 마커 제거)
                        generated_images.append(None)
                else:
                    # 단락 부족 → None 추가
                    generated_images.append(None)
        else:
            # 단락 구조 없으면 2번 이후 모두 None
            for _ in range(2, max_img_num + 1):
                generated_images.append(None)

    # 4. 생성된 이미지 개수 확인
    actual_image_count = sum(1 for img in generated_images if img is not None)

    # 5. 초과 마커 수정/제거
    modified_content = content

    for marker in sorted(markers, key=lambda x: x['position'], reverse=True):
        # 마커 범위 중 사용 가능한 부분만 남기기
        new_start = marker['start']
        new_end = min(marker['end'], actual_image_count)

        if new_start > actual_image_count:
            # 마커 전체가 범위 초과 → 제거
            modified_content = modified_content.replace(marker['full_match'], '')
        elif new_end < marker['end']:
            # 일부만 사용 가능 → 범위 수정
            if new_start == new_end:
                new_marker = f"{{img:{new_start}}}"
            else:
                new_marker = f"{{img:{new_start}-{new_end}}}"
            modified_content = modified_content.replace(marker['full_match'], new_marker)

    # 6. None 제거하고 실제 이미지만 반환
    valid_images = [img for img in generated_images if img is not None]

    # 빈 줄 정리 (마커 제거로 인한 연속 빈 줄)
    modified_content = re.sub(r'\n{3,}', '\n\n', modified_content)

    return modified_content, valid_images


def generate_auto_images_for_publish(
    title: str,
    content: str,
    max_paragraph_images: int = 10
) -> Tuple[str, List[str]]:
    """
    마커 기반 이미지 자동 생성 (발행용)

    - 마커가 있으면: 마커 개수대로 이미지 생성
    - 마커가 없으면: 이미지 생성하지 않음 (본문 그대로 반환)

    Args:
        title: 글 제목
        content: 본문 내용
        max_paragraph_images: 최대 단락 이미지 수 (미사용, 호환성 유지)

    Returns:
        (수정된 본문, 이미지 경로 리스트)
    """
    return generate_images_from_markers(title, content)


def cleanup_temp_images(image_paths: List[str]):
    """임시 이미지 파일 정리"""
    for path in image_paths:
        try:
            if os.path.exists(path) and 'tmp' in path.lower():
                os.remove(path)
        except:
            pass
