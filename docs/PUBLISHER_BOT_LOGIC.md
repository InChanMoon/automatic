# 네이버 블로그 발행봇 로직 정리

## 개요

네이버 블로그에 글을 자동으로 발행하는 시스템입니다.
Playwright + Stealth를 사용하여 브라우저 자동화를 수행합니다.

---

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `src/publisher/naver_blog_publisher.py` | 메인 발행 로직 |
| `src/utils/text_image_generator.py` | 텍스트 → 이미지 변환 |
| `src/content/gemini_generator.py` | AI 콘텐츠 생성 (Gemini) |
| `src/content/claude_generator.py` | AI 콘텐츠 생성 (Claude) |

---

## 발행 흐름

```
1. 로그인 (쿠키 또는 수동)
2. 글쓰기 페이지 이동
3. 제목 입력
4. 본문 + 이미지 입력
5. 발행 버튼 클릭 (즉시/예약)
6. 결과 확인
```

---

## 이미지 처리 옵션

### 옵션 1: "자동생성" (`auto_generate_images=True`)

이미지를 텍스트로부터 자동 생성합니다.

#### 동작 방식

1. **마커 파싱**
   - 본문에서 `{img:1}`, `{img:1-5}` 등 마커를 찾음
   - 필요한 최대 이미지 번호 계산

2. **마커가 있는 경우**
   - **1번 이미지**: 항상 제목 이미지 (`create_title_image()`)
   - **2번~ 이미지**: 단락 첫 문장 이미지 (`create_text_image()`)
   - 단락 수 < 필요한 이미지 수 → 초과 마커 제거/수정
   - 예: `{img:1-5}` + 단락 3개 → `{img:1-4}` + 이미지 4개

3. **마커가 없는 경우**
   - 이미지 생성하지 않음
   - 본문 그대로 발행

#### 코드 흐름

```python
# naver_blog_publisher.py
if auto_generate_images and HAS_TEXT_IMAGE_GENERATOR and not images:
    content, images = generate_auto_images_for_publish(title, content)

# text_image_generator.py
def generate_auto_images_for_publish(title, content):
    return generate_images_from_markers(title, content)
    # 마커가 있으면 → 마커 기반 이미지 생성
    # 마커가 없으면 → 이미지 없이 본문 그대로 반환
```

### 옵션 2: "Drive에서 가져오기" (`auto_generate_images=False`)

Google Drive에서 이미지를 가져와 사용합니다.

#### 동작 방식

1. **이미지 리스트 전달**
   - `images` 파라미터로 이미지 경로 리스트 전달

2. **마커 처리**
   - 마커 번호 ≤ 이미지 개수: 해당 이미지 삽입
   - 마커 번호 > 이미지 개수: 마커 제거

3. **이미지 부족 시**
   - 초과 마커는 그냥 제거
   - 추가 이미지 생성 없음

#### 코드 흐름

```python
# 이미지 개수 부족 처리 (naver_blog_publisher.py line 1307-1315)
for marker in markers:
    if marker['start'] > image_count:
        result = result.replace(marker['full_match'], '')  # 마커 제거
```

---

## 이미지 마커 형식

| 형식 | 의미 | 예시 |
|------|------|------|
| `{img:1}` | 1번 이미지 삽입 | 제목 이미지 |
| `{img:2}` | 2번 이미지 삽입 | 단락 이미지 |
| `{img:1-5}` | 1~5번 이미지 연속 삽입 | 여러 이미지 |

---

## 이미지 생성 함수

### create_title_image(title)

제목을 썸네일 스타일 이미지로 변환합니다.

- 크기: 800x400
- 스타일: 랜덤 색상 팔레트 + 장식 요소
- 용도: 1번 이미지 (항상)

### create_text_image(text, style)

텍스트를 이미지로 변환합니다.

- 크기: 800x200
- 스타일: "minimal", "quote", "random"
- 용도: 2번~ 이미지 (단락 첫 문장)

---

## 단락 구조 판단

```python
def has_paragraph_structure(content):
    # 이미지 마커 제거
    clean_content = re.sub(r'\{img:\d+(?:-\d+)?\}', '', content)
    # 빈 줄(\n\n)로 분리
    paragraphs = [p.strip() for p in clean_content.split('\n\n') if p.strip()]
    # 2개 이상이면 단락 구조 있음
    return len(paragraphs) >= 2
```

---

## 발행 메서드

### publish_post()

단일 글 발행

```python
def publish_post(
    self,
    title: str,                    # 글 제목
    content: str,                  # 본문 (마커 포함 가능)
    images: List[str] = None,      # 이미지 경로 리스트
    scheduled_time: str = None,    # 예약시간 (None=즉시)
    progress_callback = None,      # 진행률 콜백
    auto_generate_images = False   # 자동생성 여부
) -> Dict:
    # Returns: {success, url, error, is_scheduled}
```

### publish_multiple()

여러 글 연속 발행

```python
def publish_multiple(
    self,
    posts: List[Dict],             # 발행할 글 목록
    progress_callback = None
) -> List[Dict]:
    # 각 post에 auto_generate_images 키 포함 가능
```

---

## 에러 처리

1. **이미지 자동 생성 실패**
   - 무시하고 텍스트만 발행
   - 로그에 기록

2. **클립보드 미지원**
   - 마커 제거 후 텍스트만 입력

3. **캡차 발생**
   - Gemini로 캡차 풀이 시도
   - 실패 시 수동 입력 대기

---

## 임시 파일 정리

자동 생성된 이미지는 임시 파일로 저장됩니다.
발행 완료/실패 후 `cleanup_temp_images()`로 정리합니다.

```python
# finally 블록에서 정리
if self.auto_generated_images and HAS_TEXT_IMAGE_GENERATOR:
    cleanup_temp_images(self.auto_generated_images)
    self.auto_generated_images = []
```

---

## 예시 시나리오

### 시나리오 1: 자동생성 + 마커 있음

**입력:**
```
title: "블로그 글 제목"
content: "{img:1-3} 첫번째 단락입니다.\n\n두번째 단락입니다.\n\n{img:4} 세번째 단락입니다."
auto_generate_images: True
```

**처리:**
1. 마커 파싱 → 최대 4번 이미지 필요
2. 1번: 제목 이미지 생성
3. 2번: "첫번째 단락입니다." 이미지 생성
4. 3번: "두번째 단락입니다." 이미지 생성
5. 4번: "세번째 단락입니다." 이미지 생성

**결과:** 이미지 4개, 마커 그대로 유지

### 시나리오 2: 자동생성 + 단락 부족

**입력:**
```
title: "블로그 글 제목"
content: "{img:1-5} 첫번째 단락입니다.\n\n두번째 단락입니다."
auto_generate_images: True
```

**처리:**
1. 마커 파싱 → 최대 5번 이미지 필요
2. 1번: 제목 이미지 생성
3. 2번: "첫번째 단락입니다." 이미지 생성
4. 3번: "두번째 단락입니다." 이미지 생성
5. 4~5번: 단락 부족 → 생성 불가

**결과:**
- 이미지 3개
- `{img:1-5}` → `{img:1-3}`으로 수정

### 시나리오 3: Drive 이미지 + 부족

**입력:**
```
content: "{img:1-5} 본문 내용..."
images: ["img1.png", "img2.png", "img3.png"]
auto_generate_images: False
```

**처리:**
1. 이미지 3개 사용 가능
2. 1~3번 마커: 이미지 삽입
3. 4~5번 마커: 범위 초과 → 마커 제거

**결과:**
- 이미지 3개만 삽입
- 초과 마커 제거됨

---

## 버전 히스토리

- v0.7: 헤드리스 모드 이미지 업로드 지원
- v0.65: 프롬프트 개선 및 EXE 빌드 지원
- v0.6: 예약발행 및 이미지 기능 추가
- v0.5: 초기 버전
