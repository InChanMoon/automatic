"""
사용 가능한 Gemini 모델 확인
"""

import json
import google.generativeai as genai

# config.json에서 API 키 로드
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

api_key = config['gemini_api']['api_key']

# Gemini API 설정
genai.configure(api_key=api_key)

print("\n" + "="*60)
print("사용 가능한 Gemini 모델 목록")
print("="*60)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"\n모델명: {model.name}")
        print(f"  설명: {model.description}")
        print(f"  지원 메서드: {model.supported_generation_methods}")
