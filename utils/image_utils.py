import cv2
import numpy as np
import base64
import os
from PIL import Image
import logging

logger = logging.getLogger(__name__)

def resize_image_if_needed(image_path, max_size=1024, max_filesize=10*1024*1024):
    """큰 이미지 리사이징"""
    try:
        # 이미지 크기 확인
        img = Image.open(image_path)
        img_size = os.path.getsize(image_path)
        logger.info(f"원본 이미지 크기: {img.width}x{img.height}, {img_size} 바이트")
        
        # 큰 이미지 리사이징 (10MB 초과)
        if img_size > max_filesize:
            logger.info("큰 이미지 리사이징")
            if img.width > max_size or img.height > max_size:
                # 비율 유지하면서 리사이징
                ratio = min(max_size / img.width, max_size / img.height)
                new_width = int(img.width * ratio)
                new_height = int(img.height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 리사이징된 이미지 저장
                resized_path = f"{os.path.splitext(image_path)[0]}_resized.png"
                img.save(resized_path)
                logger.info(f"이미지 리사이징 완료: {new_width}x{new_height}")
                return resized_path
                
        return image_path
    except Exception as e:
        logger.exception(f"이미지 리사이징 오류: {e}")
        return image_path

def encode_image_to_base64(image_path):
    """이미지를 base64로 인코딩"""
    try:
        with open(image_path, "rb") as img_file:
            img_data = img_file.read()
            logger.info(f"이미지 크기: {len(img_data)} 바이트")
            return base64.b64encode(img_data).decode('utf-8')
    except Exception as e:
        logger.exception(f"이미지 인코딩 오류: {e}")
        return None

def overlay_text_on_image(image_path, translated_text):
    """이미지에 번역된 텍스트 오버레이"""
    try:
        # 원본 이미지 로드
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"이미지 로드 실패: {image_path}")
            return image_path
        
        # 결과를 이미지에 삽입 (오버레이 텍스트 방식)
        overlay = img.copy()
        h, w = img.shape[:2]
        
        # 배경색 설정 (흰색 반투명)
        bg_color = (255, 255, 255)
        alpha = 0.7  # 투명도
        
        # 텍스트 분할 (여러 줄로)
        lines = []
        words = translated_text.split()
        line = ""
        max_line_length = 50  # 한 줄에 최대 50자
        
        for word in words:
            test_line = line + " " + word if line else word
            if len(test_line) <= max_line_length:
                line = test_line
            else:
                lines.append(line)
                line = word
        
        if line:
            lines.append(line)
        
        # 텍스트 크기 계산
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        line_height = 30
        
        text_height = len(lines) * line_height
        text_width = 0
        
        for line in lines:
            (line_width, _), _ = cv2.getTextSize(line, font, font_scale, thickness)
            text_width = max(text_width, line_width)
        
        # 텍스트 위치 설정 (이미지 하단에 배치)
        text_x = 10
        text_y = h - text_height - 10
        
        # 텍스트 배경 생성
        cv2.rectangle(overlay, (text_x - 5, text_y - 15), 
                     (text_x + text_width + 5, text_y + text_height + 5), 
                     bg_color, -1)
        
        # 투명도 적용
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
        
        # 텍스트 추가
        for i, line in enumerate(lines):
            y = text_y + i * line_height
            cv2.putText(img, line, (text_x, y), font, font_scale, (0, 0, 0), thickness)
        
        # 결과 이미지 저장
        output_path = f"translated_{os.path.basename(image_path)}"
        cv2.imwrite(output_path, img)
        logger.info(f"번역된 이미지 저장: {output_path}")
        
        return output_path
    except Exception as e:
        logger.exception(f"이미지 오버레이 오류: {e}")
        return image_path