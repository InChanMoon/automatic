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

    # 콘텐츠 시트 컬럼 (0-based)
    COL_CONTENT_ID = 0          # A: content_id (고유 ID)
    COL_KEYWORD = 1             # B: keyword (발행 키워드)
    COL_TITLE = 2               # C: title
    COL_CONTENT = 3             # D: content
    COL_STATUS = 4              # E: status (ready/published/deleted)
    COL_CREATED_TIME = 5        # F: created_time
    COL_CUSTOM_PROMPT = 6       # G: custom_prompt
    COL_IMAGE_POSITIONS = 7     # H: image_positions (JSON)
    COL_AI_MODEL = 8            # I: ai_model
    COL_ACCOUNT_GROUP = 9       # J: account_group (발행 계정 그룹)

    # 헤더 정의
    HEADERS = [
        'content_id', 'keyword', 'title', 'content', 'status',
        'created_time', 'custom_prompt', 'image_positions', 'ai_model', 'account_group'
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

        try:
            # 시트 존재 확인
            self.read_range(f'{sheet_name}!A1:J1')
            return sheet_name
        except Exception:
            # 시트가 없으면 생성
            try:
                self._create_sheet_with_headers(sheet_name)
                print(f"✅ '{sheet_name}' 시트 자동 생성 완료")
                return sheet_name
            except Exception as e:
                print(f"⚠️ 시트 생성 실패: {e}")
                # 수동 생성 안내
                print(f"   수동으로 '{sheet_name}' 시트를 생성하세요.")
                print(f"   헤더: {', '.join(self.HEADERS)}")
                raise

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

        # 헤더 추가
        self.write_range(
            f'{sheet_name}!A1:J1',
            [self.HEADERS]
        )

        # 컬럼 너비 및 서식 설정
        format_body = {
            'requests': [
                # A열 (content_id): 180px
                {
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 0,
                            'endIndex': 1
                        },
                        'properties': {'pixelSize': 180},
                        'fields': 'pixelSize'
                    }
                },
                # B열 (keyword): 120px
                {
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 1,
                            'endIndex': 2
                        },
                        'properties': {'pixelSize': 120},
                        'fields': 'pixelSize'
                    }
                },
                # C열 (title): 300px (길게)
                {
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 2,
                            'endIndex': 3
                        },
                        'properties': {'pixelSize': 300},
                        'fields': 'pixelSize'
                    }
                },
                # D열 (content): 200px (짧게 - 줄넘김 있어도 짤림)
                {
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 3,
                            'endIndex': 4
                        },
                        'properties': {'pixelSize': 200},
                        'fields': 'pixelSize'
                    }
                },
                # E열 (status): 80px
                {
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 4,
                            'endIndex': 5
                        },
                        'properties': {'pixelSize': 80},
                        'fields': 'pixelSize'
                    }
                },
                # F열 (created_time): 150px
                {
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 5,
                            'endIndex': 6
                        },
                        'properties': {'pixelSize': 150},
                        'fields': 'pixelSize'
                    }
                },
                # G열 (custom_prompt): 150px
                {
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 6,
                            'endIndex': 7
                        },
                        'properties': {'pixelSize': 150},
                        'fields': 'pixelSize'
                    }
                },
                # H열 (image_positions): 100px
                {
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 7,
                            'endIndex': 8
                        },
                        'properties': {'pixelSize': 100},
                        'fields': 'pixelSize'
                    }
                },
                # I열 (ai_model): 130px
                {
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 8,
                            'endIndex': 9
                        },
                        'properties': {'pixelSize': 130},
                        'fields': 'pixelSize'
                    }
                },
                # 첫 번째 행 고정 (헤더)
                {
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': sheet_id,
                            'gridProperties': {
                                'frozenRowCount': 1
                            }
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
                            'userEnteredFormat': {
                                'wrapStrategy': 'CLIP'
                            }
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

    def add_content(self, keyword, title, content, license_key,
                   custom_prompt='', image_positions='[]', ai_model='', account_group=''):
        """
        콘텐츠 추가 (라이선스별 탭에)

        Args:
            keyword: 발행 키워드
            title: 제목
            content: 본문
            license_key: 작성자 라이선스 키
            custom_prompt: 사용자 정의 프롬프트
            image_positions: 이미지 위치 JSON
            ai_model: 사용된 AI 모델
            account_group: 발행 계정 그룹 (예: 사기, 현금화)

        Returns:
            str: content_id
        """
        # 사용자 시트 확인/생성
        sheet_name = self._ensure_user_sheet(license_key)

        content_id = self.generate_content_id()

        new_row = [
            content_id,
            keyword,
            title,
            content,
            'ready',  # 발행 준비 완료
            self.get_current_time(),
            custom_prompt,
            image_positions,
            ai_model,
            account_group
        ]

        self.append_row(sheet_name, new_row)

        print(f"✅ 콘텐츠 추가 완료 (ID: {content_id}, 시트: {sheet_name}, 그룹: {account_group or '없음'})")

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
            values = self.read_range(f'{sheet_name}!A:J')
        except Exception:
            # 시트가 없으면 빈 리스트
            return []

        if len(values) <= 1:
            return []

        results = []

        for i in range(1, len(values)):
            row = values[i]

            if len(row) < 5:
                continue

            # 상태가 deleted인 경우 제외
            status = row[self.COL_STATUS] if len(row) > self.COL_STATUS else ''
            if status == 'deleted':
                continue

            results.append({
                'content_id': row[self.COL_CONTENT_ID] if len(row) > self.COL_CONTENT_ID else '',
                'keyword': row[self.COL_KEYWORD] if len(row) > self.COL_KEYWORD else '',
                'title': row[self.COL_TITLE] if len(row) > self.COL_TITLE else '',
                'content': row[self.COL_CONTENT] if len(row) > self.COL_CONTENT else '',
                'status': status,
                'created_by': license_key,  # 탭 이름으로부터 추론
                'created_time': row[self.COL_CREATED_TIME] if len(row) > self.COL_CREATED_TIME else '',
                'custom_prompt': row[self.COL_CUSTOM_PROMPT] if len(row) > self.COL_CUSTOM_PROMPT else '',
                'image_positions': row[self.COL_IMAGE_POSITIONS] if len(row) > self.COL_IMAGE_POSITIONS else '[]',
                'ai_model': row[self.COL_AI_MODEL] if len(row) > self.COL_AI_MODEL else '',
                'account_group': row[self.COL_ACCOUNT_GROUP] if len(row) > self.COL_ACCOUNT_GROUP else '',
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
            values = self.read_range(f'{sheet_name}!A:J')
        except Exception:
            return None

        if len(values) <= 1:
            return None

        for i in range(1, len(values)):
            row = values[i]

            if len(row) < 1:
                continue

            if row[self.COL_CONTENT_ID] == content_id:
                return {
                    'content_id': row[self.COL_CONTENT_ID],
                    'keyword': row[self.COL_KEYWORD] if len(row) > self.COL_KEYWORD else '',
                    'title': row[self.COL_TITLE] if len(row) > self.COL_TITLE else '',
                    'content': row[self.COL_CONTENT] if len(row) > self.COL_CONTENT else '',
                    'status': row[self.COL_STATUS] if len(row) > self.COL_STATUS else '',
                    'created_by': license_key,
                    'created_time': row[self.COL_CREATED_TIME] if len(row) > self.COL_CREATED_TIME else '',
                    'custom_prompt': row[self.COL_CUSTOM_PROMPT] if len(row) > self.COL_CUSTOM_PROMPT else '',
                    'image_positions': row[self.COL_IMAGE_POSITIONS] if len(row) > self.COL_IMAGE_POSITIONS else '[]',
                    'ai_model': row[self.COL_AI_MODEL] if len(row) > self.COL_AI_MODEL else '',
                    'account_group': row[self.COL_ACCOUNT_GROUP] if len(row) > self.COL_ACCOUNT_GROUP else '',
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

        # 발행 URL이 있으면 custom_prompt 칸에 저장 (임시)
        if published_url:
            self.update_cell(sheet_name, row_num, self.COL_CUSTOM_PROMPT, published_url)

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
        ai_model='Gemini 2.5 Flash'
    )

    print(f"\n생성된 콘텐츠 ID: {content_id}")

    # 전체 콘텐츠 조회
    contents = manager.get_all_contents(license_key='test@example.com', is_admin=False)

    print(f"\n내 콘텐츠 개수: {len(contents)}")
