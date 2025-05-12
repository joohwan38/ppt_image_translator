import os
import tempfile
import time
import logging
import traceback
import base64
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from utils.image_utils import resize_image_if_needed, encode_image_to_base64, overlay_text_on_image

logger = logging.getLogger(__name__)

class TranslationService:
    def __init__(self, ollama_service):
        self.ollama_service = ollama_service

    def is_numeric_text(self, text):
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
    
    def translate_ppt(self, ppt_path, source_lang, target_lang, vision_model, text_model, 
                    progress_callback=None, status_callback=None, debug_mode=False):
        """파워포인트 파일 번역 실행"""
        if debug_mode:
            original_level = logger.level
            logger.setLevel(logging.DEBUG)
            logger.info("디버그 모드 활성화됨")
        
        try:
            logger.info(f"번역 프로세스 시작: {ppt_path}")
            
            if status_callback:
                status_callback("번역 프로세스 시작")
            
            logger.info(f"사용할 모델: Vision={vision_model}, Text={text_model}")
            if status_callback:
                status_callback(f"번역 준비 중: {vision_model}, {text_model}")
            
            # 파워포인트 파일 열기
            ppt = Presentation(ppt_path)
            
            # 임시 폴더 생성
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.info(f"임시 폴더 생성: {temp_dir}")
                
                # 문서 분석
                from services.document_analyzer import DocumentAnalyzer
                analyzer = DocumentAnalyzer()
                result = analyzer.analyze_ppt(ppt_path)
                
                text_elements = result['text_elements']
                image_elements = result['image_elements']
                total_elements = result['total_elements']
                
                # 번역 작업 시작
                processed_items = 0
                
                # 1. 텍스트 요소 번역
                if status_callback:
                    status_callback("텍스트 요소 번역 중...")
                logger.info("텍스트 요소 번역 시작")
                
                self._translate_text_elements(
                    ppt, text_elements, source_lang, target_lang, text_model, 
                    progress_callback, processed_items, total_elements
                )
                processed_items += len(text_elements)
                
                # 2. 이미지 요소 번역
                if status_callback:
                    status_callback("이미지 요소 번역 중...")
                logger.info("이미지 요소 번역 시작")
                
                self._translate_image_elements(
                    ppt, image_elements, temp_dir, source_lang, target_lang, 
                    vision_model, text_model, progress_callback, processed_items, total_elements
                )
                
                # 번역된 파일 저장
                output_path = os.path.splitext(ppt_path)[0] + "_translated.pptx"
                logger.info(f"번역된 파일 저장: {output_path}")
                ppt.save(output_path)
                
                if status_callback:
                    status_callback(f"번역 완료! 파일 저장됨: {output_path}")
                
                logger.info(f"번역 완료")
                return output_path
            
        except Exception as e:
            logger.exception(f"번역 프로세스 오류: {str(e)}")
            if status_callback:
                status_callback(f"번역 오류: {str(e)}")
            raise
        finally:
            if debug_mode:
                logger.setLevel(original_level)
                logger.info("디버그 모드 비활성화됨")
    
    def _translate_text_elements(self, ppt, text_elements, source_lang, target_lang, text_model, 
                               progress_callback=None, processed_items=0, total_elements=0):
        """텍스트 요소 번역 처리"""
        for idx, text_element in enumerate(text_elements):
            slide_idx = text_element['slide_idx']
            slide = ppt.slides[slide_idx]
            
            try:
                if text_element['type'] == 'text_run':
                    logger.info(f"텍스트 번역 (슬라이드 {slide_idx+1}, 요소 {text_element['shape_idx']}): '{text_element['text'][:30]}...'")
                    
                    shape = slide.shapes[text_element['shape_idx']]
                    for paragraph in shape.text_frame.paragraphs:
                        for run in paragraph.runs:
                            if run.text.strip() == text_element['text']:
                                if self.is_numeric_text(run.text):
                                    logger.info(f"숫자 텍스트 감지됨, 번역 건너뜀: '{run.text}'")
                                    text_element['translated'] = True
                                else:
                                    translated_text = self.ollama_service.translate_text(
                                        run.text, source_lang, target_lang, text_model
                                    )
                                    run.text = translated_text
                                    text_element['translated'] = True
                                break
                
                elif text_element['type'] == 'table_cell':
                    logger.info(f"테이블 셀 번역 (슬라이드 {slide_idx+1}, 요소 {text_element['shape_idx']}): '{text_element['text'][:30]}...'")
                    
                    shape = slide.shapes[text_element['shape_idx']]
                    if hasattr(shape, "table"):
                        table = shape.table
                        cell = table.rows[text_element['row_idx']].cells[text_element['col_idx']]
                        
                        if cell.text.strip() == text_element['text']:
                            if self.is_numeric_text(cell.text):
                                logger.info(f"숫자 텍스트 감지됨, 번역 건너뜀: '{cell.text}'")
                                text_element['translated'] = True
                            else:
                                translated_text = self.ollama_service.translate_text(
                                    cell.text, source_lang, target_lang, text_model
                                )
                                
                                text_frame = cell.text_frame
                                while len(text_frame.paragraphs) > 1:
                                    tr_element = text_frame._txBody.remove(text_frame._txBody[1])
                                
                                text_frame.paragraphs[0].text = translated_text
                                text_element['translated'] = True
                
                elif text_element['type'] == 'paragraph':
                    logger.info(f"문단 번역 (슬라이드 {slide_idx+1}, 요소 {text_element['shape_idx']}): '{text_element['text'][:30]}...'")
                    
                    shape = slide.shapes[text_element['shape_idx']]
                    paragraph = shape.text_frame.paragraphs[text_element['para_idx']]
                    
                    if paragraph.text.strip() == text_element['text']:
                        if self.is_numeric_text(paragraph.text):
                            logger.info(f"숫자 텍스트 감지됨, 번역 건너뜀: '{paragraph.text}'")
                            text_element['translated'] = True
                        else:
                            translated_text = self.ollama_service.translate_text(
                                paragraph.text, source_lang, target_lang, text_model
                            )
                            
                            # 모든 run 삭제 후 새 텍스트로 대체
                            while len(paragraph.runs):
                                paragraph._p.remove(paragraph.runs[0]._r)
                            
                            paragraph.text = translated_text
                            text_element['translated'] = True
            
            except Exception as e:
                logger.error(f"텍스트 번역 오류 (요소 {idx+1}/{len(text_elements)}): {str(e)}")
                logger.error(traceback.format_exc())
            
            # 진행 상황 업데이트
            if progress_callback:
                current = processed_items + idx + 1
                progress_callback(current, total_elements)
    
    def _translate_image_elements(self, ppt, image_elements, temp_dir, source_lang, target_lang, 
                                vision_model, text_model, progress_callback=None, 
                                processed_items=0, total_elements=0):
        """이미지 요소 번역 처리"""
        for idx, image_element in enumerate(image_elements):
            slide_idx = image_element['slide_idx']
            slide = ppt.slides[slide_idx]
            
            try:
                logger.info(f"이미지 번역 (슬라이드 {slide_idx+1}, 요소 {image_element['shape_idx']})")
                
                shape = slide.shapes[image_element['shape_idx']]
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    # 이미지 추출 및 저장
                    image = shape.image
                    image_bytes = image.blob
                    
                    # 이미지 크기 확인 (너무 큰 이미지 건너뛰기)
                    if len(image_bytes) > 5*1024*1024:  # 5MB 제한
                        logger.warning(f"이미지 크기가 너무 큽니다 ({len(image_bytes)} 바이트). 건너뜁니다.")
                        continue
                    
                    temp_image_path = os.path.join(temp_dir, f"slide_{slide_idx}_image_{image_element['shape_idx']}.png")
                    with open(temp_image_path, "wb") as f:
                        f.write(image_bytes)
                    
                    logger.info(f"이미지 저장: {temp_image_path} ({len(image_bytes)} 바이트)")
                    
                    # 이미지 처리 과정
                    temp_image_path = resize_image_if_needed(temp_image_path)
                    image_base64 = encode_image_to_base64(temp_image_path)
                    
                    if image_base64:
                        # 텍스트 추출 및 번역
                        extracted_text = self.ollama_service.extract_text_from_image(image_base64, vision_model)
                        
                        if extracted_text and not (extracted_text.startswith("오류") or 
                                                extracted_text.startswith("API 오류") or 
                                                extracted_text == "응답 타임아웃" or
                                                extracted_text == "연결 타임아웃" or
                                                extracted_text == "이미지 크기 초과"):
                            translated_text = self.ollama_service.translate_text(
                                extracted_text, source_lang, target_lang, text_model
                            )
                            
                            if translated_text and translated_text != extracted_text:
                                # 번역된 텍스트로 이미지 오버레이
                                translated_image_path = overlay_text_on_image(temp_image_path, translated_text)
                                
                                # 번역된 이미지로 교체
                                if os.path.exists(translated_image_path) and translated_image_path != temp_image_path:
                                    left, top, width, height = shape.left, shape.top, shape.width, shape.height
                                    pic = slide.shapes.add_picture(translated_image_path, left, top, width, height)
                                    pic.left, pic.top, pic.width, pic.height = left, top, width, height
                                    
                                    image_element['translated'] = True
                                    logger.info("이미지 교체 완료")
                    
                    # 불필요한 임시 파일 정리
                    try:
                        if os.path.exists(temp_image_path):
                            os.remove(temp_image_path)
                    except:
                        pass
                    
                    # GC 힌트
                    import gc
                    gc.collect()
            
            except Exception as e:
                logger.error(f"이미지 번역 오류 (요소 {idx+1}/{len(image_elements)}): {str(e)}")
                logger.error(traceback.format_exc())
            
            # 진행 상황 업데이트
            if progress_callback:
                current = processed_items + idx + 1
                progress_callback(current, total_elements)