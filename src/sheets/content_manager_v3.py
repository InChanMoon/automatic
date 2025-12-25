"""
콘텐츠 관리자 V3 - 발행봇용

발행봇 관리자가 사용하는 콘텐츠 관리 기능:
- 모든 사용자 콘텐츠 조회 (account_group 필터링)
- 발행 상태 관리 (ready -> publishing -> published)
- 아카이브 이동 기능
- 시트 목록 캐싱으로 API 호출 최소화
"""

from datetime import datetime
from .base import SheetsBase


class ContentManagerV3(SheetsBase):
    """발행봇용 콘텐츠 관리자"""

    # 컬럼 인덱스 (0-based) - 새 구조 (마이그레이션 완료)
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

    # 상태값
    STATUS_DRAFT = 'draft'           # 초안 (검토 필요)
    STATUS_READY = 'ready'           # 발행 대기
    STATUS_PUBLISHING = 'publishing' # 발행 중
    STATUS_PUBLISHED = 'published'   # 발행 완료
    STATUS_FAILED = 'failed'         # 발행 실패

    # 캐시 유효 시간 (초)
    CACHE_TTL = 60

    def __init__(self):
        """초기화"""
        super().__init__()
        # 시트 목록 캐시
        self._sheet_cache = None
        self._sheet_cache_time = None

    def _is_cache_valid(self):
        """캐시 유효성 확인"""
        if not self._sheet_cache_time:
            return False
        elapsed = (datetime.now() - self._sheet_cache_time).total_seconds()
        return elapsed < self.CACHE_TTL

    def invalidate_cache(self):
        """캐시 무효화 (새 시트 생성 후 등)"""
        self._sheet_cache = None
        self._sheet_cache_time = None

    def get_all_content_sheets(self):
        """
        모든 콘텐츠 시트 목록 가져오기 (캐싱 적용)

        Returns:
            list: 콘텐츠 시트 이름 리스트
        """
        # 캐시 유효하면 캐시 반환
        if self._is_cache_valid() and self._sheet_cache is not None:
            return self._sheet_cache

        # 캐시 갱신
        all_sheets = self.get_all_sheet_names()
        self._sheet_cache = [name for name in all_sheets if name.startswith('콘텐츠_')]
        self._sheet_cache_time = datetime.now()
        return self._sheet_cache

    def get_ready_contents_by_group(self, account_group):
        """
        특정 계정그룹의 발행대기(ready) 콘텐츠 가져오기

        Args:
            account_group: 계정 그룹명 (예: '사기', '현금화')

        Returns:
            list: 발행대기 콘텐츠 리스트
        """
        contents = []
        content_sheets = self.get_all_content_sheets()

        for sheet_name in content_sheets:
            try:
                values = self.read_range(f'{sheet_name}!A:K')  # A~K열 (11개 컬럼)
                if len(values) <= 1:
                    continue

                for i in range(1, len(values)):
                    row = values[i]
                    # 최소 1개 컬럼
                    if len(row) < 1:
                        continue

                    # account_group(A열)과 status(J열) 확인
                    row_group = row[self.COL_ACCOUNT_GROUP] if len(row) > self.COL_ACCOUNT_GROUP else ''
                    row_status = row[self.COL_STATUS] if len(row) > self.COL_STATUS else ''

                    if row_group == account_group and row_status == self.STATUS_READY:
                        contents.append({
                            'account_group': row_group,
                            'keyword': row[self.COL_KEYWORD] if len(row) > self.COL_KEYWORD else '',
                            'title': row[self.COL_TITLE] if len(row) > self.COL_TITLE else '',
                            'content': row[self.COL_CONTENT] if len(row) > self.COL_CONTENT else '',
                            'created_time': row[self.COL_CREATED_TIME] if len(row) > self.COL_CREATED_TIME else '',
                            'published_url': row[self.COL_PUBLISHED_URL] if len(row) > self.COL_PUBLISHED_URL else '',
                            'published_time': row[self.COL_PUBLISHED_TIME] if len(row) > self.COL_PUBLISHED_TIME else '',
                            'published_account': row[self.COL_PUBLISHED_ACCOUNT] if len(row) > self.COL_PUBLISHED_ACCOUNT else '',
                            'content_id': row[self.COL_CONTENT_ID] if len(row) > self.COL_CONTENT_ID else '',
                            'status': row_status,
                            'scheduled_time': row[self.COL_SCHEDULED_TIME] if len(row) > self.COL_SCHEDULED_TIME else '즉시발행',
                            'row_num': i + 1,
                            'sheet_name': sheet_name
                        })
            except Exception as e:
                print(f"[!] {sheet_name} 읽기 실패: {e}")
                continue

        return contents

    def get_all_ready_contents(self):
        """
        모든 발행대기(ready) 콘텐츠 가져오기 (그룹별로 분류)

        Returns:
            dict: {account_group: [콘텐츠 리스트]}
        """
        result = {}
        account_groups = self.get_account_groups()

        for group in account_groups:
            contents = self.get_ready_contents_by_group(group)
            if contents:
                result[group] = contents

        return result

    def update_status(self, sheet_name, row_num, new_status):
        """
        콘텐츠 상태 업데이트

        Args:
            sheet_name: 시트 이름
            row_num: 행 번호 (1-based)
            new_status: 새 상태값

        Returns:
            bool: 성공 여부
        """
        try:
            self.update_cell(sheet_name, row_num, self.COL_STATUS, new_status)
            return True
        except Exception as e:
            print(f"[X] 상태 업데이트 실패: {e}")
            return False

    def mark_as_publishing(self, sheet_name, row_num):
        """발행 중으로 표시"""
        return self.update_status(sheet_name, row_num, self.STATUS_PUBLISHING)

    def release_publishing_lock(self, sheet_name, row_num):
        """발행 중 상태를 다시 ready로 되돌림 (계정 문제로 실패 시)"""
        return self.update_status(sheet_name, row_num, self.STATUS_READY)

    def mark_as_published(self, sheet_name, row_num, published_url='', account_id=''):
        """
        발행 완료로 표시 + URL/시간/계정 저장

        Args:
            sheet_name: 시트 이름
            row_num: 행 번호 (1-based)
            published_url: 발행된 블로그 URL
            account_id: 발행에 사용된 계정 ID
        """
        try:
            # 상태 변경
            self.update_cell(sheet_name, row_num, self.COL_STATUS, self.STATUS_PUBLISHED)

            # 발행 URL 저장
            if published_url:
                self.update_cell(sheet_name, row_num, self.COL_PUBLISHED_URL, published_url)

            # 발행 시간 저장
            self.update_cell(sheet_name, row_num, self.COL_PUBLISHED_TIME, self.get_current_time())

            # 발행 계정 저장
            if account_id:
                self.update_cell(sheet_name, row_num, self.COL_PUBLISHED_ACCOUNT, account_id)

            return True
        except Exception as e:
            print(f"[X] 발행 완료 처리 실패: {e}")
            return False

    def mark_as_failed(self, sheet_name, row_num):
        """발행 실패로 표시"""
        return self.update_status(sheet_name, row_num, self.STATUS_FAILED)

    def get_content_stats(self):
        """
        전체 콘텐츠 통계

        Returns:
            dict: {
                'total': 전체 수,
                'by_status': {status: count},
                'by_group': {group: count}
            }
        """
        stats = {
            'total': 0,
            'by_status': {
                self.STATUS_READY: 0,
                self.STATUS_PUBLISHING: 0,
                self.STATUS_PUBLISHED: 0,
                self.STATUS_FAILED: 0
            },
            'by_group': {}
        }

        content_sheets = self.get_all_content_sheets()

        for sheet_name in content_sheets:
            try:
                values = self.read_range(f'{sheet_name}!A:J')  # A~J열
                if len(values) <= 1:
                    continue

                for i in range(1, len(values)):
                    row = values[i]
                    if len(row) < 1:
                        continue

                    status = row[self.COL_STATUS] if len(row) > self.COL_STATUS else ''
                    group = row[self.COL_ACCOUNT_GROUP] if len(row) > self.COL_ACCOUNT_GROUP else ''

                    stats['total'] += 1

                    if status in stats['by_status']:
                        stats['by_status'][status] += 1

                    if group:
                        stats['by_group'][group] = stats['by_group'].get(group, 0) + 1

            except Exception as e:
                print(f"[!] {sheet_name} 통계 읽기 실패: {e}")
                continue

        return stats

    def get_content_by_id_admin(self, content_id):
        """
        콘텐츠 ID로 콘텐츠 찾기 (관리자용 - 모든 시트 검색)

        Args:
            content_id: 콘텐츠 ID

        Returns:
            dict or None
        """
        content_sheets = self.get_all_content_sheets()

        for sheet_name in content_sheets:
            try:
                values = self.read_range(f'{sheet_name}!A:J')  # A~J열
                if len(values) <= 1:
                    continue

                for i in range(1, len(values)):
                    row = values[i]
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
                            'row_num': i + 1,
                            'sheet_name': sheet_name
                        }
            except Exception:
                continue

        return None


# 테스트
if __name__ == '__main__':
    manager = ContentManagerV3()

    print("=" * 50)
    print("ContentManagerV3 테스트")
    print("=" * 50)

    # 콘텐츠 시트 목록
    sheets = manager.get_all_content_sheets()
    print(f"\n콘텐츠 시트: {sheets}")

    # 계정 그룹 목록
    groups = manager.get_account_groups()
    print(f"계정 그룹: {groups}")

    # 그룹별 대기 콘텐츠
    for group in groups:
        contents = manager.get_ready_contents_by_group(group)
        print(f"\n[{group}] 발행대기: {len(contents)}개")
        for c in contents[:3]:  # 최대 3개만 출력
            print(f"  - {c['content_id']}: {c['title'][:30]}...")

    # 통계
    stats = manager.get_content_stats()
    print(f"\n전체 통계:")
    print(f"  총 콘텐츠: {stats['total']}개")
    print(f"  상태별: {stats['by_status']}")
    print(f"  그룹별: {stats['by_group']}")
