"""
테스트용 이미지 생성 스크립트

간단한 테스트 이미지를 생성합니다.
"""

from PIL import Image, ImageDraw, ImageFont

def create_test_image():
    """테스트용 이미지 생성"""

    # 800x600 흰색 배경 이미지
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)

    # 테두리
    draw.rectangle([(10, 10), (790, 590)], outline='blue', width=5)

    # 텍스트 추가
    try:
        # 시스템 폰트 사용
        font = ImageFont.truetype("arial.ttf", 48)
    except:
        # 기본 폰트
        font = ImageFont.load_default()

    # 중앙에 텍스트
    text = "Test Image\nfor Naver Blog"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (800 - text_width) // 2
    y = (600 - text_height) // 2

    draw.text((x, y), text, fill='black', font=font)

    # 저장
    img.save('test/test_image.jpg', 'JPEG', quality=95)
    print("✅ 테스트 이미지 생성 완료: test/test_image.jpg")
    print("   크기: 800x600")


if __name__ == "__main__":
    create_test_image()
