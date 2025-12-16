"""
스프레드시트 구조 업데이트 스크립트

기존 콘텐츠 탭들에:
1. account_group 컬럼(J열) 헤더 추가
2. published_url 컬럼(K열) 헤더 추가
3. published_time 컬럼(L열) 헤더 추가
4. published_account 컬럼(M열) 헤더 추가
5. content 컬럼 너비 축소 (200px -> 150px)
"""

import sys
sys.path.append('.')

from src.sheets.base import SheetsBase


def get_sheet_id(service, spreadsheet_id, sheet_name):
    """시트 이름으로 시트 ID 가져오기"""
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in spreadsheet.get('sheets', []):
        if sheet['properties']['title'] == sheet_name:
            return sheet['properties']['sheetId']
    return None


def update_content_sheet(base, sheet_name):
    """콘텐츠 시트 구조 업데이트"""
    print(f"\n[콘텐츠] {sheet_name} 업데이트 중...")

    # 시트 ID 가져오기
    sheet_id = get_sheet_id(base.service, base.spreadsheet_id, sheet_name)
    if sheet_id is None:
        print(f"  [X] 시트를 찾을 수 없음")
        return False

    # 현재 헤더 확인
    try:
        headers = base.read_range(f'{sheet_name}!A1:M1')
        if headers and len(headers) > 0:
            current_headers = headers[0]
            print(f"  현재 헤더: {current_headers}")

            # 필요한 컬럼들 추가
            new_headers = []
            if len(current_headers) < 10 or 'account_group' not in current_headers:
                new_headers.append(('J1', 'account_group'))
            if len(current_headers) < 11 or 'published_url' not in current_headers:
                new_headers.append(('K1', 'published_url'))
            if len(current_headers) < 12 or 'published_time' not in current_headers:
                new_headers.append(('L1', 'published_time'))
            if len(current_headers) < 13 or 'published_account' not in current_headers:
                new_headers.append(('M1', 'published_account'))

            for cell, header in new_headers:
                print(f"  -> {header} 헤더 추가")
                base.write_range(f'{sheet_name}!{cell}', [[header]])
    except Exception as e:
        print(f"  [!] 헤더 확인 실패: {e}")
        # 새 시트일 수 있으니 헤더 추가 시도
        base.write_range(f'{sheet_name}!J1:M1', [['account_group', 'published_url', 'published_time', 'published_account']])

    # 컬럼 서식 업데이트
    format_body = {
        'requests': [
            # D열 (content): 150px로 축소
            {
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 3,
                        'endIndex': 4
                    },
                    'properties': {'pixelSize': 150},
                    'fields': 'pixelSize'
                }
            },
            # J열 (account_group): 100px
            {
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 9,
                        'endIndex': 10
                    },
                    'properties': {'pixelSize': 100},
                    'fields': 'pixelSize'
                }
            },
            # K열 (published_url): 250px
            {
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 10,
                        'endIndex': 11
                    },
                    'properties': {'pixelSize': 250},
                    'fields': 'pixelSize'
                }
            },
            # L열 (published_time): 140px
            {
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 11,
                        'endIndex': 12
                    },
                    'properties': {'pixelSize': 140},
                    'fields': 'pixelSize'
                }
            },
            # M열 (published_account): 120px
            {
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 12,
                        'endIndex': 13
                    },
                    'properties': {'pixelSize': 120},
                    'fields': 'pixelSize'
                }
            },
            # D열 (content) 텍스트 줄바꿈 끄기
            {
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startColumnIndex': 3,
                        'endColumnIndex': 4
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'wrapStrategy': 'CLIP'
                        }
                    },
                    'fields': 'userEnteredFormat.wrapStrategy'
                }
            }
        ]
    }

    try:
        base.service.spreadsheets().batchUpdate(
            spreadsheetId=base.spreadsheet_id,
            body=format_body
        ).execute()
        print(f"  [OK] 서식 업데이트 완료")
        return True
    except Exception as e:
        print(f"  [X] 서식 업데이트 실패: {e}")
        return False


def setup_account_sheet(base, sheet_name):
    """계정 시트 구조 설정"""
    print(f"\n[계정] {sheet_name} 설정 중...")

    sheet_id = get_sheet_id(base.service, base.spreadsheet_id, sheet_name)
    if sheet_id is None:
        print(f"  [X] 시트를 찾을 수 없음")
        return False

    # 계정 시트 헤더
    account_headers = [
        'account_id',      # A: 네이버 ID
        'password',        # B: 비밀번호 (암호화 권장)
        'status',          # C: active/suspended/banned
        'daily_limit',     # D: 일일 발행 한도 (현금화용)
        'today_count',     # E: 오늘 발행 수
        'last_used',       # F: 마지막 사용 시간
        'created_date',    # G: 등록일
        'memo'             # H: 메모
    ]

    # 현재 헤더 확인
    try:
        existing = base.read_range(f'{sheet_name}!A1:H1')
        if existing and len(existing) > 0 and len(existing[0]) >= 8:
            print(f"  이미 헤더가 있음: {existing[0]}")
        else:
            print(f"  -> 헤더 추가")
            base.write_range(f'{sheet_name}!A1:H1', [account_headers])
    except:
        print(f"  -> 헤더 추가")
        base.write_range(f'{sheet_name}!A1:H1', [account_headers])

    # 컬럼 서식
    format_body = {
        'requests': [
            # A열 (account_id): 120px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 1},
                    'properties': {'pixelSize': 120},
                    'fields': 'pixelSize'
                }
            },
            # B열 (password): 100px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 1, 'endIndex': 2},
                    'properties': {'pixelSize': 100},
                    'fields': 'pixelSize'
                }
            },
            # C열 (status): 80px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 2, 'endIndex': 3},
                    'properties': {'pixelSize': 80},
                    'fields': 'pixelSize'
                }
            },
            # D열 (daily_limit): 80px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 3, 'endIndex': 4},
                    'properties': {'pixelSize': 80},
                    'fields': 'pixelSize'
                }
            },
            # E열 (today_count): 80px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 4, 'endIndex': 5},
                    'properties': {'pixelSize': 80},
                    'fields': 'pixelSize'
                }
            },
            # F열 (last_used): 140px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 5, 'endIndex': 6},
                    'properties': {'pixelSize': 140},
                    'fields': 'pixelSize'
                }
            },
            # G열 (created_date): 100px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 6, 'endIndex': 7},
                    'properties': {'pixelSize': 100},
                    'fields': 'pixelSize'
                }
            },
            # H열 (memo): 150px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 7, 'endIndex': 8},
                    'properties': {'pixelSize': 150},
                    'fields': 'pixelSize'
                }
            },
            # 첫 번째 행 고정
            {
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sheet_id,
                        'gridProperties': {'frozenRowCount': 1}
                    },
                    'fields': 'gridProperties.frozenRowCount'
                }
            }
        ]
    }

    try:
        base.service.spreadsheets().batchUpdate(
            spreadsheetId=base.spreadsheet_id,
            body=format_body
        ).execute()
        print(f"  [OK] 서식 설정 완료")
        return True
    except Exception as e:
        print(f"  [X] 서식 설정 실패: {e}")
        return False


def main():
    print("=" * 50)
    print("스프레드시트 구조 업데이트")
    print("=" * 50)

    base = SheetsBase()

    # 모든 시트 가져오기
    all_sheets = base.get_all_sheet_names()
    print(f"\n현재 탭 목록: {all_sheets}")

    # 콘텐츠 시트 업데이트
    for sheet_name in all_sheets:
        if sheet_name.startswith('콘텐츠_'):
            update_content_sheet(base, sheet_name)

    # 계정 시트 설정
    for sheet_name in all_sheets:
        if sheet_name.startswith('계정_'):
            setup_account_sheet(base, sheet_name)

    print("\n" + "=" * 50)
    print("[OK] 업데이트 완료!")
    print("=" * 50)


if __name__ == '__main__':
    main()
