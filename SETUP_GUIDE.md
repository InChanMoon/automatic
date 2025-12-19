# 네이버 블로그 자동화 시스템 - 설정 가이드

## 목차
1. [프로젝트 구조](#프로젝트-구조)
2. [필수 패키지 설치](#필수-패키지-설치)
3. [Google Cloud 설정](#google-cloud-설정)
4. [스프레드시트 설정](#스프레드시트-설정)
5. [config.json 설정](#configjson-설정)
6. [프로그램 실행](#프로그램-실행)

---

## 프로젝트 구조

```
automatic/
├── content_creator_pro_v3.py   # 콘텐츠 생성기 (GUI)
├── publisher_bot.py            # 발행봇 (GUI)
├── publisher_engine.py         # 발행 엔진 (핵심 로직)
├── config.json                 # 설정 파일 (직접 수정)
├── credentials/                # Google 인증 파일
│   └── google_service_account.json
├── src/
│   ├── sheets/                 # Google Sheets 연동
│   │   ├── base.py             # 기본 클래스
│   │   ├── content_manager_v3.py
│   │   ├── account_manager.py
│   │   ├── publish_settings_manager.py
│   │   └── license_manager.py
│   ├── content/                # AI 콘텐츠 생성
│   │   ├── gemini_generator.py
│   │   └── claude_generator.py
│   ├── publisher/              # 네이버 발행
│   │   └── naver_blog_publisher.py
│   ├── drive/                  # Google Drive 이미지
│   │   └── image_manager.py
│   └── crawler/                # 블로그 크롤러
│       └── naver_blog_crawler.py
├── setup/                      # 설정 스크립트
│   ├── update_sheets_structure.py
│   ├── apply_content_sheet_format.py
│   ├── apply_account_sheet_format.py
│   └── migrate_sheets_v2.py
└── dist/publisher_bot/         # EXE 빌드 결과
```

---

## 필수 패키지 설치

### Python 설치
- Python 3.10 이상 필요
- https://www.python.org/downloads/

### 패키지 설치
```bash
pip install -r requirements_phase1.txt
```

### Playwright 브라우저 설치
```bash
python -m playwright install chromium
```

### requirements_phase1.txt 내용
```
playwright==1.41.0
playwright-stealth==1.0.6
pyperclip==1.8.2
setuptools
Pillow
pywin32  # Windows만
google-auth==2.27.0
google-api-python-client==2.116.0
google-generativeai==0.3.2
anthropic
requests
```

---

## Google Cloud 설정

### 1. Google Cloud Console 프로젝트 생성
1. https://console.cloud.google.com/ 접속
2. 새 프로젝트 생성

### 2. API 활성화
- **Google Sheets API** 활성화
- **Google Drive API** 활성화

### 3. 서비스 계정 생성
1. IAM 및 관리자 > 서비스 계정
2. 서비스 계정 만들기
3. JSON 키 생성 및 다운로드
4. 다운로드한 파일을 `credentials/google_service_account.json`으로 저장

### 4. Gemini API 키 (콘텐츠 생성용)
1. https://makersuite.google.com/app/apikey
2. API 키 생성
3. `config.json`의 `gemini_api.api_key`에 입력

### 5. Claude API 키 (선택)
1. https://console.anthropic.com/
2. API 키 생성
3. `config.json`의 `claude_api.api_key`에 입력

---

## 스프레드시트 설정

### 1. 새 스프레드시트 생성
1. https://docs.google.com/spreadsheets/ 에서 새 스프레드시트 생성
2. URL에서 스프레드시트 ID 복사
   - 예: `https://docs.google.com/spreadsheets/d/[이 부분이 ID]/edit`

### 2. 서비스 계정에 권한 부여
1. 스프레드시트 우측 상단 "공유" 클릭
2. 서비스 계정 이메일 추가 (예: `xxx@xxx.iam.gserviceaccount.com`)
3. **편집자** 권한 부여

### 3. 필수 시트(탭) 생성

#### 라이선스 시트
탭 이름: `라이선스`
| 컬럼 | 내용 |
|------|------|
| A | license_key |
| B | status (active/inactive) |
| C | plan |
| D | daily_limit |
| E | used_today |
| F | last_reset |
| G | created_date |

예시 데이터:
```
LICENSE-ADMIN | active | unlimited | 9999 | 0 | 2024-01-01 | 2024-01-01
```

#### 계정 시트 (그룹별)
탭 이름: `계정_그룹명` (예: `계정_테스트`, `계정_메인`)
| 컬럼 | 내용 |
|------|------|
| A | account_id (네이버 ID) |
| B | password |
| C | status (active/suspended/banned) |
| D | last_used |

예시 데이터:
```
naver_id_1 | password123 | active |
naver_id_2 | password456 | active |
```

#### 콘텐츠 시트 (그룹별)
탭 이름: `콘텐츠_그룹명` (예: `콘텐츠_테스트`, `콘텐츠_메인`)
| 컬럼 | 내용 |
|------|------|
| A | account_group |
| B | keyword |
| C | title |
| D | content (HTML) |
| E | created_time |
| F | published_url |
| G | published_time |
| H | published_account |
| I | content_id |
| J | status (ready/publishing/published/failed) |
| K | scheduled_time |

#### 발행설정 시트
탭 이름: `발행설정`
| 컬럼 | 내용 |
|------|------|
| A | 그룹 |
| B | 발행대기 |
| C | 계정 |
| D | 계정당발행수 |
| E | 현재계정발행수 |
| F | 이미지인덱스 |
| G | 잠금상태 |
| H | 잠금시간 |

예시 데이터 (그룹당 1행):
```
테스트 | 0 |  | 5 | 0 | {} |  |
메인   | 0 |  | 5 | 0 | {} |  |
```

### 4. 시트 서식 적용 (선택)
```bash
cd setup
python apply_content_sheet_format.py
python apply_account_sheet_format.py
```

---

## config.json 설정

`config_template.json`을 복사하여 `config.json` 생성 후 수정:

```json
{
  "google_drive": {
    "image_root_folder_id": "Google Drive 이미지 폴더 ID"
  },
  "gemini_api": {
    "api_key": "Gemini API 키"
  },
  "claude_api": {
    "api_key": "Claude API 키 (선택)"
  },
  "google_sheets": {
    "spreadsheet_id": "스프레드시트 ID"
  },
  "default_license": "LICENSE-ADMIN"
}
```

### Google Drive 이미지 폴더 구조 (선택)
```
이미지루트폴더/
├── 키워드1/
│   ├── 세트1/
│   │   ├── 1.jpg
│   │   ├── 2.jpg
│   │   └── 3.jpg
│   └── 세트2/
│       ├── 1.jpg
│       └── 2.jpg
└── 키워드2/
    └── 세트1/
        └── 1.jpg
```

Drive 폴더 ID는 URL에서 확인:
- `https://drive.google.com/drive/folders/[이 부분이 ID]`

---

## 프로그램 실행

### 콘텐츠 생성기
```bash
python content_creator_pro_v3.py
```
또는 `콘텐츠생성기실행.bat` 더블클릭

### 발행봇
```bash
python publisher_bot.py
```
또는 `발행봇실행.bat` 더블클릭

### EXE 빌드 (선택)
```bash
build_exe.bat
```
결과물: `dist/publisher_bot/publisher_bot.exe`

---

## 주요 기능 요약

### 콘텐츠 생성기
- **URL 리라이팅**: 기존 블로그 글 URL을 입력하여 AI로 리라이팅
- **프롬프트 작성**: 직접 프롬프트 입력하여 콘텐츠 생성
- **직접 작성**: AI 없이 직접 원고 입력 (라이선스 차감 없음)
- **이미지 마커**: `{img:1}`, `{img:1-5}` 형식으로 이미지 위치 지정
- **예약 발행**: 발행 시간 예약 가능

### 발행봇
- **그룹별 발행**: 계정 그룹 선택하여 발행
- **자동 계정 로테이션**: last_used 기준으로 오래된 계정부터 사용
- **예약 발행 지원**: scheduled_time에 설정된 시간에 발행
- **이미지 자동 삽입**: Drive에서 키워드별 이미지 세트 순환 사용
- **동시 실행**: 여러 발행봇 동시 실행 가능 (잠금 시스템)

---

## 문제 해결

### 1. Google Sheets 연결 실패
- 서비스 계정 JSON 파일 경로 확인
- 스프레드시트에 서비스 계정 이메일 공유 확인
- API 활성화 확인

### 2. Playwright 오류
```bash
python -m playwright install chromium
```

### 3. 네이버 로그인 실패
- 쿠키 만료 시 다시 로그인 필요
- 보안 설정으로 차단된 경우 수동 로그인 후 쿠키 저장

### 4. 이미지 삽입 안됨
- Drive 폴더 ID 확인
- 서비스 계정에 Drive 폴더 공유 확인
- 키워드별 폴더 구조 확인

---

## 시트 구조 마이그레이션

기존 시트 구조에서 새 구조로 변경 시:
```bash
cd setup
python migrate_sheets_v2.py
```

변경 내용:
- 계정 시트: daily_limit, today_count, created_date, memo 컬럼 삭제
- 발행설정 시트: today_count 삭제, 이미지인덱스 추가
