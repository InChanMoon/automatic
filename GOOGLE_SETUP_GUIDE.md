# Google Cloud 설정 가이드

## 📋 목차
1. [Google Cloud Console 프로젝트 생성](#1-google-cloud-console-프로젝트-생성)
2. [Google Drive API 활성화](#2-google-drive-api-활성화)
3. [Service Account 생성](#3-service-account-생성)
4. [JSON 키 다운로드](#4-json-키-다운로드)
5. [Google Drive 폴더 준비](#5-google-drive-폴더-준비)
6. [Service Account에 폴더 공유](#6-service-account에-폴더-공유)
7. [테스트](#7-테스트)

---

## 1. Google Cloud Console 프로젝트 생성

### 1-1. Google Cloud Console 접속
1. 브라우저에서 https://console.cloud.google.com/ 접속
2. Google 계정으로 로그인

### 1-2. 새 프로젝트 생성
1. 상단의 **프로젝트 선택** 클릭
2. **새 프로젝트** 클릭
3. 프로젝트 이름 입력: `naver-blog-automation`
4. **만들기** 클릭
5. 프로젝트 생성 완료 (1~2분 소요)

---

## 2. Google Drive API 활성화

### 2-1. API 및 서비스 페이지
1. 좌측 메뉴 → **API 및 서비스** → **라이브러리** 클릭
2. 또는 직접 URL 접속: https://console.cloud.google.com/apis/library

### 2-2. Drive API 활성화
1. 검색창에 **"Google Drive API"** 입력
2. **Google Drive API** 클릭
3. **사용** 버튼 클릭
4. API 활성화 완료

### 2-3. (선택) Gemini API 확인
- Gemini API는 이미 활성화되어 있을 것입니다 (API 키가 있으므로)
- 확인: https://console.cloud.google.com/apis/library
- 검색: "Generative Language API" → 이미 사용 설정됨 확인

---

## 3. Service Account 생성

### 3-1. Service Account 페이지 이동
1. 좌측 메뉴 → **API 및 서비스** → **사용자 인증 정보** 클릭
2. 또는 직접 URL: https://console.cloud.google.com/apis/credentials

### 3-2. Service Account 생성
1. 상단의 **+ 사용자 인증 정보 만들기** 클릭
2. **서비스 계정** 선택
3. 서비스 계정 세부정보:
   - **서비스 계정 이름**: `blog-automation-service`
   - **서비스 계정 ID**: 자동 생성됨 (예: `blog-automation-service@...`)
   - **서비스 계정 설명**: `네이버 블로그 자동화용 서비스 계정`
4. **만들기 및 계속하기** 클릭

### 3-3. 역할 설정 (선택 사항)
1. **역할 선택** → 건너뛰기 (역할 없이 사용 가능)
2. **계속** 클릭
3. **완료** 클릭

---

## 4. JSON 키 다운로드

### 4-1. 서비스 계정 선택
1. **API 및 서비스** → **사용자 인증 정보** 페이지에서
2. 방금 만든 서비스 계정 이메일 클릭
   - 형식: `blog-automation-service@naver-blog-automation.iam.gserviceaccount.com`

### 4-2. 키 생성
1. 상단 **키** 탭 클릭
2. **키 추가** → **새 키 만들기** 클릭
3. **JSON** 선택
4. **만들기** 클릭
5. JSON 파일 자동 다운로드됨
   - 파일명 예: `naver-blog-automation-xxxxx.json`

### 4-3. JSON 파일 배치
1. 다운로드된 JSON 파일을 프로젝트 폴더로 이동
2. 파일 위치: `c:\Users\tt\Desktop\project\automatic\credentials\`
3. 파일명 변경: `google_service_account.json`

**최종 경로:**
```
c:\Users\tt\Desktop\project\automatic\credentials\google_service_account.json
```

---

## 5. Google Drive 폴더 준비

### 5-1. Drive에서 폴더 생성
1. Google Drive 접속: https://drive.google.com/
2. **+ 새로 만들기** → **폴더** 클릭
3. 폴더 이름: `blog_images`
4. **만들기** 클릭

### 5-2. 테스트용 하위 폴더 생성
1. `blog_images` 폴더 열기
2. 하위 폴더 생성:
   ```
   blog_images/
   ├── 테스트_키워드/
   │   ├── 001/
   │   └── 002/
   └── _used/
   ```

3. 구체적 단계:
   - `blog_images` 폴더 안에서 **+ 새로 만들기** → **폴더**
   - 이름: `테스트_키워드`
   - `테스트_키워드` 안에 `001`, `002` 폴더 생성
   - `blog_images` 안에 `_used` 폴더 생성

### 5-3. 테스트 이미지 업로드
1. `001` 폴더에 이미지 2~3개 업로드
2. `002` 폴더에 이미지 2~3개 업로드
3. (이미지 없으면 임시로 아무 이미지나 사용)

### 5-4. 폴더 ID 복사
1. `blog_images` 폴더에서 우클릭 → **공유** → **링크 복사**
2. URL 형식: `https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz`
3. **폴더 ID는 마지막 부분**: `1AbCdEfGhIjKlMnOpQrStUvWxYz`
4. 메모장에 복사해두기

---

## 6. Service Account에 폴더 공유

### 6-1. Service Account 이메일 복사
1. Google Cloud Console → **사용자 인증 정보** 페이지
2. 서비스 계정 이메일 복사
   - 예: `blog-automation-service@naver-blog-automation.iam.gserviceaccount.com`

### 6-2. Drive 폴더 공유
1. Google Drive에서 `blog_images` 폴더 우클릭
2. **공유** 클릭
3. **사용자 및 그룹 추가** 입력란에 Service Account 이메일 붙여넣기
4. 권한: **편집자** 선택
5. **전송** 클릭
6. ✅ 공유 완료!

---

## 7. 테스트

### 7-1. 테스트 스크립트 실행
프로젝트 폴더에 테스트 스크립트가 생성됩니다.

```bash
python setup/test_drive_connection.py
```

### 7-2. 예상 출력
```
✅ Google Drive 연결 성공!
✅ blog_images 폴더 찾기 성공!
   폴더 ID: 1AbCdEfGhIjKlMnOpQrStUvWxYz

📁 폴더 목록:
   - 테스트_키워드
   - _used

✅ 테스트 완료!
```

### 7-3. 오류 발생 시

**오류 1: JSON 파일을 찾을 수 없음**
```
FileNotFoundError: credentials/google_service_account.json
```
→ JSON 파일 경로 확인

**오류 2: 권한 없음**
```
HttpError 403: Insufficient Permission
```
→ Service Account에 폴더 공유했는지 확인

**오류 3: API 활성화 안됨**
```
Google Drive API has not been used in project
```
→ Drive API 활성화 확인

---

## ✅ 완료 체크리스트

설정이 완료되면 아래 항목들이 준비되어 있어야 합니다:

- [ ] Google Cloud 프로젝트 생성됨
- [ ] Google Drive API 활성화됨
- [ ] Service Account 생성됨
- [ ] `credentials/google_service_account.json` 파일 존재
- [ ] Google Drive `blog_images` 폴더 생성됨
- [ ] Service Account에 폴더 공유됨
- [ ] 폴더 ID 복사됨
- [ ] 테스트 스크립트 성공

---

## 📝 다음 단계

Google Cloud 설정이 완료되면:

1. `config.json` 파일 생성 (자동)
2. Gemini API 키 설정
3. 네이버 계정 설정
4. 프로그램 실행

**설정이 완료되면 알려주세요!**
