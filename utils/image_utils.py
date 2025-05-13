# utils/image_utils.py
import cv2
import numpy as np
import os
import logging
import time
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import pytesseract
from collections import defaultdict
import math

from config import MAX_IMAGE_SIZE, MAX_IMAGE_FILESIZE, OCR_LANG_MAPPING

logger = logging.getLogger(__name__)

# PaddleOCR 가용성 확인
PADDLE_AVAILABLE = False
try:
    import paddle
    import paddleocr
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
    logger.info("PaddleOCR을 이미지 처리에 사용할 수 있습니다.")
except ImportError:
    logger.warning("PaddleOCR을 사용할 수 없어 기본 Tesseract OCR을 사용합니다.")

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

def get_multilingual_font(font_size=24, bold=False):
    """다국어를 지원하는 폰트 가져오기"""
    # 프로젝트 루트 기준 폰트 경로 계산
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 폰트 경로 - 일반 및 볼드
    builtin_regular_font_path = os.path.join(project_root, 'fonts', 'NotoSansCJK-Regular.ttc')
    builtin_bold_font_path = os.path.join(project_root, 'fonts', 'NotoSansCJK-Bold.ttc')
    
    # 폰트 경로 목록 (우선순위 순)
    regular_font_paths = [
        # 프로젝트 내 포함된 폰트
        builtin_regular_font_path,
        # Windows 폰트
        "C:\\Windows\\Fonts\\malgun.ttf",
        "C:\\Windows\\Fonts\\meiryo.ttc",
        "C:\\Windows\\Fonts\\simsun.ttc",
        # Mac 폰트
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        # Linux 폰트
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"
    ]
    
    bold_font_paths = [
        # 프로젝트 내 포함된 볼드 폰트
        builtin_bold_font_path,
        # Windows 폰트
        "C:\\Windows\\Fonts\\malgunbd.ttf",
        "C:\\Windows\\Fonts\\meiryob.ttc",
        # Mac 폰트
        "/System/Library/Fonts/AppleSDGothicNeo-Bold.otf",
        # Linux 폰트
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"
    ]
    
    # 사용할 폰트 경로 목록 선택 (볼드 또는 일반)
    font_paths = bold_font_paths if bold else regular_font_paths
    
    # 사용 가능한 첫 번째 폰트 찾기
    for path in font_paths:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, font_size)
                logger.info(f"폰트 로드 성공: {path} (크기: {font_size}, 볼드: {bold})")
                return font
            except Exception as e:
                logger.debug(f"폰트 로드 실패: {path}, 오류: {e}")
                continue
    
    # 볼드 폰트를 찾지 못했는데 볼드를 요청한 경우, 일반 폰트 시도
    if bold:
        logger.warning("볼드 폰트를 찾지 못했습니다. 일반 폰트로 시도합니다.")
        return get_multilingual_font(font_size, False)
    
    # 폰트를 찾지 못한 경우 기본 폰트 사용
    logger.warning("다국어 폰트를 찾을 수 없음, 기본 폰트 사용")
    return ImageFont.load_default()

def estimate_text_properties(block, img_height):
    """OCR 텍스트 블록에서 속성 추정 (폰트 크기, 볼드 여부 등)"""
    height = block['height']
    width = block['width']
    text = block['text']
    confidence = block['conf']
    
    # 텍스트 길이
    text_length = len(text)
    if text_length == 0:
        return {'font_size': 20, 'is_bold': False}
    
    # 폰트 크기 추정 (텍스트 높이 기반)
    # 일반적으로 OCR 높이의 약 70%가 폰트 크기와 비슷
    estimated_font_size = int(height * 0.7)
    
    # 최소, 최대 폰트 크기 제한
    estimated_font_size = max(12, min(estimated_font_size, 72))
    
    # 이미지 크기에 따른 폰트 크기 조정
    if img_height > 1000:
        # 큰 이미지인 경우 폰트 크기를 더 크게
        estimated_font_size = int(estimated_font_size * 1.2)
    
    # 볼드 여부 추정 (단순한 휴리스틱)
    # 텍스트 폭/높이 비율이 일정 이상이면 볼드로 간주
    char_width_avg = width / max(1, text_length)
    width_to_height_ratio = char_width_avg / max(1, height)
    is_bold = width_to_height_ratio > 0.5  # 이 임계값은 조정 가능
    
    # 대문자나 특정 패턴이 있으면 볼드일 가능성 증가
    if text.isupper() or any(marker in text for marker in ['제목', '타이틀', 'TITLE', 'HEADER']):
        is_bold = True
    
    return {
        'font_size': estimated_font_size,
        'is_bold': is_bold
    }

def group_text_blocks(blocks, min_y_diff=10):
    """인접한 텍스트 블록을 그룹화하여 문단 형성"""
    # 블록이 없거나 하나뿐인 경우
    if not blocks or len(blocks) <= 1:
        return [blocks] if blocks else []

    # y좌표(top)에 따라 정렬
    sorted_blocks = sorted(blocks, key=lambda b: b['top'])
    
    groups = []
    current_group = [sorted_blocks[0]]
    
    # 인접한 블록 그룹화 (y좌표 기준)
    for i in range(1, len(sorted_blocks)):
        current_block = sorted_blocks[i]
        previous_block = sorted_blocks[i - 1]
        
        # y좌표 차이가 임계값 이하면 같은 그룹
        if abs(current_block['top'] - previous_block['top']) <= min_y_diff:
            current_group.append(current_block)
        else:
            # 새 그룹 시작
            groups.append(current_group)
            current_group = [current_block]
    
    # 마지막 그룹 추가
    if current_group:
        groups.append(current_group)
    
    # 각 그룹 내에서 x좌표(left)에 따라 정렬
    for i in range(len(groups)):
        groups[i] = sorted(groups[i], key=lambda b: b['left'])
    
    return groups

def wrap_text(text, font, max_width):
    """텍스트를 주어진 폭에 맞게 줄바꿈"""
    if not text:
        return []
        
    lines = []
    words = text.split()
    current_line = words[0]
    
    for word in words[1:]:
        # 현재 줄에 단어를 추가했을 때의 폭 계산
        test_line = current_line + " " + word
        test_width = font.getlength(test_line)
        
        if test_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines

def map_language_to_paddle(lang):
    """언어 코드를 PaddleOCR 언어 코드로 변환"""
    paddle_lang_map = {
        '한국어': 'korean',
        '일본어': 'japan',
        '영어': 'en',
        '중국어간체': 'ch',
        '중국어번체': 'chinese_cht',
        '태국어': 'thai',
        '스페인어': 'spanish',
        '프랑스어': 'french'
    }
    
    return paddle_lang_map.get(lang, 'en')  # 기본값은 영어

def match_original_and_translated(original_texts, translated_lines):
    """원본 텍스트와 번역된 텍스트를 매핑"""
    # 원본 텍스트 수와 번역된 텍스트 수가 같으면 1:1 매핑
    if len(original_texts) == len(translated_lines):
        return {original: translated for original, translated in zip(original_texts, translated_lines)}
    
    # 원본 텍스트 수보다 번역된 텍스트 수가 적으면, 나머지는 빈 문자열로 매핑
    if len(original_texts) > len(translated_lines):
        mapping = {}
        for i, original in enumerate(original_texts):
            if i < len(translated_lines):
                mapping[original] = translated_lines[i]
            else:
                mapping[original] = ""
        return mapping
    
    # 원본 텍스트 수보다 번역된 텍스트 수가 많으면, 마지막 원본 텍스트에 나머지 번역 텍스트 합치기
    mapping = {}
    for i, original in enumerate(original_texts):
        if i < len(original_texts) - 1:
            mapping[original] = translated_lines[i]
        else:
            # 마지막 원본 텍스트에 나머지 번역 텍스트 합치기
            mapping[original] = "\n".join(translated_lines[i:])
    
    return mapping

def extract_text_style(img, bbox, text):
    """텍스트 스타일 속성 추출 (폰트 크기, 회전, 색상)"""
    # 경계 상자에서 높이를 기반으로 폰트 크기 추정
    x1, y1 = bbox[0]
    x2, y2 = bbox[2]
    width = int(math.sqrt((x2 - x1)**2 + (y2 - y1)**2))
    height = int(math.sqrt((bbox[1][0] - bbox[0][0])**2 + (bbox[1][1] - bbox[0][1])**2))
    
    # 텍스트 길이와 높이를 기반으로 대략적인 폰트 크기 추정
    char_count = len(text)
    if char_count > 0:
        font_size = max(12, min(72, int(height * 0.7)))
    else:
        font_size = 16  # 기본 폰트 크기
    
    # 회전 계산 (bbox 포인트의 각도)
    dx = bbox[1][0] - bbox[0][0]
    dy = bbox[1][1] - bbox[0][1]
    rotation = math.degrees(math.atan2(dy, dx)) if dx != 0 else 0
    
    # 텍스트 영역에서 가장 많이 사용된 색상 추출
    roi = img[
        max(0, int(min(p[1] for p in bbox))):min(img.shape[0], int(max(p[1] for p in bbox) + 1)),
        max(0, int(min(p[0] for p in bbox))):min(img.shape[1], int(max(p[0] for p in bbox) + 1))
    ]
    
    # 색상 샘플링
    if roi.size > 0:
        # 이미지 가장자리 영역의 색상은 제외
        if roi.shape[0] > 4 and roi.shape[1] > 4:
            inner_roi = roi[2:-2, 2:-2]
            if inner_roi.size > 0:
                # 가장 많이 사용된 색상 찾기 (BGR)
                pixels = inner_roi.reshape(-1, 3)
                color_count = defaultdict(int)
                for pixel in pixels:
                    color_count[tuple(pixel)] += 1
                
                # 가장 많이 사용된 색상 선택
                dominant_color = max(color_count.items(), key=lambda x: x[1])[0]
                
                # 검은색이나 흰색이 지배적이면 텍스트 색상일 가능성이 높음
                black_like = sum(c < 50 for c in dominant_color) >= 2
                white_like = sum(c > 200 for c in dominant_color) >= 2
                
                if black_like:
                    color = (0, 0, 0)  # 검은색
                elif white_like:
                    color = (255, 255, 255)  # 흰색
                else:
                    color = dominant_color
            else:
                color = (0, 0, 0)  # 기본 검은색
        else:
            color = (0, 0, 0)  # 기본 검은색
    else:
        color = (0, 0, 0)  # 기본 검은색
    
    return font_size, rotation, color

def insert_text_with_style(img, text, bbox, font_size, rotation, color):
    """스타일을 유지하면서 번역된 텍스트 삽입"""
    # 텍스트 영역 중심점 계산
    center_x = sum(p[0] for p in bbox) / 4
    center_y = sum(p[1] for p in bbox) / 4
    
    # 텍스트 영역 크기 계산
    width = max(p[0] for p in bbox) - min(p[0] for p in bbox)
    height = max(p[1] for p in bbox) - min(p[1] for p in bbox)
    
    # 이미지를 PIL Image로 변환
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    
    # 폰트 로드
    font = get_multilingual_font(font_size, False)
    
    # 텍스트 줄 나누기
    lines = text.split('\n')
    
    # 회전 이미지 준비
    if abs(rotation) > 0.5:
        # 투명한 이미지 생성
        txt_img = Image.new('RGBA', (int(width * 1.5), int(height * 1.5)), (255, 255, 255, 0))
        txt_draw = ImageDraw.Draw(txt_img)
        
        # 텍스트 그리기
        text_width, text_height = 0, 0
        for i, line in enumerate(lines):
            w, h = txt_draw.textsize(line, font=font)
            text_width = max(text_width, w)
            text_height += h
        
        # 텍스트 중앙 정렬하여 그리기
        y_offset = (txt_img.height - text_height) // 2
        for line in lines:
            w, h = txt_draw.textsize(line, font=font)
            x_pos = (txt_img.width - w) // 2
            txt_draw.text((x_pos, y_offset), line, fill=color, font=font)
            y_offset += h
        
        # 회전
        txt_img = txt_img.rotate(-rotation, expand=True, resample=Image.BICUBIC)
        
        # 원본 이미지에 합성
        x_pos = int(center_x - txt_img.width // 2)
        y_pos = int(center_y - txt_img.height // 2)
        pil_img.paste(txt_img, (x_pos, y_pos), txt_img)
    else:
        # 회전이 없는 경우 직접 그리기
        total_height = sum(draw.textsize(line, font=font)[1] for line in lines)
        y_offset = center_y - total_height // 2
        
        for line in lines:
            w, h = draw.textsize(line, font=font)
            x_pos = center_x - w // 2
            draw.text((x_pos, y_offset), line, fill=color, font=font)
            y_offset += h
    
    # PIL 이미지를 다시 OpenCV 이미지로 변환
    result_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return result_img

def enhanced_overlay_text(image_path, translated_text, source_lang=None):
    """고급 텍스트 오버레이 (PaddleOCR + 인페인팅 + 스타일 보존)"""
    logger.info(f"고급 이미지 번역 시작: {image_path}")
    
    # PaddleOCR이 설치되지 않은 경우 기본 방식으로 전환
    if not PADDLE_AVAILABLE:
        logger.warning("PaddleOCR이 설치되지 않아 기본 방식으로 전환합니다.")
        return overlay_text_on_image(image_path, translated_text, source_lang)
    
    try:
        # 이미지 로드
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"이미지 로드 실패: {image_path}")
            return basic_overlay_text(image_path, translated_text)
        
        # 1. PaddleOCR로 텍스트 영역 감지
        ocr = PaddleOCR(use_angle_cls=True, lang=map_language_to_paddle(source_lang))
        result = ocr.ocr(image_path, cls=True)
        
        logger.debug(f"PaddleOCR 결과: {result}")
        
        # 텍스트 블록 없으면 기본 방식 사용
        if not result or len(result[0]) == 0:
            logger.warning("PaddleOCR: 텍스트 블록을 찾을 수 없습니다.")
            return basic_overlay_text(image_path, translated_text)
        
        # 2. 추출된 텍스트와 번역된 텍스트 매핑
        original_texts = []
        text_regions = []
        
        for line in result[0]:
            bbox = line[0]  # 텍스트 경계 상자
            text = line[1][0]  # 텍스트 내용
            confidence = line[1][1]  # 신뢰도
            
            logger.debug(f"감지된 텍스트: '{text}', 신뢰도: {confidence}, 위치: {bbox}")
            
            if confidence > 0.6 and len(text.strip()) > 1:
                # 숫자만 있는 텍스트는 제외
                if not is_numeric_text(text):
                    original_texts.append(text)
                    text_regions.append(bbox)
        
        # 감지된 텍스트가 없으면 기본 방식 사용
        if not original_texts:
            logger.warning("PaddleOCR: 유효한 텍스트가 감지되지 않았습니다.")
            return basic_overlay_text(image_path, translated_text)
        
        # 번역된 텍스트 분할 (원본 텍스트 블록 수에 맞게)
        translated_lines = translated_text.split('\n')
        text_mapping = match_original_and_translated(original_texts, translated_lines)
        
        # 결과 이미지 준비
        result_img = img.copy()
        
        # 3. 각 텍스트 영역 처리
        for i, bbox in enumerate(text_regions):
            if i >= len(original_texts):
                continue
            
            # 원본 텍스트
            original_text = original_texts[i]
            # 번역된 텍스트
            translated_text = text_mapping.get(original_text, "")
            
            if not translated_text:
                continue
            
            logger.debug(f"텍스트 번역: '{original_text}' -> '{translated_text}'")
            
            # 텍스트 영역 마스크 생성
            mask = np.zeros(img.shape[:2], dtype=np.uint8)
            points = np.array([[int(p[0]), int(p[1])] for p in bbox], dtype=np.int32)
            cv2.fillPoly(mask, [points], 255)
            
            # 4. 인페인팅으로 원본 텍스트 제거
            result_img = cv2.inpaint(result_img, mask, 3, cv2.INPAINT_TELEA)
            
            # 5. 텍스트 스타일 속성 추출 (색상, 크기, 각도)
            font_size, rotation, color = extract_text_style(img, bbox, original_text)
            logger.debug(f"추출된 스타일: 폰트 크기 {font_size}, 회전 {rotation}, 색상 {color}")
            
            # 6. 번역된 텍스트 삽입 (스타일 보존)
            result_img = insert_text_with_style(result_img, translated_text, bbox, 
                                             font_size, rotation, color)
        
        # 결과 저장
        timestamp = int(time.time() * 1000)
        output_path = f"enhanced_translated_{timestamp}_{os.path.basename(image_path)}"
        cv2.imwrite(output_path, result_img)
        logger.info(f"고급 번역 이미지 저장: {output_path}")
        
        return output_path
        
    except Exception as e:
        logger.exception(f"고급 이미지 번역 오류: {e}")
        return basic_overlay_text(image_path, translated_text)

def overlay_text_on_image(image_path, translated_text, source_lang=None):
    """이미지의 텍스트를 번역된 텍스트로 정확히 대체 (위치, 크기, 스타일 유지)"""
    try:
        # PaddleOCR이 설치되어 있으면 향상된 방식 사용
        if PADDLE_AVAILABLE:
            return enhanced_overlay_text(image_path, translated_text, source_lang)

        # OCR 언어 설정
        ocr_lang = 'eng'  # 기본값
        if source_lang in OCR_LANG_MAPPING:
            ocr_lang_list = OCR_LANG_MAPPING[source_lang]
            ocr_lang = '+'.join(ocr_lang_list)
        
        # 이미지 로드 (PIL 및 OpenCV)
        pil_img = Image.open(image_path)
        cv_img = cv2.imread(image_path)
        if cv_img is None:
            logger.error(f"이미지 로드 실패: {image_path}")
            return image_path
        
        img_height, img_width = cv_img.shape[:2]
        
        # 텍스트 추출 (세부 정보 포함)
        try:
            import pytesseract
            custom_config = r'--oem 3 --psm 11'
            ocr_data = pytesseract.image_to_data(
                cv_img, lang=ocr_lang, config=custom_config, output_type=pytesseract.Output.DICT
            )
        except Exception as e:
            logger.error(f"OCR 오류: {e}")
            return basic_overlay_text(image_path, translated_text)
        
        # 유효한 텍스트 블록 추출
        valid_blocks = []
        for i in range(len(ocr_data['text'])):
            # 빈 텍스트나 짧은 텍스트는 제외
            if not ocr_data['text'][i] or len(ocr_data['text'][i].strip()) < 2:
                continue
            
            # 숫자만 있는 텍스트는 제외
            if is_numeric_text(ocr_data['text'][i]):
                continue
            
            # 유효한 텍스트 블록 필터링 (신뢰도 기준)
            if int(ocr_data['conf'][i]) > 50:
                block = {
                    'text': ocr_data['text'][i],
                    'left': ocr_data['left'][i],
                    'top': ocr_data['top'][i],
                    'width': ocr_data['width'][i],
                    'height': ocr_data['height'][i],
                    'conf': ocr_data['conf'][i]
                }
                valid_blocks.append(block)
        
        # 유효한 블록이 없으면 기본 방식 사용
        if not valid_blocks:
            logger.warning("유효한 텍스트 블록을 찾을 수 없습니다. 기본 방식으로 전환합니다.")
            return basic_overlay_text(image_path, translated_text)
        
        # 텍스트 블록을 문단으로 그룹화
        text_groups = group_text_blocks(valid_blocks)
        
        # 번역된 텍스트를 줄 단위로 분할
        translated_lines = translated_text.split('\n')
        
        # 그룹과 번역된 텍스트 줄을 매핑
        # 그룹 수와 번역 줄 수가 다를 수 있으므로 조정 필요
        group_text_map = {}
        
        # 가장 간단한 매핑: 순서대로 할당
        for i, group in enumerate(text_groups):
            if i < len(translated_lines):
                group_text_map[i] = translated_lines[i]
            else:
                # 번역 줄이 부족한 경우 마지막 줄 재사용 또는 빈 텍스트 할당
                group_text_map[i] = translated_lines[-1] if translated_lines else ""
        
        # 번역된 텍스트 줄이 더 많으면 마지막 그룹에 나머지 텍스트 추가
        if text_groups and len(translated_lines) > len(text_groups):
            last_group_idx = len(text_groups) - 1
            group_text_map[last_group_idx] = "\n".join(translated_lines[last_group_idx:])
        
        # 그리기 객체 생성
        draw = ImageDraw.Draw(pil_img)
        
        # 각 그룹을 처리하여 원본 위치에 번역된 텍스트 표시
        for i, group in enumerate(text_groups):
            if i not in group_text_map:
                continue
                
            translated_text_for_group = group_text_map[i]
            
            # 그룹 영역 계산
            left = min(block['left'] for block in group)
            top = min(block['top'] for block in group)
            right = max(block['left'] + block['width'] for block in group)
            bottom = max(block['top'] + block['height'] for block in group)
            
            # 텍스트 속성 추정 (첫 번째 블록 기준)
            text_props = estimate_text_properties(group[0], img_height)
            font_size = text_props['font_size']
            is_bold = text_props['is_bold']
            
            # 적절한 폰트 로드
            font = get_multilingual_font(font_size, is_bold)
            
            # 텍스트 영역 지우기 (흰색 또는 배경색으로)
            # PIL에서 직사각형 채우기
            draw.rectangle([left, top, right, bottom], fill=(255, 255, 255))
            
            # 텍스트가 영역에 맞게 줄바꿈이 필요한지 계산
            max_width = right - left
            wrapped_text = wrap_text(translated_text_for_group, font, max_width)
            
            # 번역된 텍스트 렌더링
            y_offset = top
            for line in wrapped_text:
                # PIL로 텍스트 그리기 (검정색)
                draw.text((left, y_offset), line, font=font, fill=(0, 0, 0))
                # 다음 줄로 이동 (줄 간격은 폰트 크기의 1.2배 정도)
                y_offset += int(font_size * 1.2)
        
        # 결과 저장
        timestamp = int(time.time() * 1000)
        basename = os.path.basename(image_path)
        output_path = f"translated_{timestamp}_{basename}"
        pil_img.save(output_path)
        logger.info(f"번역된 이미지 저장: {output_path}")
        return output_path
    
    except Exception as e:
        logger.exception(f"이미지 텍스트 대체 오류: {e}")
        return basic_overlay_text(image_path, translated_text)

def basic_overlay_text(image_path, translated_text):
    """기본 텍스트 오버레이 방식 - 향상된 버전"""
    try:
        # PIL로 이미지 열기
        pil_img = Image.open(image_path)
        width, height = pil_img.size
        
        # 그리기 객체 생성
        draw = ImageDraw.Draw(pil_img)
        
        # 기본 폰트 크기 계산 (이미지 크기에 비례)
        base_font_size = max(16, min(36, int(height / 20)))
        
        # 폰트 가져오기
        font = get_multilingual_font(base_font_size)
        
        # 텍스트 줄 분할 (자동 줄바꿈)
        max_width = width - 40  # 여백 20px씩
        wrapped_lines = wrap_text(translated_text, font, max_width)
        
        # 텍스트 영역 높이 계산
        line_height = int(base_font_size * 1.5)
        text_height = len(wrapped_lines) * line_height + 40  # 위아래 여백 20px씩
        
        # 이미지 상단 약 1/3 영역에 반투명 흰색 배경 생성
        overlay_height = min(text_height, int(height / 3))
        overlay = Image.new('RGBA', (width, overlay_height), (255, 255, 255, 220))
        pil_img.paste(overlay, (0, 0), overlay)
        
        # 텍스트 렌더링
        y_offset = 20  # 상단 여백
        for line in wrapped_lines:
            # 텍스트 중앙 정렬
            text_width = font.getlength(line)
            x_pos = (width - text_width) / 2
            
            # 텍스트 그림자 효과 (옵션)
            draw.text((x_pos+1, y_offset+1), line, font=font, fill=(100, 100, 100))
            
            # 메인 텍스트
            draw.text((x_pos, y_offset), line, font=font, fill=(0, 0, 0))
            
            y_offset += line_height
        
        # 결과 저장
        timestamp = int(time.time() * 1000)
        basename = os.path.basename(image_path)
        output_path = f"basic_translated_{timestamp}_{basename}"
        pil_img.save(output_path)
        logger.info(f"기본 오버레이 이미지 저장: {output_path}")
        return output_path
    except Exception as e:
        logger.exception(f"기본 오버레이 오류: {e}")
        return image_path