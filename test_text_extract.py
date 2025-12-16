"""
텍스트 추출 디버그
"""

import sys
import io
import re
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

url = 'https://blog.naver.com/sunny12221/224107556066'

# iframe URL 가져오기
resp = requests.get(url)
iframe_match = re.search(r'<iframe[^>]+src="(/PostView\.naver[^"]+)"', resp.text)
iframe_url = f"https://blog.naver.com{iframe_match.group(1).replace('&amp;', '&')}"

# iframe HTML 가져오기
resp = requests.get(iframe_url)
html = resp.text

# se-main-container 찾기
container_match = re.search(r'<div class="se-main-container">(.*)', html, re.DOTALL)
container_html = container_match.group(1)

# se-text component 찾기
text_comps = re.findall(
    r'<div class="se-component\s+se-text[^>]*>(.*?)</div>\s*<script',
    container_html,
    re.DOTALL
)

print(f"텍스트 컴포넌트 개수: {len(text_comps)}\n")

if text_comps:
    print("첫 번째 텍스트 컴포넌트 (처음 2000자):")
    print("=" * 80)
    print(text_comps[0][:2000])
    print("=" * 80)
