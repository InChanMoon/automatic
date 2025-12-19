"""
스프레드시트 구조 마이그레이션 스크립트 V2

변경사항:
1. 계정 시트: daily_limit, today_count, created_date, memo 컬럼 삭제
   - 기존: A:ID, B:PW, C:status, D:daily_limit, E:today_count, F:last_used, G:created_date, H:memo
   - 신규: A:ID, B:PW, C:status, D:last_used

2. 발행설정 시트: today_count 컬럼 삭제, 이미지인덱스 컬럼 추가
   - 기존: A:그룹, B:발행대기, C:계정, D:오늘발행, E:계정당발행수, F:현재계정발행수, G:잠금상태, H:잠금시간
   - 신규: A:그룹, B:발행대기, C:계정, D:계정당발행수, E:현재계정발행수, F:이미지인덱스, G:잠금상태, H:잠금시간
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sheets.base import SheetsBase


class SheetsMigrator(SheetsBase):
    """스프레드시트 마이그레이션 클래스"""

    # 새 헤더 정의
    NEW_ACCOUNT_HEADERS = ['account_id', 'password', 'status', 'last_used']
    NEW_SETTINGS_HEADERS = ['그룹', '발행대기', '계정', '계정당발행수', '현재계정발행수', '이미지인덱스', '잠금상태', '잠금시간']

    def __init__(self):
        super().__init__()

    def migrate_account_sheet(self, group_name):
        """
        계정 시트 마이그레이션

        기존 컬럼에서 필요한 데이터만 추출하여 새 구조로 변환
        """
        sheet_name = f"계정_{group_name}"
        print(f"\n[{sheet_name}] 마이그레이션 시작...")

        try:
            # 기존 데이터 읽기
            values = self.read_range(f'{sheet_name}!A:H')
        except Exception as e:
            print(f"  [X] 시트 읽기 실패: {e}")
            return False

        if len(values) <= 1:
            print(f"  [!] 데이터 없음, 헤더만 업데이트")
            self.write_range(f'{sheet_name}!A1:D1', [self.NEW_ACCOUNT_HEADERS])
            return True

        # 새 데이터 구조로 변환
        new_data = [self.NEW_ACCOUNT_HEADERS]  # 헤더

        for i in range(1, len(values)):
            row = values[i]
            if len(row) < 1 or not row[0]:
                continue

            # 기존: A:ID, B:PW, C:status, D:daily_limit, E:today_count, F:last_used, G:created_date, H:memo
            # 신규: A:ID, B:PW, C:status, D:last_used
            account_id = row[0] if len(row) > 0 else ''
            password = row[1] if len(row) > 1 else ''
            status = row[2] if len(row) > 2 else 'active'
            last_used = row[5] if len(row) > 5 else ''  # 기존 F열

            new_data.append([account_id, password, status, last_used])

        # 기존 데이터 삭제 후 새 데이터 쓰기
        print(f"  [*] {len(new_data) - 1}개 계정 변환...")

        # 전체 범위 클리어
        try:
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!A:H'
            ).execute()
        except Exception as e:
            print(f"  [!] 클리어 실패: {e}")

        # 새 데이터 쓰기
        self.write_range(f'{sheet_name}!A1:D{len(new_data)}', new_data)
        print(f"  [OK] 완료")
        return True

    def migrate_settings_sheet(self):
        """
        발행설정 시트 마이그레이션

        기존 컬럼에서 필요한 데이터만 추출하여 새 구조로 변환
        """
        sheet_name = '발행설정'
        print(f"\n[{sheet_name}] 마이그레이션 시작...")

        try:
            values = self.read_range(f'{sheet_name}!A:H')
        except Exception as e:
            print(f"  [X] 시트 읽기 실패: {e}")
            return False

        if len(values) <= 1:
            print(f"  [!] 데이터 없음, 헤더만 업데이트")
            self.write_range(f'{sheet_name}!A1:H1', [self.NEW_SETTINGS_HEADERS])
            return True

        # 새 데이터 구조로 변환
        new_data = [self.NEW_SETTINGS_HEADERS]

        for i in range(1, len(values)):
            row = values[i]
            if len(row) < 1 or not row[0]:
                continue

            # 기존: A:그룹, B:발행대기, C:계정, D:오늘발행, E:계정당발행수, F:현재계정발행수, G:잠금상태, H:잠금시간
            # 신규: A:그룹, B:발행대기, C:계정, D:계정당발행수, E:현재계정발행수, F:이미지인덱스, G:잠금상태, H:잠금시간
            group_name = row[0] if len(row) > 0 else ''
            pending_count = row[1] if len(row) > 1 else '0'
            account = row[2] if len(row) > 2 else ''
            # D:오늘발행 건너뜀
            posts_per_account = row[4] if len(row) > 4 else '5'  # 기존 E열
            account_post_count = row[5] if len(row) > 5 else '0'  # 기존 F열
            lock_status = row[6] if len(row) > 6 else ''  # 기존 G열
            lock_time = row[7] if len(row) > 7 else ''  # 기존 H열

            new_data.append([
                group_name,
                pending_count,
                account,
                posts_per_account,
                account_post_count,
                '{}',  # 이미지인덱스 (빈 JSON)
                lock_status,
                lock_time
            ])

        print(f"  [*] {len(new_data) - 1}개 그룹 설정 변환...")

        # 전체 범위 클리어
        try:
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!A:H'
            ).execute()
        except Exception as e:
            print(f"  [!] 클리어 실패: {e}")

        # 새 데이터 쓰기
        self.write_range(f'{sheet_name}!A1:H{len(new_data)}', new_data)
        print(f"  [OK] 완료")
        return True

    def run_migration(self):
        """전체 마이그레이션 실행"""
        print("=" * 60)
        print("스프레드시트 구조 마이그레이션 V2")
        print("=" * 60)
        print("\n변경사항:")
        print("  - 계정 시트: daily_limit, today_count, created_date, memo 컬럼 삭제")
        print("  - 발행설정 시트: today_count 삭제, 이미지인덱스 추가")

        # 계정 그룹 조회
        account_groups = self.get_account_groups()
        print(f"\n계정 그룹: {account_groups}")

        # 계정 시트 마이그레이션
        for group in account_groups:
            self.migrate_account_sheet(group)

        # 발행설정 시트 마이그레이션
        self.migrate_settings_sheet()

        print("\n" + "=" * 60)
        print("마이그레이션 완료!")
        print("=" * 60)


def main():
    print("\n주의: 이 스크립트는 스프레드시트 구조를 변경합니다.")
    print("백업을 권장합니다.\n")

    confirm = input("계속하시겠습니까? (y/N): ").strip().lower()
    if confirm != 'y':
        print("취소됨")
        return

    migrator = SheetsMigrator()
    migrator.run_migration()


if __name__ == '__main__':
    main()
