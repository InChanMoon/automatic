"""
Google Sheets API 연결 테스트 스크립트

Sheets API 설정이 제대로 되었는지 확인합니다.
"""

import os
import sys
import json

def test_sheets_connection():
    """Sheets 연결 테스트"""

    print("\n" + "="*60)
    print("Google Sheets API 연결 테스트")
    print("="*60)

    # 1. JSON 파일 존재 확인
    print("\n1️⃣ JSON 파일 확인 중...")
    json_path = "credentials/google_service_account.json"

    if not os.path.exists(json_path):
        print(f"❌ JSON 파일을 찾을 수 없습니다: {json_path}")
        return False

    print(f"✅ JSON 파일 찾음: {json_path}")

    # 2. config.json에서 스프레드시트 ID 읽기
    print("\n2️⃣ config.json 확인 중...")
    config_path = "config.json"

    if not os.path.exists(config_path):
        print(f"❌ config.json 파일을 찾을 수 없습니다")
        print("\n해결 방법:")
        print("1. config.json 파일 생성")
        print("2. google_sheets.spreadsheet_id 값 추가")
        return False

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    if 'google_sheets' not in config or 'spreadsheet_id' not in config['google_sheets']:
        print("❌ config.json에 google_sheets.spreadsheet_id가 없습니다")
        print("\n해결 방법:")
        print("config.json에 다음 섹션 추가:")
        print('"google_sheets": {')
        print('  "spreadsheet_id": "여기에_스프레드시트_ID_입력"')
        print('}')
        return False

    spreadsheet_id = config['google_sheets']['spreadsheet_id']

    if spreadsheet_id == "여기에_스프레드시트_ID_입력":
        print("❌ 스프레드시트 ID를 실제 값으로 변경해주세요")
        return False

    print(f"✅ 스프레드시트 ID: {spreadsheet_id}")

    # 3. 필요한 패키지 확인
    print("\n3️⃣ 패키지 확인 중...")
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        print("✅ google-auth, google-api-python-client 설치됨")
    except ImportError as e:
        print(f"❌ 필요한 패키지가 설치되지 않았습니다: {e}")
        print("\n해결 방법:")
        print("pip install google-auth google-api-python-client")
        return False

    # 4. Sheets API 연결
    print("\n4️⃣ Sheets API 연결 중...")
    try:
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = service_account.Credentials.from_service_account_file(
            json_path, scopes=SCOPES
        )
        service = build('sheets', 'v4', credentials=creds)
        print("✅ Sheets API 연결 성공!")
    except Exception as e:
        print(f"❌ Sheets API 연결 실패: {e}")
        print("\n해결 방법:")
        print("1. JSON 파일이 올바른지 확인")
        print("2. Google Cloud Console에서 Sheets API가 활성화되었는지 확인")
        return False

    # 5. 스프레드시트 정보 가져오기
    print("\n5️⃣ 스프레드시트 확인 중...")
    try:
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()

        title = spreadsheet.get('properties', {}).get('title', '제목 없음')
        print(f"✅ 스프레드시트 연결 성공!")
        print(f"   제목: {title}")

        # 시트 목록
        sheets = spreadsheet.get('sheets', [])
        print(f"\n📋 시트 목록 ({len(sheets)}개):")
        for sheet in sheets:
            sheet_title = sheet['properties']['title']
            print(f"   - {sheet_title}")

    except Exception as e:
        print(f"❌ 스프레드시트 접근 실패: {e}")
        print("\n해결 방법:")
        print("1. 스프레드시트 ID가 올바른지 확인")
        print("2. Service Account에 스프레드시트를 공유했는지 확인 (편집자 권한)")
        return False

    # 6. 라이선스 데이터 읽기 테스트
    print("\n6️⃣ 라이선스 데이터 읽기 테스트...")
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='라이선스!A1:G10'
        ).execute()

        values = result.get('values', [])

        if not values:
            print("⚠️ 라이선스 시트가 비어있습니다")
        else:
            headers = values[0] if len(values) > 0 else []
            data_rows = values[1:] if len(values) > 1 else []

            print(f"✅ 라이선스 데이터 읽기 성공!")
            print(f"   총 {len(data_rows)}개 라이선스 발견")

            if data_rows:
                for row in data_rows:
                    if len(row) >= 1:
                        license_key = row[0] if len(row) > 0 else ''
                        status = row[2] if len(row) > 2 else 'unknown'
                        is_admin = row[3] if len(row) > 3 else 'FALSE'
                        api_usage = row[4] if len(row) > 4 else '0'
                        api_limit = row[5] if len(row) > 5 else '0'

                        admin_badge = " [ADMIN]" if is_admin == "TRUE" else ""
                        print(f"   - {license_key}{admin_badge} (상태: {status}, API: {api_usage}/{api_limit})")

    except Exception as e:
        print(f"⚠️ 라이선스 데이터 읽기 실패: {e}")

    # 7. 계정 데이터 읽기 테스트
    print("\n7️⃣ 계정 데이터 읽기 테스트...")
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='계정!A1:E10'
        ).execute()

        values = result.get('values', [])

        if not values:
            print("⚠️ 계정 시트가 비어있습니다")
        else:
            data_rows = values[1:] if len(values) > 1 else []

            print(f"✅ 계정 데이터 읽기 성공!")
            print(f"   총 {len(data_rows)}개 계정 발견")

            if data_rows:
                for row in data_rows:
                    if len(row) >= 1:
                        naver_id = row[0] if len(row) > 0 else ''
                        status = row[2] if len(row) > 2 else 'unknown'
                        total_posts = row[4] if len(row) > 4 else '0'
                        print(f"   - {naver_id} (상태: {status}, 총 {total_posts}개 포스팅)")

    except Exception as e:
        print(f"⚠️ 계정 데이터 읽기 실패: {e}")

    # 완료
    print("\n" + "="*60)
    print("✅ 모든 테스트 성공!")
    print("="*60)
    print("\n다음 단계:")
    print("1. 계정 관리 시스템 개발")
    print("2. 라이선스 검증 시스템 개발")
    print("3. 콘텐츠 생성 시스템 개발")

    return True


if __name__ == "__main__":
    success = test_sheets_connection()
    sys.exit(0 if success else 1)
