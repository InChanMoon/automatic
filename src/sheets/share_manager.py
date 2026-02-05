"""
공유 시트 매니저

공유계정, 공유한링크 탭을 관리합니다.
"""

from typing import List, Dict, Set, Optional
from .base import SheetsBase


class ShareManager(SheetsBase):
    """공유 관련 시트 관리"""

    # 시트 이름
    SHEET_ACCOUNTS = "공유계정"      # A: id, B: pw
    SHEET_SHARED = "공유한링크"      # A: 키워드, B: 링크, C~: 공유계정들
    SHEET_REPORTED = "신고한링크"    # A: 키워드, B: 링크, C~: 신고계정들

    # 공유계정 컬럼 (0-based)
    COL_ACC_ID = 0      # A
    COL_ACC_PW = 1      # B

    # 공유한링크 컬럼 (0-based)
    COL_SHARED_KEYWORD = 0   # A
    COL_SHARED_LINK = 1      # B
    COL_SHARED_ACCOUNTS = 2  # C부터 공유한 계정들

    # 신고한링크 컬럼 (0-based) - 공유한링크와 동일 구조
    COL_REPORTED_KEYWORD = 0   # A
    COL_REPORTED_LINK = 1      # B
    COL_REPORTED_ACCOUNTS = 2  # C부터 신고한 계정들

    def __init__(self, config_path=None, credentials_path=None):
        super().__init__(config_path, credentials_path)
        # 링크 캐시 (API 호출 최소화)
        self._link_cache: Dict[str, int] = {}  # link -> row_num (공유한링크)
        self._cache_valid = False

        # 신고 링크 캐시
        self._reported_cache: Dict[str, int] = {}  # link -> row_num (신고한링크)
        self._reported_cache_valid = False

    # ==================== 공유계정 탭 ====================

    def get_share_accounts(self) -> List[Dict]:
        """
        공유계정 탭에서 계정 목록 가져오기

        Returns:
            list: [{'id': str, 'pw': str}, ...]
        """
        try:
            values = self.read_range(f'{self.SHEET_ACCOUNTS}!A:B')
            accounts = []

            for i, row in enumerate(values):
                # 첫 행이 헤더인지 확인
                if i == 0 and row and row[0].lower() in ('id', '아이디', 'account'):
                    continue

                if len(row) >= 2 and row[0] and row[1]:
                    accounts.append({
                        'id': row[0].strip(),
                        'pw': row[1].strip()
                    })

            return accounts

        except Exception as e:
            print(f"공유계정 로드 오류: {e}")
            return []

    # ==================== 타겟 계정 조회 ====================

    def get_target_account_ids(self, group_name: str = "소액결제현금화") -> Set[str]:
        """
        타겟 그룹의 계정 ID 목록 가져오기 (URL 필터링용)

        Args:
            group_name: 계정 그룹명 (예: 소액결제현금화)

        Returns:
            set: 계정 ID set
        """
        try:
            # 계정_그룹명 시트에서 A열(account_id) 읽기
            sheet_name = f"계정_{group_name}"
            values = self.read_range(f'{sheet_name}!A:A')

            account_ids = set()
            for i, row in enumerate(values):
                # 첫 행이 헤더인지 확인
                if i == 0 and row and row[0].lower() in ('account_id', '아이디', 'id'):
                    continue

                if row and row[0]:
                    account_ids.add(row[0].strip())

            return account_ids

        except Exception as e:
            print(f"타겟 계정 로드 오류 ({group_name}): {e}")
            return set()

    # ==================== 공유한링크 탭 ====================

    def _refresh_link_cache(self):
        """링크 캐시 갱신"""
        try:
            values = self.read_range(f'{self.SHEET_SHARED}!B:B')
            self._link_cache = {}

            for i, row in enumerate(values):
                if row and row[0]:
                    link = row[0].strip()
                    self._link_cache[link] = i + 1  # 1-based row number

            self._cache_valid = True

        except Exception as e:
            print(f"링크 캐시 갱신 오류: {e}")
            self._cache_valid = False

    def invalidate_cache(self):
        """캐시 무효화 (공유/신고 모두)"""
        self._cache_valid = False
        self._link_cache = {}
        self._reported_cache_valid = False
        self._reported_cache = {}

    def is_link_shared(self, link: str) -> bool:
        """
        링크가 이미 공유한링크 탭에 있는지 확인

        Args:
            link: 블로그 글 링크

        Returns:
            bool: 중복 여부
        """
        if not self._cache_valid:
            self._refresh_link_cache()

        return link in self._link_cache

    def find_link_row(self, link: str) -> Optional[int]:
        """
        링크의 행 번호 찾기

        Args:
            link: 블로그 글 링크

        Returns:
            int: 행 번호 (1-based), 없으면 None
        """
        if not self._cache_valid:
            self._refresh_link_cache()

        return self._link_cache.get(link)

    def add_shared_link(self, keyword: str, link: str) -> Optional[int]:
        """
        새 링크 추가 (공유한링크 탭)

        Args:
            keyword: 검색 키워드
            link: 블로그 글 링크

        Returns:
            int: 추가된 행 번호, 실패 시 None
        """
        try:
            # 중복 체크
            if self.is_link_shared(link):
                return self.find_link_row(link)

            # 새 행 추가
            self.append_row(self.SHEET_SHARED, [keyword, link])

            # 캐시 갱신
            self._refresh_link_cache()

            return self.find_link_row(link)

        except Exception as e:
            print(f"링크 추가 오류: {e}")
            return None

    def add_shared_account_to_link(self, link: str, account_id: str) -> bool:
        """
        링크에 공유한 계정 추가

        Process:
            1. 링크 행 찾기
            2. 해당 행의 다음 빈 컬럼에 account_id 추가

        Args:
            link: 블로그 글 링크
            account_id: 공유한 계정 ID

        Returns:
            bool: 성공 여부
        """
        try:
            row_num = self.find_link_row(link)
            if not row_num:
                return False

            # 현재 행 데이터 가져오기
            row_data = self.read_range(f'{self.SHEET_SHARED}!{row_num}:{row_num}')
            if not row_data:
                return False

            current_row = row_data[0]

            # 이미 공유한 계정인지 확인
            if account_id in current_row[2:]:
                return True  # 이미 있음

            # 다음 빈 컬럼 인덱스 계산
            next_col = len(current_row)

            # 셀 업데이트
            self.update_cell(self.SHEET_SHARED, row_num, next_col, account_id)
            return True

        except Exception as e:
            print(f"계정 기록 오류: {e}")
            return False

    def get_shared_accounts_for_link(self, link: str) -> List[str]:
        """
        특정 링크를 공유한 계정 목록

        Args:
            link: 블로그 글 링크

        Returns:
            list: [account_id, ...]
        """
        try:
            row_num = self.find_link_row(link)
            if not row_num:
                return []

            row_data = self.read_range(f'{self.SHEET_SHARED}!{row_num}:{row_num}')
            if not row_data or len(row_data[0]) <= 2:
                return []

            # C열부터가 공유 계정
            return [acc.strip() for acc in row_data[0][2:] if acc.strip()]

        except Exception as e:
            print(f"공유 계정 조회 오류: {e}")
            return []

    def get_all_shared_links(self) -> List[Dict]:
        """
        모든 공유한 링크 목록

        Returns:
            list: [{'keyword': str, 'link': str, 'shared_accounts': list, 'row_num': int}, ...]
        """
        try:
            values = self.read_range(f'{self.SHEET_SHARED}!A:Z')
            results = []

            for i, row in enumerate(values):
                # 첫 행이 헤더인지 확인
                if i == 0 and row and row[0].lower() in ('keyword', '키워드'):
                    continue

                if len(row) >= 2 and row[1]:  # 링크가 있어야 함
                    results.append({
                        'keyword': row[0] if row[0] else '',
                        'link': row[1],
                        'shared_accounts': [acc.strip() for acc in row[2:] if acc.strip()],
                        'row_num': i + 1
                    })

            return results

        except Exception as e:
            print(f"공유 링크 조회 오류: {e}")
            return []

    def get_unshared_links_for_account(self, account_id: str) -> List[Dict]:
        """
        특정 계정이 아직 공유하지 않은 링크 목록

        Args:
            account_id: 확인할 계정 ID

        Returns:
            list: [{'keyword': str, 'link': str, 'row_num': int}, ...]
        """
        all_links = self.get_all_shared_links()
        return [
            link for link in all_links
            if account_id not in link['shared_accounts']
        ]

    # ==================== 신고한링크 탭 ====================

    def _refresh_reported_cache(self):
        """신고 링크 캐시 갱신"""
        try:
            values = self.read_range(f'{self.SHEET_REPORTED}!B:B')
            self._reported_cache = {}

            for i, row in enumerate(values):
                if row and row[0]:
                    link = row[0].strip()
                    self._reported_cache[link] = i + 1  # 1-based row number

            self._reported_cache_valid = True

        except Exception as e:
            print(f"신고 링크 캐시 갱신 오류: {e}")
            self._reported_cache_valid = False

    def is_link_reported(self, link: str) -> bool:
        """
        링크가 이미 신고한링크 탭에 있는지 확인

        Args:
            link: 블로그 글 링크

        Returns:
            bool: 중복 여부
        """
        if not self._reported_cache_valid:
            self._refresh_reported_cache()

        return link in self._reported_cache

    def find_reported_link_row(self, link: str) -> Optional[int]:
        """
        신고 링크의 행 번호 찾기

        Args:
            link: 블로그 글 링크

        Returns:
            int: 행 번호 (1-based), 없으면 None
        """
        if not self._reported_cache_valid:
            self._refresh_reported_cache()

        return self._reported_cache.get(link)

    def add_reported_link(self, keyword: str, link: str) -> Optional[int]:
        """
        새 링크 추가 (신고한링크 탭)

        Args:
            keyword: 검색 키워드
            link: 블로그 글 링크

        Returns:
            int: 추가된 행 번호, 실패 시 None
        """
        try:
            # 중복 체크
            if self.is_link_reported(link):
                return self.find_reported_link_row(link)

            # 새 행 추가
            self.append_row(self.SHEET_REPORTED, [keyword, link])

            # 캐시 갱신
            self._refresh_reported_cache()

            return self.find_reported_link_row(link)

        except Exception as e:
            print(f"신고 링크 추가 오류: {e}")
            return None

    def add_reported_account_to_link(self, link: str, account_id: str) -> bool:
        """
        링크에 신고한 계정 추가

        Args:
            link: 블로그 글 링크
            account_id: 신고한 계정 ID

        Returns:
            bool: 성공 여부
        """
        try:
            row_num = self.find_reported_link_row(link)
            if not row_num:
                return False

            # 현재 행 데이터 가져오기
            row_data = self.read_range(f'{self.SHEET_REPORTED}!{row_num}:{row_num}')
            if not row_data:
                return False

            current_row = row_data[0]

            # 이미 신고한 계정인지 확인
            if account_id in current_row[2:]:
                return True  # 이미 있음

            # 다음 빈 컬럼 인덱스 계산
            next_col = len(current_row)

            # 셀 업데이트
            self.update_cell(self.SHEET_REPORTED, row_num, next_col, account_id)
            return True

        except Exception as e:
            print(f"신고 계정 기록 오류: {e}")
            return False

    def get_reported_accounts_for_link(self, link: str) -> List[str]:
        """
        특정 링크를 신고한 계정 목록

        Args:
            link: 블로그 글 링크

        Returns:
            list: [account_id, ...]
        """
        try:
            row_num = self.find_reported_link_row(link)
            if not row_num:
                return []

            row_data = self.read_range(f'{self.SHEET_REPORTED}!{row_num}:{row_num}')
            if not row_data or len(row_data[0]) <= 2:
                return []

            # C열부터가 신고 계정
            return [acc.strip() for acc in row_data[0][2:] if acc.strip()]

        except Exception as e:
            print(f"신고 계정 조회 오류: {e}")
            return []

    def get_all_reported_links(self) -> List[Dict]:
        """
        모든 신고한 링크 목록

        Returns:
            list: [{'keyword': str, 'link': str, 'reported_accounts': list, 'row_num': int}, ...]
        """
        try:
            values = self.read_range(f'{self.SHEET_REPORTED}!A:Z')
            results = []

            for i, row in enumerate(values):
                # 첫 행이 헤더인지 확인
                if i == 0 and row and row[0].lower() in ('keyword', '키워드'):
                    continue

                if len(row) >= 2 and row[1]:  # 링크가 있어야 함
                    results.append({
                        'keyword': row[0] if row[0] else '',
                        'link': row[1],
                        'reported_accounts': [acc.strip() for acc in row[2:] if acc.strip()],
                        'row_num': i + 1
                    })

            return results

        except Exception as e:
            print(f"신고 링크 조회 오류: {e}")
            return []

    # ==================== 통계 ====================

    def get_share_stats(self) -> Dict:
        """
        공유 통계

        Returns:
            dict: {
                'total_links': int,
                'total_share_accounts': int,
                'total_shares': int,
                'avg_shares_per_link': float
            }
        """
        try:
            links = self.get_all_shared_links()
            accounts = self.get_share_accounts()

            total_shares = sum(len(link['shared_accounts']) for link in links)
            avg_shares = total_shares / len(links) if links else 0

            return {
                'total_links': len(links),
                'total_share_accounts': len(accounts),
                'total_shares': total_shares,
                'avg_shares_per_link': round(avg_shares, 1)
            }

        except Exception as e:
            print(f"통계 조회 오류: {e}")
            return {
                'total_links': 0,
                'total_share_accounts': 0,
                'total_shares': 0,
                'avg_shares_per_link': 0
            }


if __name__ == "__main__":
    # 테스트
    mgr = ShareManager()

    print("=== 공유계정 목록 ===")
    accounts = mgr.get_share_accounts()
    for acc in accounts:
        print(f"  - {acc['id']}")

    print("\n=== 타겟 계정 (소액결제현금화) ===")
    target_ids = mgr.get_target_account_ids("소액결제현금화")
    print(f"  총 {len(target_ids)}개")
    for acc_id in list(target_ids)[:5]:
        print(f"  - {acc_id}")

    print("\n=== 공유한 링크 목록 ===")
    links = mgr.get_all_shared_links()
    for link in links[:5]:
        print(f"  - [{link['keyword']}] {link['link'][:50]}...")
        print(f"    공유계정: {', '.join(link['shared_accounts']) or '없음'}")

    print("\n=== 통계 ===")
    stats = mgr.get_share_stats()
    print(f"  총 링크: {stats['total_links']}개")
    print(f"  공유 계정: {stats['total_share_accounts']}개")
    print(f"  총 공유 횟수: {stats['total_shares']}회")
    print(f"  링크당 평균 공유: {stats['avg_shares_per_link']}회")
