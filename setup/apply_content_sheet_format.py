"""
기존 콘텐츠 시트에 서식 적용 스크립트

콘텐츠_ 로 시작하는 모든 시트에 컬럼 너비, 헤더 고정 등 서식 적용
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sheets.base import SheetsBase


class ContentSheetFormatter(SheetsBase):
    """콘텐츠 시트 서식 적용"""

    HEADERS = [
        'account_group', 'keyword', 'title', 'content', 'created_time',
        'published_url', 'published_time', 'published_account', 'content_id', 'status',
        'scheduled_time'
    ]

    def get_content_sheets(self):
        """콘텐츠_ 로 시작하는 시트 목록 가져오기"""
        all_sheets = self.get_all_sheet_names()
        return [s for s in all_sheets if s.startswith('콘텐츠_')]

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
            existing = self.read_range(f'{sheet_name}!A1:K1')
            if not existing or existing[0] != self.HEADERS:
                print(f"  [*] 헤더 업데이트 중...")
                self.write_range(f'{sheet_name}!A1:K1', [self.HEADERS])
        except Exception as e:
            print(f"  [!] 헤더 확인 실패: {e}")

        # 조건부 서식 추가 (status별 배경색)
        self._add_conditional_formats(sheet_id, sheet_name)

        # 서식 적용
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
                # K열 (scheduled_time): 150px
                {
                    'updateDimensionProperties': {
                        'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 10, 'endIndex': 11},
                        'properties': {'pixelSize': 150},
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
                # D열 (content) 텍스트 줄바꿈 끄기
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startColumnIndex': 3,
                            'endColumnIndex': 4
                        },
                        'cell': {
                            'userEnteredFormat': {'wrapStrategy': 'CLIP'}
                        },
                        'fields': 'userEnteredFormat.wrapStrategy'
                    }
                },
                # 전체 시트 텍스트 줄바꿈 끄기 (한 줄로 표시)
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 1  # 헤더 제외
                        },
                        'cell': {
                            'userEnteredFormat': {'wrapStrategy': 'CLIP'}
                        },
                        'fields': 'userEnteredFormat.wrapStrategy'
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
            ranges=[sheet_name]
        ).execute()

        for sheet in spreadsheet.get('sheets', []):
            if sheet['properties']['sheetId'] == sheet_id:
                existing = sheet.get('conditionalFormats', [])
                if len(existing) >= 4:
                    print(f"  [*] 조건부 서식 이미 존재 ({len(existing)}개)")
                    return

        # 조건부 서식 추가
        requests = [
            # ready -> 연한 파랑
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1}],
                        'booleanRule': {
                            'condition': {
                                'type': 'CUSTOM_FORMULA',
                                'values': [{'userEnteredValue': '=$J2="ready"'}]
                            },
                            'format': {
                                'backgroundColor': {'red': 0.89, 'green': 0.95, 'blue': 0.99}
                            }
                        }
                    },
                    'index': 0
                }
            },
            # published -> 연한 녹색
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1}],
                        'booleanRule': {
                            'condition': {
                                'type': 'CUSTOM_FORMULA',
                                'values': [{'userEnteredValue': '=$J2="published"'}]
                            },
                            'format': {
                                'backgroundColor': {'red': 0.91, 'green': 0.96, 'blue': 0.91}
                            }
                        }
                    },
                    'index': 1
                }
            },
            # failed -> 연한 빨강
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1}],
                        'booleanRule': {
                            'condition': {
                                'type': 'CUSTOM_FORMULA',
                                'values': [{'userEnteredValue': '=$J2="failed"'}]
                            },
                            'format': {
                                'backgroundColor': {'red': 1.00, 'green': 0.92, 'blue': 0.93}
                            }
                        }
                    },
                    'index': 2
                }
            },
            # deleted -> 연한 빨강
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1}],
                        'booleanRule': {
                            'condition': {
                                'type': 'CUSTOM_FORMULA',
                                'values': [{'userEnteredValue': '=$J2="deleted"'}]
                            },
                            'format': {
                                'backgroundColor': {'red': 1.00, 'green': 0.92, 'blue': 0.93}
                            }
                        }
                    },
                    'index': 3
                }
            },
            # publishing -> 연한 주황
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1}],
                        'booleanRule': {
                            'condition': {
                                'type': 'CUSTOM_FORMULA',
                                'values': [{'userEnteredValue': '=$J2="publishing"'}]
                            },
                            'format': {
                                'backgroundColor': {'red': 1.00, 'green': 0.95, 'blue': 0.80}
                            }
                        }
                    },
                    'index': 4
                }
            }
        ]

        try:
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': requests}
            ).execute()
            print(f"  [*] 조건부 서식 5개 추가")
        except Exception as e:
            print(f"  [!] 조건부 서식 추가 실패: {e}")


def main():
    print("=" * 50)
    print("콘텐츠 시트 서식 적용 스크립트")
    print("=" * 50)

    formatter = ContentSheetFormatter()

    # 콘텐츠 시트 찾기
    sheets = formatter.get_content_sheets()

    if not sheets:
        print("\n콘텐츠_ 로 시작하는 시트가 없습니다.")
        return

    print(f"\n발견된 콘텐츠 시트: {len(sheets)}개")
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


if __name__ == '__main__':
    main()
