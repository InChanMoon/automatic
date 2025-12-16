"""
라이선스 관리 모듈

라이선스 검증, API 사용량 추적 등
"""

from .base import SheetsBase


class LicenseManager(SheetsBase):
    """라이선스 관리 클래스"""

    SHEET_NAME = '라이선스'

    # 컬럼 인덱스 (0-based)
    COL_LICENSE_KEY = 0      # A: license_key
    COL_USER_EMAIL = 1       # B: user_email
    COL_STATUS = 2           # C: status
    COL_IS_ADMIN = 3         # D: is_admin
    COL_API_USAGE = 4        # E: api_usage_today
    COL_API_LIMIT = 5        # F: api_limit_daily
    COL_CREATED_DATE = 6     # G: created_date

    def validate_license(self, license_key):
        """
        라이선스 검증

        Args:
            license_key: 라이선스 키

        Returns:
            dict: {
                'valid': bool,
                'is_admin': bool,
                'api_usage': int,
                'api_limit': int,
                'can_use_api': bool,
                'message': str
            }
        """
        row_num = self.find_row_by_column(self.SHEET_NAME, self.COL_LICENSE_KEY, license_key)

        if not row_num:
            return {
                'valid': False,
                'is_admin': False,
                'api_usage': 0,
                'api_limit': 0,
                'can_use_api': False,
                'message': '라이선스를 찾을 수 없습니다.'
            }

        # 라이선스 정보 읽기
        values = self.read_range(f'{self.SHEET_NAME}!A{row_num}:G{row_num}')
        row = values[0] if values else []

        status = row[self.COL_STATUS] if len(row) > self.COL_STATUS else ''
        is_admin = row[self.COL_IS_ADMIN] if len(row) > self.COL_IS_ADMIN else 'FALSE'
        api_usage = int(row[self.COL_API_USAGE]) if len(row) > self.COL_API_USAGE and row[self.COL_API_USAGE] else 0
        api_limit = int(row[self.COL_API_LIMIT]) if len(row) > self.COL_API_LIMIT and row[self.COL_API_LIMIT] else 0

        # 상태 확인
        if status != 'active':
            return {
                'valid': False,
                'is_admin': False,
                'api_usage': api_usage,
                'api_limit': api_limit,
                'can_use_api': False,
                'message': f'라이선스 상태: {status} (비활성)'
            }

        # Admin은 무제한
        if is_admin == 'TRUE':
            return {
                'valid': True,
                'is_admin': True,
                'api_usage': api_usage,
                'api_limit': api_limit,
                'can_use_api': True,
                'message': 'Admin 라이선스 (무제한)'
            }

        # 일반 사용자 - API 사용량 확인
        can_use = api_usage < api_limit

        return {
            'valid': True,
            'is_admin': False,
            'api_usage': api_usage,
            'api_limit': api_limit,
            'can_use_api': can_use,
            'message': f'API 사용량: {api_usage}/{api_limit}'
        }

    def increment_api_usage(self, license_key):
        """
        API 사용량 +1 증가

        Args:
            license_key: 라이선스 키

        Returns:
            bool: 성공 여부
        """
        row_num = self.find_row_by_column(self.SHEET_NAME, self.COL_LICENSE_KEY, license_key)

        if not row_num:
            return False

        # 현재 사용량 읽기
        values = self.read_range(f'{self.SHEET_NAME}!A{row_num}:G{row_num}')
        row = values[0] if values else []

        api_usage = int(row[self.COL_API_USAGE]) if len(row) > self.COL_API_USAGE and row[self.COL_API_USAGE] else 0

        # +1 증가
        new_usage = api_usage + 1

        # 업데이트
        self.update_cell(self.SHEET_NAME, row_num, self.COL_API_USAGE, str(new_usage))

        return True

    def reset_daily_usage(self):
        """
        모든 라이선스의 일일 API 사용량을 0으로 리셋

        매일 자정에 실행하는 함수
        """
        values = self.read_range(f'{self.SHEET_NAME}!A:G')

        if len(values) <= 1:  # 헤더만 있거나 비어있음
            return

        # 헤더 제외
        for i in range(1, len(values)):
            row_num = i + 1
            self.update_cell(self.SHEET_NAME, row_num, self.COL_API_USAGE, '0')

        print(f"✅ {len(values) - 1}개 라이선스의 API 사용량 리셋 완료")

    def get_license_info(self, license_key):
        """
        라이선스 전체 정보 가져오기

        Args:
            license_key: 라이선스 키

        Returns:
            dict: 라이선스 정보 또는 None
        """
        row_num = self.find_row_by_column(self.SHEET_NAME, self.COL_LICENSE_KEY, license_key)

        if not row_num:
            return None

        values = self.read_range(f'{self.SHEET_NAME}!A{row_num}:G{row_num}')
        row = values[0] if values else []

        return {
            'license_key': row[self.COL_LICENSE_KEY] if len(row) > self.COL_LICENSE_KEY else '',
            'user_email': row[self.COL_USER_EMAIL] if len(row) > self.COL_USER_EMAIL else '',
            'status': row[self.COL_STATUS] if len(row) > self.COL_STATUS else '',
            'is_admin': row[self.COL_IS_ADMIN] if len(row) > self.COL_IS_ADMIN else 'FALSE',
            'api_usage': int(row[self.COL_API_USAGE]) if len(row) > self.COL_API_USAGE and row[self.COL_API_USAGE] else 0,
            'api_limit': int(row[self.COL_API_LIMIT]) if len(row) > self.COL_API_LIMIT and row[self.COL_API_LIMIT] else 0,
            'created_date': row[self.COL_CREATED_DATE] if len(row) > self.COL_CREATED_DATE else ''
        }

    def add_license(self, license_key, user_email, is_admin=False, api_limit=50):
        """
        새 라이선스 추가

        Args:
            license_key: 라이선스 키
            user_email: 사용자 이메일
            is_admin: Admin 여부
            api_limit: 일일 API 제한
        """
        # 중복 확인
        existing = self.find_row_by_column(self.SHEET_NAME, self.COL_LICENSE_KEY, license_key)
        if existing:
            print(f"⚠️ 라이선스 {license_key}가 이미 존재합니다.")
            return False

        # 새 행 추가
        new_row = [
            license_key,
            user_email,
            'active',
            'TRUE' if is_admin else 'FALSE',
            '0',  # api_usage_today
            str(api_limit),
            self.get_current_date()
        ]

        self.append_row(self.SHEET_NAME, new_row)
        print(f"✅ 라이선스 {license_key} 추가 완료")

        return True
