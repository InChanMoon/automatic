"""
OpenAI GPT API 콘텐츠 생성기

키워드 → 블로그 글 생성
"""

import sys
import os
import json
from openai import OpenAI
from src.utils.content_parser import parse_title_and_content
from src.utils.retry import retry_with_backoff


def _get_resource_path(relative_path):
    """PyInstaller EXE 호환 리소스 경로"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)


class GPTGenerator:
    """OpenAI GPT API 콘텐츠 생성 클래스"""

    def __init__(self, config_path=None):
        """
        초기화

        Args:
            config_path: config.json 경로 (None이면 자동 탐색)
        """
        if config_path is None:
            config_path = _get_resource_path('config.json')

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        api_key = config['openai_api']['api_key']

        # OpenAI 클라이언트 생성
        self.client = OpenAI(api_key=api_key)
        self.model_name = 'gpt-4o-mini'  # 가성비 좋은 모델

    def generate_blog_post(self, keyword):
        """
        키워드로부터 블로그 글 생성

        Args:
            keyword: 키워드

        Returns:
            dict: {
                'title': str,
                'content': str
            }
        """
        prompt = f"""
당신은 전문 블로그 작가입니다. 다음 키워드를 주제로 네이버 블로그 글을 작성해주세요.

키워드: {keyword}

요구사항:
1. 제목: 클릭을 유도하는 매력적인 제목 (30자 이내)
2. 본문:
   - 자연스럽고 읽기 쉬운 한국어
   - 1000자 이상
   - 소제목 2-3개 포함 (### 사용)
   - 실용적인 정보 제공
   - SEO 최적화 (키워드 자연스럽게 포함)
   - 이미지 삽입 위치에 마커 포함: {{img:시작번호-끝번호}} 또는 {{img:번호}}
     예: {{img:1-3}} = 1~3번 이미지 삽입, {{img:4}} = 4번 이미지만 삽입
   - 본문 중간중간에 이미지 마커를 2-4개 자연스럽게 배치
3. 형식:
   - 제목과 본문을 명확히 구분
   - 본문은 마크다운 형식

출력 형식:
제목: [여기에 제목]

본문:
[여기에 본문]
"""

        try:
            # API 호출 (재시도 로직 적용)
            @retry_with_backoff(max_attempts=3, initial_delay=2.0, backoff_factor=2.0)
            def _call_api():
                return self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "당신은 전문 블로그 작가입니다."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.7
                )

            response = _call_api()
            text = response.choices[0].message.content

            # 공통 파싱 유틸리티 사용
            result = parse_title_and_content(text)

            # 제목이 추출되지 않은 경우 대체
            if not result['title']:
                result['title'] = f"{keyword}에 대한 완벽 가이드"

            return result

        except Exception as e:
            print(f"[X] GPT API 오류: {e}")
            return {
                'title': f"{keyword} 관련 정보",
                'content': f"죄송합니다. 콘텐츠 생성 중 오류가 발생했습니다.\n\n키워드: {keyword}"
            }

    def generate_with_custom_prompt(self, user_prompt, original_text=None):
        """
        사용자 프롬프트로 콘텐츠 생성

        Args:
            user_prompt: 사용자 프롬프트
            original_text: 원본 텍스트 (리라이팅 시)

        Returns:
            dict: {'title': str, 'content': str}
        """
        if original_text:
            prompt = f"""{user_prompt}

원본 텍스트:
{original_text}

출력 형식:
제목: [여기에 제목]

본문:
[여기에 본문]
"""
        else:
            prompt = f"""{user_prompt}

출력 형식:
제목: [여기에 제목]

본문:
[여기에 본문]
"""

        try:
            # API 호출 (재시도 로직 적용)
            @retry_with_backoff(max_attempts=3, initial_delay=2.0, backoff_factor=2.0)
            def _call_api():
                return self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "당신은 전문 블로그 작가입니다."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.7
                )

            response = _call_api()
            text = response.choices[0].message.content

            # 공통 파싱 유틸리티 사용
            result = parse_title_and_content(text)

            # 제목이 없으면 기본값
            if not result['title']:
                result['title'] = "생성된 글"

            return result

        except Exception as e:
            print(f"[X] GPT API 오류: {e}")
            return {
                'title': "생성 실패",
                'content': f"콘텐츠 생성 중 오류가 발생했습니다.\n오류: {e}"
            }

    def generate_image_description(self, keyword):
        """
        키워드에 맞는 이미지 설명 생성 (이미지 검색용)

        Args:
            keyword: 키워드

        Returns:
            str: 이미지 검색어
        """
        prompt = f"""
다음 키워드와 관련된 블로그 글에 사용할 이미지 검색어를 1개 생성해주세요.

키워드: {keyword}

출력: 검색어만 한 줄로
"""

        try:
            # API 호출 (재시도 로직 적용)
            @retry_with_backoff(max_attempts=3, initial_delay=2.0, backoff_factor=2.0)
            def _call_api():
                return self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=50,
                    temperature=0.7
                )

            response = _call_api()
            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"[X] GPT API 오류: {e}")
            return keyword  # 기본값으로 키워드 사용
