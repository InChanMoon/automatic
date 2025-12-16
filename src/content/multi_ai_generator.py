"""
멀티 AI 생성기

Gemini, Claude 등 여러 AI를 통합 지원
"""

import json
from .advanced_generator import AdvancedContentGenerator
from .claude_generator import ClaudeGenerator


class MultiAIGenerator:
    """멀티 AI 생성기"""

    def __init__(self, config_path="config.json", ai_type='gemini'):
        """
        초기화

        Args:
            config_path: config.json 경로
            ai_type: 'gemini' 또는 'claude'
        """
        self.ai_type = ai_type
        self.config_path = config_path

        # AI 엔진 초기화
        if ai_type == 'gemini':
            self.generator = AdvancedContentGenerator(config_path)
        elif ai_type == 'claude':
            self.generator = ClaudeGenerator(config_path)
        else:
            raise ValueError(f"지원하지 않는 AI 타입: {ai_type}")

    def generate_with_custom_prompt(self, user_prompt, original_text=None):
        """사용자 정의 프롬프트로 생성"""
        return self.generator.generate_with_custom_prompt(user_prompt, original_text)

    def rewrite_article(self, original_text, tone_instruction=""):
        """글 리라이팅"""
        return self.generator.rewrite_article(original_text, tone_instruction)

    def generate_with_template(self, keyword, template_type='default'):
        """템플릿 기반 생성"""
        return self.generator.generate_with_template(keyword, template_type)

    def get_model_name(self):
        """현재 사용 중인 모델 이름 반환"""
        if self.ai_type == 'gemini':
            return "Gemini 2.5 Flash"
        elif self.ai_type == 'claude':
            return "Claude 3.5 Sonnet"
        return "Unknown"
