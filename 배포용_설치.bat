@echo off
chcp 65001 >nul
echo ========================================
echo   네이버 블로그 발행봇 설치
echo ========================================
echo.

REM Python 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python이 설치되어 있지 않습니다.
    echo     https://www.python.org/downloads/ 에서 설치 후 다시 실행하세요.
    pause
    exit /b 1
)

echo [1/3] Python 패키지 설치 중...
pip install -r requirements_phase1.txt

echo.
echo [2/3] Playwright 브라우저 설치 중...
python -m playwright install chromium

echo.
echo [3/3] 설정 확인...
if not exist "config.json" (
    echo [!] config.json 파일이 없습니다. config_template.json을 복사하여 설정하세요.
)
if not exist "credentials\google_service_account.json" (
    echo [!] credentials\google_service_account.json 파일이 없습니다.
)

echo.
echo ========================================
echo   설치 완료!
echo ========================================
echo.
echo 실행 방법: python publisher_bot.py
echo 또는: 발행봇실행.bat 더블클릭
echo.
pause
