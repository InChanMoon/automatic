# Google Sheets API 설정 가이드

## 1. Google Sheets API 활성화

### 1-1. Google Cloud Console 접속
1. https://console.cloud.google.com/ 접속
2. 기존에 만든 프로젝트 선택: `naver-blog-automation`

### 1-2. Google Sheets API 활성화
1. 좌측 메뉴 → **API 및 서비스** → **라이브러리**
2. 또는 직접 URL: https://console.cloud.google.com/apis/library
3. 검색창에 **"Google Sheets API"** 입력
4. **Google Sheets API** 클릭
5. **사용** 버튼 클릭
6. API 활성화 완료!

---

## 2. 테스트용 스프레드시트 생성

### 2-1. Google Sheets 접속
1. https://docs.google.com/spreadsheets/ 접속
2. **새 스프레드시트 만들기** (+) 클릭
3. 스프레드시트 이름: `블로그 자동화 관리`

### 2-2. Sheet 1: 라이선스 관리
1. 첫 번째 시트 이름을 `라이선스`로 변경
2. A1부터 다음 헤더 입력:

| license_key | user_email | status | is_admin | api_usage_today | api_limit_daily | created_date |
|-------------|------------|--------|----------|-----------------|-----------------|--------------|

**컬럼 설명:**
- `license_key`: 라이선스 키 (예: LICENSE-001)
- `user_email`: 사용자 이메일
- `status`: active/suspended (관리자가 직접 변경)
- `is_admin`: TRUE/FALSE (TRUE면 API 무제한)
- `api_usage_today`: 오늘 사용한 Gemini API 호출 횟수
- `api_limit_daily`: 일일 API 호출 제한 (is_admin=TRUE면 무시됨)
- `created_date`: 생성일자

3. 테스트 데이터 입력 예시:
```
A2: LICENSE-ADMIN | your@email.com | active | TRUE | 0 | 999999 | 2025-01-15
A3: LICENSE-001 | test@example.com | active | FALSE | 0 | 50 | 2025-01-15
```

### 2-3. Sheet 2: 계정 관리
1. 하단의 **+** 버튼으로 새 시트 추가
2. 시트 이름: `계정`
3. A1부터 다음 헤더 입력:

| naver_id | naver_pw | status | last_post_time | total_posts |
|----------|----------|--------|----------------|-------------|

**컬럼 설명:**
- `naver_id`: 네이버 아이디
- `naver_pw`: 네이버 비밀번호
- `status`: available/in_use/blocked (시스템이 자동 관리)
- `last_post_time`: 마지막 포스팅 시간
- `total_posts`: 총 발행 글 수

**중요:** 모든 라이선스가 모든 계정을 공유해서 사용합니다.

4. 테스트 데이터 입력 예시:
```
A2: kddselect | mrxw4hB7fT | available | | 0
```

### 2-4. Sheet 3: 콘텐츠 관리
1. 새 시트 추가
2. 시트 이름: `콘텐츠`
3. A1부터 다음 헤더 입력:

| keyword | title | content | status | license_key | assigned_account | published_url | created_time | published_time |
|---------|-------|---------|--------|-------------|------------------|---------------|--------------|----------------|

**컬럼 설명:**
- `keyword`: 키워드
- `title`: 생성된 제목
- `content`: 생성된 본문
- `status`: pending/generated/publishing/published/failed
- `license_key`: 이 콘텐츠를 요청한 라이선스 키
- `assigned_account`: 발행에 사용된 네이버 계정
- `published_url`: 발행된 URL
- `created_time`: 콘텐츠 생성 시간
- `published_time`: 발행 완료 시간

4. 테스트 데이터 입력 예시:
```
A2: 테스트키워드 | | | pending | LICENSE-001 | | | 2025-01-15 10:00:00 |
```

---

## 3. Service Account에 스프레드시트 공유

### 3-1. 스프레드시트 ID 확인
1. 스프레드시트 URL 확인:
   ```
   https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/edit
   ```
2. **스프레드시트 ID는 중간 부분**: `1AbCdEfGhIjKlMnOpQrStUvWxYz`
3. 메모장에 복사해두기

### 3-2. Service Account에 공유
1. 스프레드시트 우측 상단 **공유** 버튼 클릭
2. **사용자 및 그룹 추가** 입력란에 Service Account 이메일 입력
   - 예: `blog-automation-service@naver-blog-automation.iam.gserviceaccount.com`
3. 권한: **편집자** 선택
4. **전송** 클릭

---

## 4. config.json에 스프레드시트 ID 추가

`config.json` 파일을 열어서 다음 섹션 추가:

```json
{
  "google_drive": { ... },
  "gemini_api": { ... },
  "google_sheets": {
    "spreadsheet_id": "여기에_스프레드시트_ID_입력"
  },
  "naver_accounts": [ ... ]
}
```

---

## 5. 테스트

테스트 스크립트로 Sheets API 연결 확인:

```bash
python setup/test_sheets_connection.py
```

### 예상 출력:
```
============================================================
Google Sheets API 연결 테스트
============================================================

1. JSON 파일 확인 중...
✅ JSON 파일 찾음: credentials/google_service_account.json

2. Google Sheets API 활성화 확인 중...
✅ Sheets API 활성화됨

3. 스프레드시트 연결 중...
✅ 스프레드시트 연결 성공!
   제목: 블로그 자동화 관리

4. 시트 목록 확인 중...
✅ 시트 목록:
   - 라이선스
   - 계정
   - 콘텐츠

5. 계정 데이터 읽기 테스트...
✅ 계정 데이터 읽기 성공!
   총 1개 계정 발견
   - kddselect (상태: available)

============================================================
✅ 모든 테스트 성공!
============================================================
```

---

## ✅ 완료 체크리스트

- [ ] Google Sheets API 활성화됨
- [ ] 스프레드시트 생성됨 (3개 시트)
- [ ] 헤더 입력 완료
- [ ] Service Account에 스프레드시트 공유됨
- [ ] 스프레드시트 ID 복사됨
- [ ] config.json에 spreadsheet_id 추가됨
- [ ] 테스트 스크립트 성공

---

## 다음 단계

Sheets API 설정이 완료되면:
1. 계정 관리 기능 개발 (CRUD)
2. 라이선스 검증 시스템
3. 콘텐츠 생성 및 할당 시스템
