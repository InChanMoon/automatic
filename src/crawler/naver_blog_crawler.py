"""
네이버 블로그 크롤러

RSS Atom 피드 기반으로 글 목록 가져오기 + HTML 파싱
"""

import re
import xml.etree.ElementTree as ET
import requests
from urllib.parse import urlparse


class NaverBlogCrawler:
    """네이버 블로그 크롤러"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def get_blog_id_from_url(self, blog_url):
        """
        블로그 URL에서 블로그 ID 추출

        예: https://blog.naver.com/sunny12221 -> sunny12221
        예: https://blog.naver.com/sunny12221/224107556066 -> sunny12221
        """
        try:
            parsed = urlparse(blog_url)
            path_parts = parsed.path.strip('/').split('/')

            if len(path_parts) >= 1:
                return path_parts[0]

            return None
        except:
            return None

    def get_rss_feed(self, blog_id):
        """
        RSS Atom 피드 가져오기

        Args:
            blog_id: 블로그 ID (예: sunny12221)

        Returns:
            list: [{'title': str, 'link': str, 'published': str}, ...]
        """
        rss_url = f"https://rss.blog.naver.com/{blog_id}.xml?atom=0.3"

        try:
            response = requests.get(rss_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # XML 파싱
            root = ET.fromstring(response.content)

            # Atom 네임스페이스
            ns = {'atom': 'http://purl.org/atom/ns#'}

            entries = []

            for entry in root.findall('.//atom:entry', ns):
                title_elem = entry.find('atom:title', ns)
                link_elem = entry.find('atom:link', ns)
                issued_elem = entry.find('atom:issued', ns)

                if title_elem is not None and link_elem is not None:
                    # CDATA에서 링크 추출
                    link_text = link_elem.text or ''
                    # ?fromRss=true&trackingCode=rss 제거
                    link_text = link_text.split('?')[0]

                    entries.append({
                        'title': title_elem.text or '',
                        'link': link_text,
                        'published': issued_elem.text if issued_elem is not None else ''
                    })

            return entries

        except Exception as e:
            print(f"❌ RSS 피드 가져오기 실패: {e}")
            return []

    def find_post_by_keyword(self, blog_id, keyword):
        """
        RSS에서 키워드가 제목에 포함된 글 찾기

        Args:
            blog_id: 블로그 ID
            keyword: 검색 키워드 (대소문자 구분 없음)

        Returns:
            dict or None: {'title': str, 'link': str, 'published': str}
        """
        entries = self.get_rss_feed(blog_id)

        keyword_lower = keyword.lower()

        for entry in entries:
            if keyword_lower in entry['title'].lower():
                return entry

        return None

    def parse_blog_post(self, post_url):
        """
        블로그 글 본문 파싱

        Args:
            post_url: 글 URL

        Returns:
            dict: {
                'title': str,
                'content_with_markers': str  # [이미지1], [이미지2] 포함된 본문
            }
        """
        try:
            response = requests.get(post_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            html = response.text

            # iframe URL 찾기
            iframe_match = re.search(r'<iframe[^>]+src="(/PostView\.naver[^"]+)"', html)

            if iframe_match:
                iframe_path = iframe_match.group(1)
                # HTML 엔티티 디코딩
                iframe_path = iframe_path.replace('&amp;', '&')

                # iframe URL 가져오기
                iframe_url = f"https://blog.naver.com{iframe_path}"

                response = requests.get(iframe_url, headers=self.headers, timeout=15)
                response.raise_for_status()

                html = response.text

            # 제목 추출
            title = self._extract_title(html)

            # 본문 추출 (이미지 위치 포함)
            content_with_markers = self._extract_content_with_images(html)

            return {
                'title': title,
                'content_with_markers': content_with_markers
            }

        except Exception as e:
            print(f"❌ 글 파싱 실패: {e}")
            return {
                'title': '',
                'content_with_markers': ''
            }

    def _extract_title(self, html):
        """제목 추출"""
        # <p class="se-text-paragraph se-text-paragraph-align-" ...>제목 내용</p>
        # se-title-text 또는 se-documentTitle 내부

        match = re.search(
            r'<div class="se-module se-module-text se-title-text">.*?<p[^>]*>(.*?)</p>',
            html,
            re.DOTALL
        )

        if match:
            title_html = match.group(1)
            # <span> 태그 제거
            title = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', title_html)
            # HTML 주석 제거
            title = re.sub(r'<!--.*?-->', '', title)
            return title.strip()

        return ''

    def _extract_content_with_images(self, html):
        """본문 추출 (이미지 위치 포함)"""
        # se-main-container 내부 파싱

        container_match = re.search(
            r'<div class="se-main-container">(.*)',
            html,
            re.DOTALL
        )

        if not container_match:
            return ''

        container_html = container_match.group(1)

        # 각 component는 <script type="text/data" class="__se_module_data" ...로 끝남
        # 이걸 기준으로 분할

        # component + script 패턴으로 찾기
        component_blocks = re.split(r'(?=<div class="se-component\s+se-)', container_html)

        result = []
        image_count = 0

        for block in component_blocks:
            if not block.strip():
                continue

            # component 타입 파악
            type_match = re.search(r'<div class="se-component\s+se-(\w+)', block)

            if not type_match:
                continue

            comp_type = type_match.group(1)

            if comp_type == 'image':
                image_count += 1
                result.append(f'{{img:{image_count}}}')

            elif comp_type == 'text':
                # 텍스트 추출
                text = self._extract_text_from_component(block)
                if text.strip():
                    result.append(text)

            elif comp_type == 'quotation':
                # 인용문 추출
                text = self._extract_quotation(block)
                if text.strip():
                    result.append(f'> {text}')

            elif comp_type == 'table':
                # 표 추출
                text = self._extract_table(block)
                if text.strip():
                    result.append(text)

        # 연속 이미지 마커 압축
        result = self._compress_image_markers(result)

        return '\n\n'.join(result)

    def _compress_image_markers(self, items):
        """연속된 이미지 마커를 압축 (예: {img:1} {img:2} {img:3} -> {img:1-3})"""
        if not items:
            return items

        compressed = []
        i = 0

        while i < len(items):
            item = items[i]

            # 이미지 마커인지 확인
            match = re.match(r'\{img:(\d+)\}', item)
            if match:
                start_num = int(match.group(1))
                end_num = start_num

                # 연속된 이미지 마커 찾기
                j = i + 1
                while j < len(items):
                    next_match = re.match(r'\{img:(\d+)\}', items[j])
                    if next_match and int(next_match.group(1)) == end_num + 1:
                        end_num = int(next_match.group(1))
                        j += 1
                    else:
                        break

                # 압축된 마커 생성
                if start_num == end_num:
                    compressed.append(f'{{img:{start_num}}}')
                else:
                    compressed.append(f'{{img:{start_num}-{end_num}}}')

                i = j
            else:
                compressed.append(item)
                i += 1

        return compressed

    def _extract_text_from_component(self, comp_html):
        """텍스트 컴포넌트에서 텍스트 추출"""
        # HTML 주석 먼저 제거
        comp_html = re.sub(r'<!--.*?-->', '', comp_html, flags=re.DOTALL)

        lines = []

        # 1. 리스트(ul/li) 추출
        list_match = re.search(
            r'<ul[^>]*class="[^"]*se-text-list[^"]*"[^>]*>(.*?)</ul>',
            comp_html,
            re.DOTALL
        )

        if list_match:
            list_html = list_match.group(1)
            list_items = re.findall(r'<li[^>]*>(.*?)</li>', list_html, re.DOTALL)

            for li_html in list_items:
                # <p> 태그 찾기
                p_match = re.search(
                    r'<p[^>]*class="[^"]*se-text-paragraph[^"]*"[^>]*>(.*?)</p>',
                    li_html,
                    re.DOTALL
                )

                if p_match:
                    p_html = p_match.group(1)

                    # span 제거
                    while '<span' in p_html:
                        p_html = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', p_html, count=1, flags=re.DOTALL)

                    # 스타일 태그 보존
                    p_html = re.sub(r'<b>(.*?)</b>', r'**\1**', p_html)
                    p_html = re.sub(r'<i>(.*?)</i>', r'*\1*', p_html)
                    p_html = re.sub(r'<u>(.*?)</u>', r'_\1_', p_html)

                    # 나머지 태그 제거
                    text = re.sub(r'<[^>]+>', '', p_html)
                    text = self._decode_entities(text)

                    if text.strip():
                        lines.append(f'• {text.strip()}')

        else:
            # 2. 일반 문단(<p>) 추출
            paragraphs = re.findall(
                r'<p[^>]*class="[^"]*se-text-paragraph[^"]*"[^>]*>(.*?)</p>',
                comp_html,
                re.DOTALL
            )

            for p_html in paragraphs:
                # 중첩된 span 태그 반복 제거
                while '<span' in p_html:
                    p_html = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', p_html, count=1, flags=re.DOTALL)

                # <b>, <i>, <u> 등 보존
                p_html = re.sub(r'<b>(.*?)</b>', r'**\1**', p_html)
                p_html = re.sub(r'<i>(.*?)</i>', r'*\1*', p_html)
                p_html = re.sub(r'<u>(.*?)</u>', r'_\1_', p_html)

                # 일반 텍스트 추출 (태그 모두 제거)
                text = re.sub(r'<[^>]+>', '', p_html)
                text = self._decode_entities(text)

                if text.strip():
                    lines.append(text.strip())

        return '\n'.join(lines)

    def _extract_quotation(self, comp_html):
        """인용문 컴포넌트에서 텍스트 추출"""
        # <blockquote> 안의 텍스트 추출
        blockquote_match = re.search(
            r'<blockquote[^>]*>(.*?)</blockquote>',
            comp_html,
            re.DOTALL
        )

        if not blockquote_match:
            return ''

        blockquote_html = blockquote_match.group(1)

        # <p> 태그들 추출
        paragraphs = re.findall(
            r'<p[^>]*class="[^"]*se-text-paragraph[^"]*"[^>]*>(.*?)</p>',
            blockquote_html,
            re.DOTALL
        )

        lines = []
        for p_html in paragraphs:
            # span 태그 제거
            while '<span' in p_html:
                p_html = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', p_html, count=1, flags=re.DOTALL)

            # 스타일 태그 보존
            p_html = re.sub(r'<b>(.*?)</b>', r'**\1**', p_html)
            p_html = re.sub(r'<i>(.*?)</i>', r'*\1*', p_html)
            p_html = re.sub(r'<u>(.*?)</u>', r'_\1_', p_html)

            # 나머지 태그 제거
            text = re.sub(r'<[^>]+>', '', p_html)
            text = self._decode_entities(text)

            if text.strip():
                lines.append(text.strip())

        return '\n'.join(lines)

    def _extract_table(self, comp_html):
        """표 컴포넌트에서 텍스트 추출"""
        # <table> 찾기
        table_match = re.search(
            r'<table[^>]*class="[^"]*se-table[^"]*"[^>]*>(.*?)</table>',
            comp_html,
            re.DOTALL
        )

        if not table_match:
            return ''

        table_html = table_match.group(1)

        # <tr> 행들 추출
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)

        if not rows:
            return ''

        lines = []

        for row_html in rows:
            # <th> 또는 <td> 셀 추출
            cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row_html, re.DOTALL)

            cell_texts = []
            for cell_html in cells:
                # span 제거
                while '<span' in cell_html:
                    cell_html = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', cell_html, count=1, flags=re.DOTALL)

                # 스타일 태그 보존
                cell_html = re.sub(r'<b>(.*?)</b>', r'**\1**', cell_html)
                cell_html = re.sub(r'<i>(.*?)</i>', r'*\1*', cell_html)

                # 나머지 태그 제거
                cell_text = re.sub(r'<[^>]+>', '', cell_html)
                cell_text = self._decode_entities(cell_text)

                if cell_text.strip():
                    cell_texts.append(cell_text.strip())

            if cell_texts:
                lines.append('| ' + ' | '.join(cell_texts) + ' |')

        return '\n'.join(lines)

    def _decode_entities(self, text):
        """HTML 엔티티 디코딩"""
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&lsquo;', ''')
        text = text.replace('&rsquo;', ''')
        return text.strip()


# 테스트
if __name__ == '__main__':
    crawler = NaverBlogCrawler()

    # 예시 1: RSS에서 키워드 검색
    blog_id = 'sunny12221'
    keyword = 'yatpor'

    print(f"🔍 '{keyword}' 검색 중...")
    post = crawler.find_post_by_keyword(blog_id, keyword)

    if post:
        print(f"\n✅ 찾은 글:")
        print(f"  제목: {post['title']}")
        print(f"  링크: {post['link']}")
        print(f"\n📄 본문 파싱 중...")

        result = crawler.parse_blog_post(post['link'])

        print(f"\n제목: {result['title']}")
        print(f"\n본문:\n{result['content_with_markers'][:500]}...")
    else:
        print(f"❌ '{keyword}'가 포함된 글을 찾을 수 없습니다")
