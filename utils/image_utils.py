# utils/image_utils.py
import cv2
import numpy as np
import os
import logging
from PIL import Image, ImageDraw, ImageFont

from config import MAX_IMAGE_SIZE, MAX_IMAGE_FILESIZE, OCR_LANG_MAPPING

logger = logging.getLogger(__name__)

def resize_image_if_needed(image_path):
    """이미지 크기가 임계값을 초과하는 경우 리사이징"""
    try:
        img = Image.open(image_path)
        img_size = os.path.getsize(image_path)
        logger.info(f"원본 이미지 크기: {img.width}x{img.height}, {img_size} 바이트")
        
        if img_size > MAX_IMAGE_FILESIZE or img.width > MAX_IMAGE_SIZE or img.height > MAX_IMAGE_SIZE:
            logger.info("이미지 리사이징 시작")
            ratio = min(MAX_IMAGE_SIZE / img.width, MAX_IMAGE_SIZE / img.height)
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            resized_path = f"{os.path.splitext(image_path)[0]}_resized.png"
            img.save(resized_path, optimize=True, quality=85)
            logger.info(f"이미지 리사이징 완료: {new_width}x{new_height}")
            
            # 메모리에서 이미지 해제
            img.close()
            return resized_path
        
        # 메모리에서 이미지 해제
        img.close()
        return image_path
    except Exception as e:
        logger.exception(f"이미지 리사이징 오류: {e}")
        return image_path

def is_numeric_text(text):
    """숫자와 관련된 텍스트 감지"""
    text = text.strip()
    
    if not text:
        return False
    
    # 순수 숫자 확인
    numeric_only = text.replace(',', '').replace('.', '')
    if numeric_only.isdigit():
        return True
    
    # 퍼센트 표시 감지
    if text.endswith('%'):
        text_without_percent = text[:-1].strip()
        try:
            float(text_without_percent.replace(',', ''))
            return True
        except ValueError:
            pass
    
    # 소수점 확인
    try:
        float(text.replace(',', ''))
        return True
    except ValueError:
        return False

def get_multilingual_font(font_size=24):
    """다국어를 지원하는 폰트 가져오기"""
    # 프로젝트 루트 기준 폰트 경로 계산
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    builtin_font_path = os.path.join(project_root, 'fonts', 'NotoSansCJK-Regular.ttc')
    
    # 폰트 경로 목록 (우선순위 순)
    font_paths = [
        # 프로젝트 내 포함된 폰트를 최우선으로 사용
        builtin_font_path,
        
        # 시스템 폰트는 백업으로만 사용
        # Windows 폰트
        "C:\\Windows\\Fonts\\malgun.ttf",      # 맑은 고딕 (한중일)
        "C:\\Windows\\Fonts\\seguisym.ttf",    # Segoe UI Symbol (다국어)
        "C:\\Windows\\Fonts\\arialuni.ttf",    # Arial Unicode MS
        # Mac 폰트
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        # Linux 폰트
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    
    # 내장 폰트가 존재하는지 먼저 확인
    if os.path.exists(builtin_font_path):
        try:
            font = ImageFont.truetype(builtin_font_path, font_size)
            logger.info(f"내장 다국어 폰트 로드: {builtin_font_path}")
            return font
        except Exception as e:
            logger.warning(f"내장 폰트 로드 실패: {e}, 시스템 폰트 시도")
    
    # 내장 폰트 로드 실패 시 시스템 폰트 시도
    for path in font_paths:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, font_size)
                logger.info(f"시스템 다국어 폰트 로드: {path}")
                return font
            except Exception as e:
                logger.debug(f"폰트 로드 실패: {path}, 오류: {e}")
                continue
    
    # 폰트를 찾지 못한 경우 기본 폰트 사용
    logger.warning("다국어 폰트를 찾을 수 없음, 기본 폰트 사용")
    return ImageFont.load_default()

def overlay_text_on_image(image_path, translated_text, source_lang=None):
    """이미지의 텍스트를 번역된 텍스트로 정확히 대체 (PIL 사용)"""
    try:
        # OCR 언어 설정
        ocr_lang = 'eng'  # 기본값
        if source_lang in OCR_LANG_MAPPING:
            ocr_lang_list = OCR_LANG_MAPPING[source_lang]
            ocr_lang = '+'.join(ocr_lang_list)
        
        # 이미지 로드 (PIL 사용)
        pil_img = Image.open(image_path)
        
        # OCR 수행 (텍스트 블록 감지) - 이 부분은 그대로 pytesseract 사용
        try:
            import pytesseract
            boxes = pytesseract.image_to_boxes(np.array(pil_img), lang=ocr_lang, config=r'--oem 3 --psm 11')
        except Exception as e:
            logger.error(f"OCR 오류: {e}")
            boxes = None
        
        # 결과 없는 경우 다른 방식 시도
        if not boxes or len(boxes.strip()) == 0:
            return basic_overlay_text(image_path, translated_text)
        
        # 이미지 크기
        width, height = pil_img.size
        
        # PIL로 새 이미지 준비 (그림 그리기용)
        draw = ImageDraw.Draw(pil_img)
        
        # 폰트 로드 - 더 큰 글자 크기 사용(24pt)
        font = get_multilingual_font(24)
        
        # 텍스트 분할
        lines = translated_text.split('\n')
        
        # 텍스트 영역 지우기 (상단 부분에 흰색 배경)
        text_height = len(lines) * 30 + 20  # 각 줄 30픽셀, 위아래 여백 20픽셀
        overlay_height = min(int(height * 0.3), text_height)  # 이미지 높이의 최대 30%까지 사용
        
        # 반투명 흰색 배경 그리기 (완전 흰색 대신 약간 투명하게)
        overlay = Image.new('RGBA', (width, overlay_height), (255, 255, 255, 220))
        pil_img.paste(overlay, (0, 0), overlay)
        
        # 텍스트 렌더링
        y_offset = 10  # 상단 여백
        for line in lines:
            # 각 줄의 너비 계산
            text_width = font.getlength(line)
            # 텍스트 중앙 정렬
            x_pos = (width - text_width) / 2
            # 텍스트 그리기 (검정색)
            draw.text((x_pos, y_offset), line, font=font, fill=(0, 0, 0))
            y_offset += 30  # 다음 줄로 이동
        
        # 결과 저장
        output_path = f"translated_{os.path.basename(image_path)}"
        pil_img.save(output_path)
        logger.info(f"번역된 이미지 저장: {output_path}")
        return output_path
    
    except Exception as e:
        logger.exception(f"이미지 텍스트 대체 오류: {e}")
        return basic_overlay_text(image_path, translated_text)

def basic_overlay_text(image_path, translated_text):
    """기본 텍스트 오버레이 방식 - PIL 사용"""
    try:
        # PIL로 이미지 열기
        pil_img = Image.open(image_path)
        width, height = pil_img.size
        
        # 그리기 객체 생성
        draw = ImageDraw.Draw(pil_img)
        
        # 폰트 가져오기 (더 큰 글자 크기 사용)
        font = get_multilingual_font(24)
        
        # 텍스트 줄 분할
        lines = []
        words = translated_text.split()
        line = ""
        max_line_length = 50  # 최대 50자 (대략적인 수치)
        
        for word in words:
            test_line = line + " " + word if line else word
            if len(test_line) <= max_line_length:
                line = test_line
            else:
                lines.append(line)
                line = word
        
        if line:
            lines.append(line)
        
        # 텍스트 배경 영역 계산
        line_height = 30
        text_height = len(lines) * line_height + 20  # 위아래 여백 20픽셀
        padding = 10
        
        # 반투명 흰색 배경 생성
        overlay = Image.new('RGBA', (width, text_height), (255, 255, 255, 220))
        pil_img.paste(overlay, (0, 0), overlay)
        
        # 텍스트 렌더링
        y_offset = padding
        for line in lines:
            # 각 줄의 너비 계산
            text_width = font.getlength(line)
            # 텍스트 중앙 정렬
            x_pos = (width - text_width) / 2
            # 텍스트 그리기 (검정색)
            draw.text((x_pos, y_offset), line, font=font, fill=(0, 0, 0))
            y_offset += line_height
        
        # 결과 저장
        output_path = f"basic_translated_{os.path.basename(image_path)}"
        pil_img.save(output_path)
        logger.info(f"기본 오버레이 이미지 저장: {output_path}")
        return output_path
    except Exception as e:
        logger.exception(f"기본 오버레이 오류: {e}")
        return image_path