"""
공유봇 V1 실행 스크립트 (RSS 기반)

Usage:
    python share_bot.py
"""

import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.share.share_bot_v1 import ShareBot
import tkinter as tk


def main():
    root = tk.Tk()
    app = ShareBot(root)
    root.mainloop()


if __name__ == "__main__":
    main()
