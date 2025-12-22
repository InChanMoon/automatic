"""
재시도 유틸리티

API 호출 등에서 사용하는 재시도 로직
"""

import time
import functools
from typing import Callable, Tuple, Type


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] = None
):
    """
    지수 백오프 재시도 데코레이터

    Args:
        max_attempts: 최대 시도 횟수
        initial_delay: 첫 재시도 전 대기 시간 (초)
        backoff_factor: 대기 시간 증가 배수
        exceptions: 재시도할 예외 타입들
        on_retry: 재시도 시 호출할 콜백 (attempt, exception)

    Usage:
        @retry_with_backoff(max_attempts=3, exceptions=(ConnectionError,))
        def api_call():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        raise

                    if on_retry:
                        on_retry(attempt, e)

                    time.sleep(delay)
                    delay *= backoff_factor

            raise last_exception

        return wrapper
    return decorator


def retry_api_call(
    func: Callable,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    log_callback: Callable[[str], None] = None
):
    """
    API 호출 재시도 함수

    Args:
        func: 실행할 함수 (인자 없음)
        max_attempts: 최대 시도 횟수
        initial_delay: 첫 재시도 전 대기 시간 (초)
        backoff_factor: 대기 시간 증가 배수
        log_callback: 로그 콜백

    Returns:
        함수 실행 결과

    Raises:
        마지막 예외
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e

            if attempt == max_attempts:
                if log_callback:
                    log_callback(f"[X] 최대 재시도 횟수 초과: {e}")
                raise

            if log_callback:
                log_callback(f"[!] 시도 {attempt}/{max_attempts} 실패, {delay:.1f}초 후 재시도: {e}")

            time.sleep(delay)
            delay *= backoff_factor

    raise last_exception
