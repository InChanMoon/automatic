"""
네이버 계정 관리 모듈 V2

계정 그룹별 관리:
- 계정 그룹별 계정 목록 조회 (계정_사기, 계정_현금화 등)
- 계정 상태 관리 (active/suspended/banned)
- 일일 발행 한도 관리
- 계정 로테이션 (순번 발행)
"""

from datetime import datetime
from .base import SheetsBase


class AccountManager(SheetsBase):
    """네이버 계정 관리 클래스 (그룹별)"""

    # 계정 시트 컬럼 인덱스 (0-based)
    COL_ACCOUNT_ID = 0      # A: account_id (네이버 ID)
    COL_PASSWORD = 1        # B: password
    COL_STATUS = 2          # C: status (active/suspended/banned)
    COL_DAILY_LIMIT = 3     # D: daily_limit (일일 발행 한도)
    COL_TODAY_COUNT = 4     # E: today_count (오늘 발행 수)
    COL_LAST_USED = 5       # F: last_used (마지막 사용 시간)
    COL_CREATED_DATE = 6    # G: created_date (등록일)
    COL_MEMO = 7            # H: memo

    # 계정 상태값
    STATUS_ACTIVE = 'active'        # 활성
    STATUS_SUSPENDED = 'suspended'  # 일시정지
    STATUS_BANNED = 'banned'        # 영구정지

    def __init__(self):
        """초기화"""
        super().__init__()

    def _get_sheet_name(self, group_name):
        """그룹명으로 시트 이름 생성"""
        return f"계정_{group_name}"

    def get_accounts_by_group(self, group_name, active_only=True):
        """
        특정 그룹의 계정 목록 가져오기

        Args:
            group_name: 그룹명 (예: '사기', '현금화')
            active_only: True면 active 상태만

        Returns:
            list: 계정 딕셔너리 리스트
        """
        sheet_name = self._get_sheet_name(group_name)

        try:
            values = self.read_range(f'{sheet_name}!A:H')
        except Exception as e:
            print(f"[X] {sheet_name} 읽기 실패: {e}")
            return []

        if len(values) <= 1:
            return []

        accounts = []
        for i in range(1, len(values)):
            row = values[i]
            if len(row) < 3:
                continue

            status = row[self.COL_STATUS] if len(row) > self.COL_STATUS else ''

            if active_only and status != self.STATUS_ACTIVE:
                continue

            accounts.append({
                'account_id': row[self.COL_ACCOUNT_ID],
                'password': row[self.COL_PASSWORD] if len(row) > self.COL_PASSWORD else '',
                'status': status,
                'daily_limit': int(row[self.COL_DAILY_LIMIT]) if len(row) > self.COL_DAILY_LIMIT and row[self.COL_DAILY_LIMIT] else 10,
                'today_count': int(row[self.COL_TODAY_COUNT]) if len(row) > self.COL_TODAY_COUNT and row[self.COL_TODAY_COUNT] else 0,
                'last_used': row[self.COL_LAST_USED] if len(row) > self.COL_LAST_USED else '',
                'created_date': row[self.COL_CREATED_DATE] if len(row) > self.COL_CREATED_DATE else '',
                'memo': row[self.COL_MEMO] if len(row) > self.COL_MEMO else '',
                'row_num': i + 1,
                'group_name': group_name
            })

        return accounts

    def get_available_account(self, group_name):
        """
        발행 가능한 계정 1개 가져오기 (로테이션)

        - active 상태
        - today_count < daily_limit
        - last_used가 가장 오래된 계정 우선

        Args:
            group_name: 그룹명

        Returns:
            dict or None: 사용 가능한 계정
        """
        accounts = self.get_accounts_by_group(group_name, active_only=True)

        available = []
        for acc in accounts:
            # 일일 한도 체크
            if acc['today_count'] >= acc['daily_limit']:
                continue

            available.append(acc)

        if not available:
            return None

        # last_used 기준 정렬 (오래된 것 우선)
        available.sort(key=lambda x: x['last_used'] or '0000-00-00 00:00:00')

        return available[0]

    def increment_usage(self, group_name, account_id):
        """
        계정 사용 카운트 증가

        Args:
            group_name: 그룹명
            account_id: 계정 ID

        Returns:
            bool: 성공 여부
        """
        sheet_name = self._get_sheet_name(group_name)

        try:
            values = self.read_range(f'{sheet_name}!A:H')
        except Exception:
            return False

        if len(values) <= 1:
            return False

        for i in range(1, len(values)):
            row = values[i]
            if len(row) > 0 and row[0] == account_id:
                row_num = i + 1

                # today_count 증가
                current_count = int(row[self.COL_TODAY_COUNT]) if len(row) > self.COL_TODAY_COUNT and row[self.COL_TODAY_COUNT] else 0
                new_count = current_count + 1

                # last_used 업데이트
                current_time = self.get_current_time()

                try:
                    # today_count 업데이트
                    self.update_cell(sheet_name, row_num, self.COL_TODAY_COUNT, str(new_count))
                    # last_used 업데이트
                    self.update_cell(sheet_name, row_num, self.COL_LAST_USED, current_time)
                    return True
                except Exception as e:
                    print(f"[X] 사용량 업데이트 실패: {e}")
                    return False

        return False

    def reset_daily_counts(self, group_name=None):
        """
        일일 카운트 리셋 (매일 자정에 실행)

        Args:
            group_name: 특정 그룹만 리셋 (None이면 모든 그룹)

        Returns:
            int: 리셋된 계정 수
        """
        groups = [group_name] if group_name else self.get_account_groups()
        reset_count = 0

        for group in groups:
            sheet_name = self._get_sheet_name(group)

            try:
                values = self.read_range(f'{sheet_name}!A:H')
            except Exception:
                continue

            if len(values) <= 1:
                continue

            for i in range(1, len(values)):
                row = values[i]
                if len(row) > self.COL_TODAY_COUNT:
                    current_count = row[self.COL_TODAY_COUNT] if len(row) > self.COL_TODAY_COUNT else '0'
                    if current_count and current_count != '0':
                        try:
                            self.update_cell(sheet_name, i + 1, self.COL_TODAY_COUNT, '0')
                            reset_count += 1
                        except Exception:
                            pass

        return reset_count

    def update_status(self, group_name, account_id, new_status):
        """
        계정 상태 변경

        Args:
            group_name: 그룹명
            account_id: 계정 ID
            new_status: 새 상태 (active/suspended/banned)

        Returns:
            bool: 성공 여부
        """
        sheet_name = self._get_sheet_name(group_name)

        try:
            values = self.read_range(f'{sheet_name}!A:H')
        except Exception:
            return False

        if len(values) <= 1:
            return False

        for i in range(1, len(values)):
            row = values[i]
            if len(row) > 0 and row[0] == account_id:
                try:
                    self.update_cell(sheet_name, i + 1, self.COL_STATUS, new_status)
                    return True
                except Exception:
                    return False

        return False

    def add_account(self, group_name, account_id, password, daily_limit=10, memo=''):
        """
        새 계정 추가

        Args:
            group_name: 그룹명
            account_id: 네이버 ID
            password: 비밀번호
            daily_limit: 일일 한도
            memo: 메모

        Returns:
            bool: 성공 여부
        """
        sheet_name = self._get_sheet_name(group_name)

        new_row = [
            account_id,
            password,
            self.STATUS_ACTIVE,
            str(daily_limit),
            '0',  # today_count
            '',   # last_used
            self.get_current_date(),  # created_date
            memo
        ]

        try:
            self.append_row(sheet_name, new_row)
            return True
        except Exception as e:
            print(f"[X] 계정 추가 실패: {e}")
            return False

    def get_group_stats(self, group_name):
        """
        그룹 계정 통계

        Args:
            group_name: 그룹명

        Returns:
            dict: 통계 정보
        """
        accounts = self.get_accounts_by_group(group_name, active_only=False)

        stats = {
            'total': len(accounts),
            'active': 0,
            'suspended': 0,
            'banned': 0,
            'available_today': 0,
            'total_capacity': 0,
            'used_today': 0
        }

        for acc in accounts:
            if acc['status'] == self.STATUS_ACTIVE:
                stats['active'] += 1
                stats['total_capacity'] += acc['daily_limit']
                stats['used_today'] += acc['today_count']

                if acc['today_count'] < acc['daily_limit']:
                    stats['available_today'] += 1
            elif acc['status'] == self.STATUS_SUSPENDED:
                stats['suspended'] += 1
            elif acc['status'] == self.STATUS_BANNED:
                stats['banned'] += 1

        stats['remaining_capacity'] = stats['total_capacity'] - stats['used_today']

        return stats

    def get_all_groups_stats(self):
        """
        모든 그룹 통계

        Returns:
            dict: {group_name: stats}
        """
        groups = self.get_account_groups()
        return {group: self.get_group_stats(group) for group in groups}


# 테스트
if __name__ == '__main__':
    manager = AccountManager()

    print("=" * 50)
    print("AccountManager 테스트")
    print("=" * 50)

    # 계정 그룹 목록
    groups = manager.get_account_groups()
    print(f"\n계정 그룹: {groups}")

    # 그룹별 통계
    for group in groups:
        stats = manager.get_group_stats(group)
        print(f"\n[{group}] 통계:")
        print(f"  총 계정: {stats['total']}개")
        print(f"  활성: {stats['active']}개")
        print(f"  오늘 가용: {stats['available_today']}개")
        print(f"  일일 용량: {stats['total_capacity']}개")
        print(f"  오늘 사용: {stats['used_today']}개")
        print(f"  남은 용량: {stats['remaining_capacity']}개")

        # 사용 가능한 계정
        available = manager.get_available_account(group)
        if available:
            print(f"  다음 사용 계정: {available['account_id']}")
        else:
            print(f"  사용 가능한 계정 없음")
