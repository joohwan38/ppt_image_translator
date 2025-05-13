# utils/paddle_ocr_utils.py 개선된 버전
import os
import platform
import subprocess
import logging
import tkinter.messagebox as messagebox
import sys
import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)

# 전역 변수로 패키지 가용성 설정
PADDLE_AVAILABLE = False
PADDLEOCR_AVAILABLE = False

# 시작 시 패키지 가용성 확인
try:
    import paddle
    PADDLE_AVAILABLE = True
    try:
        import paddleocr
        from paddleocr import PaddleOCR
        PADDLEOCR_AVAILABLE = True
        logger.info(f"Paddle 설치됨 (버전: {paddle.__version__})")
        logger.info(f"PaddleOCR 설치됨 (버전: {paddleocr.__version__})")
    except ImportError:
        logger.warning("paddleocr 패키지가 설치되지 않았습니다.")
except ImportError:
    logger.warning("paddle 패키지가 설치되지 않았습니다.")

def check_paddleocr():
    """PaddleOCR 설치 상태 확인"""
    if not PADDLE_AVAILABLE or not PADDLEOCR_AVAILABLE:
        return False
        
    try:
        # 언어 모델 파일 확인 (선택 사항)
        model_dir = os.path.expanduser("~/.paddleocr")
        if os.path.exists(model_dir):
            logger.info(f"PaddleOCR 모델 디렉토리 확인: {model_dir}")
        else:
            logger.warning(f"PaddleOCR 모델 디렉토리가 없습니다. 최초 실행 시 자동으로 다운로드됩니다.")
        
        return True
    except Exception as e:
        logger.exception(f"PaddleOCR 확인 오류: {e}")
        return False

def install_paddleocr():
    """PaddleOCR 설치 함수"""
    try:
        logger.info("PaddleOCR 설치 시작...")
        
        # paddlepaddle 설치 (패키지 이름은 paddlepaddle)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "paddlepaddle", "-U"])
        
        # PaddleOCR 설치
        subprocess.check_call([sys.executable, "-m", "pip", "install", "paddleocr", "-U"])
        
        logger.info("PaddleOCR 설치 완료")
        
        # 재시작 요청 안내
        messagebox.showinfo("재시작 필요", "PaddleOCR 설치가 완료되었습니다. 프로그램을 재시작해주세요.")
        
        return True
        
    except Exception as e:
        logger.exception(f"PaddleOCR 설치 오류: {e}")
        return False

def show_paddleocr_install_guide():
    """PaddleOCR 설치 가이드 표시"""
    from tkinter import messagebox
    
    msg = ("PaddleOCR 설치 방법:\n\n"
          "1. 콘솔 또는 명령 프롬프트에서 다음 명령어를 실행하세요:\n"
          "   pip install paddlepaddle -U\n"
          "   pip install paddleocr -U\n\n"
          "2. 프로그램을 재시작하여 PaddleOCR 상태를 확인하세요.\n\n"
          "또는 아래 '설치' 버튼을 클릭하여 자동으로 설치할 수 있습니다.")
    
    response = messagebox.askyesno("PaddleOCR 설치 안내", 
                                  msg + "\n\nPaddleOCR을 지금 설치하시겠습니까?")
    if response:
        try:
            success = install_paddleocr()
            if success:
                messagebox.showinfo("설치 완료", "PaddleOCR이 성공적으로 설치되었습니다. 프로그램을 재시작하세요.")
            else:
                messagebox.showerror("설치 실패", "PaddleOCR 설치에 실패했습니다. 수동으로 설치해 주세요.")
        except Exception as e:
            messagebox.showerror("설치 오류", f"설치 중 오류가 발생했습니다: {e}")
    
    logger.info("PaddleOCR 설치 안내 표시됨")

def download_lama_model(model_path="lama-model"):
    """LaMa 인페인팅 모델 다운로드"""
    # LaMa 모델 URL
    lama_url = "https://github.com/advimman/lama/releases/download/v1.0/big-lama.pt"
    
    # 모델 디렉토리 생성
    os.makedirs(model_path, exist_ok=True)
    
    # 모델 파일 경로
    model_file = os.path.join(model_path, "big-lama.pt")
    
    # 이미 다운로드된 경우 건너뛰기
    if os.path.exists(model_file):
        logger.info(f"LaMa 모델이 이미 존재합니다: {model_file}")
        return model_file
    
    try:
        logger.info(f"LaMa 모델 다운로드 시작: {lama_url}")
        
        # 파일 다운로드
        response = requests.get(lama_url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        
        # 진행 상황 표시와 함께 다운로드
        with open(model_file, 'wb') as f, tqdm(
            desc="LaMa 모델 다운로드",
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
        
        logger.info(f"LaMa 모델 다운로드 완료: {model_file}")
        return model_file
        
    except Exception as e:
        logger.exception(f"LaMa 모델 다운로드 오류: {e}")
        return None