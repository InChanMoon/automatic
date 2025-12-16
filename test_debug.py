"""
디버깅
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

# se-component 찾기
pos = 0
comp_num = 0

while True:
    comp_match = re.search(r'<div class="se-component\s+se-(\w+)', container_html[pos:])

    if not comp_match:
        break

    comp_num += 1
    comp_type = comp_match.group(1)
    start_pos = pos + comp_match.start()

    # component 끝 찾기
    next_comp = re.search(r'<div class="se-component', container_html[start_pos + 10:])

    if next_comp:
        end_pos = start_pos + 10 + next_comp.start()
    else:
        end_pos = len(container_html)

    comp_html = container_html[start_pos:end_pos]

    print(f"Component #{comp_num}: {comp_type}")

    if comp_type == 'text':
        print(f"  길이: {len(comp_html)} 문자")
        print(f"  미리보기:")
        print("  " + "=" * 70)
        print("  " + comp_html[:500].replace('\n', '\n  '))
        print("  " + "=" * 70)

    pos = end_pos

print(f"\n총 {comp_num}개 컴포넌트")
