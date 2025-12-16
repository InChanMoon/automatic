"""
RSS 원본 확인
"""

import sys
import io
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# RSS Atom 가져오기
blog_id = 'sunny12221'
rss_url = f"https://rss.blog.naver.com/{blog_id}.xml?atom=0.3"

print(f"RSS URL: {rss_url}\n")

response = requests.get(rss_url, timeout=10)
response.raise_for_status()

# 처음 3000자만 출력
print("RSS 응답 (처음 3000자):")
print("=" * 80)
print(response.text[:3000])
print("=" * 80)
