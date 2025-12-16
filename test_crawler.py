"""
네이버 블로그 크롤러 테스트
"""

import sys
import io

# Windows 콘솔 인코딩 문제 해결
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.crawler.naver_blog_crawler import NaverBlogCrawler


def test_crawler():
    """크롤러 기능 테스트"""
    crawler = NaverBlogCrawler()

    print("=" * 60)
    print("네이버 블로그 크롤러 테스트")
    print("=" * 60)

    # 테스트 1: RSS 피드 가져오기
    print("\n[테스트 1] RSS 피드 가져오기")
    blog_id = 'sunny12221'
    print(f"블로그 ID: {blog_id}")

    entries = crawler.get_rss_feed(blog_id)

    if entries:
        print(f"✅ RSS 피드 가져오기 성공! (총 {len(entries)}개 글)")
        print("\n최근 5개 글:")
        for i, entry in enumerate(entries[:5], 1):
            print(f"  {i}. {entry['title']}")
            print(f"     링크: {entry['link']}")
            print()
    else:
        print("❌ RSS 피드 가져오기 실패")
        return

    # 테스트 2: 키워드 검색
    print("\n[테스트 2] 키워드로 글 검색")
    keyword = 'yatpor'
    print(f"검색 키워드: {keyword}")

    post = crawler.find_post_by_keyword(blog_id, keyword)

    if post:
        print(f"✅ 키워드 검색 성공!")
        print(f"  제목: {post['title']}")
        print(f"  링크: {post['link']}")
        print(f"  발행일: {post['published']}")
    else:
        print(f"❌ '{keyword}'가 포함된 글을 찾을 수 없습니다")
        return

    # 테스트 3: 글 파싱
    print("\n[테스트 3] 글 본문 파싱")
    print(f"파싱 URL: {post['link']}")

    result = crawler.parse_blog_post(post['link'])

    if result['title']:
        print(f"\n✅ 파싱 성공!")
        print(f"\n제목: {result['title']}")
        print(f"\n본문 미리보기 (처음 500자):")
        print("=" * 60)
        print(result['content_with_markers'][:500])
        print("=" * 60)

        # 이미지 마커 개수 세기
        import re
        markers = re.findall(r'\[이미지\d+\]', result['content_with_markers'])
        print(f"\n이미지 마커 개수: {len(markers)}개")
        if markers:
            print(f"마커 목록: {', '.join(markers)}")

    else:
        print("❌ 파싱 실패")

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


if __name__ == '__main__':
    test_crawler()
