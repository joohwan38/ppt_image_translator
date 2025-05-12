# main.py
import argparse
import tkinter as tk
import logging
import sys
from ui.app import PowerPointTranslatorApp
from utils.logging_utils import setup_logging

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