# Phase 0 설치 및 사용 가이드

## 1. Python 버전 확인
```bash
python --version
# Python 3.8 이상 필요
```

## 2. 가상환경 생성 (권장)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# 가상환경 활성화 확인 - 프롬프트 앞에 (venv) 표시됨
```

## 3. pip 업그레이드
```bash
python -m pip install --upgrade pip
```

## 4. 패키지 설치

### 방법 1: requirements 파일로 한번에 설치
```bash
pip install -r requirements_phase0.txt
```

### 방법 2: 하나씩 설치 (에러 발생 시)
```bash
pip install playwright==1.41.0
pip install playwright-stealth==1.0.6
pip install pyperclip==1.8.2
pip install setuptools
pip install Pillow
```

## 5. Playwright 브라우저 설치
```bash
python -m playwright install chromium
```

## 6. 테스트 이미지 생성 (선택 사항)
```bash
python test/create_test_image.py
```
→ `test/test_image.jpg` 파일이 생성됩니다.

## 7. 테스트 실행
```bash
cd test
python test_blog_login.py
```

### 실행 시 입력 사항
1. **네이버 아이디**: 테스트할 네이버 계정 아이디
2. **네이버 비밀번호**: 테스트할 네이버 계정 비밀번호
3. **이미지 업로드 테스트**: `y` 입력 시 이미지 업로드 테스트
4. **이미지 파일 경로**: 이미지 테스트 선택 시 이미지 절대 경로
   - 예: `C:\Users\tt\Desktop\project\automatic\test\test_image.jpg`

---

## 흔한 에러 해결

### 에러 1: playwright-stealth 설치 안됨
```
ERROR: Could not find a version that satisfies the requirement playwright-stealth
```

**해결:** playwright-stealth는 pip 저장소에 없을 수 있습니다.
```bash
# GitHub에서 직접 설치
pip install git+https://github.com/AtuboDad/playwright_stealth.git
```

### 에러 2: pkg_resources 모듈 없음
```
ModuleNotFoundError: No module named 'pkg_resources'
```

**해결:**
```bash
pip install setuptools
```

### 에러 3: UnicodeDecodeError (인코딩 오류)
```
UnicodeDecodeError: 'cp949' codec can't decode byte
```

**해결:** requirements 파일에 한글 주석이 있으면 발생. 이미 영문으로 수정되어 있습니다.

### 에러 4: Microsoft Visual C++ 필요
```
error: Microsoft Visual C++ 14.0 or greater is required
```

**해결:**
- https://visualstudio.microsoft.com/ko/downloads/
- "Visual Studio용 빌드 도구" 다운로드 및 설치
- "C++를 사용한 데스크톱 개발" 체크

### 에러 5: 권한 오류
```
PermissionError: [WinError 5] Access is denied
```

**해결:**
```bash
# --user 옵션 추가
pip install --user -r requirements_phase0.txt
```

### 에러 6: Playwright 브라우저 설치 실패
```
Failed to install browsers
```

**해결:**
```bash
# 관리자 권한으로 CMD 실행 후
python -m playwright install chromium --with-deps
```

---

## 테스트 성공 시 출력 예시

```
============================================================
네이버 블로그 자동화 테스트기 (Phase 0)
============================================================

네이버 아이디: myuser
네이버 비밀번호: ****
이미지 업로드 테스트? (y/n, 기본값: n): y
이미지 파일 경로 (절대 경로): C:\...\test\test_image.jpg
✅ 이미지 파일 확인: C:\...\test\test_image.jpg

🌐 브라우저 초기화 중...
✅ 브라우저 초기화 완료

📄 로그인 페이지 접속 중...
🔐 로그인 시도 중...
✅ 아이디 입력 완료
✅ 비밀번호 입력 완료
✅ 로그인 버튼 클릭
✅ 로그인 성공!

📝 글쓰기 페이지 이동 중...
🔄 iframe 전환 중...
✅ iframe 전환 완료

🗑️ 팝업 닫기 시도 중...
✅ 임시 저장 글 팝업 닫기 (취소 버튼 클릭)

✍️ 테스트 글 작성 중...
✅ 제목 입력: 테스트 글 - 2025-12-15 14:30:00
✅ 본문 입력: 이것은 테스트 글입니다.

🖼️ 이미지 업로드 시도 중...
✅ 이미지 파일 선택 완료
✅ 이미지 업로드 완료

📤 발행 시도 중...
✅ 발행 버튼 클릭
✅ 발행 확인 버튼 클릭

📋 발행 완료 대기 중...

============================================================
✅ 테스트 완료!
============================================================
발행된 글 제목: 테스트 글 - 2025-12-15 14:30:00
발행된 URL: https://blog.naver.com/myuser/223xxxxx

✅ 발행 성공! 글이 정상적으로 발행되었습니다.

============================================================
브라우저를 확인하세요. 종료하려면 Enter를 누르세요...
```

---

## 주요 개선 사항 (v1.1)

### 1. 발행 URL 정확한 감지
- 발행 후 URL 변경 완료까지 대기 (`wait_for_url`)
- 글쓰기 페이지 → 발행된 글 페이지 전환 확인
- 최대 30초 타임아웃

### 2. 이미지 업로드 기능 추가
- 테스트 이미지 자동 생성 스크립트 제공
- `input[type='file']`에 직접 파일 설정
- 업로드 완료 대기

### 3. 로그인 성공 감지 개선
- URL 변경 대기 방식으로 리다이렉트 처리
- 타임아웃 및 예외 처리 강화

### 4. 팝업 처리
- 임시 저장 글 팝업 자동 닫기
- 도움말 패널 자동 닫기

---

## 다음 단계

Phase 0 테스트가 성공하면:
- Phase 1: 발행 봇 기본 기능 개발
- Phase 2: 콘텐츠 생성기 GUI 개발
- Phase 3: IP 관리 및 고도화

테스트 성공 여부를 확인한 후 다음 단계로 진행하세요!
