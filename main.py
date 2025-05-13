# main.py
import argparse
import tkinter as tk
import logging
import sys
from ui.app import PowerPointTranslatorApp
from utils.logging_utils import setup_logging

# PaddleOCR 의존성 체크
try:
    import paddle
    import paddleocr
    from paddleocr import PaddleOCR
    logging.info(f"PaddleOCR 확인 성공: paddle v{paddle.__version__}, paddleocr v{paddleocr.__version__}")
except ImportError as e:
    print("\n========================================================================")
    print("오류: 필수 패키지 PaddleOCR이 설치되지 않았습니다.")
    print("다음 명령어로 필요한 패키지를 설치하세요:")
    print("    pip install paddlepaddle -U")
    print("    pip install paddleocr -U")
    print("설치 후 프로그램을 다시 실행하세요.")
    print("========================================================================\n")
    sys.exit(1)

def main():
    # 명령행 인자 파싱
    parser = argparse.ArgumentParser(description="PowerPoint 번역 도구")
    parser.add_argument("--debug", action="store_true", help="디버그 모드 활성화")
    args = parser.parse_args()
    
    # 로깅 설정
    log_file = setup_logging(debug=args.debug)
    logger = logging.getLogger(__name__)
    
    logger.info(f"PowerPoint Translator 시작 (디버그 모드: {args.debug})")
    
    # UI 초기화
    root = tk.Tk()
    app = PowerPointTranslatorApp(root, debug_mode=args.debug)
    
    try:
        root.mainloop()
    except Exception as e:
        logger.exception(f"예상치 못한 오류: {e}")
    finally:
        logger.info("프로그램 종료")

if __name__ == "__main__":
    main()