"""
발행 엔진 - Publisher Engine

API 호출 최소화 버전:
- 루프 시작 시 데이터 캐싱
- 네트워크 오류 시 짧은 대기 후 재시도
- 잠금은 유지 (여러 봇 동시 실행 지원)
"""

import time
import random
import os
import threading
from datetime import datetime
from typing import Callable, Dict, List, Optional

from src.sheets.content_manager_v3 import ContentManagerV3
from src.sheets.account_manager import AccountManager
from src.sheets.publish_settings_manager import PublishSettingsManager
from src.publisher.naver_blog_publisher import NaverBlogPublisher


class PublisherEngine:
    """발행 엔진 - API 호출 최소화"""

    def __init__(self, bot_id: str, headless: bool = False, image_mgr=None):
        """
        초기화

        Args:
            bot_id: 봇 고유 ID (동시성 제어용)
            headless: 헤드리스 모드
            image_mgr: DriveImageManager 인스턴스 (선택)
        """
        self.bot_id = bot_id
        self.headless = headless
        self.image_mgr = image_mgr

        # 매니저 초기화
        self.content_mgr = ContentManagerV3()
        self.account_mgr = AccountManager()
        self.settings_mgr = PublishSettingsManager()

        # 상태
        self.stop_requested = False
        self.stats = {'published': 0, 'failed': 0}

        # 현재 실행 중인 publisher (즉시 중지용)
        self._current_publisher: Optional[NaverBlogPublisher] = None

        # 로그 콜백
        self.log_callback: Optional[Callable[[str, str], None]] = None

        # 캐시 (네트워크 오류 시 재사용)
        self._cache = {
            'settings': {},      # {grp: setting}
            'accounts': {},      # {grp: [accounts]}
            'cache_time': None   # 캐시 시간
        }
        self._cache_ttl = 60  # 캐시 유효 시간 (초)

    def set_log_callback(self, callback: Callable[[str, str], None]):
        """로그 콜백 설정"""
        self.log_callback = callback

    def log(self, message: str, level: str = 'info'):
        """로그 출력"""
        # 사용자 친화적 메시지 변환
        friendly_messages = {
            '데이터 로드 중...': '설정 불러오는 중...',
            '대기중... (12초)': '다음 발행 대기 중...',
        }
        display_msg = friendly_messages.get(message, message)

        if self.log_callback:
            self.log_callback(display_msg, level)
        else:
            print(f"[{level.upper()}] {display_msg}")

    def stop(self):
        """중지 요청 - 즉시 브라우저 종료"""
        self.stop_requested = True
        # 현재 실행 중인 publisher가 있으면 강제 종료
        if self._current_publisher:
            try:
                self._current_publisher.request_stop()
            except:
                pass

    def _is_cache_valid(self) -> bool:
        """캐시 유효성 확인"""
        if not self._cache['cache_time']:
            return False
        elapsed = (datetime.now() - self._cache['cache_time']).total_seconds()
        return elapsed < self._cache_ttl

    def _refresh_cache(self, groups: List[str]) -> bool:
        """
        캐시 갱신 (한 번에 모든 데이터 로드)

        Returns:
            bool: 성공 여부
        """
        try:
            self.log("데이터 로드 중...")

            # 설정 로드
            all_settings = self.settings_mgr.get_all_settings()
            self._cache['settings'] = {g: all_settings.get(g, {}) for g in groups}

            # 계정 로드
            for grp in groups:
                try:
                    accounts = self.account_mgr.get_accounts_by_group(grp, active_only=True)
                    self._cache['accounts'][grp] = accounts
                except Exception as e:
                    self.log(f"[{grp}] 계정 로드 실패: {e}", 'warning')
                    self._cache['accounts'][grp] = []

            self._cache['cache_time'] = datetime.now()
            return True

        except Exception as e:
            self.log(f"캐시 갱신 실패: {e}", 'error')
            return False

    def _get_setting_cached(self, grp: str) -> Optional[Dict]:
        """캐시된 설정 가져오기 (실패 시 API 호출)"""
        # 캐시 유효하면 캐시 반환
        if self._is_cache_valid() and grp in self._cache['settings']:
            return self._cache['settings'][grp]

        # 캐시 무효 -> API 호출
        try:
            setting = self.settings_mgr.get_setting(grp)
            if setting:
                self._cache['settings'][grp] = setting
            return setting
        except Exception as e:
            self.log(f"[{grp}] 설정 조회 실패: {e}", 'warning')
            # 캐시에 있으면 캐시 반환 (오래됐더라도)
            return self._cache['settings'].get(grp)

    def _get_accounts_cached(self, grp: str) -> List[Dict]:
        """캐시된 계정 목록 가져오기"""
        if self._is_cache_valid() and grp in self._cache['accounts']:
            return self._cache['accounts'][grp]

        try:
            accounts = self.account_mgr.get_accounts_by_group(grp, active_only=True)
            self._cache['accounts'][grp] = accounts
            return accounts
        except Exception as e:
            self.log(f"[{grp}] 계정 목록 조회 실패: {e}", 'warning')
            return self._cache['accounts'].get(grp, [])

    def _get_available_account(self, grp: str) -> Optional[Dict]:
        """사용 가능한 계정 가져오기 (캐시 활용)"""
        accounts = self._get_accounts_cached(grp)

        # 활성 계정만 필터링
        available = [acc for acc in accounts if acc.get('status') == 'active']

        if not available:
            return None

        # last_used 기준 정렬 (오래된 것 우선)
        available.sort(key=lambda x: x.get('last_used') or '0000-00-00 00:00:00')
        return available[0]

    def _count_markers(self, content: str) -> int:
        """이미지 마커 개수 카운트"""
        import re
        pattern = r'\{img:(\d+)(?:-(\d+))?\}'
        mx = 0
        for m in re.finditer(pattern, content):
            s, e = int(m.group(1)), int(m.group(2)) if m.group(2) else int(m.group(1))
            mx = max(mx, s, e)
        return mx

    def _wait(self, sec: int):
        """중지 요청 체크하며 대기"""
        for _ in range(sec):
            if self.stop_requested:
                break
            time.sleep(1)

    def publish_single(self, grp: str, acc: Dict, content: Dict) -> Dict:
        """
        단일 콘텐츠 발행

        Args:
            grp: 그룹명
            acc: 계정 정보
            content: 콘텐츠 정보

        Returns:
            dict: {success, protected, error, browser_crash}
        """
        # 중지 요청 체크
        if self.stop_requested:
            return {'success': False, 'protected': False, 'error': '중지됨', 'stopped': True}

        # 로그 메시지는 run()에서 진행률 포함하여 출력하므로 여기서는 생략

        pub = None
        try:
            self.content_mgr.mark_as_publishing(content['sheet_name'], content['row_num'])

            # keyword 확인 - "자동생성"이면 이미지 자동 생성
            kw = content.get('keyword', '')
            auto_generate = (kw == '자동생성')

            # 이미지 준비
            images = []
            if not auto_generate:
                # Drive에서 이미지 가져오기
                cnt = self._count_markers(content['content'])
                if cnt > 0 and self.image_mgr:
                    if kw:
                        self.image_mgr.set_group(grp)
                        images = self.image_mgr.get_images_for_post(kw, cnt)

            # 브라우저 시작
            pub = NaverBlogPublisher(headless=self.headless)
            self._current_publisher = pub  # 즉시 중지용 참조 저장
            pub.set_log_callback(lambda m: self.log(f"  {m}"))
            pub.start_browser()

            # 쿠키 설정
            cookie = f"cookies/{acc['account_id']}_cookies.json"
            os.makedirs('cookies', exist_ok=True)
            pub.cookie_path = cookie

            login_result = {'success': False, 'protected': False, 'reason': ''}

            # 쿠키 로그인 시도
            if os.path.exists(cookie):
                login_result = pub.login_with_cookies()

            # 쿠키 실패 -> 비밀번호 로그인
            if not login_result.get('success'):
                if login_result.get('protected'):
                    # 보호조치: 계정 상태를 suspended로 변경
                    self.account_mgr.mark_as_suspended(grp, acc['account_id'])
                    self.log(f"[{grp}] 계정 '{acc['account_id']}' 보호조치 → suspended 처리", 'warning')
                    self.content_mgr.release_publishing_lock(content['sheet_name'], content['row_num'])
                    pub.close_browser()
                    return {'success': False, 'protected': True, 'error': login_result.get('reason', '보호조치')}

                login_result = pub.login_with_credentials(acc['account_id'], acc['password'])
                if login_result.get('protected'):
                    # 보호조치: 계정 상태를 suspended로 변경
                    self.account_mgr.mark_as_suspended(grp, acc['account_id'])
                    self.log(f"[{grp}] 계정 '{acc['account_id']}' 보호조치 → suspended 처리", 'warning')
                    self.content_mgr.release_publishing_lock(content['sheet_name'], content['row_num'])
                    pub.close_browser()
                    return {'success': False, 'protected': True, 'error': login_result.get('reason', '보호조치')}

                if not login_result.get('success'):
                    reason = login_result.get('reason', '')
                    # 캡차 감지: 계정 상태를 captcha로 변경
                    if '캡차' in reason:
                        self.account_mgr.mark_as_captcha(grp, acc['account_id'])
                        self.log(f"[{grp}] 계정 '{acc['account_id']}' 캡차 필요 → captcha 처리", 'warning')
                    self.content_mgr.release_publishing_lock(content['sheet_name'], content['row_num'])
                    pub.close_browser()
                    return {'success': False, 'protected': False, 'error': f'로그인 실패 ({reason})'}

            # 발행
            result = pub.publish_post(
                title=content['title'],
                content=content['content'],
                images=images,
                scheduled_time=content.get('scheduled_time'),
                auto_generate_images=auto_generate
            )

            if result['success']:
                self.content_mgr.mark_as_published(
                    content['sheet_name'], content['row_num'],
                    published_url=result.get('url', ''), account_id=acc['account_id']
                )
                self.account_mgr.increment_usage(grp, acc['account_id'])
                self.settings_mgr.increment_today_count(grp)
                self.log(f"[{grp}] 성공!", 'success')
                pub.close_browser()
                self._current_publisher = None
                return {'success': True, 'protected': False, 'error': ''}
            else:
                self.content_mgr.mark_as_failed(content['sheet_name'], content['row_num'])
                self.log(f"[{grp}] 실패: {result['error']}", 'error')
                pub.close_browser()
                self._current_publisher = None
                return {'success': False, 'protected': False, 'error': result['error']}

        except Exception as e:
            error_msg = str(e)
            self.log(f"[{grp}] 오류: {error_msg}", 'error')

            # 중지 요청으로 인한 브라우저 종료인지 확인
            is_stopped = self.stop_requested or (pub and pub.stop_requested)
            is_browser_crash = any(x in error_msg.lower() for x in ['epipe', 'broken pipe', 'connection', 'target closed'])

            if is_stopped or is_browser_crash:
                # 중지 또는 크래시: 콘텐츠 복원 (ready 상태로)
                self.log(f"[{grp}] {'중지됨' if is_stopped else '브라우저 크래시'} - 콘텐츠 복원", 'warning')
                try:
                    self.content_mgr.release_publishing_lock(content['sheet_name'], content['row_num'])
                except:
                    pass
            else:
                try:
                    self.content_mgr.mark_as_failed(content['sheet_name'], content['row_num'])
                except:
                    pass

            if pub:
                try:
                    pub.close_browser()
                except:
                    pass

            self._current_publisher = None
            return {'success': False, 'protected': False, 'error': error_msg, 'browser_crash': is_browser_crash, 'stopped': is_stopped}

    def run(self, groups: List[str], on_stats_update: Callable = None, on_refresh: Callable = None):
        """
        발행 루프 실행

        Args:
            groups: 발행할 그룹 목록
            on_stats_update: 통계 업데이트 콜백 (published, failed)
            on_refresh: 새로고침 콜백
        """
        self.log(f"시작: {', '.join(groups)}", 'success')
        self.stop_requested = False

        # 초기 캐시 로드
        if not self._refresh_cache(groups):
            self.log("초기 데이터 로드 실패, 재시도...", 'warning')
            self._wait(3)
            self._refresh_cache(groups)

        consecutive_network_errors = 0

        try:
            while not self.stop_requested:
                published = False
                had_network_error = False

                for grp in groups:
                    if self.stop_requested:
                        break

                    # 잠금 획득 시도
                    try:
                        if not self.settings_mgr.acquire_lock(grp, self.bot_id):
                            self.log(f"[{grp}] 다른 봇이 사용 중 (잠금 대기)", 'info')
                            continue
                    except Exception as e:
                        self.log(f"[{grp}] 잠금 획득 오류: {e}", 'warning')
                        had_network_error = True
                        continue

                    try:
                        # 설정 가져오기 (캐시 활용)
                        setting = self._get_setting_cached(grp)
                        if not setting:
                            self.log(f"[{grp}] 설정 없음", 'warning')
                            continue

                        # 계정당 발행 수 체크
                        posts_per_account = setting.get('posts_per_account', 5)
                        account_post_count = setting.get('account_post_count', 0)
                        current_acc_id = setting.get('account', '')

                        # 계정 전환 필요 체크
                        if account_post_count >= posts_per_account and current_acc_id:
                            self.log(f"[{grp}] 계정당 발행수 도달 ({account_post_count}/{posts_per_account})", 'warning')

                            # 다음 계정 선택
                            accounts = self._get_accounts_cached(grp)
                            acc_ids = [a['account_id'] for a in accounts]

                            if current_acc_id in acc_ids:
                                idx = acc_ids.index(current_acc_id)
                                next_acc_id = acc_ids[(idx + 1) % len(acc_ids)]
                            else:
                                next_acc_id = acc_ids[0] if acc_ids else None

                            if next_acc_id:
                                try:
                                    self.settings_mgr.switch_to_next_account(grp, next_acc_id)
                                    self._cache['settings'][grp]['account'] = next_acc_id
                                    self._cache['settings'][grp]['account_post_count'] = 0
                                    self.log(f"[{grp}] 계정전환: {next_acc_id}", 'warning')
                                    self._wait(12)
                                except Exception as e:
                                    self.log(f"[{grp}] 계정전환 오류: {e}", 'warning')
                                    had_network_error = True

                        # 현재 계정 정보 가져오기
                        acc_id = self._cache['settings'].get(grp, {}).get('account', '') or current_acc_id
                        acc = None

                        if acc_id:
                            accounts = self._get_accounts_cached(grp)
                            for a in accounts:
                                if a['account_id'] == acc_id and a.get('status') == 'active':
                                    acc = a
                                    break

                        # 계정 없으면 새로 찾기
                        if not acc:
                            acc = self._get_available_account(grp)
                            if acc:
                                acc_id = acc['account_id']
                                try:
                                    # 새 계정 선택 시 account_post_count도 0으로 초기화
                                    self.settings_mgr.update_setting(grp, account=acc_id, account_post_count=0)
                                    self._cache['settings'][grp]['account'] = acc_id
                                    self._cache['settings'][grp]['account_post_count'] = 0
                                    self.log(f"[{grp}] 계정 선택: {acc_id}", 'warning')
                                except Exception as e:
                                    self.log(f"[{grp}] 계정 설정 오류: {e}", 'warning')

                        if not acc:
                            self.log(f"[{grp}] 사용 가능한 계정 없음", 'warning')
                            continue

                        # 콘텐츠 확인
                        try:
                            contents = self.content_mgr.get_ready_contents_by_group(grp)
                        except Exception as e:
                            self.log(f"[{grp}] 콘텐츠 조회 오류: {e}", 'warning')
                            had_network_error = True
                            continue

                        if not contents:
                            self.log(f"[{grp}] 발행대기 콘텐츠 없음", 'info')
                            continue

                        content = contents[0]
                        total_contents = len(contents)

                        # 발행 실행 (진행률 표시 개선)
                        self.log(f"[{grp}] 발행 시작 [1/{total_contents}]: {content['title'][:25]}...", 'info')
                        result = self.publish_single(grp, acc, content)

                        if result['success']:
                            published = True
                            self.stats['published'] += 1
                            consecutive_network_errors = 0

                            # 캐시 업데이트
                            if grp in self._cache['settings']:
                                self._cache['settings'][grp]['account_post_count'] = \
                                    self._cache['settings'][grp].get('account_post_count', 0) + 1

                            if not self.stop_requested:
                                wait = random.randint(3, 8)
                                self.log(f"{wait}초 대기...")
                                self._wait(wait)
                        else:
                            if result.get('protected'):
                                # 보호조치: 계정 suspended 처리
                                try:
                                    self.account_mgr.update_status(grp, acc['account_id'], 'suspended')
                                except:
                                    pass

                                # 쿠키 삭제
                                cookie_path = f"cookies/{acc['account_id']}_cookies.json"
                                if os.path.exists(cookie_path):
                                    os.remove(cookie_path)

                                # 계정 초기화
                                try:
                                    self.settings_mgr.update_setting(grp, account='')
                                    self._cache['settings'][grp]['account'] = ''
                                except:
                                    pass

                                self.log(f"[{grp}] {acc['account_id']} 보호조치 -> suspended", 'error')

                                # 콘텐츠는 ready로 복원
                                try:
                                    self.content_mgr.release_publishing_lock(content['sheet_name'], content['row_num'])
                                except:
                                    pass
                            else:
                                self.stats['failed'] += 1

                        # 통계 업데이트 콜백
                        if on_stats_update:
                            on_stats_update(self.stats['published'], self.stats['failed'])

                        # 새로고침 콜백
                        if on_refresh:
                            on_refresh()

                    except Exception as e:
                        self.log(f"[{grp}] 루프 오류: {e}", 'error')
                        had_network_error = True

                    finally:
                        try:
                            self.settings_mgr.release_lock(grp, self.bot_id)
                        except:
                            pass

                # 대기 로직
                if not self.stop_requested:
                    if had_network_error:
                        consecutive_network_errors += 1
                        wait_time = min(3 * consecutive_network_errors, 12)  # 최대 12초
                        self.log(f"네트워크 오류 발생, {wait_time}초 대기...", 'warning')
                        self._wait(wait_time)

                        # 캐시 갱신 시도
                        if consecutive_network_errors >= 3:
                            self._refresh_cache(groups)
                            consecutive_network_errors = 0
                    elif not published:
                        self.log("대기중... (12초)")
                        self._wait(12)
                    # published=True면 이미 발행 후 대기했으므로 추가 대기 없음

        finally:
            self.log("발행 엔진 종료", 'warning')

            # 잠금 해제 (별도 스레드에서 처리 - 메인 종료 차단 방지)
            def release_locks_async():
                for grp in groups:
                    try:
                        self.settings_mgr.release_lock(grp, self.bot_id)
                    except:
                        pass

            threading.Thread(target=release_locks_async, daemon=True).start()
