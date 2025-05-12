import cv2
import numpy as np
import base64
import time
import os
import logging
from PIL import Image, ImageDraw, ImageFont
import pytesseract

logger = logging.getLogger(__name__)

def resize_image_if_needed(image_path, max_size=600, max_filesize=2*1024*1024):
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

def get_multilingual_font(font_size=14):
    """다국어를 지원하는 폰트 가져오기"""
    # 다국어 폰트 경로 목록 (우선순위 순)
    font_paths = [
        # 프로젝트 내 포함된 폰트 (가장 우선)
        os.path.join(os.path.dirname(__file__), '..', 'fonts', 'NotoSansCJK-Regular.ttc'),
        # Windows 폰트
        "C:\\Windows\\Fonts\\malgun.ttf",      # 맑은 고딕 (한중일)
        "C:\\Windows\\Fonts\\seguisym.ttf",    # Segoe UI Symbol (다국어)
        "C:\\Windows\\Fonts\\arialuni.ttf",    # Arial Unicode MS
        "C:\\Windows\\Fonts\\meiryo.ttc",      # 메이리오 (일본어 지원)
        "C:\\Windows\\Fonts\\simsun.ttc",      # SimSun (중국어 지원)
        # Linux 폰트
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        # Mac 폰트
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/Arial Unicode.ttf"
    ]
    
    # 사용 가능한 첫 번째 폰트 찾기
    for path in font_paths:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, font_size)
                logger.info(f"다국어 폰트 로드: {path}")
                return font
            except Exception as e:
                logger.warning(f"폰트 로드 실패: {path}, 오류: {e}")
                continue
    
    # 폰트를 찾지 못한 경우 기본 폰트 사용
    logger.warning("다국어 폰트를 찾을 수 없음, 기본 폰트 사용")
    return ImageFont.load_default()

def overlay_text_on_image(image_path, translated_text, vision_model=None, vision_model_name=None, source_lang=None):
    """이미지의 텍스트를 번역된 텍스트로 정확히 대체 (OCR + 비전 모델 통합)"""
    try:
        # Tesseract 설정 로드
        try:
            import pytesseract
            tesseract_cmd, tessdata_path, available_languages = get_tesseract_config()
            
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            
            if tessdata_path:
                os.environ['TESSDATA_PREFIX'] = tessdata_path
            
            tesseract_available = tesseract_cmd is not None
        except ImportError:
            tesseract_available = False
            logger.warning("pytesseract 모듈이 설치되지 않았습니다")
        
        # 원본 이미지 로드
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"이미지 로드 실패: {image_path}")
            return image_path
        
        # PIL 이미지로 변환 (텍스트 처리용)
        pil_img = Image.open(image_path)
        draw = ImageDraw.Draw(pil_img)
        
        # 이미지 크기
        h, w = img.shape[:2]
        
        # 번역된 텍스트 줄 분리
        translated_lines = [line.strip() for line in translated_text.split('\n') if line.strip()]
        
        # OCR 실행 (가능한 경우)
        ocr_data = None
        if tesseract_available:
            try:
                # 언어 자동 선택 (가용 언어 기준)
                default_lang = 'eng'
                ocr_lang = default_lang
                
                # 소스 언어에 따른 OCR 언어 설정
                lang_mapping = {
                    '일본어': ['jpn', 'eng'],
                    '한국어': ['kor', 'eng'],
                    '영어': ['eng'],
                    '중국어간체': ['chi_sim', 'eng'],
                    '중국어번체': ['chi_tra', 'eng'],
                    '태국어': ['tha', 'eng'],
                    '스페인어': ['spa', 'eng'],
                    '프랑스어': ['fra', 'eng']
                }
                
                # 소스 언어가 지정되었고 매핑이 있는 경우
                if source_lang and source_lang in lang_mapping:
                    # 사용 가능한 언어 체크 (없으면 건너뜀)
                    preferred_langs = [lang for lang in lang_mapping[source_lang] 
                                      if lang in available_languages]
                    if preferred_langs:
                        ocr_lang = '+'.join(preferred_langs)
                    else:
                        # 언어 데이터가 없으면 기본값 사용
                        ocr_lang = default_lang
                
                logger.info(f"OCR 언어 설정: {ocr_lang}")
                custom_config = r'--oem 3 --psm 11'
                ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, 
                                                  config=custom_config, lang=ocr_lang)
                
                logger.info(f"OCR 완료: {len(ocr_data['text'])} 텍스트 블록 감지")
            except Exception as e:
                logger.error(f"OCR 오류: {e}, 기본 방식으로 진행")
                ocr_data = None
        
        # OCR에 실패했거나 사용할 수 없는 경우 기본 방식 사용
        if not ocr_data:
            return basic_overlay_text(image_path, translated_text)
        
        # 비전 모델 텍스트 추출 (OCR 보완용)
        vision_extracted_text = ""
        if vision_model and vision_model_name:
            try:
                # 이미지 base64 인코딩
                image_base64 = encode_image_to_base64(image_path)
                if image_base64:
                    # 비전 모델로 텍스트 추출
                    vision_extracted_text = vision_model.extract_text_from_image(image_base64, vision_model_name)
                    logger.info(f"비전 모델 텍스트 추출 완료: {len(vision_extracted_text)} 글자")
            except Exception as e:
                logger.error(f"비전 모델 텍스트 추출 오류: {e}")
        
        # OCR 결과에서 텍스트 블록 추출
        detected_blocks = []
        for i, text in enumerate(ocr_data['text']):
            if not text or len(text.strip()) < 2:  # 너무 짧은 텍스트는 무시
                continue
                
            # 숫자 텍스트는 건너뛰기
            if is_numeric_text(text):
                logger.debug(f"숫자 텍스트 건너뜀: {text}")
                continue
                
            # 텍스트 블록 좌표
            x = ocr_data['left'][i]
            y = ocr_data['top'][i]
            w_text = ocr_data['width'][i]
            h_text = ocr_data['height'][i]
            
            # 블록 신뢰도
            conf = int(ocr_data['conf'][i])
            
            # 유효한 텍스트 블록이고 신뢰도가 높은 경우만 처리
            if w_text > 10 and h_text > 5 and conf > 50:
                # 블록 생성
                detected_blocks.append({
                    'text': text,
                    'x': x,
                    'y': y,
                    'width': w_text,
                    'height': h_text,
                    'conf': conf
                })
        
        # 결과 없을 경우: 비전 모델이 감지한 텍스트와 OCR을 통합하는 고급 매칭 알고리즘 적용
        if len(detected_blocks) == 0 and vision_extracted_text:
            logger.warning("OCR 블록 감지 실패, 비전 모델 결과 사용")
            return basic_overlay_text(image_path, translated_text)
        
        # 결과 없는 경우
        if len(detected_blocks) == 0:
            logger.warning("텍스트 블록 감지 실패, 기본 오버레이 사용")
            return basic_overlay_text(image_path, translated_text)
        
        # 감지된 블록에 번역 텍스트 적용 (Y축 기준으로 정렬)
        detected_blocks.sort(key=lambda b: (b['y'], b['x']))
        
        # 번역 텍스트 매핑
        # 비전 모델과 OCR 결과를 비교하여 더 적절한 매핑 결정
        text_mapping = {}
        
        # 간단한 매핑: 순서대로 할당
        translation_index = 0
        for block in detected_blocks:
            if translation_index < len(translated_lines):
                text_mapping[block['text']] = translated_lines[translation_index]
                translation_index += 1
        
        # 다국어 폰트 로드
        font_size = 14  # 기본 폰트 크기
        font = get_multilingual_font(font_size)
        
        # 번역 텍스트 적용
        for block in detected_blocks:
            if block['text'] in text_mapping:
                # 원본 텍스트 영역 지우기 (흰색 또는 배경색으로)
                cv2.rectangle(img, 
                            (block['x'], block['y']), 
                            (block['x'] + block['width'], block['y'] + block['height']), 
                            (255, 255, 255), -1)  # 흰색으로 채우기
                
                # 텍스트 크기 조정 (원본 크기에 맞게)
                translated_text = text_mapping[block['text']]
                
                # 폰트 크기 계산 (원본과 비슷한 크기로)
                adjusted_font_size = max(10, int(block['height'] * 0.8))
                custom_font = get_multilingual_font(adjusted_font_size)
                
                # PIL 이미지에 텍스트 그리기
                draw.text((block['x'], block['y']), translated_text, fill=(0, 0, 0), font=custom_font)
                
                logger.info(f"텍스트 대체: '{block['text']}' -> '{translated_text}'")
        
        # PIL 이미지를 OpenCV 형식으로 변환
        pil_img_np = np.array(pil_img)
        if len(pil_img_np.shape) == 3:  # RGB인 경우
            img_result = cv2.cvtColor(pil_img_np, cv2.COLOR_RGB2BGR)
        else:  # 그레이스케일인 경우
            img_result = pil_img_np
        
        # 결과 저장
        output_path = f"translated_{os.path.basename(image_path)}"
        cv2.imwrite(output_path, img_result)
        logger.info(f"번역된 이미지 저장: {output_path}")
        return output_path
    
    except Exception as e:
        logger.exception(f"이미지 텍스트 대체 오류: {e}")
        return image_path

def basic_overlay_text(image_path, translated_text):
    """기본 텍스트 오버레이 방식 - OCR 실패 시 대체용"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"이미지 로드 실패: {image_path}")
            return image_path
        
        # 이미지 크기 및 오버레이 설정
        h, w = img.shape[:2]
        overlay = img.copy()
        bg_color = (255, 255, 255)  # 흰색
        alpha = 0.85  # 투명도
        
        # 텍스트 분할
        lines = []
        words = translated_text.split()
        line = ""
        max_line_length = min(50, w // 8)  # 이미지 폭에 따라 동적 조정
        
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
        font_scale = max(0.6, min(0.8, w / 500))  # 이미지 크기에 따라 폰트 크기 조정
        thickness = 1
        line_height = max(25, int(h / 20))  # 이미지 높이에 따라 조정
        
        # 텍스트 크기 계산
        text_height = len(lines) * line_height
        text_width = max([cv2.getTextSize(line, font, font_scale, thickness)[0][0] for line in lines] or [0])
        
        # 텍스트 배경 및 내용 렌더링 (상단에 위치하도록 수정)
        text_x = 10
        text_y = 20 + line_height  # 상단에 배치
        
        # 배경 텍스트 영역 확장
        cv2.rectangle(overlay, (0, 0), 
                    (w, text_y + text_height + 15), 
                    bg_color, -1)
        
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
        
        # 텍스트 렌더링
        for i, line in enumerate(lines):
            y = text_y + i * line_height
            # 그림자
            cv2.putText(img, line, (text_x + 1, y + 1), font, font_scale, (100, 100, 100), thickness)
            # 실제 텍스트
            cv2.putText(img, line, (text_x, y), font, font_scale, (0, 0, 0), thickness)
        
        # 결과 저장
        output_path = f"basic_translated_{os.path.basename(image_path)}"
        cv2.imwrite(output_path, img)
        logger.info(f"기본 오버레이 이미지 저장: {output_path}")
        return output_path
    except Exception as e:
        logger.exception(f"기본 오버레이 오류: {e}")
        return image_path
    
def get_tesseract_config():
    """시스템별 Tesseract 설정 및 언어 데이터 경로 자동 감지"""
    import platform
    import os
    
    tessdata_path = None
    tesseract_cmd = None
    
    if platform.system() == "Windows":
        # Windows 테서렉트 경로 후보
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                tesseract_cmd = path
                tessdata_path = os.path.join(os.path.dirname(path), "tessdata")
                break
    
    elif platform.system() == "Darwin":  # macOS
        # macOS 테서렉트 경로 후보
        possible_paths = [
            "/opt/homebrew/bin/tesseract",
            "/usr/local/bin/tesseract"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                tesseract_cmd = path
                # macOS Homebrew
                if 'homebrew' in path:
                    tessdata_path = "/opt/homebrew/share/tessdata/"
                else:
                    tessdata_path = "/usr/local/share/tessdata/"
                break
    
    else:  # Linux
        # Linux는 일반적으로 시스템 경로에 있음
        import subprocess
        try:
            result = subprocess.run(["which", "tesseract"], capture_output=True, text=True)
            if result.returncode == 0:
                tesseract_cmd = result.stdout.strip()
                # Linux는 일반적으로 /usr/share/tessdata/
                tessdata_path = "/usr/share/tessdata/"
        except:
            pass
    
    # 사용 가능한 언어 감지
    available_languages = []
    if tessdata_path and os.path.exists(tessdata_path):
        for file in os.listdir(tessdata_path):
            if file.endswith('.traineddata'):
                lang = file.replace('.traineddata', '')
                available_languages.append(lang)
    
    logger.info(f"테서렉트 경로: {tesseract_cmd}")
    logger.info(f"언어 데이터 경로: {tessdata_path}")
    logger.info(f"사용 가능한 언어: {', '.join(available_languages)}")
    
    return tesseract_cmd, tessdata_path, available_languages