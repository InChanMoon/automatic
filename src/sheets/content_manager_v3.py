"""
콘텐츠 관리자 V3 - 발행봇용

발행봇 관리자가 사용하는 콘텐츠 관리 기능:
- 모든 사용자 콘텐츠 조회 (account_group 필터링)
- 발행 상태 관리 (ready -> publishing -> published)
- 아카이브 이동 기능
"""

from datetime import datetime
from .base import SheetsBase


class ContentManagerV3(SheetsBase):
    """발행봇용 콘텐츠 관리자"""

    # 컬럼 인덱스 (0-based)
    COL_CONTENT_ID = 0      # A: content_id
    COL_KEYWORD = 1         # B: keyword
    COL_TITLE = 2           # C: title
    COL_CONTENT = 3         # D: content
    COL_STATUS = 4          # E: status (ready/publishing/published/failed)
    COL_CREATED_TIME = 5    # F: created_time
    COL_CUSTOM_PROMPT = 6   # G: custom_prompt
    COL_IMAGE_POSITIONS = 7 # H: image_positions
    COL_AI_MODEL = 8        # I: ai_model
    COL_ACCOUNT_GROUP = 9   # J: account_group
    COL_PUBLISHED_URL = 10  # K: published_url (발행된 URL)
    COL_PUBLISHED_TIME = 11 # L: published_time (발행 시간)
    COL_PUBLISHED_ACCOUNT = 12  # M: published_account (발행 계정)

    # 상태값
    STATUS_READY = 'ready'           # 발행 대기
    STATUS_PUBLISHING = 'publishing' # 발행 중
    STATUS_PUBLISHED = 'published'   # 발행 완료
    STATUS_FAILED = 'failed'         # 발행 실패

    def __init__(self):
        """초기화"""
        super().__init__()

    def get_all_content_sheets(self):
        """
        모든 콘텐츠 시트 목록 가져오기

        Returns:
            list: 콘텐츠 시트 이름 리스트
        """
        all_sheets = self.get_all_sheet_names()
        return [name for name in all_sheets if name.startswith('콘텐츠_')]

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
                values = self.read_range(f'{sheet_name}!A:J')
                if len(values) <= 1:
                    continue

                for i in range(1, len(values)):
                    row = values[i]
                    if len(row) < 10:
                        continue

                    # account_group과 status 확인
                    row_group = row[self.COL_ACCOUNT_GROUP] if len(row) > self.COL_ACCOUNT_GROUP else ''
                    row_status = row[self.COL_STATUS] if len(row) > self.COL_STATUS else ''

                    if row_group == account_group and row_status == self.STATUS_READY:
                        contents.append({
                            'content_id': row[self.COL_CONTENT_ID],
                            'keyword': row[self.COL_KEYWORD] if len(row) > self.COL_KEYWORD else '',
                            'title': row[self.COL_TITLE] if len(row) > self.COL_TITLE else '',
                            'content': row[self.COL_CONTENT] if len(row) > self.COL_CONTENT else '',
                            'status': row_status,
                            'created_time': row[self.COL_CREATED_TIME] if len(row) > self.COL_CREATED_TIME else '',
                            'custom_prompt': row[self.COL_CUSTOM_PROMPT] if len(row) > self.COL_CUSTOM_PROMPT else '',
                            'image_positions': row[self.COL_IMAGE_POSITIONS] if len(row) > self.COL_IMAGE_POSITIONS else '[]',
                            'ai_model': row[self.COL_AI_MODEL] if len(row) > self.COL_AI_MODEL else '',
                            'account_group': row_group,
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
                values = self.read_range(f'{sheet_name}!A:J')
                if len(values) <= 1:
                    continue

                for i in range(1, len(values)):
                    row = values[i]
                    if len(row) < 5:
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
                values = self.read_range(f'{sheet_name}!A:J')
                if len(values) <= 1:
                    continue

                for i in range(1, len(values)):
                    row = values[i]
                    if len(row) > 0 and row[0] == content_id:
                        return {
                            'content_id': row[self.COL_CONTENT_ID],
                            'keyword': row[self.COL_KEYWORD] if len(row) > self.COL_KEYWORD else '',
                            'title': row[self.COL_TITLE] if len(row) > self.COL_TITLE else '',
                            'content': row[self.COL_CONTENT] if len(row) > self.COL_CONTENT else '',
                            'status': row[self.COL_STATUS] if len(row) > self.COL_STATUS else '',
                            'created_time': row[self.COL_CREATED_TIME] if len(row) > self.COL_CREATED_TIME else '',
                            'custom_prompt': row[self.COL_CUSTOM_PROMPT] if len(row) > self.COL_CUSTOM_PROMPT else '',
                            'image_positions': row[self.COL_IMAGE_POSITIONS] if len(row) > self.COL_IMAGE_POSITIONS else '[]',
                            'ai_model': row[self.COL_AI_MODEL] if len(row) > self.COL_AI_MODEL else '',
                            'account_group': row[self.COL_ACCOUNT_GROUP] if len(row) > self.COL_ACCOUNT_GROUP else '',
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
