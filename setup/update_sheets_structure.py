"""
스프레드시트 구조 업데이트 스크립트

새 콘텐츠 탭 구조:
A: account_group (발행 계정 그룹)
B: keyword
C: title
D: content
E: created_time
F: published_url
G: published_time
H: published_account
I: content_id
J: status

+ status 기반 조건부 서식 (행 전체 색상):
- ready: #E3F2FD (연한 파랑)
- published: #E8F5E9 (연한 초록)
- failed/deleted: #FFEBEE (연한 빨강)
"""

import sys
sys.path.append('.')

from src.sheets.base import SheetsBase


# 새 헤더 정의
NEW_HEADERS = [
    'account_group', 'keyword', 'title', 'content', 'created_time',
    'published_url', 'published_time', 'published_account', 'content_id', 'status'
]


def get_sheet_id(service, spreadsheet_id, sheet_name):
    """시트 이름으로 시트 ID 가져오기"""
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in spreadsheet.get('sheets', []):
        if sheet['properties']['title'] == sheet_name:
            return sheet['properties']['sheetId']
    return None


def update_content_sheet(base, sheet_name):
    """콘텐츠 시트 구조 업데이트 (새 구조로)"""
    print(f"\n[콘텐츠] {sheet_name} 업데이트 중...")

    # 시트 ID 가져오기
    sheet_id = get_sheet_id(base.service, base.spreadsheet_id, sheet_name)
    if sheet_id is None:
        print(f"  [X] 시트를 찾을 수 없음")
        return False

    # 헤더 업데이트
    print(f"  -> 헤더 업데이트: {NEW_HEADERS}")
    base.write_range(f'{sheet_name}!A1:J1', [NEW_HEADERS])

    # 컬럼 서식 및 조건부 서식 설정
    format_body = {
        'requests': [
            # A열 (account_group): 100px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 1},
                    'properties': {'pixelSize': 100},
                    'fields': 'pixelSize'
                }
            },
            # B열 (keyword): 120px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 1, 'endIndex': 2},
                    'properties': {'pixelSize': 120},
                    'fields': 'pixelSize'
                }
            },
            # C열 (title): 300px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 2, 'endIndex': 3},
                    'properties': {'pixelSize': 300},
                    'fields': 'pixelSize'
                }
            },
            # D열 (content): 200px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 3, 'endIndex': 4},
                    'properties': {'pixelSize': 200},
                    'fields': 'pixelSize'
                }
            },
            # E열 (created_time): 150px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 4, 'endIndex': 5},
                    'properties': {'pixelSize': 150},
                    'fields': 'pixelSize'
                }
            },
            # F열 (published_url): 200px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 5, 'endIndex': 6},
                    'properties': {'pixelSize': 200},
                    'fields': 'pixelSize'
                }
            },
            # G열 (published_time): 150px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 6, 'endIndex': 7},
                    'properties': {'pixelSize': 150},
                    'fields': 'pixelSize'
                }
            },
            # H열 (published_account): 120px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 7, 'endIndex': 8},
                    'properties': {'pixelSize': 120},
                    'fields': 'pixelSize'
                }
            },
            # I열 (content_id): 180px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 8, 'endIndex': 9},
                    'properties': {'pixelSize': 180},
                    'fields': 'pixelSize'
                }
            },
            # J열 (status): 80px
            {
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 9, 'endIndex': 10},
                    'properties': {'pixelSize': 80},
                    'fields': 'pixelSize'
                }
            },
            # 첫 번째 행 고정 (헤더)
            {
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sheet_id,
                        'gridProperties': {'frozenRowCount': 1}
                    },
                    'fields': 'gridProperties.frozenRowCount'
                }
            },
            # D열 (content) 텍스트 줄바꿈 끄기 (CLIP)
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
        print(f"  [OK] 컬럼 서식 설정 완료")
    except Exception as e:
        print(f"  [X] 서식 설정 실패: {e}")
        return False

    # 조건부 서식 추가 (status 기반 행 색상)
    add_conditional_formatting(base, sheet_id, sheet_name)

    return True


def add_conditional_formatting(base, sheet_id, sheet_name):
    """status 기반 조건부 서식 추가"""
    print(f"  -> 조건부 서식 추가 중...")

    # 기존 조건부 서식 삭제 후 새로 추가
    # status는 J열(인덱스 9)

    # 색상 정의 (RGB 0-1 범위)
    # ready: #E3F2FD (연한 파랑)
    color_ready = {'red': 0.89, 'green': 0.95, 'blue': 0.99}
    # published: #E8F5E9 (연한 초록)
    color_published = {'red': 0.91, 'green': 0.96, 'blue': 0.91}
    # failed/deleted: #FFEBEE (연한 빨강)
    color_failed = {'red': 1.0, 'green': 0.92, 'blue': 0.93}

    conditional_format_body = {
        'requests': [
            # ready 상태 - 연한 파랑
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{
                            'sheetId': sheet_id,
                            'startRowIndex': 1,  # 헤더 제외
                            'startColumnIndex': 0,
                            'endColumnIndex': 10  # A-J열
                        }],
                        'booleanRule': {
                            'condition': {
                                'type': 'CUSTOM_FORMULA',
                                'values': [{'userEnteredValue': '=$J2="ready"'}]
                            },
                            'format': {
                                'backgroundColor': color_ready
                            }
                        }
                    },
                    'index': 0
                }
            },
            # published 상태 - 연한 초록
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{
                            'sheetId': sheet_id,
                            'startRowIndex': 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': 10
                        }],
                        'booleanRule': {
                            'condition': {
                                'type': 'CUSTOM_FORMULA',
                                'values': [{'userEnteredValue': '=$J2="published"'}]
                            },
                            'format': {
                                'backgroundColor': color_published
                            }
                        }
                    },
                    'index': 1
                }
            },
            # failed 상태 - 연한 빨강
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{
                            'sheetId': sheet_id,
                            'startRowIndex': 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': 10
                        }],
                        'booleanRule': {
                            'condition': {
                                'type': 'CUSTOM_FORMULA',
                                'values': [{'userEnteredValue': '=$J2="failed"'}]
                            },
                            'format': {
                                'backgroundColor': color_failed
                            }
                        }
                    },
                    'index': 2
                }
            },
            # deleted 상태 - 연한 빨강
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{
                            'sheetId': sheet_id,
                            'startRowIndex': 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': 10
                        }],
                        'booleanRule': {
                            'condition': {
                                'type': 'CUSTOM_FORMULA',
                                'values': [{'userEnteredValue': '=$J2="deleted"'}]
                            },
                            'format': {
                                'backgroundColor': color_failed
                            }
                        }
                    },
                    'index': 3
                }
            }
        ]
    }

    try:
        base.service.spreadsheets().batchUpdate(
            spreadsheetId=base.spreadsheet_id,
            body=conditional_format_body
        ).execute()
        print(f"  [OK] 조건부 서식 추가 완료")
        print(f"       - ready: 연한 파랑")
        print(f"       - published: 연한 초록")
        print(f"       - failed/deleted: 연한 빨강")
    except Exception as e:
        print(f"  [X] 조건부 서식 추가 실패: {e}")


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
        'password',        # B: 비밀번호
        'status',          # C: active/suspended/banned
        'daily_limit',     # D: 일일 발행 한도
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
    print("스프레드시트 구조 업데이트 (새 구조)")
    print("=" * 50)
    print("\n새 콘텐츠 컬럼 구조:")
    print("  A: account_group | B: keyword | C: title | D: content")
    print("  E: created_time | F: published_url | G: published_time")
    print("  H: published_account | I: content_id | J: status")
    print("\n조건부 서식:")
    print("  - ready: 연한 파랑 (#E3F2FD)")
    print("  - published: 연한 초록 (#E8F5E9)")
    print("  - failed/deleted: 연한 빨강 (#FFEBEE)")

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
