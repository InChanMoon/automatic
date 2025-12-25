# -*- coding: utf-8 -*-
"""
콘텐츠 시트 서식 적용 도구

사용법: python apply_sheet_format.py [시트명]
예시: python apply_sheet_format.py 콘텐츠_test
"""

import sys
import io

# Windows 콘솔 UTF-8 출력 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, '.')

from src.sheets.base import SheetsBase


def get_sheet_id(service, spreadsheet_id, sheet_name):
    """시트 이름으로 시트 ID 가져오기"""
    spreadsheet = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id
    ).execute()

    for sheet in spreadsheet.get('sheets', []):
        if sheet['properties']['title'] == sheet_name:
            return sheet['properties']['sheetId']
    return None


def apply_content_sheet_format(sheet_name):
    """콘텐츠 시트에 서식 적용"""

    # SheetsBase로 API 연결
    base = SheetsBase()
    service = base.service
    spreadsheet_id = base.spreadsheet_id

    # 시트 ID 가져오기
    sheet_id = get_sheet_id(service, spreadsheet_id, sheet_name)

    if sheet_id is None:
        print(f"[X] 시트를 찾을 수 없습니다: {sheet_name}")
        return False

    print(f"[O] 시트 발견: {sheet_name} (ID: {sheet_id})")

    # 헤더 배경색 (연한 회색)
    header_bg_color = {
        'red': 0.9,
        'green': 0.9,
        'blue': 0.9
    }

    # 헤더 텍스트 색상 (검정)
    header_text_color = {
        'red': 0.0,
        'green': 0.0,
        'blue': 0.0
    }

    # 서식 설정 요청
    format_body = {
        'requests': [
            # A열 (account_group): 100px
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 1}, 'properties': {'pixelSize': 100}, 'fields': 'pixelSize'}},
            # B열 (keyword): 120px
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 1, 'endIndex': 2}, 'properties': {'pixelSize': 120}, 'fields': 'pixelSize'}},
            # C열 (title): 300px
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 2, 'endIndex': 3}, 'properties': {'pixelSize': 300}, 'fields': 'pixelSize'}},
            # D열 (content): 200px
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 3, 'endIndex': 4}, 'properties': {'pixelSize': 200}, 'fields': 'pixelSize'}},
            # E열 (created_time): 150px
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 4, 'endIndex': 5}, 'properties': {'pixelSize': 150}, 'fields': 'pixelSize'}},
            # F열 (published_url): 200px
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 5, 'endIndex': 6}, 'properties': {'pixelSize': 200}, 'fields': 'pixelSize'}},
            # G열 (published_time): 150px
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 6, 'endIndex': 7}, 'properties': {'pixelSize': 150}, 'fields': 'pixelSize'}},
            # H열 (published_account): 120px
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 7, 'endIndex': 8}, 'properties': {'pixelSize': 120}, 'fields': 'pixelSize'}},
            # I열 (content_id): 180px
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 8, 'endIndex': 9}, 'properties': {'pixelSize': 180}, 'fields': 'pixelSize'}},
            # J열 (status): 80px
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 9, 'endIndex': 10}, 'properties': {'pixelSize': 80}, 'fields': 'pixelSize'}},
            # K열 (scheduled_time): 150px
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 10, 'endIndex': 11}, 'properties': {'pixelSize': 150}, 'fields': 'pixelSize'}},

            # 첫 번째 행 고정 (헤더)
            {'updateSheetProperties': {'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 1}}, 'fields': 'gridProperties.frozenRowCount'}},

            # 모든 데이터 행 높이 21px 고정 (한 줄만 표시)
            {'updateDimensionProperties': {
                'range': {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': 1, 'endIndex': 1000},
                'properties': {'pixelSize': 21},
                'fields': 'pixelSize'
            }},

            # 헤더 행 (1행) 배경색 + 텍스트 서식
            {'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': 11  # A~K (11개 컬럼)
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': header_bg_color,
                        'textFormat': {
                            'foregroundColor': header_text_color,
                            'bold': True
                        },
                        'horizontalAlignment': 'CENTER',
                        'verticalAlignment': 'MIDDLE'
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)'
            }},

            # D열 (content) 데이터 영역 - 텍스트 줄바꿈 끄기 (CLIP)
            {'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 1,  # 헤더 제외
                    'startColumnIndex': 3,
                    'endColumnIndex': 4
                },
                'cell': {
                    'userEnteredFormat': {'wrapStrategy': 'CLIP'}
                },
                'fields': 'userEnteredFormat.wrapStrategy'
            }},

            # 조건부 서식: status = 'draft' -> 하늘색
            {'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1, 'startColumnIndex': 0, 'endColumnIndex': 11}],
                    'booleanRule': {
                        'condition': {
                            'type': 'CUSTOM_FORMULA',
                            'values': [{'userEnteredValue': '=$J2="draft"'}]
                        },
                        'format': {'backgroundColor': {'red': 0.85, 'green': 0.93, 'blue': 1.0}}
                    }
                },
                'index': 0
            }},

            # 조건부 서식: status = 'ready' -> 연한 녹색
            {'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1, 'startColumnIndex': 0, 'endColumnIndex': 11}],
                    'booleanRule': {
                        'condition': {
                            'type': 'CUSTOM_FORMULA',
                            'values': [{'userEnteredValue': '=$J2="ready"'}]
                        },
                        'format': {'backgroundColor': {'red': 0.85, 'green': 0.95, 'blue': 0.85}}
                    }
                },
                'index': 1
            }},

            # 조건부 서식: status = 'publishing' -> 연한 노랑
            {'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1, 'startColumnIndex': 0, 'endColumnIndex': 11}],
                    'booleanRule': {
                        'condition': {
                            'type': 'CUSTOM_FORMULA',
                            'values': [{'userEnteredValue': '=$J2="publishing"'}]
                        },
                        'format': {'backgroundColor': {'red': 1.0, 'green': 0.95, 'blue': 0.8}}
                    }
                },
                'index': 2
            }},

            # 조건부 서식: status = 'published' -> 회색
            {'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1, 'startColumnIndex': 0, 'endColumnIndex': 11}],
                    'booleanRule': {
                        'condition': {
                            'type': 'CUSTOM_FORMULA',
                            'values': [{'userEnteredValue': '=$J2="published"'}]
                        },
                        'format': {'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}}
                    }
                },
                'index': 3
            }},

            # 조건부 서식: status = 'failed' -> 연한 빨강
            {'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1, 'startColumnIndex': 0, 'endColumnIndex': 11}],
                    'booleanRule': {
                        'condition': {
                            'type': 'CUSTOM_FORMULA',
                            'values': [{'userEnteredValue': '=$J2="failed"'}]
                        },
                        'format': {'backgroundColor': {'red': 1.0, 'green': 0.85, 'blue': 0.85}}
                    }
                },
                'index': 4
            }}
        ]
    }

    try:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=format_body
        ).execute()
        print(f"[O] 서식 적용 완료!")
        print(f"    - 컬럼 너비 설정 (A~K)")
        print(f"    - 첫 번째 행 고정 (헤더)")
        print(f"    - 헤더 행 배경색 + 볼드 + 가운데 정렬")
        print(f"    - 데이터 행 높이 21px 고정 (한 줄)")
        print(f"    - D열(content) 텍스트 줄바꿈 해제 (CLIP)")
        print(f"    - status별 조건부 서식 (draft=하늘색, ready=녹색, publishing=노랑, published=회색, failed=빨강)")
        return True
    except Exception as e:
        print(f"[X] 서식 적용 실패: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        # 대화형 모드
        print("=" * 50)
        print("콘텐츠 시트 서식 적용 도구")
        print("=" * 50)
        sheet_name = input("\n시트명 입력 (예: 콘텐츠_test): ").strip()
    else:
        sheet_name = sys.argv[1]

    if not sheet_name:
        print("[X] 시트명을 입력하세요.")
        return

    print(f"\n'{sheet_name}' 시트에 서식 적용 중...")
    apply_content_sheet_format(sheet_name)


if __name__ == "__main__":
    main()
