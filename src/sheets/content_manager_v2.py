"""
콘텐츠 관리 모듈 v2.1

개선사항:
- 라이선스 키 기준 탭 분리 (동시성 해결)
- 콘텐츠 고유 ID 추가
- 사용자 권한 관리 (본인/admin)
- 수정/삭제 기능
"""

import json
from datetime import datetime
from .base import SheetsBase


class ContentManagerV2(SheetsBase):
    """콘텐츠 관리 클래스 v2.1 - 라이선스별 탭 구조"""

    # 콘텐츠 시트 컬럼 (0-based) - 새 구조 (마이그레이션 완료)
    COL_ACCOUNT_GROUP = 0       # A: account_group
    COL_KEYWORD = 1             # B: keyword
    COL_TITLE = 2               # C: title
    COL_CONTENT = 3             # D: content
    COL_CREATED_TIME = 4        # E: created_time
    COL_PUBLISHED_URL = 5       # F: published_url
    COL_PUBLISHED_TIME = 6      # G: published_time
    COL_PUBLISHED_ACCOUNT = 7   # H: published_account
    COL_CONTENT_ID = 8          # I: content_id
    COL_STATUS = 9              # J: status
    COL_SCHEDULED_TIME = 10     # K: scheduled_time (예약발행 시간)

    # 헤더 정의
    HEADERS = [
        'account_group', 'keyword', 'title', 'content', 'created_time',
        'published_url', 'published_time', 'published_account', 'content_id', 'status',
        'scheduled_time'
    ]

    def __init__(self):
        """초기화"""
        super().__init__()

    def _get_user_sheet_name(self, license_key):
        """라이선스 키로부터 시트 이름 생성"""
        # 이메일 형태면 @ 앞부분 사용, 아니면 키 그대로 사용
        if '@' in license_key:
            sheet_name = license_key.split('@')[0]
        else:
            sheet_name = license_key[:20]  # 최대 20자

        # 시트 이름에서 특수문자 제거 (Google Sheets 호환)
        sheet_name = ''.join(c for c in sheet_name if c.isalnum() or c in '_-')

        return f"콘텐츠_{sheet_name}"

    def _ensure_user_sheet(self, license_key):
        """사용자 시트가 없으면 생성"""
        sheet_name = self._get_user_sheet_name(license_key)

        # 먼저 시트 목록에서 존재 여부 확인
        all_sheets = self.get_all_sheet_names()
        if sheet_name in all_sheets:
            return sheet_name

        # 시트가 없으면 생성
        try:
            self._create_sheet_with_headers(sheet_name)
            print(f"✅ '{sheet_name}' 시트 자동 생성 완료")
            return sheet_name
        except Exception as e:
            error_msg = str(e)
            # 이미 존재하는 경우 (동시성 문제로 다른 프로세스가 먼저 생성)
            if 'already exists' in error_msg:
                print(f"ℹ️ '{sheet_name}' 시트가 이미 존재합니다.")
                return sheet_name
            # 다른 에러는 경고만 출력하고 계속 진행
            print(f"⚠️ 시트 생성 실패: {e}")
            print(f"   수동으로 '{sheet_name}' 시트를 생성하세요.")
            print(f"   헤더: {', '.join(self.HEADERS)}")
            # 예외를 던지지 않고 시트 이름 반환 시도 (이미 있을 수 있음)
            return sheet_name

    def _create_sheet_with_headers(self, sheet_name):
        """새 시트 생성 후 헤더 추가 및 서식 설정"""
        # 새 시트 생성
        body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }]
        }

        result = self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body=body
        ).execute()

        # 새로 생성된 시트 ID 가져오기
        sheet_id = result['replies'][0]['addSheet']['properties']['sheetId']

        # 헤더 추가 (A~K열, 11개)
        self.write_range(
            f'{sheet_name}!A1:K1',
            [self.HEADERS]
        )

        # 컬럼 너비 및 서식 설정 (새 구조)
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
                # D열 (content) 텍스트 줄바꿈 끄기 (CLIP으로 설정)
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
                }
            ]
        }

        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body=format_body
        ).execute()

    def generate_content_id(self):
        """고유 콘텐츠 ID 생성"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        import random
        random_suffix = random.randint(1000, 9999)
        return f"CNT{timestamp}{random_suffix}"

    def add_content(self, keyword, title, content, license_key, account_group='', scheduled_time='즉시발행'):
        """
        콘텐츠 추가 (라이선스별 탭에)

        Args:
            keyword: 발행 키워드
            title: 제목
            content: 본문
            license_key: 작성자 라이선스 키
            account_group: 발행 계정 그룹 (예: 사기, 현금화)
            scheduled_time: 예약발행 시간 ('즉시발행' 또는 'YYYY-MM-DD HH:MM' 형식)

        Returns:
            str: content_id
        """
        # 사용자 시트 확인/생성
        sheet_name = self._ensure_user_sheet(license_key)

        content_id = self.generate_content_id()

        # 새 구조: account_group, keyword, title, content, created_time,
        #         published_url, published_time, published_account, content_id, status, scheduled_time
        new_row = [
            account_group,            # A: account_group
            keyword,                  # B: keyword
            title,                    # C: title
            content,                  # D: content
            self.get_current_time(),  # E: created_time
            '',                       # F: published_url (빈값)
            '',                       # G: published_time (빈값)
            '',                       # H: published_account (빈값)
            content_id,               # I: content_id
            'ready',                  # J: status
            scheduled_time            # K: scheduled_time
        ]

        self.append_row(sheet_name, new_row)

        print(f"✅ 콘텐츠 추가 완료 (ID: {content_id}, 시트: {sheet_name}, 그룹: {account_group or '없음'}, 예약: {scheduled_time})")

        return content_id

    def get_all_contents(self, license_key=None, is_admin=False):
        """
        콘텐츠 가져오기

        - 일반 사용자: 본인 탭만 조회
        - 관리자: 모든 탭 조회 (TODO: 구현 예정)

        Args:
            license_key: 사용자 라이선스 키
            is_admin: 관리자 여부

        Returns:
            list: 콘텐츠 딕셔너리 리스트
        """
        if not license_key:
            return []

        sheet_name = self._get_user_sheet_name(license_key)

        try:
            values = self.read_range(f'{sheet_name}!A:K')  # A~K열 (11개)
        except Exception:
            # 시트가 없으면 빈 리스트
            return []

        if len(values) <= 1:
            return []

        results = []

        for i in range(1, len(values)):
            row = values[i]

            if len(row) < 1:  # 최소 1개 컬럼
                continue

            # 상태가 deleted인 경우 제외
            status = row[self.COL_STATUS] if len(row) > self.COL_STATUS else ''
            if status == 'deleted':
                continue

            results.append({
                'account_group': row[self.COL_ACCOUNT_GROUP] if len(row) > self.COL_ACCOUNT_GROUP else '',
                'keyword': row[self.COL_KEYWORD] if len(row) > self.COL_KEYWORD else '',
                'title': row[self.COL_TITLE] if len(row) > self.COL_TITLE else '',
                'content': row[self.COL_CONTENT] if len(row) > self.COL_CONTENT else '',
                'created_time': row[self.COL_CREATED_TIME] if len(row) > self.COL_CREATED_TIME else '',
                'published_url': row[self.COL_PUBLISHED_URL] if len(row) > self.COL_PUBLISHED_URL else '',
                'published_time': row[self.COL_PUBLISHED_TIME] if len(row) > self.COL_PUBLISHED_TIME else '',
                'published_account': row[self.COL_PUBLISHED_ACCOUNT] if len(row) > self.COL_PUBLISHED_ACCOUNT else '',
                'content_id': row[self.COL_CONTENT_ID] if len(row) > self.COL_CONTENT_ID else '',
                'status': status,
                'scheduled_time': row[self.COL_SCHEDULED_TIME] if len(row) > self.COL_SCHEDULED_TIME else '즉시발행',
                'created_by': license_key,  # 탭 이름으로부터 추론
                'row_num': i + 1,
                'sheet_name': sheet_name
            })

        return results

    def get_content_by_id(self, content_id, license_key=None):
        """
        ID로 콘텐츠 찾기

        Args:
            content_id: 콘텐츠 ID
            license_key: 라이선스 키 (시트 찾기용)

        Returns:
            dict or None
        """
        if not license_key:
            return None

        sheet_name = self._get_user_sheet_name(license_key)

        try:
            values = self.read_range(f'{sheet_name}!A:K')  # A~K열
        except Exception:
            return None

        if len(values) <= 1:
            return None

        for i in range(1, len(values)):
            row = values[i]

            if len(row) < 1:
                continue

            # content_id는 I열(인덱스 8)
            row_content_id = row[self.COL_CONTENT_ID] if len(row) > self.COL_CONTENT_ID else ''
            if row_content_id == content_id:
                return {
                    'account_group': row[self.COL_ACCOUNT_GROUP] if len(row) > self.COL_ACCOUNT_GROUP else '',
                    'keyword': row[self.COL_KEYWORD] if len(row) > self.COL_KEYWORD else '',
                    'title': row[self.COL_TITLE] if len(row) > self.COL_TITLE else '',
                    'content': row[self.COL_CONTENT] if len(row) > self.COL_CONTENT else '',
                    'created_time': row[self.COL_CREATED_TIME] if len(row) > self.COL_CREATED_TIME else '',
                    'published_url': row[self.COL_PUBLISHED_URL] if len(row) > self.COL_PUBLISHED_URL else '',
                    'published_time': row[self.COL_PUBLISHED_TIME] if len(row) > self.COL_PUBLISHED_TIME else '',
                    'published_account': row[self.COL_PUBLISHED_ACCOUNT] if len(row) > self.COL_PUBLISHED_ACCOUNT else '',
                    'content_id': row_content_id,
                    'status': row[self.COL_STATUS] if len(row) > self.COL_STATUS else '',
                    'scheduled_time': row[self.COL_SCHEDULED_TIME] if len(row) > self.COL_SCHEDULED_TIME else '즉시발행',
                    'created_by': license_key,
                    'row_num': i + 1,
                    'sheet_name': sheet_name
                }

        return None

    def update_content(self, content_id, title=None, content=None, keyword=None,
                      license_key=None, is_admin=False):
        """
        콘텐츠 수정

        Args:
            content_id: 콘텐츠 ID
            title: 수정할 제목
            content: 수정할 본문
            keyword: 수정할 키워드
            license_key: 요청자 라이선스 키
            is_admin: 관리자 여부

        Returns:
            bool: 성공 여부
        """
        content_data = self.get_content_by_id(content_id, license_key)

        if not content_data:
            print(f"❌ 콘텐츠를 찾을 수 없습니다 (ID: {content_id})")
            return False

        sheet_name = content_data['sheet_name']
        row_num = content_data['row_num']

        # 수정
        if keyword is not None:
            self.update_cell(sheet_name, row_num, self.COL_KEYWORD, keyword)

        if title is not None:
            self.update_cell(sheet_name, row_num, self.COL_TITLE, title)

        if content is not None:
            self.update_cell(sheet_name, row_num, self.COL_CONTENT, content)

        print(f"✅ 콘텐츠 수정 완료 (ID: {content_id})")

        return True

    def delete_content(self, content_id, license_key=None, is_admin=False):
        """
        콘텐츠 삭제

        Args:
            content_id: 콘텐츠 ID
            license_key: 요청자 라이선스 키
            is_admin: 관리자 여부

        Returns:
            bool: 성공 여부
        """
        content_data = self.get_content_by_id(content_id, license_key)

        if not content_data:
            print(f"❌ 콘텐츠를 찾을 수 없습니다 (ID: {content_id})")
            return False

        sheet_name = content_data['sheet_name']
        row_num = content_data['row_num']

        # 상태를 'deleted'로 변경 (실제 삭제 X)
        self.update_cell(sheet_name, row_num, self.COL_STATUS, 'deleted')

        print(f"✅ 콘텐츠 삭제 완료 (ID: {content_id})")

        return True

    def update_content_status(self, content_id, status, published_url=None, license_key=None):
        """
        콘텐츠 상태 업데이트

        Args:
            content_id: 콘텐츠 ID
            status: 새 상태 (ready/publishing/published)
            published_url: 발행된 URL (선택)
            license_key: 라이선스 키

        Returns:
            bool: 성공 여부
        """
        content_data = self.get_content_by_id(content_id, license_key)

        if not content_data:
            print(f"❌ 콘텐츠를 찾을 수 없습니다 (ID: {content_id})")
            return False

        sheet_name = content_data['sheet_name']
        row_num = content_data['row_num']

        # 상태 업데이트
        self.update_cell(sheet_name, row_num, self.COL_STATUS, status)

        # 발행 URL이 있으면 published_url 칸에 저장
        if published_url:
            self.update_cell(sheet_name, row_num, self.COL_PUBLISHED_URL, published_url)

        print(f"✅ 콘텐츠 상태 업데이트 완료 (ID: {content_id}, 상태: {status})")

        return True


# 테스트
if __name__ == '__main__':
    manager = ContentManagerV2()

    # 콘텐츠 추가 테스트
    content_id = manager.add_content(
        keyword='yatpor',
        title='Yatpor 사기 주의사항',
        content='본문 내용...',
        license_key='test@example.com',
        account_group='사기'
    )

    print(f"\n생성된 콘텐츠 ID: {content_id}")

    # 전체 콘텐츠 조회
    contents = manager.get_all_contents(license_key='test@example.com', is_admin=False)

    print(f"\n내 콘텐츠 개수: {len(contents)}")
