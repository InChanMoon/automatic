"""
콘텐츠 관리 모듈

콘텐츠 생성, 할당, 발행 상태 관리
"""

from .base import SheetsBase


class ContentManager(SheetsBase):
    """콘텐츠 관리 클래스"""

    SHEET_NAME = '콘텐츠'

    # 컬럼 인덱스 (0-based)
    COL_KEYWORD = 0              # A: keyword
    COL_TITLE = 1                # B: title
    COL_CONTENT = 2              # C: content
    COL_STATUS = 3               # D: status
    COL_LICENSE_KEY = 4          # E: license_key
    COL_ASSIGNED_ACCOUNT = 5     # F: assigned_account
    COL_PUBLISHED_URL = 6        # G: published_url
    COL_CREATED_TIME = 7         # H: created_time
    COL_PUBLISHED_TIME = 8       # I: published_time

    def add_keyword_request(self, keyword, license_key):
        """
        키워드 요청 추가 (pending 상태로)

        Args:
            keyword: 키워드
            license_key: 요청한 라이선스 키

        Returns:
            int: 추가된 행 번호
        """
        new_row = [
            keyword,
            '',  # title (나중에 생성)
            '',  # content (나중에 생성)
            'pending',
            license_key,
            '',  # assigned_account
            '',  # published_url
            self.get_current_time(),
            ''   # published_time
        ]

        self.append_row(self.SHEET_NAME, new_row)

        # 방금 추가한 행 번호 찾기
        row_num = self.find_row_by_column(self.SHEET_NAME, self.COL_KEYWORD, keyword)

        print(f"✅ 키워드 '{keyword}' 요청 추가 완료 (행: {row_num})")

        return row_num

    def get_pending_content(self):
        """
        pending 상태인 콘텐츠 1개 가져오기

        Returns:
            dict: {
                'keyword': str,
                'license_key': str,
                'row_num': int
            } 또는 None
        """
        values = self.read_range(f'{self.SHEET_NAME}!A:I')

        if len(values) <= 1:
            return None

        for i in range(1, len(values)):
            row = values[i]
            status = row[self.COL_STATUS] if len(row) > self.COL_STATUS else ''

            if status == 'pending':
                return {
                    'keyword': row[self.COL_KEYWORD] if len(row) > self.COL_KEYWORD else '',
                    'license_key': row[self.COL_LICENSE_KEY] if len(row) > self.COL_LICENSE_KEY else '',
                    'row_num': i + 1
                }

        return None

    def update_generated_content(self, row_num, title, content):
        """
        생성된 콘텐츠 업데이트 (pending → generated)

        Args:
            row_num: 행 번호
            title: 생성된 제목
            content: 생성된 본문
        """
        self.update_cell(self.SHEET_NAME, row_num, self.COL_TITLE, title)
        self.update_cell(self.SHEET_NAME, row_num, self.COL_CONTENT, content)
        self.update_cell(self.SHEET_NAME, row_num, self.COL_STATUS, 'generated')

        print(f"✅ 행 {row_num}: 콘텐츠 생성 완료")

    def get_generated_content(self):
        """
        generated 상태인 콘텐츠 1개 가져오기 (발행 대기)

        Returns:
            dict: {
                'keyword': str,
                'title': str,
                'content': str,
                'license_key': str,
                'row_num': int
            } 또는 None
        """
        values = self.read_range(f'{self.SHEET_NAME}!A:I')

        if len(values) <= 1:
            return None

        for i in range(1, len(values)):
            row = values[i]
            status = row[self.COL_STATUS] if len(row) > self.COL_STATUS else ''

            if status == 'generated':
                return {
                    'keyword': row[self.COL_KEYWORD] if len(row) > self.COL_KEYWORD else '',
                    'title': row[self.COL_TITLE] if len(row) > self.COL_TITLE else '',
                    'content': row[self.COL_CONTENT] if len(row) > self.COL_CONTENT else '',
                    'license_key': row[self.COL_LICENSE_KEY] if len(row) > self.COL_LICENSE_KEY else '',
                    'row_num': i + 1
                }

        return None

    def mark_publishing(self, row_num, naver_id):
        """
        발행 시작 (generated → publishing)

        Args:
            row_num: 행 번호
            naver_id: 사용할 네이버 계정
        """
        self.update_cell(self.SHEET_NAME, row_num, self.COL_STATUS, 'publishing')
        self.update_cell(self.SHEET_NAME, row_num, self.COL_ASSIGNED_ACCOUNT, naver_id)

        print(f"✅ 행 {row_num}: 발행 시작 (계정: {naver_id})")

    def mark_published(self, row_num, published_url):
        """
        발행 완료 (publishing → published)

        Args:
            row_num: 행 번호
            published_url: 발행된 URL
        """
        self.update_cell(self.SHEET_NAME, row_num, self.COL_STATUS, 'published')
        self.update_cell(self.SHEET_NAME, row_num, self.COL_PUBLISHED_URL, published_url)
        self.update_cell(self.SHEET_NAME, row_num, self.COL_PUBLISHED_TIME, self.get_current_time())

        print(f"✅ 행 {row_num}: 발행 완료 ({published_url})")

    def mark_failed(self, row_num):
        """
        발행 실패 (publishing/generated → failed)

        Args:
            row_num: 행 번호
        """
        self.update_cell(self.SHEET_NAME, row_num, self.COL_STATUS, 'failed')

        print(f"⚠️ 행 {row_num}: 발행 실패")

    def get_content_by_status(self, status):
        """
        특정 상태의 모든 콘텐츠 가져오기

        Args:
            status: pending/generated/publishing/published/failed

        Returns:
            list: 콘텐츠 딕셔너리 리스트
        """
        values = self.read_range(f'{self.SHEET_NAME}!A:I')

        if len(values) <= 1:
            return []

        results = []
        for i in range(1, len(values)):
            row = values[i]
            row_status = row[self.COL_STATUS] if len(row) > self.COL_STATUS else ''

            if row_status == status:
                results.append({
                    'keyword': row[self.COL_KEYWORD] if len(row) > self.COL_KEYWORD else '',
                    'title': row[self.COL_TITLE] if len(row) > self.COL_TITLE else '',
                    'content': row[self.COL_CONTENT] if len(row) > self.COL_CONTENT else '',
                    'status': row_status,
                    'license_key': row[self.COL_LICENSE_KEY] if len(row) > self.COL_LICENSE_KEY else '',
                    'assigned_account': row[self.COL_ASSIGNED_ACCOUNT] if len(row) > self.COL_ASSIGNED_ACCOUNT else '',
                    'published_url': row[self.COL_PUBLISHED_URL] if len(row) > self.COL_PUBLISHED_URL else '',
                    'created_time': row[self.COL_CREATED_TIME] if len(row) > self.COL_CREATED_TIME else '',
                    'published_time': row[self.COL_PUBLISHED_TIME] if len(row) > self.COL_PUBLISHED_TIME else '',
                    'row_num': i + 1
                })

        return results
