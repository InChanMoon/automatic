"""
이미지 클립보드 붙여넣기 테스트

Google Drive에서 이미지를 가져와 네이버 블로그 에디터에 붙여넣기 테스트
"""

import sys
import os

# 1. 먼저 Drive에서 이미지 가져오기 테스트
print("=" * 50)
print("1. Google Drive 이미지 매니저 테스트")
print("=" * 50)

from src.drive.image_manager import DriveImageManager

try:
    img_mgr = DriveImageManager()

    # 연결 테스트
    if img_mgr.test_connection():
        print("[OK] Drive 연결 성공")
    else:
        print("[X] Drive 연결 실패")
        sys.exit(1)

    # 법온길 키워드 폴더 찾기
    keyword = "법온길"
    print(f"\n키워드 '{keyword}' 폴더 검색 중...")

    folder_id = img_mgr.get_keyword_folder_id(keyword)
    if folder_id:
        print(f"[OK] 폴더 발견: {folder_id}")
    else:
        print(f"[X] '{keyword}' 폴더를 찾을 수 없음")
        print("\nDrive 루트 폴더 내 폴더 목록 확인...")

        # 루트 폴더 내 하위 폴더 목록
        subfolders = img_mgr._list_subfolders(img_mgr.root_folder_id)
        print(f"하위 폴더 {len(subfolders)}개:")
        for f in subfolders:
            print(f"  - {f['name']} ({f['id']})")

        if subfolders:
            # 첫 번째 폴더를 키워드로 사용
            keyword = subfolders[0]['name']
            print(f"\n첫 번째 폴더 '{keyword}' 사용")

    # 이미지 세트 확인
    print(f"\n'{keyword}' 내 이미지 세트 확인...")
    image_sets = img_mgr.get_image_sets_for_keyword(keyword)

    if not image_sets:
        print("[X] 이미지 세트 없음")
        sys.exit(1)

    print(f"[OK] {len(image_sets)}개 이미지 세트 발견:")
    for s in image_sets:
        print(f"  - {s['name']}: {s['image_count']}개 이미지")

    # 이미지 가져오기 (마커 3개 가정)
    print(f"\n이미지 3개 요청...")
    images = img_mgr.get_images_for_post(keyword, 3)

    if images:
        print(f"[OK] {len(images)}개 이미지 준비됨:")
        for img in images:
            print(f"  - {img}")
    else:
        print("[X] 이미지 가져오기 실패")
        sys.exit(1)

except Exception as e:
    print(f"[X] Drive 테스트 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# 2. 클립보드 복사 테스트
print("\n" + "=" * 50)
print("2. 클립보드 이미지 복사 테스트")
print("=" * 50)

if sys.platform != 'win32':
    print("[X] Windows에서만 지원됨")
    sys.exit(1)

try:
    import win32clipboard
    from PIL import Image
    import io

    test_image = images[0]
    print(f"테스트 이미지: {test_image}")

    # 이미지 열기
    image = Image.open(test_image)
    print(f"이미지 크기: {image.size}, 모드: {image.mode}")

    # RGBA -> RGB 변환
    if image.mode == 'RGBA':
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])
        image = background
        print("RGBA -> RGB 변환 완료")

    # BMP 형식으로 변환
    output = io.BytesIO()
    image.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]  # BMP 헤더 제외

    # 클립보드에 복사
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        print("[OK] 클립보드에 이미지 복사 완료!")
        print("     지금 아무 곳에나 Ctrl+V 해보세요")
    finally:
        win32clipboard.CloseClipboard()

except Exception as e:
    print(f"[X] 클립보드 테스트 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# 3. 네이버 블로그 에디터에 붙여넣기 테스트
print("\n" + "=" * 50)
print("3. 네이버 블로그 에디터 테스트")
print("=" * 50)

proceed = input("네이버 블로그 에디터 테스트를 진행하시겠습니까? (y/n): ")
if proceed.lower() != 'y':
    print("테스트 종료")
    sys.exit(0)

from src.publisher.naver_blog_publisher import NaverBlogPublisher

try:
    publisher = NaverBlogPublisher(headless=False)
    publisher.start_browser()

    # 쿠키로 로그인 시도
    cookie_files = [f for f in os.listdir('cookies') if f.endswith('_cookies.json')]
    if cookie_files:
        publisher.cookie_path = f"cookies/{cookie_files[0]}"
        logged_in = publisher.login_with_cookies()

        if logged_in:
            print("[OK] 쿠키 로그인 성공")
        else:
            print("[X] 쿠키 로그인 실패 - 수동 로그인 필요")
            input("로그인 후 Enter를 눌러주세요...")
    else:
        print("[!] 쿠키 파일 없음 - 수동 로그인 필요")
        publisher.page.goto("https://nid.naver.com/nidlogin.login")
        input("로그인 후 Enter를 눌러주세요...")

    # 글쓰기 페이지로 이동
    print("\n글쓰기 페이지로 이동 중...")
    publisher.page.goto("https://blog.naver.com/GoBlogWrite.naver")
    publisher.page.wait_for_load_state('networkidle')

    import time
    time.sleep(3)

    # iframe 접근
    frame = publisher.page.frame_locator("#mainFrame")

    # 본문 영역 클릭
    print("본문 영역 클릭...")
    content_area = frame.locator(".se-section-text")
    content_area.click()
    time.sleep(1)

    # 이미지 붙여넣기
    print("이미지 붙여넣기 (Ctrl+V)...")
    publisher.page.keyboard.press("Control+v")
    time.sleep(3)

    print("[OK] 이미지 붙여넣기 완료!")
    print("브라우저에서 이미지가 삽입되었는지 확인하세요.")

    input("확인 후 Enter를 눌러 종료...")
    publisher.close_browser()

except Exception as e:
    print(f"[X] 에디터 테스트 실패: {e}")
    import traceback
    traceback.print_exc()


print("\n테스트 완료!")
