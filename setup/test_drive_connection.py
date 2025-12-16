"""
Google Drive 연결 테스트 스크립트

Service Account 설정이 제대로 되었는지 확인합니다.
"""

import os
import sys

def test_drive_connection():
    """Drive 연결 테스트"""

    print("\n" + "="*60)
    print("Google Drive 연결 테스트")
    print("="*60)

    # 1. JSON 파일 존재 확인
    print("\n1️⃣ JSON 파일 확인 중...")
    json_path = "credentials/google_service_account.json"

    if not os.path.exists(json_path):
        print(f"❌ JSON 파일을 찾을 수 없습니다: {json_path}")
        print("\n해결 방법:")
        print("1. Google Cloud Console에서 Service Account JSON 키 다운로드")
        print("2. 파일을 credentials/ 폴더에 google_service_account.json 이름으로 저장")
        return False

    print(f"✅ JSON 파일 찾음: {json_path}")

    # 2. 필요한 패키지 확인
    print("\n2️⃣ 패키지 확인 중...")
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        print("✅ google-auth, google-api-python-client 설치됨")
    except ImportError as e:
        print(f"❌ 필요한 패키지가 설치되지 않았습니다: {e}")
        print("\n해결 방법:")
        print("pip install google-auth google-api-python-client")
        return False

    # 3. Drive API 연결
    print("\n3️⃣ Drive API 연결 중...")
    try:
        SCOPES = ['https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_file(
            json_path, scopes=SCOPES
        )
        service = build('drive', 'v3', credentials=creds)
        print("✅ Drive API 연결 성공!")
    except Exception as e:
        print(f"❌ Drive API 연결 실패: {e}")
        print("\n해결 방법:")
        print("1. JSON 파일이 올바른지 확인")
        print("2. Google Cloud Console에서 Drive API가 활성화되었는지 확인")
        return False

    # 4. blog_images 폴더 찾기
    print("\n4️⃣ blog_images 폴더 검색 중...")
    try:
        # 공유된 파일 검색
        results = service.files().list(
            q="name='blog_images' and mimeType='application/vnd.google-apps.folder'",
            spaces='drive',
            fields='files(id, name, owners)',
            pageSize=10
        ).execute()

        files = results.get('files', [])

        if not files:
            print("❌ blog_images 폴더를 찾을 수 없습니다")
            print("\n해결 방법:")
            print("1. Google Drive에서 blog_images 폴더 생성")
            print("2. Service Account 이메일에 폴더 공유")
            print("   (편집자 권한)")
            return False

        folder = files[0]
        folder_id = folder['id']
        print(f"✅ blog_images 폴더 찾기 성공!")
        print(f"   폴더 ID: {folder_id}")

        # 5. 하위 폴더 목록
        print("\n5️⃣ 하위 폴더 확인 중...")
        subfolders = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
            fields='files(id, name)',
            pageSize=100
        ).execute()

        sub_files = subfolders.get('files', [])

        if not sub_files:
            print("⚠️ 하위 폴더 없음")
            print("   테스트용 폴더를 만들어보세요:")
            print("   - 테스트_키워드/001/")
            print("   - 테스트_키워드/002/")
        else:
            print("📁 폴더 목록:")
            for f in sub_files:
                print(f"   - {f['name']}")

        # 6. config.json에 폴더 ID 저장
        print("\n6️⃣ config.json 생성 중...")
        import json

        config = {
            "google_drive": {
                "root_folder_id": folder_id,
                "delete_after_use": False,
                "move_to_used": True
            },
            "gemini_api": {
                "api_key": "YOUR_GEMINI_API_KEY_HERE"
            },
            "naver_accounts": [
                {
                    "id": "test_user",
                    "password": "test_password"
                }
            ]
        }

        config_path = "config.json"
        if not os.path.exists(config_path):
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"✅ config.json 생성됨")
            print("   다음 단계:")
            print("   1. config.json 열기")
            print("   2. gemini_api.api_key 값 수정")
            print("   3. naver_accounts 정보 수정")
        else:
            print(f"ℹ️ config.json 이미 존재함 (건너뜀)")

        # 완료
        print("\n" + "="*60)
        print("✅ 모든 테스트 성공!")
        print("="*60)
        print("\n다음 단계:")
        print("1. config.json에 Gemini API 키 입력")
        print("2. 네이버 계정 정보 입력")
        print("3. 테스트용 이미지를 blog_images 폴더에 업로드")
        print("4. 프로그램 실행!")

        return True

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_drive_connection()
    sys.exit(0 if success else 1)
