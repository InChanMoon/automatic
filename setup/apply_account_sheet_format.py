"""
계정 시트에 조건부 서식 적용 스크립트

계정_ 로 시작하는 모든 시트에 status별 배경색 적용:
- active: 연한 녹색
- suspended: 연한 빨강
- banned: 진한 빨강
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sheets.base import SheetsBase


class AccountSheetFormatter(SheetsBase):
    """계정 시트 서식 적용"""

    HEADERS = ['account_id', 'password', 'status', 'last_used']

    def get_account_sheets(self):
        """계정_ 로 시작하는 시트 목록 가져오기"""
        all_sheets = self.get_all_sheet_names()
        return [s for s in all_sheets if s.startswith('계정_')]

    def get_sheet_id(self, sheet_name):
        """시트 이름으로 시트 ID 가져오기"""
        spreadsheet = self.service.spreadsheets().get(
            spreadsheetId=self.spreadsheet_id
        ).execute()

        for sheet in spreadsheet.get('sheets', []):
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']

        return None

    def apply_format(self, sheet_name):
        """시트에 서식 적용"""
        sheet_id = self.get_sheet_id(sheet_name)
        if sheet_id is None:
            print(f"  [!] 시트 ID를 찾을 수 없음: {sheet_name}")
            return False

        # 헤더 확인/업데이트
        try:
            existing = self.read_range(f'{sheet_name}!A1:D1')
            if not existing or existing[0] != self.HEADERS:
                print(f"  [*] 헤더 업데이트 중...")
                self.write_range(f'{sheet_name}!A1:D1', [self.HEADERS])
        except Exception as e:
            print(f"  [!] 헤더 확인 실패: {e}")

        # 조건부 서식 추가 (status별 배경색)
        self._add_conditional_formats(sheet_id, sheet_name)

        # 서식 적용
        format_body = {
            'requests': [
                # A열 (account_id): 150px
                {
                    'updateDimensionProperties': {
                        'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 1},
                        'properties': {'pixelSize': 150},
                        'fields': 'pixelSize'
                    }
                },
                # B열 (password): 150px
                {
                    'updateDimensionProperties': {
                        'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 1, 'endIndex': 2},
                        'properties': {'pixelSize': 150},
                        'fields': 'pixelSize'
                    }
                },
                # C열 (status): 100px
                {
                    'updateDimensionProperties': {
                        'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 2, 'endIndex': 3},
                        'properties': {'pixelSize': 100},
                        'fields': 'pixelSize'
                    }
                },
                # D열 (last_used): 180px
                {
                    'updateDimensionProperties': {
                        'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 3, 'endIndex': 4},
                        'properties': {'pixelSize': 180},
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
                }
            ]
        }

        try:
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=format_body
            ).execute()
            return True
        except Exception as e:
            print(f"  [!] 서식 적용 실패: {e}")
            return False

    def _add_conditional_formats(self, sheet_id, sheet_name):
        """조건부 서식 추가 (status별 배경색)"""
        # 기존 조건부 서식 확인
        spreadsheet = self.service.spreadsheets().get(
            spreadsheetId=self.spreadsheet_id,
            ranges=[sheet_name],
            fields='sheets.conditionalFormats'
        ).execute()

        for sheet in spreadsheet.get('sheets', []):
            existing = sheet.get('conditionalFormats', [])
            if len(existing) >= 3:
                print(f"  [*] 조건부 서식 이미 존재 ({len(existing)}개)")
                return

        # 조건부 서식 추가
        # C열(status)이 active/suspended/banned일 때 전체 행에 배경색 적용
        requests = [
            # active -> 연한 녹색
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1}],
                        'booleanRule': {
                            'condition': {
                                'type': 'CUSTOM_FORMULA',
                                'values': [{'userEnteredValue': '=$C2="active"'}]
                            },
                            'format': {
                                'backgroundColor': {'red': 0.85, 'green': 0.95, 'blue': 0.85}
                            }
                        }
                    },
                    'index': 0
                }
            },
            # suspended -> 연한 빨강
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1}],
                        'booleanRule': {
                            'condition': {
                                'type': 'CUSTOM_FORMULA',
                                'values': [{'userEnteredValue': '=$C2="suspended"'}]
                            },
                            'format': {
                                'backgroundColor': {'red': 1.00, 'green': 0.85, 'blue': 0.85}
                            }
                        }
                    },
                    'index': 1
                }
            },
            # banned -> 진한 빨강
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1}],
                        'booleanRule': {
                            'condition': {
                                'type': 'CUSTOM_FORMULA',
                                'values': [{'userEnteredValue': '=$C2="banned"'}]
                            },
                            'format': {
                                'backgroundColor': {'red': 0.95, 'green': 0.70, 'blue': 0.70}
                            }
                        }
                    },
                    'index': 2
                }
            }
        ]

        try:
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': requests}
            ).execute()
            print(f"  [*] 조건부 서식 3개 추가 (active=녹색, suspended=빨강, banned=진한빨강)")
        except Exception as e:
            print(f"  [!] 조건부 서식 추가 실패: {e}")


def main():
    print("=" * 50)
    print("계정 시트 조건부 서식 적용 스크립트")
    print("=" * 50)

    formatter = AccountSheetFormatter()

    # 계정 시트 찾기
    sheets = formatter.get_account_sheets()

    if not sheets:
        print("\n계정_ 로 시작하는 시트가 없습니다.")
        return

    print(f"\n발견된 계정 시트: {len(sheets)}개")
    for s in sheets:
        print(f"  - {s}")

    print("\n서식 적용 중...")

    success = 0
    for sheet_name in sheets:
        print(f"\n[{sheet_name}]")
        if formatter.apply_format(sheet_name):
            print(f"  [OK] 서식 적용 완료")
            success += 1
        else:
            print(f"  [X] 서식 적용 실패")

    print(f"\n완료: {success}/{len(sheets)}개 시트에 서식 적용됨")
    print("\n서식 안내:")
    print("  - active: 연한 녹색 배경")
    print("  - suspended: 연한 빨강 배경")
    print("  - banned: 진한 빨강 배경")


if __name__ == '__main__':
    main()
