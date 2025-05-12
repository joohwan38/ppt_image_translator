import os
import logging
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

logger = logging.getLogger(__name__)

class DocumentAnalyzer:
    def __init__(self):
        pass
    
    def analyze_ppt(self, file_path):
        """PPT 파일 분석"""
        logger.info(f"문서 분석 시작: {file_path}")
        
        try:
            # 분석 작업 시작
            file_name = os.path.basename(file_path)
            ppt = Presentation(file_path)
            slide_count = len(ppt.slides)
            
            # 요소 초기화
            text_elements = []
            image_elements = []
            
            total_text_count = 0
            total_image_count = 0
            total_table_cells = 0
            
            # 각 슬라이드 분석
            for slide_idx, slide in enumerate(ppt.slides):
                logger.debug(f"슬라이드 {slide_idx+1} 분석 중")
                
                # 텍스트 요소 분석
                for shape_idx, shape in enumerate(slide.shapes):
                    try:
                        # 텍스트 프레임 처리
                        if hasattr(shape, "text_frame") and shape.text.strip():
                            for paragraph in shape.text_frame.paragraphs:
                                for run in paragraph.runs:
                                    if run.text.strip():
                                        text_elements.append({
                                            'slide_idx': slide_idx,
                                            'shape_idx': shape_idx,
                                            'type': 'text_run',
                                            'text': run.text,
                                            'translated': False
                                        })
                                        total_text_count += 1
                        
                        # 테이블 처리
                        if hasattr(shape, "table"):
                            table = shape.table
                            for row_idx, row in enumerate(table.rows):
                                for col_idx, cell in enumerate(row.cells):
                                    if cell.text.strip():
                                        text_elements.append({
                                            'slide_idx': slide_idx,
                                            'shape_idx': shape_idx,
                                            'type': 'table_cell',
                                            'row_idx': row_idx,
                                            'col_idx': col_idx,
                                            'text': cell.text,
                                            'translated': False
                                        })
                                        total_text_count += 1
                                        total_table_cells += 1
                        
                        # 이미지 처리
                        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                            image = shape.image
                            image_bytes = image.blob
                            image_size = len(image_bytes)
                            
                            image_elements.append({
                                'slide_idx': slide_idx,
                                'shape_idx': shape_idx,
                                'type': 'image',
                                'size': image_size,
                                'translated': False
                            })
                            total_image_count += 1
                            
                    except Exception as e:
                        logger.error(f"요소 분석 오류 (슬라이드 {slide_idx+1}, 요소 {shape_idx}): {str(e)}")
            
            # 총 요소 수 계산
            total_elements = total_text_count + total_image_count
            
            # 결과 저장
            result = {
                'file_name': file_name,
                'slide_count': slide_count,
                'text_elements': text_elements,
                'image_elements': image_elements,
                'total_text_count': total_text_count,
                'total_image_count': total_image_count,
                'total_table_cells': total_table_cells,
                'total_elements': total_elements
            }
            
            logger.info(f"문서 분석 완료: 슬라이드 {slide_count}개, 텍스트 요소 {total_text_count}개, 이미지 {total_image_count}개")
            return result
            
        except Exception as e:
            logger.exception(f"문서 분석 오류: {str(e)}")
            raise