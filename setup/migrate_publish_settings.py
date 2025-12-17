"""
발행설정 시트 마이그레이션 스크립트

기존 컬럼 구조:
- group_name, enabled, interval_min, interval_max, daily_limit, today_count,
  start_hour, end_hour, last_publish, memo

새 컬럼 구조:
- 그룹, 발행대기, 계정, 오늘발행, 계정당발행수, 현재계정발행수, 잠금상태, 잠금시간

실행 방법:
python setup/migrate_publish_settings.py
"""

import os
import sys
import json

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2 import service_account
from googleapiclient.discovery import build


def load_config():
    """설정 로드"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_sheets_service():
    """Google Sheets 서비스 객체 생성"""
    config = load_config()

    credentials_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'credentials',
        'google_service_account.json'
    )

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )

    return build('sheets', 'v4', credentials=creds), config['google_sheets']['spreadsheet_id']


def migrate_publish_settings():
    """발행설정 시트 마이그레이션"""
    service, spreadsheet_id = get_sheets_service()
    sheet_name = '발행설정'

    print("=" * 50)
    print("발행설정 시트 마이그레이션")
    print("=" * 50)

    # 1. 기존 데이터 읽기
    print("\n1. 기존 데이터 읽기...")
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!A:J'
        ).execute()
        old_data = result.get('values', [])

        if len(old_data) <= 1:
            print("   기존 데이터 없음 (헤더만 있거나 시트가 비어있음)")
            old_data = []
        else:
            print(f"   {len(old_data) - 1}개 그룹 데이터 발견")

    except Exception as e:
        print(f"   기존 데이터 읽기 실패: {e}")
        old_data = []

    # 2. 기존 데이터 파싱
    groups_data = []
    if len(old_data) > 1:
        # 기존 헤더 확인
        old_headers = old_data[0] if old_data else []
        print(f"   기존 헤더: {old_headers}")

        for row in old_data[1:]:
            if row and row[0]:
                group_name = row[0]
                today_count = row[5] if len(row) > 5 else '0'

                groups_data.append({
                    'group_name': group_name,
                    'today_count': today_count
                })
                print(f"   - {group_name}: 오늘발행 {today_count}")

    # 3. 기존 시트 삭제 후 재생성
    print("\n2. 시트 재생성 중...")

    # 시트 ID 찾기
    spreadsheet = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id
    ).execute()

    sheet_id = None
    for sheet in spreadsheet.get('sheets', []):
        if sheet['properties']['title'] == sheet_name:
            sheet_id = sheet['properties']['sheetId']
            break

    if sheet_id is not None:
        # 기존 시트 삭제
        requests = [{
            'deleteSheet': {
                'sheetId': sheet_id
            }
        }]

        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()
        print(f"   기존 '{sheet_name}' 시트 삭제")

    # 새 시트 생성
    requests = [{
        'addSheet': {
            'properties': {
                'title': sheet_name
            }
        }
    }]

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': requests}
    ).execute()
    print(f"   새 '{sheet_name}' 시트 생성")

    # 4. 새 헤더 추가
    print("\n3. 새 헤더 추가 중...")
    new_headers = ['그룹', '발행대기', '계정', '오늘발행', '계정당발행수', '현재계정발행수', '잠금상태', '잠금시간']

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f'{sheet_name}!A1:H1',
        valueInputOption='RAW',
        body={'values': [new_headers]}
    ).execute()
    print(f"   헤더: {new_headers}")

    # 5. 기존 데이터 마이그레이션
    if groups_data:
        print("\n4. 데이터 마이그레이션 중...")

        new_rows = []
        for group in groups_data:
            new_row = [
                group['group_name'],  # 그룹
                '0',                   # 발행대기 (콘텐츠 매니저에서 업데이트)
                '',                    # 계정 (자동 설정)
                group['today_count'],  # 오늘발행 (기존 값 유지)
                '5',                   # 계정당발행수 (기본값)
                '0',                   # 현재계정발행수
                '',                    # 잠금상태
                ''                     # 잠금시간
            ]
            new_rows.append(new_row)
            print(f"   - {group['group_name']} 마이그레이션 완료")

        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!A2',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': new_rows}
        ).execute()

        print(f"\n   총 {len(new_rows)}개 그룹 마이그레이션 완료")
    else:
        print("\n4. 마이그레이션할 데이터 없음")

    # 6. 열 너비 조정
    print("\n5. 열 너비 조정 중...")

    # 새로 생성된 시트 ID 찾기
    spreadsheet = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id
    ).execute()

    new_sheet_id = None
    for sheet in spreadsheet.get('sheets', []):
        if sheet['properties']['title'] == sheet_name:
            new_sheet_id = sheet['properties']['sheetId']
            break

    if new_sheet_id is not None:
        column_widths = [100, 80, 120, 80, 100, 100, 100, 150]  # 각 열 너비

        requests = []
        for i, width in enumerate(column_widths):
            requests.append({
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': new_sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': i,
                        'endIndex': i + 1
                    },
                    'properties': {
                        'pixelSize': width
                    },
                    'fields': 'pixelSize'
                }
            })

        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()
        print("   열 너비 조정 완료")

    print("\n" + "=" * 50)
    print("마이그레이션 완료!")
    print("=" * 50)
    print("\n새 컬럼 구조:")
    for i, header in enumerate(new_headers):
        print(f"  {chr(65+i)}: {header}")


if __name__ == '__main__':
    migrate_publish_settings()
