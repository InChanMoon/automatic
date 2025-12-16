"""
HTML 구조 확인
"""

import sys
import io
import re
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

url = 'https://blog.naver.com/sunny12221/224107567534'

print(f"URL: {url}\n")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers, timeout=15)
response.raise_for_status()

html = response.text

# iframe URL 찾기
iframe_match = re.search(r'<iframe[^>]+src="(/PostView\.naver[^"]+)"', html)

if iframe_match:
    iframe_path = iframe_match.group(1).replace('&amp;', '&')
    iframe_url = f"https://blog.naver.com{iframe_path}"

    print(f"✅ iframe 발견: {iframe_url}\n")
    print("iframe HTML 가져오는 중...")

    response = requests.get(iframe_url, headers=headers, timeout=15)
    response.raise_for_status()

    html = response.text
    print("✅ iframe HTML 가져옴\n")
else:
    print("❌ iframe 없음\n")

# se-main-container 찾기
import re

container_match = re.search(
    r'<div class="se-main-container">(.*?)</div>\s*</div>',
    html,
    re.DOTALL
)

if container_match:
    print("✅ se-main-container 찾음!")
    container_html = container_match.group(1)
    print(f"\n컨테이너 길이: {len(container_html)} 문자")
    print(f"\n컨테이너 미리보기 (처음 2000자):")
    print("=" * 80)
    print(container_html[:2000])
    print("=" * 80)
else:
    print("❌ se-main-container를 찾을 수 없습니다")
    print("\nHTML 미리보기 (처음 3000자):")
    print("=" * 80)
    print(html[:3000])
    print("=" * 80)
