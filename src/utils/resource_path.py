# -*- coding: utf-8 -*-
"""
PyInstaller EXE 빌드 시 리소스 경로 처리
"""

import sys
import os


def get_resource_path(relative_path):
    """
    PyInstaller로 빌드된 EXE에서 리소스 파일 경로 반환

    Args:
        relative_path: 상대 경로 (예: 'config.json', 'credentials/xxx.json')

    Returns:
        절대 경로
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller로 빌드된 EXE 실행 시
        base_path = sys._MEIPASS
    else:
        # 일반 Python 실행 시
        base_path = os.path.abspath('.')

    return os.path.join(base_path, relative_path)


def get_config_path():
    """config.json 경로 반환"""
    return get_resource_path('config.json')


def get_credentials_path():
    """credentials/google_service_account.json 경로 반환"""
    return get_resource_path('credentials/google_service_account.json')
