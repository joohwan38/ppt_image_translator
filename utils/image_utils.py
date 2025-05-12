import cv2
import numpy as np
import base64
import time
import os
from PIL import Image
import logging

logger = logging.getLogger(__name__)

def resize_image_if_needed(image_path, max_size=400, max_filesize=1*1024*1024):  # 400px, 1MB로 제한
    """이미지 크기가 임계값을 초과하는 경우 리사이징"""
    try:
        img = Image.open(image_path)
        img_size = os.path.getsize(image_path)
        logger.info(f"원본 이미지 크기: {img.width}x{img.height}, {img_size} 바이트")
        
        if img_size > max_filesize or img.width > max_size or img.height > max_size:
            logger.info("이미지 리사이징 시작")
            ratio = min(max_size / img.width, max_size / img.height)
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            resized_path = f"{os.path.splitext(image_path)[0]}_resized.png"
            img.save(resized_path, optimize=True, quality=75)  # 품질 낮춤
            logger.info(f"이미지 리사이징 완료: {new_width}x{new_height}")
            
            # 메모리에서 이미지 제거
            img.close()
            return resized_path
        
        # 메모리에서 이미지 제거
        img.close()
        return image_path
    except Exception as e:
        logger.exception(f"이미지 리사이징 오류: {e}")
        return image_path

def encode_image_to_base64(image_path):
    """이미지를 base64로 인코딩"""
    try:
        with open(image_path, "rb") as img_file:
            img_data = img_file.read()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
        
        logger.info(f"인코딩된 이미지 크기: {len(img_base64)} 문자")
        return img_base64
    except Exception as e:
        logger.exception(f"이미지 인코딩 오류: {e}")
        return None

def overlay_text_on_image(image_path, translated_text):
    """이미지에 번역된 텍스트 오버레이"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"이미지 로드 실패: {image_path}")
            return image_path
        
        # 이미지 크기 및 오버레이 설정
        h, w = img.shape[:2]
        overlay = img.copy()
        bg_color = (255, 255, 255)  # 흰색
        alpha = 0.7  # 투명도
        
        # 텍스트 분할
        lines = []
        words = translated_text.split()
        line = ""
        max_line_length = 50
        
        for word in words:
            test_line = line + " " + word if line else word
            if len(test_line) <= max_line_length:
                line = test_line
            else:
                lines.append(line)
                line = word
        
        if line:
            lines.append(line)
        
        # 텍스트 렌더링 설정
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        line_height = 30
        
        # 텍스트 크기 계산
        text_height = len(lines) * line_height
        text_width = max([cv2.getTextSize(line, font, font_scale, thickness)[0][0] for line in lines] or [0])
        
        # 텍스트 배경 및 내용 렌더링
        text_x = 10
        text_y = h - text_height - 10
        
        cv2.rectangle(overlay, (text_x - 5, text_y - 15), 
                    (text_x + text_width + 5, text_y + text_height + 5), 
                    bg_color, -1)
        
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
        
        for i, line in enumerate(lines):
            y = text_y + i * line_height
            cv2.putText(img, line, (text_x, y), font, font_scale, (0, 0, 0), thickness)
        
        # 결과 저장
        output_path = f"translated_{os.path.basename(image_path)}"
        cv2.imwrite(output_path, img)
        logger.info(f"번역된 이미지 저장: {output_path}")
        return output_path
    except Exception as e:
        logger.exception(f"이미지 오버레이 오류: {e}")
        return image_path

# process_image_for_vision 함수는 encode_image_to_base64와 기능이 유사하여 제거