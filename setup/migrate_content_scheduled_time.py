"""
콘텐츠 시트 예약발행 컬럼 마이그레이션 스크립트

기존 컬럼 구조 (A~J):
- account_group, keyword, title, content, created_time,
  published_url, published_time, published_account, content_id, status

새 컬럼 구조 (A~K):
- account_group, keyword, title, content, created_time,
  published_url, published_time, published_account, content_id, status,
  scheduled_time (K열 추가)

실행 방법:
python setup/migrate_content_scheduled_time.py
"""

import os
import sys

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
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


def get_content_sheets(service, spreadsheet_id):
    """콘텐츠 시트 목록 가져오기"""
    spreadsheet = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id
    ).execute()

    content_sheets = []
    for sheet in spreadsheet.get('sheets', []):
        title = sheet['properties']['title']
        if title.startswith('콘텐츠_'):
            content_sheets.append({
                'title': title,
                'sheetId': sheet['properties']['sheetId']
            })

    return content_sheets


def migrate_content_sheets():
    """콘텐츠 시트에 scheduled_time 컬럼 추가"""
    service, spreadsheet_id = get_sheets_service()

    print("=" * 60)
    print("콘텐츠 시트 예약발행(scheduled_time) 컬럼 마이그레이션")
    print("=" * 60)

    # 1. 콘텐츠 시트 목록 가져오기
    print("\n1. 콘텐츠 시트 검색 중...")
    content_sheets = get_content_sheets(service, spreadsheet_id)

    if not content_sheets:
        print("   콘텐츠 시트가 없습니다. (콘텐츠_로 시작하는 시트)")
        return

    print(f"   {len(content_sheets)}개 콘텐츠 시트 발견:")
    for sheet in content_sheets:
        print(f"   - {sheet['title']}")

    # 2. 각 시트 마이그레이션
    print("\n2. 마이그레이션 시작...")

    for sheet in content_sheets:
        sheet_name = sheet['title']
        sheet_id = sheet['sheetId']

        try:
            # 헤더 읽기
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f'{sheet_name}!A1:K1'
            ).execute()

            headers = result.get('values', [[]])[0]

            # 이미 scheduled_time이 있는지 확인
            if len(headers) >= 11 and headers[10] == 'scheduled_time':
                print(f"   [{sheet_name}] 이미 마이그레이션됨 (스킵)")
                continue

            # K열에 scheduled_time 헤더 추가
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'{sheet_name}!K1',
                valueInputOption='RAW',
                body={'values': [['scheduled_time']]}
            ).execute()

            # 기존 데이터 행 수 확인
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f'{sheet_name}!A:A'
            ).execute()

            row_count = len(result.get('values', []))

            # 2행부터 모든 데이터 행에 기본값 '즉시발행' 설정
            if row_count > 1:
                default_values = [['즉시발행'] for _ in range(row_count - 1)]
                service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f'{sheet_name}!K2:K{row_count}',
                    valueInputOption='RAW',
                    body={'values': default_values}
                ).execute()

            # K열 너비 조정
            requests = [{
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 10,  # K열 (0-based index)
                        'endIndex': 11
                    },
                    'properties': {
                        'pixelSize': 150
                    },
                    'fields': 'pixelSize'
                }
            }]

            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()

            print(f"   [{sheet_name}] 마이그레이션 완료 ({row_count - 1}개 행)")

        except Exception as e:
            print(f"   [{sheet_name}] 오류: {e}")

    print("\n" + "=" * 60)
    print("마이그레이션 완료!")
    print("=" * 60)
    print("\n새 컬럼 구조:")
    print("  A: account_group")
    print("  B: keyword")
    print("  C: title")
    print("  D: content")
    print("  E: created_time")
    print("  F: published_url")
    print("  G: published_time")
    print("  H: published_account")
    print("  I: content_id")
    print("  J: status")
    print("  K: scheduled_time (신규)")


if __name__ == '__main__':
    migrate_content_sheets()
