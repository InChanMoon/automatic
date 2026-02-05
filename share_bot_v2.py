"""
공유봇 V2 실행 스크립트

Usage:
    python share_bot_v2.py
"""

import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.share.share_bot import ShareBotV2, main

if __name__ == "__main__":
    main()
