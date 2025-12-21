"""
네이버 계정 관리 모듈 V3

계정 그룹별 관리:
- 계정 그룹별 계정 목록 조회 (계정_사기, 계정_현금화 등)
- 계정 상태 관리 (active/suspended/banned/captcha)
- 계정 로테이션 (last_used 기준)

컬럼 구조 (간소화):
- A: account_id (네이버 ID)
- B: password
- C: status (active/suspended/banned/captcha)
- D: last_used (마지막 사용 시간)
"""

from datetime import datetime
from .base import SheetsBase


class AccountManager(SheetsBase):
    """네이버 계정 관리 클래스 (그룹별)"""

    # 계정 시트 컬럼 인덱스 (0-based) - 간소화된 구조
    COL_ACCOUNT_ID = 0      # A: account_id (네이버 ID)
    COL_PASSWORD = 1        # B: password
    COL_STATUS = 2          # C: status (active/suspended/banned)
    COL_LAST_USED = 3       # D: last_used (마지막 사용 시간)

    # 계정 상태값
    STATUS_ACTIVE = 'active'        # 활성
    STATUS_SUSPENDED = 'suspended'  # 보호조치 (영구 사용 불가)
    STATUS_BANNED = 'banned'        # 영구정지
    STATUS_CAPTCHA = 'captcha'      # 캡차 필요 (수동 로그인 대기)

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
            values = self.read_range(f'{sheet_name}!A:D')
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
                'last_used': row[self.COL_LAST_USED] if len(row) > self.COL_LAST_USED else '',
                'row_num': i + 1,
                'group_name': group_name
            })

        return accounts

    def get_available_account(self, group_name):
        """
        발행 가능한 계정 1개 가져오기 (로테이션)

        - active 상태
        - last_used가 가장 오래된 계정 우선

        Args:
            group_name: 그룹명

        Returns:
            dict or None: 사용 가능한 계정
        """
        accounts = self.get_accounts_by_group(group_name, active_only=True)

        if not accounts:
            return None

        # last_used 기준 정렬 (오래된 것 우선)
        accounts.sort(key=lambda x: x['last_used'] or '0000-00-00 00:00:00')

        return accounts[0]

    def get_account_by_id(self, group_name, account_id):
        """
        계정 ID로 특정 계정 정보 가져오기

        Args:
            group_name: 그룹명
            account_id: 계정 ID

        Returns:
            dict or None: 계정 정보
        """
        accounts = self.get_accounts_by_group(group_name, active_only=False)

        for acc in accounts:
            if acc['account_id'] == account_id:
                return acc

        return None

    def update_last_used(self, group_name, account_id):
        """
        계정 마지막 사용 시간 업데이트

        Args:
            group_name: 그룹명
            account_id: 계정 ID

        Returns:
            bool: 성공 여부
        """
        sheet_name = self._get_sheet_name(group_name)

        try:
            values = self.read_range(f'{sheet_name}!A:D')
        except Exception:
            return False

        if len(values) <= 1:
            return False

        for i in range(1, len(values)):
            row = values[i]
            if len(row) > 0 and row[0] == account_id:
                row_num = i + 1
                current_time = self.get_current_time()

                try:
                    self.update_cell(sheet_name, row_num, self.COL_LAST_USED, current_time)
                    return True
                except Exception as e:
                    print(f"[X] last_used 업데이트 실패: {e}")
                    return False

        return False

    # 하위호환: increment_usage -> update_last_used
    def increment_usage(self, group_name, account_id):
        """하위호환용 - update_last_used 호출"""
        return self.update_last_used(group_name, account_id)


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
            values = self.read_range(f'{sheet_name}!A:D')
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

    def add_account(self, group_name, account_id, password):
        """
        새 계정 추가

        Args:
            group_name: 그룹명
            account_id: 네이버 ID
            password: 비밀번호

        Returns:
            bool: 성공 여부
        """
        sheet_name = self._get_sheet_name(group_name)

        new_row = [
            account_id,
            password,
            self.STATUS_ACTIVE,
            ''   # last_used
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
            'captcha': 0
        }

        for acc in accounts:
            if acc['status'] == self.STATUS_ACTIVE:
                stats['active'] += 1
            elif acc['status'] == self.STATUS_SUSPENDED:
                stats['suspended'] += 1
            elif acc['status'] == self.STATUS_BANNED:
                stats['banned'] += 1
            elif acc['status'] == self.STATUS_CAPTCHA:
                stats['captcha'] += 1

        return stats

    def get_all_groups_stats(self):
        """
        모든 그룹 통계

        Returns:
            dict: {group_name: stats}
        """
        groups = self.get_account_groups()
        return {group: self.get_group_stats(group) for group in groups}

    def get_captcha_accounts(self, group_name):
        """
        캡차 필요 상태의 계정 목록 가져오기

        Args:
            group_name: 그룹명

        Returns:
            list: captcha 상태 계정 리스트
        """
        accounts = self.get_accounts_by_group(group_name, active_only=False)
        return [acc for acc in accounts if acc['status'] == self.STATUS_CAPTCHA]

    def mark_as_captcha(self, group_name, account_id):
        """
        계정을 캡차 필요 상태로 변경

        Args:
            group_name: 그룹명
            account_id: 계정 ID

        Returns:
            bool: 성공 여부
        """
        return self.update_status(group_name, account_id, self.STATUS_CAPTCHA)

    def mark_as_suspended(self, group_name, account_id):
        """
        계정을 보호조치 상태로 변경

        Args:
            group_name: 그룹명
            account_id: 계정 ID

        Returns:
            bool: 성공 여부
        """
        return self.update_status(group_name, account_id, self.STATUS_SUSPENDED)

    def mark_as_active(self, group_name, account_id):
        """
        계정을 활성 상태로 변경 (수동 로그인 후)

        Args:
            group_name: 그룹명
            account_id: 계정 ID

        Returns:
            bool: 성공 여부
        """
        return self.update_status(group_name, account_id, self.STATUS_ACTIVE)


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
        print(f"  정지: {stats['suspended']}개")
        print(f"  차단: {stats['banned']}개")

        # 사용 가능한 계정
        available = manager.get_available_account(group)
        if available:
            print(f"  다음 사용 계정: {available['account_id']}")
        else:
            print(f"  사용 가능한 계정 없음")
