"""
발행 설정 관리자 - PublishSettingsManager

그룹별 발행 설정 관리:
- 발행대기 콘텐츠 수
- 활성 계정
- 오늘 발행 수
- 계정당 발행 수
- 잠금 상태 (동시성 제어)
"""

import json
from datetime import datetime
from .base import SheetsBase


class PublishSettingsManager(SheetsBase):
    """발행 설정 관리자"""

    SHEET_NAME = '발행설정'

    # 컬럼 인덱스 (0-based)
    COL_GROUP_NAME = 0       # A: 그룹명
    COL_PENDING_COUNT = 1    # B: 발행대기 (대기 콘텐츠 수)
    COL_ACCOUNT = 2          # C: 계정 (활성 계정)
    COL_TODAY_COUNT = 3      # D: 오늘 발행 (오늘 발행 수)
    COL_POSTS_PER_ACCOUNT = 4  # E: 계정당 발행 수
    COL_ACCOUNT_POST_COUNT = 5  # F: 현재 계정 발행 수 (내부용)
    COL_LOCK_STATUS = 6      # G: 잠금 상태 (동시성 제어)
    COL_LOCK_TIME = 7        # H: 잠금 시간

    # 헤더
    HEADERS = [
        '그룹', '발행대기', '계정', '오늘발행',
        '계정당발행수', '현재계정발행수', '잠금상태', '잠금시간'
    ]

    def __init__(self):
        """초기화"""
        super().__init__()
        self._ensure_sheet()

    def _ensure_sheet(self):
        """설정 시트가 없으면 생성"""
        try:
            self.read_range(f'{self.SHEET_NAME}!A1:H1')
        except Exception:
            # 시트 생성
            try:
                body = {
                    'requests': [{
                        'addSheet': {
                            'properties': {'title': self.SHEET_NAME}
                        }
                    }]
                }
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body=body
                ).execute()

                # 헤더 추가
                self.write_range(f'{self.SHEET_NAME}!A1:H1', [self.HEADERS])
                print(f"[OK] '{self.SHEET_NAME}' 시트 생성 완료")
            except Exception as e:
                print(f"[!] 설정 시트 생성 실패: {e}")

    def get_setting(self, group_name):
        """
        특정 그룹의 발행 설정 가져오기

        Args:
            group_name: 그룹명

        Returns:
            dict or None: 설정 정보
        """
        try:
            values = self.read_range(f'{self.SHEET_NAME}!A:H')
        except Exception:
            return None

        if len(values) <= 1:
            return None

        for i in range(1, len(values)):
            row = values[i]
            if len(row) > 0 and row[0] == group_name:
                return {
                    'group_name': group_name,
                    'pending_count': int(row[self.COL_PENDING_COUNT]) if len(row) > self.COL_PENDING_COUNT and row[self.COL_PENDING_COUNT] else 0,
                    'account': row[self.COL_ACCOUNT] if len(row) > self.COL_ACCOUNT else '',
                    'today_count': int(row[self.COL_TODAY_COUNT]) if len(row) > self.COL_TODAY_COUNT and row[self.COL_TODAY_COUNT] else 0,
                    'posts_per_account': int(row[self.COL_POSTS_PER_ACCOUNT]) if len(row) > self.COL_POSTS_PER_ACCOUNT and row[self.COL_POSTS_PER_ACCOUNT] else 5,
                    'account_post_count': int(row[self.COL_ACCOUNT_POST_COUNT]) if len(row) > self.COL_ACCOUNT_POST_COUNT and row[self.COL_ACCOUNT_POST_COUNT] else 0,
                    'lock_status': row[self.COL_LOCK_STATUS] if len(row) > self.COL_LOCK_STATUS else '',
                    'lock_time': row[self.COL_LOCK_TIME] if len(row) > self.COL_LOCK_TIME else '',
                    'row_num': i + 1
                }

        return None

    def get_all_settings(self):
        """
        모든 그룹 발행 설정 가져오기

        Returns:
            dict: {group_name: setting}
        """
        try:
            values = self.read_range(f'{self.SHEET_NAME}!A:H')
        except Exception:
            return {}

        if len(values) <= 1:
            return {}

        settings = {}
        for i in range(1, len(values)):
            row = values[i]
            if len(row) > 0 and row[0]:
                group_name = row[0]
                settings[group_name] = {
                    'group_name': group_name,
                    'pending_count': int(row[self.COL_PENDING_COUNT]) if len(row) > self.COL_PENDING_COUNT and row[self.COL_PENDING_COUNT] else 0,
                    'account': row[self.COL_ACCOUNT] if len(row) > self.COL_ACCOUNT else '',
                    'today_count': int(row[self.COL_TODAY_COUNT]) if len(row) > self.COL_TODAY_COUNT and row[self.COL_TODAY_COUNT] else 0,
                    'posts_per_account': int(row[self.COL_POSTS_PER_ACCOUNT]) if len(row) > self.COL_POSTS_PER_ACCOUNT and row[self.COL_POSTS_PER_ACCOUNT] else 5,
                    'account_post_count': int(row[self.COL_ACCOUNT_POST_COUNT]) if len(row) > self.COL_ACCOUNT_POST_COUNT and row[self.COL_ACCOUNT_POST_COUNT] else 0,
                    'lock_status': row[self.COL_LOCK_STATUS] if len(row) > self.COL_LOCK_STATUS else '',
                    'lock_time': row[self.COL_LOCK_TIME] if len(row) > self.COL_LOCK_TIME else '',
                    'row_num': i + 1
                }

        return settings

    def create_setting(self, group_name, posts_per_account=5):
        """
        새 그룹 발행 설정 생성

        Args:
            group_name: 그룹명
            posts_per_account: 계정당 발행 수 (기본값: 5)

        Returns:
            bool: 성공 여부
        """
        # 이미 존재하는지 확인
        existing = self.get_setting(group_name)
        if existing:
            print(f"[!] '{group_name}' 설정이 이미 존재합니다.")
            return False

        new_row = [
            group_name,
            '0',  # pending_count (콘텐츠 매니저에서 업데이트)
            '',   # account (자동 설정)
            '0',  # today_count
            str(posts_per_account),
            '0',  # account_post_count
            '',   # lock_status
            ''    # lock_time
        ]

        try:
            self.append_row(self.SHEET_NAME, new_row)
            return True
        except Exception as e:
            print(f"[X] 설정 생성 실패: {e}")
            return False

    def update_setting(self, group_name, **kwargs):
        """
        그룹 발행 설정 업데이트

        Args:
            group_name: 그룹명
            **kwargs: 업데이트할 필드들
                - pending_count: int
                - account: str
                - today_count: int
                - posts_per_account: int
                - account_post_count: int
                - lock_status: str
                - lock_time: str

        Returns:
            bool: 성공 여부
        """
        setting = self.get_setting(group_name)
        if not setting:
            print(f"[!] '{group_name}' 설정을 찾을 수 없습니다.")
            return False

        row_num = setting['row_num']

        col_map = {
            'pending_count': (self.COL_PENDING_COUNT, str),
            'account': (self.COL_ACCOUNT, str),
            'today_count': (self.COL_TODAY_COUNT, str),
            'posts_per_account': (self.COL_POSTS_PER_ACCOUNT, str),
            'account_post_count': (self.COL_ACCOUNT_POST_COUNT, str),
            'lock_status': (self.COL_LOCK_STATUS, str),
            'lock_time': (self.COL_LOCK_TIME, str)
        }

        try:
            for key, value in kwargs.items():
                if key in col_map:
                    col_idx, converter = col_map[key]
                    self.update_cell(self.SHEET_NAME, row_num, col_idx, converter(value))
            return True
        except Exception as e:
            print(f"[X] 설정 업데이트 실패: {e}")
            return False

    def increment_today_count(self, group_name):
        """
        오늘 발행 카운트 증가 + 계정 발행 수 증가

        Args:
            group_name: 그룹명

        Returns:
            bool: 성공 여부
        """
        setting = self.get_setting(group_name)
        if not setting:
            return False

        row_num = setting['row_num']
        new_today_count = setting['today_count'] + 1
        new_account_post_count = setting['account_post_count'] + 1

        try:
            self.update_cell(self.SHEET_NAME, row_num, self.COL_TODAY_COUNT, str(new_today_count))
            self.update_cell(self.SHEET_NAME, row_num, self.COL_ACCOUNT_POST_COUNT, str(new_account_post_count))
            return True
        except Exception:
            return False

    def reset_all_today_counts(self):
        """
        모든 그룹의 오늘 발행 카운트 리셋 (매일 자정에 실행)

        Returns:
            int: 리셋된 그룹 수
        """
        settings = self.get_all_settings()
        reset_count = 0

        for group_name, setting in settings.items():
            if setting['today_count'] > 0:
                try:
                    self.update_cell(self.SHEET_NAME, setting['row_num'],
                                     self.COL_TODAY_COUNT, '0')
                    reset_count += 1
                except Exception:
                    pass

        return reset_count

    def should_switch_account(self, group_name):
        """
        계정 전환이 필요한지 확인

        Args:
            group_name: 그룹명

        Returns:
            bool: 계정 전환 필요 여부
        """
        setting = self.get_setting(group_name)
        if not setting:
            return False

        return setting['account_post_count'] >= setting['posts_per_account']

    def switch_to_next_account(self, group_name, next_account):
        """
        다음 계정으로 전환

        Args:
            group_name: 그룹명
            next_account: 다음 계정 ID

        Returns:
            bool: 성공 여부
        """
        setting = self.get_setting(group_name)
        if not setting:
            return False

        row_num = setting['row_num']

        try:
            # 계정 변경 + 계정 발행 수 리셋
            self.update_cell(self.SHEET_NAME, row_num, self.COL_ACCOUNT, next_account)
            self.update_cell(self.SHEET_NAME, row_num, self.COL_ACCOUNT_POST_COUNT, '0')
            return True
        except Exception:
            return False

    def acquire_lock(self, group_name, bot_id):
        """
        그룹 잠금 획득 (동시성 제어)

        Args:
            group_name: 그룹명
            bot_id: 봇 식별자

        Returns:
            bool: 잠금 획득 성공 여부
        """
        setting = self.get_setting(group_name)
        if not setting:
            return False

        # 이미 잠겨있으면 실패
        if setting['lock_status']:
            # 5분 이상 경과한 잠금은 해제된 것으로 간주
            if setting['lock_time']:
                try:
                    lock_time = datetime.strptime(setting['lock_time'], '%Y-%m-%d %H:%M:%S')
                    elapsed = (datetime.now() - lock_time).total_seconds()
                    if elapsed < 300:  # 5분
                        return False
                except Exception:
                    pass

        row_num = setting['row_num']
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            self.update_cell(self.SHEET_NAME, row_num, self.COL_LOCK_STATUS, bot_id)
            self.update_cell(self.SHEET_NAME, row_num, self.COL_LOCK_TIME, current_time)
            return True
        except Exception:
            return False

    def release_lock(self, group_name, bot_id):
        """
        그룹 잠금 해제

        Args:
            group_name: 그룹명
            bot_id: 봇 식별자 (본인 잠금만 해제 가능)

        Returns:
            bool: 해제 성공 여부
        """
        setting = self.get_setting(group_name)
        if not setting:
            return False

        # 본인 잠금이 아니면 해제 불가
        if setting['lock_status'] != bot_id:
            return False

        row_num = setting['row_num']

        try:
            self.update_cell(self.SHEET_NAME, row_num, self.COL_LOCK_STATUS, '')
            self.update_cell(self.SHEET_NAME, row_num, self.COL_LOCK_TIME, '')
            return True
        except Exception:
            return False

    def force_release_lock(self, group_name):
        """
        그룹 잠금 강제 해제 (관리자용)

        Args:
            group_name: 그룹명

        Returns:
            bool: 해제 성공 여부
        """
        setting = self.get_setting(group_name)
        if not setting:
            return False

        row_num = setting['row_num']

        try:
            self.update_cell(self.SHEET_NAME, row_num, self.COL_LOCK_STATUS, '')
            self.update_cell(self.SHEET_NAME, row_num, self.COL_LOCK_TIME, '')
            return True
        except Exception:
            return False

    def is_locked(self, group_name):
        """
        그룹이 잠겨있는지 확인

        Args:
            group_name: 그룹명

        Returns:
            tuple: (잠겨있음 여부, 잠금 주체)
        """
        setting = self.get_setting(group_name)
        if not setting:
            return False, None

        if not setting['lock_status']:
            return False, None

        # 5분 이상 경과한 잠금은 해제된 것으로 간주
        if setting['lock_time']:
            try:
                lock_time = datetime.strptime(setting['lock_time'], '%Y-%m-%d %H:%M:%S')
                elapsed = (datetime.now() - lock_time).total_seconds()
                if elapsed >= 300:  # 5분
                    return False, None
            except Exception:
                pass

        return True, setting['lock_status']

    def update_pending_count(self, group_name, count):
        """
        발행대기 콘텐츠 수 업데이트

        Args:
            group_name: 그룹명
            count: 대기 콘텐츠 수

        Returns:
            bool: 성공 여부
        """
        return self.update_setting(group_name, pending_count=count)

    def sync_with_account_groups(self):
        """
        계정 그룹과 발행 설정 동기화
        (새 계정 그룹이 있으면 기본 설정 생성)

        Returns:
            list: 새로 생성된 그룹명 리스트
        """
        account_groups = self.get_account_groups()
        existing_settings = self.get_all_settings()

        created = []
        for group in account_groups:
            if group not in existing_settings:
                if self.create_setting(group):
                    created.append(group)
                    print(f"[OK] '{group}' 기본 발행 설정 생성")

        return created


# 테스트
if __name__ == '__main__':
    manager = PublishSettingsManager()

    print("=" * 50)
    print("PublishSettingsManager 테스트")
    print("=" * 50)

    # 계정 그룹과 동기화
    created = manager.sync_with_account_groups()
    if created:
        print(f"\n새로 생성된 설정: {created}")

    # 모든 설정 조회
    settings = manager.get_all_settings()
    print(f"\n전체 설정 ({len(settings)}개):")

    for name, s in settings.items():
        locked, locker = manager.is_locked(name)
        lock_status = f"잠금({locker})" if locked else "사용가능"
        print(f"\n  [{name}]")
        print(f"    발행대기: {s['pending_count']}개")
        print(f"    활성계정: {s['account'] or '없음'}")
        print(f"    오늘발행: {s['today_count']}개")
        print(f"    계정당발행: {s['posts_per_account']}개")
        print(f"    현재계정발행: {s['account_post_count']}개")
        print(f"    상태: {lock_status}")
