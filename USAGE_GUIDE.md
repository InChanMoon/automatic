# 네이버 블로그 자동화 시스템 - 사용 가이드

## 📋 시스템 구조

```
콘텐츠 생성 워커 → Google Sheets (콘텐츠 시트)
                    ↓
발행 워커 ← Google Drive (이미지)
                    ↓
               네이버 블로그
```

## 🚀 설치

### 1. 패키지 설치
```bash
pip install -r requirements_phase1.txt
```

### 2. Playwright 브라우저 설치
```bash
python -m playwright install chromium
```

---

## 📖 주요 기능

### 1. 키워드 추가

```bash
python main.py --add-keyword "키워드" --license LICENSE-ADMIN
```

**예시:**
```bash
python main.py --add-keyword "파이썬 강좌" --license LICENSE-ADMIN
```

**결과:**
- Google Sheets `콘텐츠` 시트에 pending 상태로 추가됨

---

### 2. 콘텐츠 생성 워커 실행

```bash
python main.py --worker content
```

**동작:**
1. pending 상태의 키워드 검색
2. 라이선스 검증 (API 사용량 확인)
3. Gemini API로 블로그 글 생성
4. 생성된 콘텐츠를 Sheets에 저장 (generated 상태)
5. 무한 루프 (Ctrl+C로 종료)

**로그 예시:**
```
============================================================
콘텐츠 생성 워커 시작
============================================================

⏳ pending 콘텐츠 검색 중...

📝 콘텐츠 생성 시작:
   키워드: 파이썬 강좌
   라이선스: LICENSE-ADMIN

✅ 라이선스 검증 성공: Admin 라이선스 (무제한)

🤖 Gemini API 호출 중...
✅ 콘텐츠 생성 완료
   제목: 파이썬 초보자를 위한 완벽 가이드
   본문 길이: 1524자

✅ 작업 완료!
```

---

### 3. 발행 워커 실행 (TODO)

```bash
python main.py --worker publisher
```

**현재 상태:** 미구현
**다음 단계:** `test/test_blog_login.py` 기반으로 통합 예정

---

### 4. 시스템 상태 확인

```bash
python main.py --status
```

**출력 예시:**
```
============================================================
시스템 상태
============================================================

📊 콘텐츠 상태:
   pending: 2개
   generated: 5개
   publishing: 0개
   published: 15개
   failed: 0개

👥 계정 상태:
   available: 3개
   in_use: 0개
   blocked: 0개
```

---

## 🔧 Google Sheets 수동 작업

### 1. 라이선스 관리

**새 라이선스 추가:**
1. Google Sheets → `라이선스` 시트 열기
2. 새 행 추가:
   ```
   LICENSE-002 | user@email.com | active | FALSE | 0 | 50 | 2025-01-15
   ```

**API 사용량 리셋 (매일):**
- `api_usage_today` 컬럼을 모두 0으로 변경
- 또는 Python 스크립트:
  ```python
  from src.sheets.license_manager import LicenseManager

  mgr = LicenseManager()
  mgr.reset_daily_usage()
  ```

---

### 2. 계정 관리

**새 계정 추가:**
1. Google Sheets → `계정` 시트 열기
2. 새 행 추가:
   ```
   newaccount | password123 | available | | 0
   ```

**또는 Python 스크립트:**
```python
from src.sheets.account_manager import AccountManager

mgr = AccountManager()
mgr.add_account('newaccount', 'password123')
```

---

### 3. 콘텐츠 관리

**수동으로 키워드 추가:**
1. Google Sheets → `콘텐츠` 시트 열기
2. 새 행 추가:
   ```
   키워드 | | | pending | LICENSE-ADMIN | | | 2025-01-15 10:00:00 |
   ```

**실패한 콘텐츠 재시도:**
- `status` 컬럼을 `failed` → `pending`으로 변경

---

## 🖼️ Google Drive 이미지 폴더 구조

```
blog_images/
├── 파이썬_강좌/
│   ├── 001/
│   │   ├── image1.jpg
│   │   ├── image2.jpg
│   │   └── image3.jpg
│   ├── 002/
│   │   ├── image1.jpg
│   │   └── image2.jpg
│   └── _used/
│       └── 001/  (사용 완료된 폴더)
├── 다이어트_방법/
│   ├── 001/
│   └── 002/
└── _used/
```

**주의:**
- 키워드 이름으로 폴더 생성
- 하위에 001, 002, 003... 배치 폴더 생성
- 각 배치 폴더에 이미지 업로드
- 사용 완료된 배치는 자동으로 `_used`로 이동

---

## 💡 팁

### 1. 백그라운드 실행 (Linux/Mac)

```bash
nohup python main.py --worker content > content_worker.log 2>&1 &
```

### 2. 여러 워커 동시 실행

터미널 1:
```bash
python main.py --worker content
```

터미널 2 (나중에 구현):
```bash
python main.py --worker publisher
```

### 3. 라이선스별 API 사용량 확인

Google Sheets에서 `라이선스` 시트의 `api_usage_today` / `api_limit_daily` 컬럼 확인

---

## ⚠️ 주의사항

1. **API 키 보안:**
   - `config.json`은 절대 Git에 커밋하지 마세요
   - `.gitignore`에 추가되어 있음

2. **라이선스 관리:**
   - Admin 라이선스 (`is_admin=TRUE`)는 신중하게 부여
   - 일반 사용자는 적절한 `api_limit_daily` 설정

3. **계정 보안:**
   - 네이버 계정 비밀번호는 Google Sheets에 평문 저장됨
   - 스프레드시트 공유 시 주의!

4. **이미지 폴더:**
   - 키워드 이름과 폴더 이름이 정확히 일치해야 함
   - 배치 폴더 이름은 숫자만 (001, 002, ...)

---

## 🐛 문제 해결

### 1. ModuleNotFoundError

```bash
pip install -r requirements_phase1.txt
```

### 2. Google Sheets API 오류

- Service Account JSON 파일 확인
- 스프레드시트 공유 확인 (편집자 권한)
- Sheets API 활성화 확인

### 3. Gemini API 오류

- API 키 확인
- 사용량 제한 확인 (무료 tier 제한)

---

## 📝 다음 단계 (TODO)

1. **발행 워커 구현**
   - `test/test_blog_login.py` 통합
   - Drive 이미지 다운로드 및 클립보드 삽입
   - 발행 상태 업데이트

2. **스케줄링**
   - 매일 자정 API 사용량 리셋
   - 주기적 콘텐츠 생성
   - 주기적 발행

3. **GUI 또는 웹 인터페이스**
   - 키워드 추가
   - 상태 모니터링
   - 라이선스 관리

4. **고도화**
   - 이미지 자동 검색 및 다운로드
   - 카테고리 자동 분류
   - 태그 자동 생성
