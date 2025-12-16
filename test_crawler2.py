"""
크롤러 테스트 - 사용자 제공 URL
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.crawler.naver_blog_crawler import NaverBlogCrawler

crawler = NaverBlogCrawler()

# 사용자가 제공한 예시 URL
url = 'https://blog.naver.com/sunny12221/224107556066'

print(f"테스트 URL: {url}\n")

result = crawler.parse_blog_post(url)

print(f"제목: {result['title']}\n")
print(f"본문 (처음 1000자):")
print("=" * 80)
print(result['content_with_markers'][:1000])
print("=" * 80)

import re
markers = re.findall(r'\[이미지\d+\]', result['content_with_markers'])
print(f"\n이미지 마커 개수: {len(markers)}개")
