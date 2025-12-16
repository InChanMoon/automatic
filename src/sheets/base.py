"""
Google Sheets 기본 라이브러리

모든 Sheets 작업의 기반이 되는 클래스
"""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime


class SheetsBase:
    """Google Sheets 기본 클래스"""

    def __init__(self, config_path="config.json", credentials_path="credentials/google_service_account.json"):
        """
        초기화

        Args:
            config_path: config.json 경로
            credentials_path: Service Account JSON 경로
        """
        # Config 로드
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.spreadsheet_id = self.config['google_sheets']['spreadsheet_id']

        # Sheets API 연결
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )

        self.service = build('sheets', 'v4', credentials=creds)

    def read_range(self, range_name):
        """
        특정 범위 읽기

        Args:
            range_name: 예) '라이선스!A1:G100'

        Returns:
            list: 2D 배열 [[row1], [row2], ...]
        """
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=range_name
        ).execute()

        return result.get('values', [])

    def write_range(self, range_name, values):
        """
        특정 범위에 쓰기

        Args:
            range_name: 예) '라이선스!A2:G2'
            values: 2D 배열 [[row1], [row2], ...]
        """
        body = {
            'values': values
        }

        result = self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()

        return result

    def append_row(self, sheet_name, values):
        """
        시트 끝에 행 추가

        Args:
            sheet_name: 시트 이름 (예: '라이선스')
            values: 1D 배열 [col1, col2, col3, ...]
        """
        body = {
            'values': [values]
        }

        result = self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f'{sheet_name}!A:Z',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()

        return result

    def find_row_by_column(self, sheet_name, column_index, search_value):
        """
        특정 컬럼에서 값을 찾아 행 번호 반환

        Args:
            sheet_name: 시트 이름
            column_index: 컬럼 인덱스 (0-based)
            search_value: 찾을 값

        Returns:
            int: 행 번호 (1-based), 없으면 None
        """
        values = self.read_range(f'{sheet_name}!A:Z')

        for i, row in enumerate(values):
            if len(row) > column_index and row[column_index] == search_value:
                return i + 1  # 1-based index

        return None

    def update_cell(self, sheet_name, row, col, value):
        """
        특정 셀 업데이트

        Args:
            sheet_name: 시트 이름
            row: 행 번호 (1-based)
            col: 컬럼 인덱스 (0-based, A=0, B=1, ...)
            value: 값
        """
        # 컬럼 인덱스를 A1 표기법으로 변환
        col_letter = chr(65 + col)  # 65 = 'A'
        range_name = f'{sheet_name}!{col_letter}{row}'

        self.write_range(range_name, [[value]])

    def get_all_sheet_names(self):
        """
        스프레드시트의 모든 탭(시트) 이름 가져오기

        Returns:
            list: 시트 이름 리스트
        """
        spreadsheet = self.service.spreadsheets().get(
            spreadsheetId=self.spreadsheet_id
        ).execute()

        sheets = spreadsheet.get('sheets', [])
        return [sheet['properties']['title'] for sheet in sheets]

    def get_account_groups(self):
        """
        계정 그룹 목록 가져오기 (계정_ 으로 시작하는 탭들)

        Returns:
            list: 그룹 이름 리스트 (예: ['사기', '현금화'])
        """
        all_sheets = self.get_all_sheet_names()
        groups = []

        for name in all_sheets:
            if name.startswith('계정_'):
                group_name = name[3:]  # '계정_' 제거
                groups.append(group_name)

        return groups

    @staticmethod
    def get_current_time():
        """현재 시간을 문자열로 반환"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def get_current_date():
        """현재 날짜를 문자열로 반환"""
        return datetime.now().strftime('%Y-%m-%d')
