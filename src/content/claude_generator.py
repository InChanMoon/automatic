"""
Claude API 콘텐츠 생성기

Anthropic Claude API 지원
"""

import json
import anthropic


class ClaudeGenerator:
    """Claude API 콘텐츠 생성 클래스"""

    def __init__(self, config_path="config.json"):
        """초기화"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Claude API 키 확인
        if 'claude_api' not in config or 'api_key' not in config['claude_api']:
            raise Exception("config.json에 claude_api.api_key가 설정되지 않았습니다")

        api_key = config['claude_api']['api_key']

        if not api_key or api_key == "YOUR_CLAUDE_API_KEY_HERE":
            raise Exception("Claude API 키를 설정하세요")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"  # 최신 Claude 모델

    def generate_with_custom_prompt(self, user_prompt, original_text=None):
        """
        사용자 정의 프롬프트로 콘텐츠 생성

        Args:
            user_prompt: 사용자 프롬프트
            original_text: 원본 글 (리라이팅 시)

        Returns:
            dict: {
                'title': str,
                'content': str
            }
        """
        if original_text:
            full_prompt = f"""{user_prompt}

[원본 글]
{original_text}

출력 형식:
제목: [여기에 제목]

본문:
[여기에 본문]
"""
        else:
            full_prompt = f"""{user_prompt}

출력 형식:
제목: [여기에 제목]

본문:
[여기에 본문]
"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": full_prompt}
                ]
            )

            text = message.content[0].text

            title, content = self._parse_response(text)

            return {
                'title': title,
                'content': content
            }

        except Exception as e:
            print(f"❌ Claude API 오류: {e}")
            return {
                'title': '콘텐츠 생성 오류',
                'content': f'오류가 발생했습니다: {str(e)}'
            }

    def rewrite_article(self, original_text, tone_instruction=""):
        """
        글 리라이팅

        Args:
            original_text: 원본 글
            tone_instruction: 말투 지시

        Returns:
            dict
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
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            text = message.content[0].text

            title, content = self._parse_response(text)

            return {
                'title': title,
                'content': content
            }

        except Exception as e:
            print(f"❌ Claude API 오류: {e}")
            return {
                'title': '리라이팅 오류',
                'content': f'오류가 발생했습니다: {str(e)}'
            }

    def generate_with_template(self, keyword, template_type='default'):
        """
        템플릿 기반 생성

        Args:
            keyword: 키워드
            template_type: 템플릿 종류

        Returns:
            dict
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
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            text = message.content[0].text

            title, content = self._parse_response(text)

            return {
                'title': title,
                'content': content
            }

        except Exception as e:
            print(f"❌ Claude API 오류: {e}")
            return {
                'title': f'{keyword} 관련 정보',
                'content': f'오류가 발생했습니다: {str(e)}'
            }

    def _parse_response(self, text):
        """응답 파싱"""
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

        if not title:
            title = lines[0].strip() if lines else '제목 없음'

        if not content:
            content = '\n'.join(lines[1:]).strip() if len(lines) > 1 else text

        return title, content
