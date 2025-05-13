# main.py에 추가할 코드 (시작 부분)
import logging
import sys

# 로깅 기본 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PaddleOCR 의존성 체크
try:
    import paddle
    import paddleocr
    from paddleocr import PaddleOCR
    logger.info(f"PaddleOCR 확인 성공: paddle v{paddle.__version__}, paddleocr v{paddleocr.__version__}")
except ImportError as e:
    logger.error(f"PaddleOCR 패키지가 설치되지 않았습니다: {e}")
    print("\n========================================================================")
    print("오류: 필수 패키지 PaddleOCR이 설치되지 않았습니다.")
    print("다음 명령어로 필요한 패키지를 설치하세요:")
    print("    pip install paddlepaddle -U")
    print("    pip install paddleocr -U")
    print("설치 후 프로그램을 다시 실행하세요.")
    print("========================================================================\n")
    sys.exit(1)

# 기존 main.py 코드 계속...