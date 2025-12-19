@echo off
chcp 65001 >nul
echo ========================================
echo   발행봇 EXE 빌드
echo ========================================
echo.

pip install pyinstaller

echo.
echo 빌드 중... (2-3분 소요)
echo.

pyinstaller --noconfirm ^
    --name "publisher_bot" ^
    --windowed ^
    --hidden-import "google.auth" ^
    --hidden-import "google.oauth2.service_account" ^
    --hidden-import "googleapiclient.discovery" ^
    --hidden-import "googleapiclient.http" ^
    --hidden-import "playwright.sync_api" ^
    --hidden-import "playwright_stealth" ^
    --hidden-import "PIL" ^
    --hidden-import "PIL.Image" ^
    --hidden-import "pyperclip" ^
    --hidden-import "anthropic" ^
    --hidden-import "google.generativeai" ^
    --collect-all "playwright" ^
    publisher_bot.py

if %errorlevel% neq 0 (
    echo.
    echo [X] 빌드 실패!
    pause
    exit /b 1
)

echo.
echo 필수 파일 복사 중...

copy "config.json" "dist\publisher_bot\" 2>nul
xcopy /e /i /y "credentials" "dist\publisher_bot\credentials" 2>nul
copy "naver_cookies.json" "dist\publisher_bot\" 2>nul
if not exist "dist\publisher_bot\image_cache" mkdir "dist\publisher_bot\image_cache"

echo.
echo ========================================
echo   빌드 완료!
echo ========================================
echo.
echo 위치: dist\publisher_bot\publisher_bot.exe
echo.
pause
