# utils/tesseract_utils.py
import os
import platform
import subprocess
import logging
import tkinter.messagebox as messagebox

logger = logging.getLogger(__name__)

def check_tesseract():
    """Tesseract OCR 설치 상태 확인"""
    try:
        import pytesseract
        
        if platform.system() == "Windows":
            tesseract_path, tessdata_path, available_languages = _check_tesseract_windows()
        elif platform.system() == "Darwin":  # macOS
            tesseract_path, tessdata_path, available_languages = _check_tesseract_macos()
        else:  # Linux
            tesseract_path, tessdata_path, available_languages = _check_tesseract_linux()
            
        # 결과 확인
        if tesseract_path:
            # Tesseract 경로 설정
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
            # 언어 데이터 경로 설정
            if tessdata_path:
                os.environ['TESSDATA_PREFIX'] = tessdata_path
                
            # 한국어, 일본어 데이터 확인
            kor_available = 'kor' in available_languages
            jpn_available = 'jpn' in available_languages
            
            logger.info(f"Tesseract OCR: 설치됨 (경로: {tesseract_path})")
            logger.info(f"언어 데이터: KOR {kor_available}, JPN {jpn_available}")
            
            return True, kor_available, jpn_available
        else:
            logger.warning("Tesseract OCR이 설치되어 있지 않습니다.")
            return False, False, False
            
    except ImportError:
        logger.error("pytesseract 모듈이 설치되지 않았습니다.")
        return False, False, False
        
    except Exception as e:
        logger.exception(f"Tesseract OCR 확인 오류: {e}")
        return False, False, False

def _check_tesseract_windows():
    """Windows에서 Tesseract OCR 확인"""
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            # 데이터 경로 확인
            tessdata_path = os.path.join(os.path.dirname(path), "tessdata")
            available_languages = _get_available_languages(tessdata_path)
            
            return path, tessdata_path, available_languages
    
    return None, None, []

def _check_tesseract_macos():
    """macOS에서 Tesseract OCR 확인"""
    try:
        result = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            # 데이터 경로 확인
            tessdata_paths = [
                "/opt/homebrew/share/tessdata/",
                "/usr/local/share/tessdata/",
                "/usr/share/tessdata/"
            ]
            
            for path in tessdata_paths:
                if os.path.exists(path):
                    available_languages = _get_available_languages(path)
                    return "tesseract", path, available_languages
            
            return "tesseract", None, []
        else:
            return None, None, []
    except:
        return None, None, []

def _check_tesseract_linux():
    """Linux에서 Tesseract OCR 확인"""
    try:
        result = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            # 데이터 경로 확인
            tessdata_paths = [
                "/usr/share/tessdata/",
                "/usr/local/share/tessdata/"
            ]
            
            for path in tessdata_paths:
                if os.path.exists(path):
                    available_languages = _get_available_languages(path)
                    return "tesseract", path, available_languages
            
            return "tesseract", None, []
        else:
            return None, None, []
    except:
        return None, None, []

def _get_available_languages(tessdata_path):
    """사용 가능한 Tesseract 언어 목록 가져오기"""
    available_languages = []
    
    if tessdata_path and os.path.exists(tessdata_path):
        for file in os.listdir(tessdata_path):
            if file.endswith('.traineddata'):
                lang = file.replace('.traineddata', '')
                available_languages.append(lang)
    
    return available_languages

def show_tesseract_install_guide():
    """Tesseract OCR 설치 가이드 표시"""
    from tkinter import messagebox
    import webbrowser
    
    if platform.system() == "Windows":
        msg = ("Tesseract OCR 설치 방법:\n\n"
              "1. https://github.com/UB-Mannheim/tesseract/wiki 에서 최신 인스톨러 다운로드\n"
              "2. 설치 시 '추가 언어 데이터' 옵션에서 Korean과 Japanese 선택\n"
              "3. 프로그램을 재시작하여 Tesseract 상태를 확인하세요.")
        
        response = messagebox.askyesno("Tesseract OCR 설치 안내", 
                                      msg + "\n\n다운로드 페이지로 이동하시겠습니까?")
        if response:
            webbrowser.open("https://github.com/UB-Mannheim/tesseract/wiki")
            
    elif platform.system() == "Darwin":  # macOS
        msg = ("Tesseract OCR 설치 방법:\n\n"
            "1. Homebrew 설치 (아직 설치하지 않은 경우):\n"
            "   터미널에서 다음 명령어를 실행하세요:\n"
            "   /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"\n\n"
            "2. Tesseract 및 언어 패키지 설치:\n"
            "   brew install tesseract\n"
            "   brew install tesseract-lang\n\n"
            "설치 후 프로그램을 재시작하여 Tesseract 상태를 확인하세요.")
        
        response = messagebox.askyesno("Tesseract OCR 설치 안내", 
                                    msg + "\n\n터미널을 실행하시겠습니까?")
        if response:
            os.system("open -a Terminal")
            
    else:  # Linux
        msg = ("Tesseract OCR 설치 방법:\n\n"
              "터미널에서 다음 명령어를 실행하세요:\n\n"
              "sudo apt-get install tesseract-ocr\n"
              "sudo apt-get install tesseract-ocr-kor tesseract-ocr-jpn\n\n"
              "설치 후 프로그램을 재시작하여 Tesseract 상태를 확인하세요.")
        
        response = messagebox.askyesno("Tesseract OCR 설치 안내", 
                                      msg + "\n\n터미널을 실행하시겠습니까?")
        if response:
            os.system("gnome-terminal")
    
    logger.info("Tesseract OCR 설치 안내 표시됨")