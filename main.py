"""
네이버 블로그 자동화 시스템 - 메인 스크립트

사용법:
1. 콘텐츠 생성 워커 실행: python main.py --worker content
2. 발행 워커 실행: python main.py --worker publisher
3. 키워드 추가: python main.py --add-keyword "키워드" --license LICENSE-ADMIN
4. 상태 확인: python main.py --status
"""

import argparse
import time
import sys

# 모듈 import
from src.sheets.license_manager import LicenseManager
from src.sheets.account_manager import AccountManager
from src.sheets.content_manager import ContentManager
from src.content.gemini_generator import GeminiGenerator
from src.images.drive_manager import DriveImageManager


def content_worker():
    """
    콘텐츠 생성 워커

    pending 상태의 키워드를 찾아서 Gemini로 콘텐츠 생성
    """
    print("\n" + "="*60)
    print("콘텐츠 생성 워커 시작")
    print("="*60)

    license_mgr = LicenseManager()
    content_mgr = ContentManager()
    generator = GeminiGenerator()

    while True:
        print("\n⏳ pending 콘텐츠 검색 중...")

        # pending 상태인 콘텐츠 가져오기
        pending = content_mgr.get_pending_content()

        if not pending:
            print("ℹ️ pending 콘텐츠 없음. 10초 대기...")
            time.sleep(10)
            continue

        keyword = pending['keyword']
        license_key = pending['license_key']
        row_num = pending['row_num']

        print(f"\n📝 콘텐츠 생성 시작:")
        print(f"   키워드: {keyword}")
        print(f"   라이선스: {license_key}")

        # 라이선스 검증
        validation = license_mgr.validate_license(license_key)

        if not validation['valid']:
            print(f"❌ 라이선스 검증 실패: {validation['message']}")
            content_mgr.mark_failed(row_num)
            continue

        if not validation['can_use_api']:
            print(f"⚠️ API 사용량 초과: {validation['message']}")
            print("   10초 대기...")
            time.sleep(10)
            continue

        print(f"✅ 라이선스 검증 성공: {validation['message']}")

        # Gemini로 콘텐츠 생성
        print("\n🤖 Gemini API 호출 중...")
        result = generator.generate_blog_post(keyword)

        title = result['title']
        content = result['content']

        print(f"✅ 콘텐츠 생성 완료")
        print(f"   제목: {title}")
        print(f"   본문 길이: {len(content)}자")

        # API 사용량 증가
        license_mgr.increment_api_usage(license_key)

        # 콘텐츠 업데이트
        content_mgr.update_generated_content(row_num, title, content)

        print("✅ 작업 완료!")


def publisher_worker():
    """
    발행 워커

    generated 상태의 콘텐츠를 찾아서 네이버 블로그에 발행

    TODO: 다음 단계에서 구현 (Playwright 통합)
    """
    print("\n" + "="*60)
    print("발행 워커 (미구현)")
    print("="*60)
    print("발행 기능은 다음 단계에서 구현됩니다.")
    print("test/test_blog_login.py를 기반으로 통합 예정")


def add_keyword(keyword, license_key):
    """
    키워드 추가

    Args:
        keyword: 키워드
        license_key: 라이선스 키
    """
    print(f"\n📌 키워드 추가: {keyword} (라이선스: {license_key})")

    license_mgr = LicenseManager()
    content_mgr = ContentManager()

    # 라이선스 검증
    validation = license_mgr.validate_license(license_key)

    if not validation['valid']:
        print(f"❌ 라이선스 검증 실패: {validation['message']}")
        return

    print(f"✅ 라이선스 검증 성공")

    # 키워드 추가
    row_num = content_mgr.add_keyword_request(keyword, license_key)

    print(f"✅ 키워드 추가 완료 (행: {row_num})")


def show_status():
    """
    시스템 상태 확인
    """
    print("\n" + "="*60)
    print("시스템 상태")
    print("="*60)

    content_mgr = ContentManager()
    account_mgr = AccountManager()

    # 콘텐츠 상태별 개수
    print("\n📊 콘텐츠 상태:")
    for status in ['pending', 'generated', 'publishing', 'published', 'failed']:
        items = content_mgr.get_content_by_status(status)
        print(f"   {status}: {len(items)}개")

    # 계정 상태별 개수
    print("\n👥 계정 상태:")
    accounts = account_mgr.get_all_accounts()

    status_counts = {}
    for account in accounts:
        status = account['status']
        status_counts[status] = status_counts.get(status, 0) + 1

    for status, count in status_counts.items():
        print(f"   {status}: {count}개")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='네이버 블로그 자동화 시스템')

    parser.add_argument('--worker', choices=['content', 'publisher'],
                        help='워커 실행 (content: 콘텐츠 생성, publisher: 발행)')

    parser.add_argument('--add-keyword', type=str,
                        help='키워드 추가')

    parser.add_argument('--license', type=str,
                        help='라이선스 키 (키워드 추가 시 필요)')

    parser.add_argument('--status', action='store_true',
                        help='시스템 상태 확인')

    args = parser.parse_args()

    if args.worker == 'content':
        content_worker()

    elif args.worker == 'publisher':
        publisher_worker()

    elif args.add_keyword:
        if not args.license:
            print("❌ --license 옵션이 필요합니다")
            sys.exit(1)

        add_keyword(args.add_keyword, args.license)

    elif args.status:
        show_status()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
