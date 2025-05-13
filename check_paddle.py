# check_paddle.py
try:
    import paddle
    import paddleocr
    from paddleocr import PaddleOCR
    
    print(f"PaddlePaddle 버전: {paddle.__version__}")
    print(f"PaddleOCR 버전: {paddleocr.__version__}")
    
    # 간단한 초기화 테스트
    ocr = PaddleOCR(use_angle_cls=True, lang='en')
    print("PaddleOCR 초기화 성공!")
    
except ImportError as e:
    print(f"패키지 불러오기 실패: {e}")
except Exception as e:
    print(f"오류 발생: {e}")