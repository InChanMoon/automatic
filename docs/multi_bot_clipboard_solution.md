# 다중 발행봇 클립보드 충돌 해결 방안

## 문제
- 현재 발행봇은 `pyperclip`/`win32clipboard` 사용
- 여러 발행봇 동시 실행 시 클립보드 충돌 발생

## 해결 방안

### 방안 1: Sandboxie Plus (권장)
- 각 발행봇을 별도 샌드박스에서 실행
- 클립보드 분리 지원 (2025년 추가, 유료)
- 기존 코드 수정 불필요

### 방안 2: 클립보드 없이 직접 입력 (테스트 완료)
- `keyboard.type()` → 텍스트 입력
- `file input` → 이미지 업로드
- 테스트 결과: 발행 성공 (2024-12-22)

## 테스트 코드
`test_js_injection.py` 참고

### 핵심 코드
```python
# 텍스트 입력 (클립보드 없이)
page.keyboard.type("텍스트 내용", delay=20)
page.keyboard.press("Enter")

# 이미지 업로드 (file input 방식)
photo_btn = frame.locator('button[data-name="image"]').first
photo_btn.click(force=True)
time.sleep(2)

file_input = frame.locator('input[type="file"]').first
file_input.set_input_files(os.path.abspath(image_path), timeout=5000)
```

## 발행봇 수정 시 변경 포인트
1. `_paste_text()` → `keyboard.type()` 로 변경
2. `_copy_image_to_clipboard()` + `_paste_image_from_clipboard()` → `file input` 방식으로 변경
3. `_input_content_with_images()` 전체 리팩토링

## 참고 링크
- Sandboxie Plus: https://sandboxie-plus.com/
- 클립보드 분리 이슈: https://github.com/sandboxie-plus/Sandboxie/issues/2385
