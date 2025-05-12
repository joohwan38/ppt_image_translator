# config.py
import os

# 애플리케이션 기본 설정
APP_TITLE = "Powerpoint Image Translator"
APP_VERSION = "1.0.0"
DEFAULT_WINDOW_SIZE = "850x700"
DEFAULT_PADDING = 10

# 언어 설정
SUPPORTED_LANGUAGES = ["한국어", "일본어", "영어", "중국어번체", "중국어간체", "태국어", "스페인어", "프랑스어"]
DEFAULT_SOURCE_LANG = "일본어"
DEFAULT_TARGET_LANG = "한국어"
DEFAULT_MODEL = "gemma3:12b"

# OCR 설정
OCR_LANG_MAPPING = {
    '일본어': ['jpn', 'eng'],
    '한국어': ['kor', 'eng'],
    '영어': ['eng'],
    '중국어간체': ['chi_sim', 'eng'],
    '중국어번체': ['chi_tra', 'eng'],
    '태국어': ['tha', 'eng'],
    '스페인어': ['spa', 'eng'],
    '프랑스어': ['fra', 'eng']
}

# Ollama 설정
DEFAULT_OLLAMA_URL = "http://localhost:11434"
OLLAMA_CONNECT_TIMEOUT = 5
OLLAMA_READ_TIMEOUT = 60

# 이미지 처리 설정
MAX_IMAGE_SIZE = 600  # 픽셀
MAX_IMAGE_FILESIZE = 2 * 1024 * 1024  # 2MB

# 임시 디렉토리
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)