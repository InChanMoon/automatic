"""
고급 콘텐츠 생성기

사용자 정의 프롬프트 지원
"""

import json
import google.generativeai as genai


class AdvancedContentGenerator:
    """고급 콘텐츠 생성 클래스 - 사용자 프롬프트 지원"""

    def __init__(self, config_path="config.json"):
        """초기화"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        api_key = config['gemini_api']['api_key']

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')  # 최신 안정 버전 (2025년 6월)

    def generate_with_custom_prompt(self, user_prompt, original_text=None):
        """
        사용자 정의 프롬프트로 콘텐츠 생성

        Args:
            user_prompt: 사용자가 작성한 프롬프트
            original_text: 원본 글 (리라이팅 시 제공)

        Returns:
            dict: {
                'title': str,
                'content': str
            }
        """
        # 프롬프트 조합
        if original_text:
            # 리라이팅 모드
            full_prompt = f"""{user_prompt}

[원본 글]
{original_text}

출력 형식:
제목: [여기에 제목]

본문:
[여기에 본문]
"""
        else:
            # 새로 작성 모드
            full_prompt = f"""{user_prompt}

출력 형식:
제목: [여기에 제목]

본문:
[여기에 본문]
"""

        try:
            response = self.model.generate_content(full_prompt)
            text = response.text

            # 제목과 본문 분리
            title, content = self._parse_response(text)

            return {
                'title': title,
                'content': content
            }

        except Exception as e:
            print(f"❌ Gemini API 오류: {e}")
            return {
                'title': '콘텐츠 생성 오류',
                'content': f'오류가 발생했습니다: {str(e)}'
            }

    def rewrite_article(self, original_text, tone_instruction=""):
        """
        글 리라이팅 (yatpor 사기 스타일)

        Args:
            original_text: 원본 글
            tone_instruction: 말투 지시 (예: "친근한 말투로", "전문적인 말투로")

        Returns:
            dict: {
                'title': str,
                'content': str
            }
        """
        default_tone = "자연스럽고 읽기 쉬운 말투로" if not tone_instruction else tone_instruction

        prompt = f"""다음 글을 리라이팅해주세요.

요구사항:
1. 문단 및 구조는 원본과 동일하게 유지
2. 말투 어미를 {default_tone} 새롭게 수정 (조금 길게)
3. 조사를 중간중간 수정
4. 의미는 동일하게 유지
5. 자연스럽게 읽히도록
6. 중요: 설명이나 부가 설명 없이 오직 수정된 글만 출력하세요

[원본 글]
{original_text}

출력 형식:
제목: [여기에 제목]

본문:
[여기에 본문]

※ 주의: "리라이팅했습니다", "수정했습니다" 같은 답변은 절대 포함하지 마세요. 오직 제목과 본문만 출력하세요.
"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text

            title, content = self._parse_response(text)

            return {
                'title': title,
                'content': content
            }

        except Exception as e:
            print(f"❌ Gemini API 오류: {e}")
            return {
                'title': '리라이팅 오류',
                'content': f'오류가 발생했습니다: {str(e)}'
            }

    def generate_with_template(self, keyword, template_type='default'):
        """
        템플릿 기반 생성 (소액결제현금화 스타일)

        Args:
            keyword: 키워드
            template_type: 템플릿 종류
                - 'default': 기본 설명
                - 'pros_cons': 장단점
                - 'seo': SEO 최적화
                - 'with_subtitles': 소제목 포함
                - 'guide': 가이드 형식

        Returns:
            dict: {
                'title': str,
                'content': str
            }
        """
        templates = {
            'default': f"{keyword}를 설명하는 글을 1000자 내외로 써줘",

            'pros_cons': f"{keyword}의 장단점을 1000자 내외로 써줘. 장점 3개, 단점 3개 형식으로",

            'seo': f"{keyword}를 설명하는 SEO 용도의 글을 1000자 내외로 작성해줘. 키워드를 자연스럽게 여러 번 포함",

            'with_subtitles': f"{keyword}를 설명하는 글을 소제목 있는 형태로 1000자 내외로 써줘. 소제목은 ### 사용",

            'guide': f"{keyword} 완벽 가이드를 1000자 내외로 작성해줘. 초보자도 이해하기 쉽게"
        }

        user_prompt = templates.get(template_type, templates['default'])

        prompt = f"""{user_prompt}

출력 형식:
제목: [여기에 제목]

본문:
[여기에 본문]
"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text

            title, content = self._parse_response(text)

            return {
                'title': title,
                'content': content
            }

        except Exception as e:
            print(f"❌ Gemini API 오류: {e}")
            return {
                'title': f'{keyword} 관련 정보',
                'content': f'오류가 발생했습니다: {str(e)}'
            }

    def _parse_response(self, text):
        """
        응답 파싱 (제목과 본문 분리)

        Args:
            text: Gemini 응답 텍스트

        Returns:
            tuple: (title, content)
        """
        lines = text.strip().split('\n')

        title = ''
        content_lines = []
        in_content = False

        for line in lines:
            if line.startswith('제목:'):
                title = line.replace('제목:', '').strip()
            elif line.startswith('본문:'):
                in_content = True
            elif in_content:
                content_lines.append(line)

        content = '\n'.join(content_lines).strip()

        # 제목이 추출되지 않은 경우
        if not title:
            # 첫 줄을 제목으로 사용
            title = lines[0].strip() if lines else '제목 없음'

        # 본문이 추출되지 않은 경우
        if not content:
            # 전체 텍스트를 본문으로 사용 (제목 제외)
            content = '\n'.join(lines[1:]).strip() if len(lines) > 1 else text

        return title, content
