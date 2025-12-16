"""
발행 설정 관리자 - PublishSettingsManager

그룹별 발행 설정 관리:
- 발행 간격 (초)
- 일일 최대 발행 수
- 발행 활성화/비활성화
- 발행 시간대 설정
"""

import json
from datetime import datetime
from .base import SheetsBase


class PublishSettingsManager(SheetsBase):
    """발행 설정 관리자"""

    SHEET_NAME = '발행설정'

    # 컬럼 인덱스 (0-based)
    COL_GROUP_NAME = 0       # A: group_name (그룹명)
    COL_ENABLED = 1          # B: enabled (활성화 여부)
    COL_INTERVAL_MIN = 2     # C: interval_min (최소 발행 간격, 초)
    COL_INTERVAL_MAX = 3     # D: interval_max (최대 발행 간격, 초)
    COL_DAILY_LIMIT = 4      # E: daily_limit (그룹 일일 최대 발행)
    COL_TODAY_COUNT = 5      # F: today_count (오늘 발행 수)
    COL_START_HOUR = 6       # G: start_hour (발행 시작 시간)
    COL_END_HOUR = 7         # H: end_hour (발행 종료 시간)
    COL_LAST_PUBLISH = 8     # I: last_publish (마지막 발행 시간)
    COL_MEMO = 9             # J: memo

    # 헤더
    HEADERS = [
        'group_name', 'enabled', 'interval_min', 'interval_max',
        'daily_limit', 'today_count', 'start_hour', 'end_hour',
        'last_publish', 'memo'
    ]

    def __init__(self):
        """초기화"""
        super().__init__()
        self._ensure_sheet()

    def _ensure_sheet(self):
        """설정 시트가 없으면 생성"""
        try:
            self.read_range(f'{self.SHEET_NAME}!A1:J1')
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
                self.write_range(f'{self.SHEET_NAME}!A1:J1', [self.HEADERS])
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
            values = self.read_range(f'{self.SHEET_NAME}!A:J')
        except Exception:
            return None

        if len(values) <= 1:
            return None

        for i in range(1, len(values)):
            row = values[i]
            if len(row) > 0 and row[0] == group_name:
                return {
                    'group_name': group_name,
                    'enabled': row[self.COL_ENABLED].upper() == 'TRUE' if len(row) > self.COL_ENABLED else False,
                    'interval_min': int(row[self.COL_INTERVAL_MIN]) if len(row) > self.COL_INTERVAL_MIN and row[self.COL_INTERVAL_MIN] else 300,
                    'interval_max': int(row[self.COL_INTERVAL_MAX]) if len(row) > self.COL_INTERVAL_MAX and row[self.COL_INTERVAL_MAX] else 600,
                    'daily_limit': int(row[self.COL_DAILY_LIMIT]) if len(row) > self.COL_DAILY_LIMIT and row[self.COL_DAILY_LIMIT] else 100,
                    'today_count': int(row[self.COL_TODAY_COUNT]) if len(row) > self.COL_TODAY_COUNT and row[self.COL_TODAY_COUNT] else 0,
                    'start_hour': int(row[self.COL_START_HOUR]) if len(row) > self.COL_START_HOUR and row[self.COL_START_HOUR] else 0,
                    'end_hour': int(row[self.COL_END_HOUR]) if len(row) > self.COL_END_HOUR and row[self.COL_END_HOUR] else 24,
                    'last_publish': row[self.COL_LAST_PUBLISH] if len(row) > self.COL_LAST_PUBLISH else '',
                    'memo': row[self.COL_MEMO] if len(row) > self.COL_MEMO else '',
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
            values = self.read_range(f'{self.SHEET_NAME}!A:J')
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
                    'enabled': row[self.COL_ENABLED].upper() == 'TRUE' if len(row) > self.COL_ENABLED else False,
                    'interval_min': int(row[self.COL_INTERVAL_MIN]) if len(row) > self.COL_INTERVAL_MIN and row[self.COL_INTERVAL_MIN] else 300,
                    'interval_max': int(row[self.COL_INTERVAL_MAX]) if len(row) > self.COL_INTERVAL_MAX and row[self.COL_INTERVAL_MAX] else 600,
                    'daily_limit': int(row[self.COL_DAILY_LIMIT]) if len(row) > self.COL_DAILY_LIMIT and row[self.COL_DAILY_LIMIT] else 100,
                    'today_count': int(row[self.COL_TODAY_COUNT]) if len(row) > self.COL_TODAY_COUNT and row[self.COL_TODAY_COUNT] else 0,
                    'start_hour': int(row[self.COL_START_HOUR]) if len(row) > self.COL_START_HOUR and row[self.COL_START_HOUR] else 0,
                    'end_hour': int(row[self.COL_END_HOUR]) if len(row) > self.COL_END_HOUR and row[self.COL_END_HOUR] else 24,
                    'last_publish': row[self.COL_LAST_PUBLISH] if len(row) > self.COL_LAST_PUBLISH else '',
                    'memo': row[self.COL_MEMO] if len(row) > self.COL_MEMO else '',
                    'row_num': i + 1
                }

        return settings

    def create_setting(self, group_name, interval_min=300, interval_max=600,
                       daily_limit=100, start_hour=0, end_hour=24, memo=''):
        """
        새 그룹 발행 설정 생성

        Args:
            group_name: 그룹명
            interval_min: 최소 발행 간격 (초)
            interval_max: 최대 발행 간격 (초)
            daily_limit: 일일 최대 발행 수
            start_hour: 발행 시작 시간 (0-23)
            end_hour: 발행 종료 시간 (1-24)
            memo: 메모

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
            'TRUE',  # enabled
            str(interval_min),
            str(interval_max),
            str(daily_limit),
            '0',  # today_count
            str(start_hour),
            str(end_hour),
            '',  # last_publish
            memo
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
                - enabled: bool
                - interval_min: int
                - interval_max: int
                - daily_limit: int
                - start_hour: int
                - end_hour: int
                - memo: str

        Returns:
            bool: 성공 여부
        """
        setting = self.get_setting(group_name)
        if not setting:
            print(f"[!] '{group_name}' 설정을 찾을 수 없습니다.")
            return False

        row_num = setting['row_num']

        col_map = {
            'enabled': (self.COL_ENABLED, lambda v: 'TRUE' if v else 'FALSE'),
            'interval_min': (self.COL_INTERVAL_MIN, str),
            'interval_max': (self.COL_INTERVAL_MAX, str),
            'daily_limit': (self.COL_DAILY_LIMIT, str),
            'start_hour': (self.COL_START_HOUR, str),
            'end_hour': (self.COL_END_HOUR, str),
            'memo': (self.COL_MEMO, str)
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

    def set_enabled(self, group_name, enabled):
        """발행 활성화/비활성화"""
        return self.update_setting(group_name, enabled=enabled)

    def increment_today_count(self, group_name):
        """
        오늘 발행 카운트 증가 + 마지막 발행 시간 업데이트

        Args:
            group_name: 그룹명

        Returns:
            bool: 성공 여부
        """
        setting = self.get_setting(group_name)
        if not setting:
            return False

        row_num = setting['row_num']
        new_count = setting['today_count'] + 1
        current_time = self.get_current_time()

        try:
            self.update_cell(self.SHEET_NAME, row_num, self.COL_TODAY_COUNT, str(new_count))
            self.update_cell(self.SHEET_NAME, row_num, self.COL_LAST_PUBLISH, current_time)
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

    def can_publish(self, group_name):
        """
        현재 발행 가능한지 확인

        Args:
            group_name: 그룹명

        Returns:
            tuple: (가능여부, 이유)
        """
        setting = self.get_setting(group_name)
        if not setting:
            return False, "설정 없음"

        if not setting['enabled']:
            return False, "비활성화됨"

        # 일일 한도 체크
        if setting['today_count'] >= setting['daily_limit']:
            return False, f"일일 한도 초과 ({setting['today_count']}/{setting['daily_limit']})"

        # 시간대 체크
        current_hour = datetime.now().hour
        if not (setting['start_hour'] <= current_hour < setting['end_hour']):
            return False, f"발행 시간 외 ({setting['start_hour']}~{setting['end_hour']}시)"

        return True, "발행 가능"

    def get_enabled_groups(self):
        """
        발행 활성화된 그룹 목록

        Returns:
            list: 활성화된 그룹명 리스트
        """
        settings = self.get_all_settings()
        return [name for name, s in settings.items() if s['enabled']]

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
        can, reason = manager.can_publish(name)
        status = "[OK]" if can else "[X]"
        print(f"\n  [{name}]")
        print(f"    활성화: {s['enabled']}")
        print(f"    발행 간격: {s['interval_min']}~{s['interval_max']}초")
        print(f"    일일 한도: {s['today_count']}/{s['daily_limit']}")
        print(f"    발행 시간: {s['start_hour']}~{s['end_hour']}시")
        print(f"    발행 가능: {status} {reason}")
