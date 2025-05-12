import os
import time
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import webbrowser
import logging
import platform
import subprocess
import gc

from utils.logging_utils import setup_logging, TextHandler
from services.ollama_service import OllamaService
from services.document_analyzer import DocumentAnalyzer
from services.translator import TranslationService

class PowerPointTranslatorApp:
    def __init__(self, root):
        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        self.log_file = setup_logging()
        self.logger.info("프로그램 시작")
        
        self.root = root
        self.root.title("Powerpoint Image Translator")
        self.root.geometry("850x900")
        
        # OCR 초기화
        self.tesseract_available = self.check_tesseract_installation()
        
        # 모델 초기화 상태 추적
        self.models_initialized = False
        
        # Ollama 서비스 초기화
        self.ollama_service = OllamaService()
        
        # UI 컴포넌트 초기화
        self.init_ui()
        
        # 변수 초기화
        self.ppt_path = None
        self.translation_thread = None
        self.translation_running = False
        self.start_time = 0
        self.translated_items_count = 0
        
        # 문서 분석 결과 저장
        self.total_text_elements = 0
        self.total_image_elements = 0
        self.total_elements = 0
        
        # 번역 요소 저장 (상세 프로그레스 표시용)
        self.text_elements = []  # (슬라이드_인덱스, 텍스트, 요소_타입)
        self.image_elements = [] # (슬라이드_인덱스, 이미지_패스, 이미지_크기)
        
        # 타이머 관련 변수
        self.timer_running = False
        self.timer_id = None
        self.elapsed_time = 0
        self.estimated_total_time = 0
        self.last_progress_update = 0
        
        # 초기 상태 확인
        self.check_ollama_status()
        
    def check_tesseract_installation(self):
        """Tesseract OCR 설치 확인"""
        try:
            import pytesseract
            import platform
            import os
            
            # 시스템 확인
            system = platform.system()
            
            if system == "Windows":
                # Windows 테서렉트 경로 후보
                tesseract_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                ]
                
                for path in tesseract_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        self.logger.info(f"Tesseract OCR 경로 설정: {path}")
                        
                        # 데이터 경로 설정
                        tessdata_path = os.path.join(os.path.dirname(path), "tessdata")
                        if os.path.exists(tessdata_path):
                            os.environ['TESSDATA_PREFIX'] = tessdata_path
                            self.logger.info(f"언어 데이터 경로 설정: {tessdata_path}")
                            
                            # 한국어 데이터 확인
                            if os.path.exists(os.path.join(tessdata_path, "kor.traineddata")):
                                self.logger.info("한국어 언어 데이터 확인됨")
                            else:
                                self.logger.warning("한국어 언어 데이터가 없습니다")
                        return True
                
                # 설치 안 된 경우 메시지 표시
                self.logger.warning("Tesseract OCR이 설치되지 않았습니다.")
                if messagebox.askyesno("Tesseract OCR 설치 필요", 
                                    "이미지 텍스트 번역 기능을 위해 Tesseract OCR이 필요합니다. 설치 페이지로 이동하시겠습니까?"):
                    webbrowser.open("https://github.com/UB-Mannheim/tesseract/wiki")
                return False
                
            elif system == "Darwin":  # macOS
                # macOS 경로 후보
                tesseract_paths = [
                    "/opt/homebrew/bin/tesseract",
                    "/usr/local/bin/tesseract"
                ]
                
                for path in tesseract_paths:
                    if os.path.exists(path):
                        # 테서렉트 경로 설정
                        pytesseract.pytesseract.tesseract_cmd = path
                        self.logger.info(f"Tesseract OCR 경로 설정: {path}")
                        
                        # 데이터 경로 추측 (Homebrew 또는 기본 경로)
                        if 'homebrew' in path:
                            tessdata_path = "/opt/homebrew/share/tessdata/"
                        else:
                            tessdata_path = "/usr/local/share/tessdata/"
                        
                        if os.path.exists(tessdata_path):
                            os.environ['TESSDATA_PREFIX'] = tessdata_path
                            self.logger.info(f"언어 데이터 경로 설정: {tessdata_path}")
                            
                            # 한국어 데이터 확인
                            if os.path.exists(os.path.join(tessdata_path, "kor.traineddata")):
                                self.logger.info("한국어 언어 데이터 확인됨")
                            else:
                                self.logger.warning("한국어 언어 데이터가 없습니다")
                                self.prompt_install_korean_data(tessdata_path)
                        return True
                
                # 설치 안 된 경우 안내
                self.logger.warning("Tesseract OCR이 설치되지 않았습니다.")
                if messagebox.askyesno("Tesseract OCR 설치 필요", 
                                    "이미지 텍스트 번역 기능을 위해 Tesseract OCR이 필요합니다. 설치 안내를 보시겠습니까?"):
                    messagebox.showinfo("설치 안내", "터미널에서 다음 명령어를 실행하세요: brew install tesseract tesseract-lang")
                return False
                
            else:  # Linux
                # Linux 확인
                result = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    self.logger.info("Tesseract OCR 설치 확인됨")
                    
                    # 데이터 경로 확인
                    tessdata_paths = [
                        "/usr/share/tessdata/",
                        "/usr/local/share/tessdata/"
                    ]
                    
                    for path in tessdata_paths:
                        if os.path.exists(path):
                            os.environ['TESSDATA_PREFIX'] = path
                            self.logger.info(f"언어 데이터 경로 설정: {path}")
                            
                            # 한국어 데이터 확인
                            if os.path.exists(os.path.join(path, "kor.traineddata")):
                                self.logger.info("한국어 언어 데이터 확인됨")
                            else:
                                self.logger.warning("한국어 언어 데이터가 없습니다")
                            break
                    
                    return True
                else:
                    self.logger.warning("Tesseract OCR이 설치되지 않았습니다.")
                    if messagebox.askyesno("Tesseract OCR 설치 필요", 
                                        "이미지 텍스트 번역 기능을 위해 Tesseract OCR이 필요합니다. 설치 안내를 보시겠습니까?"):
                        messagebox.showinfo("설치 안내", "터미널에서 다음 명령어를 실행하세요: sudo apt-get install tesseract-ocr tesseract-ocr-all")
                    return False
        
        except ImportError:
            self.logger.warning("pytesseract 모듈이 설치되지 않았습니다.")
            if messagebox.askyesno("pytesseract 모듈 설치 필요", 
                                "이미지 텍스트 번역 기능을 위해 pytesseract 모듈이 필요합니다. 설치하시겠습니까?"):
                try:
                    subprocess.run([sys.executable, "-m", "pip", "install", "pytesseract"], check=True)
                    self.logger.info("pytesseract 모듈 설치 완료")
                    # 설치 후 다시 확인
                    return self.check_tesseract_installation()
                except Exception as e:
                    self.logger.error(f"pytesseract 모듈 설치 오류: {e}")
                    messagebox.showerror("설치 오류", f"pytesseract 모듈 설치 중 오류가 발생했습니다: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Tesseract OCR 확인 오류: {e}")
            return False

    def prompt_install_korean_data(self, tessdata_path):
        """한국어 데이터 설치 안내"""
        response = messagebox.askquestion(
            "한국어 언어 데이터 필요",
            "한국어 OCR을 위한 언어 데이터가 없습니다. 설치하시겠습니까?",
            icon='info'
        )
        
        if response == 'yes':
            if platform.system() == "Darwin":  # macOS
                messagebox.showinfo("설치 안내", "터미널에서 다음 명령어를 실행하세요: brew install tesseract-lang")
            elif platform.system() == "Windows":
                # 한국어 데이터 다운로드 URL 열기
                webbrowser.open("https://github.com/tesseract-ocr/tessdata/raw/main/kor.traineddata")
                messagebox.showinfo("설치 안내", 
                                f"다운로드된 kor.traineddata 파일을 다음 경로에 복사하세요: {tessdata_path}")
            else:  # Linux
                messagebox.showinfo("설치 안내", "터미널에서 다음 명령어를 실행하세요: sudo apt-get install tesseract-ocr-kor")
    
    def init_ui(self):
        """UI 구성 요소 초기화"""
        # 상단 프레임 (로고와 제목을 위한 프레임)
        self.top_frame = tk.Frame(self.root)
        self.top_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="ew")
        
        # 그리드 설정
        self.top_frame.columnconfigure(0, weight=1)  # 로고 열
        self.top_frame.columnconfigure(1, weight=2)  # 제목 열
        self.top_frame.columnconfigure(2, weight=1)  # 빈 공간 열
        
        # LINE studio 로고 로드
        try:
            self.logo_photo = tk.PhotoImage(file="line-studio-logo.png")
            self.logo_label = tk.Label(self.top_frame, image=self.logo_photo)
            self.logo_label.grid(row=0, column=0, sticky="w")
        except Exception as e:
            self.logger.warning(f"로고 로드 오류: {e}")
            # 로고 로드 실패 시 텍스트로 대체
            self.logo_label = tk.Label(self.top_frame, text="LINE studio", fg="#8CC63F", font=("Arial", 24, "bold"))
            self.logo_label.grid(row=0, column=0, sticky="w")
        
        # 제목 (가운데 정렬)
        self.title_label = tk.Label(self.top_frame, text="Powerpoint Image Translator", font=("Arial", 24))
        self.title_label.grid(row=0, column=1)
        
        # 파일 프레임
        self.file_frame = tk.Frame(self.root, highlightbackground="#ddd", highlightthickness=1, padx=10, pady=10)
        self.file_frame.grid(row=1, column=0, columnspan=2, padx=50, pady=20, sticky="ew")
        
        # 파일 경로 레이블
        self.file_path_label = tk.Label(self.file_frame, text="파일 경로:")
        self.file_path_label.grid(row=0, column=0, padx=(0, 10), pady=10, sticky="w")
        
        # 파일 경로 입력 상자
        self.file_path_var = tk.StringVar()
        self.file_path_entry = tk.Entry(self.file_frame, textvariable=self.file_path_var, width=60)
        self.file_path_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        
        # 찾아보기 버튼
        self.browse_button = tk.Button(self.file_frame, text="찾아보기", command=self.select_file)
        self.browse_button.grid(row=0, column=2, padx=5, pady=10)
        
        # 그리드 컬럼 설정
        self.file_frame.columnconfigure(1, weight=1)
        
        # 정보 및 진행상황 프레임 (2개의 LabelFrame 가로 배치)
        self.info_progress_frame = tk.Frame(self.root)
        self.info_progress_frame.grid(row=2, column=0, columnspan=2, padx=50, pady=10, sticky="ew")
        self.info_progress_frame.columnconfigure(0, weight=1)
        self.info_progress_frame.columnconfigure(1, weight=1)
        
        # 파일 정보 표시 영역
        self.info_frame = tk.LabelFrame(self.info_progress_frame, text="파일 정보", padx=10, pady=10)
        self.info_frame.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="nsew")
        
        # 파일 정보 라벨
        self.file_name_label = tk.Label(self.info_frame, text="파일 이름: 선택된 파일 없음")
        self.file_name_label.grid(row=0, column=0, sticky="w", pady=3)
        
        self.slide_count_label = tk.Label(self.info_frame, text="슬라이드 수: -")
        self.slide_count_label.grid(row=1, column=0, sticky="w", pady=3)
        
        self.text_count_label = tk.Label(self.info_frame, text="텍스트 요소 수: -")
        self.text_count_label.grid(row=2, column=0, sticky="w", pady=3)
        
        self.image_count_label = tk.Label(self.info_frame, text="이미지 요소 수: -")
        self.image_count_label.grid(row=3, column=0, sticky="w", pady=3)
        
        self.total_elements_label = tk.Label(self.info_frame, text="총 번역 요소: -")
        self.total_elements_label.grid(row=4, column=0, sticky="w", pady=3)
        
        # 진행상황 표시 영역
        self.progress_frame = tk.LabelFrame(self.info_progress_frame, text="진행 상황", padx=10, pady=10)
        self.progress_frame.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="nsew")
        
        # 진행상황 라벨
        self.current_slide_label = tk.Label(self.progress_frame, text="현재 슬라이드: -")
        self.current_slide_label.grid(row=0, column=0, sticky="w", pady=3)
        
        self.current_task_label = tk.Label(self.progress_frame, text="현재 작업: -")
        self.current_task_label.grid(row=1, column=0, sticky="w", pady=3)
        
        self.translated_items_label = tk.Label(self.progress_frame, text="번역된 요소: -")
        self.translated_items_label.grid(row=2, column=0, sticky="w", pady=3)
        
        self.remaining_items_label = tk.Label(self.progress_frame, text="남은 요소: -")
        self.remaining_items_label.grid(row=3, column=0, sticky="w", pady=3)
        
        # Ollama 상태 표시
        self.ollama_status_frame = tk.LabelFrame(self.root, text="Ollama 상태", padx=10, pady=10)
        self.ollama_status_frame.grid(row=3, column=0, columnspan=2, padx=50, pady=10, sticky="ew")
        
        # Ollama 설치 상태
        self.ollama_installed_label = tk.Label(self.ollama_status_frame, text="설치 상태: 확인 중...")
        self.ollama_installed_label.grid(row=0, column=0, sticky="w", pady=2)
        
        # Ollama 실행 상태
        self.ollama_running_label = tk.Label(self.ollama_status_frame, text="실행 상태: 확인 중...")
        self.ollama_running_label.grid(row=1, column=0, sticky="w", pady=2)
        
        # Ollama 포트
        self.ollama_port_label = tk.Label(self.ollama_status_frame, text="Ollama 포트: 확인 중...")
        self.ollama_port_label.grid(row=2, column=0, sticky="w", pady=2)
        
        # Tesseract 상태 추가
        self.tesseract_label = tk.Label(self.ollama_status_frame, 
                                      text=f"Tesseract OCR: {'설치됨' if self.tesseract_available else '설치되지 않음'}",
                                      fg="green" if self.tesseract_available else "red")
        self.tesseract_label.grid(row=3, column=0, sticky="w", pady=2)
        
        # Ollama 상태 확인 버튼
        self.check_ollama_button = tk.Button(self.ollama_status_frame, text="상태 확인", 
                                          command=self.check_ollama_status)
        self.check_ollama_button.grid(row=0, column=1, rowspan=4, padx=20)
        
        # 번역 옵션 프레임
        self.options_frame = tk.LabelFrame(self.root, text="번역 옵션", padx=10, pady=10)
        self.options_frame.grid(row=4, column=0, columnspan=2, padx=50, pady=10, sticky="ew")
        
        # 언어 목록 정의
        self.languages = ["한국어", "일본어", "영어", "중국어번체", "중국어간체", "태국어", "스페인어", "프랑스어"]
        
        # 원본 언어 선택
        self.source_label = tk.Label(self.options_frame, text="원본 언어:")
        self.source_label.grid(row=0, column=0, padx=10, pady=10)
        
        self.source_lang = tk.StringVar(value="일본어")
        self.source_combo = ttk.Combobox(self.options_frame, textvariable=self.source_lang, 
                                        values=self.languages)
        self.source_combo.grid(row=0, column=1, padx=10, pady=10)
        
        # 화살표 레이블
        self.arrow_label = tk.Label(self.options_frame, text="⟷")
        self.arrow_label.grid(row=0, column=2, padx=10, pady=10)
        
        # 번역 언어 선택
        self.target_label = tk.Label(self.options_frame, text="번역 언어:")
        self.target_label.grid(row=0, column=3, padx=10, pady=10)
        
        self.target_lang = tk.StringVar(value="한국어")
        self.target_combo = ttk.Combobox(self.options_frame, textvariable=self.target_lang, 
                                        values=self.languages)
        self.target_combo.grid(row=0, column=4, padx=10, pady=10)
        
        # Vision 모델 선택
        self.vision_model_label = tk.Label(self.options_frame, text="Vision 모델:")
        self.vision_model_label.grid(row=1, column=0, padx=10, pady=10)
        
        self.vision_model_var = tk.StringVar(value="")
        self.vision_model_combo = ttk.Combobox(self.options_frame, textvariable=self.vision_model_var, state="readonly")
        self.vision_model_combo.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        # Text 모델 선택
        self.text_model_label = tk.Label(self.options_frame, text="Text 모델:")
        self.text_model_label.grid(row=1, column=3, padx=10, pady=10)
        
        self.text_model_var = tk.StringVar(value="gemma3:12b")
        self.text_model_combo = ttk.Combobox(self.options_frame, textvariable=self.text_model_var, state="readonly")
        self.text_model_combo.grid(row=1, column=4, padx=10, pady=10, sticky="ew")
        
        # URL 입력
        self.url_label = tk.Label(self.options_frame, text="Ollama URL:")
        self.url_label.grid(row=2, column=0, padx=10, pady=10)
        
        self.url_var = tk.StringVar(value="http://localhost:11434")
        self.url_entry = tk.Entry(self.options_frame, textvariable=self.url_var, width=40)
        self.url_entry.grid(row=2, column=1, columnspan=4, padx=10, pady=10, sticky="ew")
        
        # 이미지 처리 옵션 추가
        self.img_process_frame = tk.Frame(self.options_frame)
        self.img_process_frame.grid(row=3, column=0, columnspan=5, padx=10, pady=5, sticky="w")
        
        # OCR 사용 여부 체크박스
        self.use_ocr_var = tk.BooleanVar(value=self.tesseract_available)
        self.use_ocr_check = tk.Checkbutton(self.img_process_frame, text="OCR 사용 (텍스트 정확한 위치 감지)", 
                                          variable=self.use_ocr_var,
                                          state=tk.NORMAL if self.tesseract_available else tk.DISABLED)
        self.use_ocr_check.pack(side=tk.LEFT, padx=10)
        
        # 메모리 최적화 체크박스
        self.optimize_memory_var = tk.BooleanVar(value=True)
        self.optimize_memory_check = tk.Checkbutton(self.img_process_frame, text="메모리 최적화", 
                                                 variable=self.optimize_memory_var)
        self.optimize_memory_check.pack(side=tk.LEFT, padx=20)
        
        # 번역 시작/중지 버튼
        self.buttons_frame = tk.Frame(self.root)
        self.buttons_frame.grid(row=5, column=0, columnspan=2, padx=50, pady=10)
        
        self.start_button = tk.Button(self.buttons_frame, text="번역 시작", 
                                    bg="#4999E9", fg="white", width=20, height=2,
                                    command=self.start_translation)
        self.start_button.grid(row=0, column=0, padx=10)
        
        self.stop_button = tk.Button(self.buttons_frame, text="번역 중지", 
                                    bg="#CCCCCC", fg="white", width=20, height=2,
                                    command=self.stop_translation,
                                    state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=10)
        
        # 진행 상황 프레임
        self.progress_bar_frame = tk.Frame(self.root)
        self.progress_bar_frame.grid(row=6, column=0, columnspan=2, padx=50, pady=5, sticky="ew")
        
        # 진행 상황 막대
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_bar_frame, variable=self.progress_var, maximum=100, length=600)
        self.progress_bar.grid(row=0, column=0, sticky="ew")
        
        # 진행율과 시간 표시 레이블
        self.progress_label = tk.Label(self.progress_bar_frame, text="0% (0:00 / 계산 중)")
        self.progress_label.grid(row=0, column=1, padx=10)
        
        # 상태 메시지
        self.status_label = tk.Label(self.root, text="준비 완료")
        self.status_label.grid(row=7, column=0, columnspan=2, padx=50, pady=5, sticky="w")
        
        # 로그 프레임
        self.log_frame = tk.LabelFrame(self.root, text="로그", padx=10, pady=10)
        self.log_frame.grid(row=8, column=0, columnspan=2, padx=50, pady=10, sticky="ew")
        
        # 로그 텍스트 영역
        self.log_text = tk.Text(self.log_frame, height=10, width=80, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 스크롤바
        log_scrollbar = tk.Scrollbar(self.log_frame, command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        # GUI에 로그 출력을 위한 핸들러 추가
        self.text_handler = TextHandler(self.log_text)
        self.text_handler.setLevel(logging.INFO)
        self.text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(self.text_handler)
        
        # 그리드 설정
        self.progress_bar_frame.columnconfigure(0, weight=1)
        
        # 파일 경로 변경 감지 및 버튼 색상 변경
        self.file_path_var.trace_add("write", self.on_file_path_change)
        
    def on_file_path_change(self, *args):
        """파일 경로 변경 시 버튼 색상 업데이트"""
        if self.file_path_var.get().strip():
            # 파일이 선택된 경우 텍스트 색상을 검정색으로 변경
            self.start_button.config(fg="black")
        else:
            # 파일이 선택되지 않은 경우 텍스트 색상을 흰색으로 유지
            self.start_button.config(fg="white")
    
    def select_file(self):
        """파일 선택 다이얼로그 열기"""
        file_path = filedialog.askopenfilename(
            filetypes=[("PowerPoint 파일", "*.pptx"), ("모든 파일", "*.*")]
        )
        if file_path:
            self.ppt_path = file_path
            self.file_path_var.set(file_path)  # 파일 경로 표시
            self.analyze_document(file_path)
    
    def analyze_document(self, file_path):
        """문서 분석 (텍스트 및 이미지 요소 추출)"""
        self.logger.info(f"문서 분석 시작: {file_path}")
        self.status_label.config(text="문서 분석 중...")
        
        try:
            analyzer = DocumentAnalyzer()
            result = analyzer.analyze_ppt(file_path)
            
            # 분석 결과 저장
            self.text_elements = result['text_elements']
            self.image_elements = result['image_elements']
            self.total_text_elements = result['total_text_count']
            self.total_image_elements = result['total_image_count']
            self.total_elements = result['total_elements']
            
            # 정보 표시
            self.file_name_label.config(text=f"파일 이름: {result['file_name']}")
            self.slide_count_label.config(text=f"슬라이드 수: {result['slide_count']}")
            self.text_count_label.config(text=f"텍스트 요소 수: {result['total_text_count']} (테이블 셀: {result['total_table_cells']})")
            self.image_count_label.config(text=f"이미지 요소 수: {result['total_image_count']}")
            self.total_elements_label.config(text=f"총 번역 요소: {self.total_elements}")
            
            # 번역 상태 초기화
            self.translated_items_count = 0
            self.translated_items_label.config(text=f"번역된 요소: 0/{self.total_elements}")
            self.remaining_items_label.config(text=f"남은 요소: {self.total_elements}")
            
            self.status_label.config(text="문서 분석 완료")
            
        except Exception as e:
            self.logger.exception(f"문서 분석 오류: {str(e)}")
            self.file_name_label.config(text=f"파일 이름: {os.path.basename(file_path)}")
            self.slide_count_label.config(text="슬라이드 수: 오류 발생")
            self.text_count_label.config(text="텍스트 요소 수: 오류 발생")
            self.image_count_label.config(text="이미지 요소 수: 오류 발생")
            self.total_elements_label.config(text="총 번역 요소: 오류 발생")
            self.status_label.config(text=f"문서 분석 오류: {str(e)}")
            messagebox.showerror("오류", f"문서 분석 중 오류가 발생했습니다: {str(e)}")
            
            # 메모리 정리
            gc.collect()
    
    def check_ollama_status(self):
        """Ollama 상태 확인"""
        # 설치 확인
        installed = self.ollama_service.is_installed()
        self.ollama_installed_label.config(
            text=f"설치 상태: {'설치됨' if installed else '설치되지 않음'}",
            fg="green" if installed else "red"
        )
        
        if not installed:
            self.show_ollama_install_guide()
            return False
        
        # 실행 상태 확인
        running, port = self.ollama_service.is_running()
        self.ollama_running_label.config(
            text=f"실행 상태: {'실행 중' if running else '실행되지 않음'}",
            fg="green" if running else "red"
        )
        
        # Ollama가 설치되어 있지만 실행 중이 아닌 경우 자동 실행
        if installed and not running:
            self.ollama_service.start_ollama()
            running, port = self.ollama_service.is_running()
        
        # 포트 정보 표시
        self.ollama_port_label.config(
            text=f"Ollama 포트: {port if running else '없음'}"
        )
        
        # URL 업데이트
        if running and port:
            self.url_var.set(f"http://localhost:{port}")
            
            # 최초 실행 시에만 모델 목록 업데이트
            if not self.models_initialized:
                text_models, vision_models = self.update_models_list()
                self.models_initialized = True
        
        return installed and running
    
    def show_ollama_install_guide(self):
        """Ollama 설치 가이드 표시"""
        response = messagebox.askquestion(
            "Ollama 설치 필요",
            "Ollama가 설치되어 있지 않습니다. Ollama 설치 페이지로 이동하시겠습니까?",
            icon='warning'
        )
        
        if response == 'yes':
            webbrowser.open("https://ollama.com/download")
    
    def update_models_list(self):
        """설치된 모델 목록 가져오기 및 UI 업데이트"""
        try:
            # 현재 선택된 모델 저장
            current_text_model = self.text_model_var.get()
            current_vision_model = self.vision_model_var.get()
            
            # 모델 목록 가져오기
            text_models, vision_models = self.ollama_service.get_models_list()
            
            # UI 업데이트
            if vision_models:
                self.vision_model_combo['values'] = vision_models
                if current_vision_model in vision_models:
                    self.vision_model_var.set(current_vision_model)
                else:
                    self.vision_model_var.set(vision_models[0])
            else:
                self.vision_model_combo['values'] = ["Vision 모델 없음"]
                self.vision_model_var.set("Vision 모델 없음")
                self.prompt_install_vision_model()
            
            if text_models:
                self.text_model_combo['values'] = text_models
                if current_text_model in text_models:
                    self.text_model_var.set(current_text_model)
                elif "gemma3:12b" in text_models:
                    self.text_model_var.set("gemma3:12b")
                else:
                    self.text_model_var.set(text_models[0])
            else:
                self.text_model_combo['values'] = ["Text 모델 없음"]
                self.text_model_var.set("Text 모델 없음")
                self.prompt_install_base_models()
            
            return text_models, vision_models
            
        except Exception as e:
            self.logger.exception(f"모델 목록 가져오기 오류: {e}")
            self.vision_model_combo['values'] = ["Vision 모델 없음"]
            self.vision_model_var.set("Vision 모델 없음")
            self.text_model_combo['values'] = ["Text 모델 없음"]
            self.text_model_var.set("Text 모델 없음")
            
            # 메모리 정리
            gc.collect()
            
            return [], []
    
    def prompt_install_base_models(self):
        """기본 모델 설치 권유"""
        response = messagebox.askquestion(
            "기본 모델 설치",
            "사용 가능한 모델이 없습니다. 기본 모델(gemma3:12b, llava)을 설치하시겠습니까?",
            icon='info'
        )
        
        if response == 'yes':
            self.status_label.config(text="기본 모델 설치 중...")
            threading.Thread(target=self.install_base_models, daemon=True).start()
    
    def prompt_install_vision_model(self):
        """Vision 모델 설치 권유"""
        response = messagebox.askquestion(
            "Vision 모델 설치",
            "이미지 처리를 위한 Vision 모델이 없습니다. llava 모델을 설치하시겠습니까?",
            icon='info'
        )
        
        if response == 'yes':
            self.status_label.config(text="llava 모델 설치 중...")
            threading.Thread(target=lambda: self.ollama_service.install_model("llava"), daemon=True).start()
    
    def install_base_models(self):
        """기본 모델 설치"""
        try:
            # Gemma 3:12b 설치
            self.ollama_service.install_model("gemma3:12b")
            
            # LLaVA 설치
            self.ollama_service.install_model("llava")
            
            # 모델 목록 업데이트
            self.update_models_list()
            
            self.status_label.config(text="모델 설치 완료")
            messagebox.showinfo("설치 완료", "기본 모델 설치가 완료되었습니다.")
        except Exception as e:
            self.status_label.config(text=f"모델 설치 오류: {str(e)}")
            messagebox.showerror("설치 오류", f"모델 설치 중 오류가 발생했습니다: {str(e)}")
            
            # 메모리 정리
            gc.collect()
    
    def format_time(self, seconds):
        """초를 분:초 형식으로 변환"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02d}"
    
    def update_timer(self):
        """타이머 업데이트 함수"""
        if self.timer_running:
            # 경과 시간 계산
            self.elapsed_time = time.time() - self.start_time
            
            # 진행율 가져오기
            progress = self.progress_var.get()
            
            # 경과 시간만 업데이트 (예상 시간은 프로그레스 업데이트 시에만 변경)
            time_text = self.progress_label.cget("text")
            if "계산 중" in time_text or progress < 1:
                self.progress_label.config(
                    text=f"{progress:.1f}% ({self.format_time(self.elapsed_time)} / 계산 중)"
                )
            
            # 1초 후 다시 호출
            self.timer_id = self.root.after(1000, self.update_timer)
    
    def update_progress(self, current, total):
        """진행 상황 업데이트"""
        if total == 0:
            return
        
        # 진행율 계산
        progress = (current / total) * 100
        self.progress_var.set(progress)
        
        # 예상 시간은 프로그레스가 갱신될 때만 업데이트
        # 경과 시간 계산
        self.elapsed_time = time.time() - self.start_time
        
        # 예상 남은 시간 계산
        if progress > 5:  # 최소 5% 이상 진행되었을 때만 예상 시간 계산
            self.estimated_total_time = self.elapsed_time * (100 / progress)
            estimated_remaining_time = self.estimated_total_time - self.elapsed_time
            
            # 진행 상황 표시 업데이트
            self.progress_label.config(
                text=f"{progress:.1f}% ({self.format_time(self.elapsed_time)} / {self.format_time(self.elapsed_time + estimated_remaining_time)})"
            )
        else:
            # 진행률이 낮을 때는 "계산 중" 표시
            self.progress_label.config(
                text=f"{progress:.1f}% ({self.format_time(self.elapsed_time)} / 계산 중)"
            )
        
        # 번역된 항목 업데이트
        self.translated_items_count = current
        self.translated_items_label.config(text=f"번역된 요소: {current}/{total}")
        self.remaining_items_label.config(text=f"남은 요소: {total - current}")
        
        self.root.update_idletasks()
        
        # 메모리 최적화 옵션이 켜져 있으면 주기적으로 GC 실행
        if self.optimize_memory_var.get() and current % 10 == 0:
            gc.collect()
    
    def update_status(self, status_text):
        """상태 메시지 업데이트"""
        self.status_label.config(text=status_text)
        self.root.update_idletasks()
    
    def start_translation(self):
        """번역 프로세스 시작"""
        if not self.file_path_var.get():
            messagebox.showerror("오류", "파일을 먼저 선택해주세요.")
            return
        
        self.ppt_path = self.file_path_var.get()
        
        # 파일 존재 확인
        if not os.path.exists(self.ppt_path):
            messagebox.showerror("오류", "선택한 파일이 존재하지 않습니다.")
            return
        
        # Ollama 상태 확인
        if not self.check_ollama_status():
            messagebox.showerror("오류", "Ollama가 설치되어 있지 않거나 실행 중이 아닙니다.")
            return
        
        # 모델 확인
        vision_model = self.vision_model_var.get()
        text_model = self.text_model_var.get()
        
        if "Vision 모델 없음" in vision_model:
            response = messagebox.askquestion(
                "Vision 모델 없음",
                "이미지 처리를 위한 Vision 모델이 없습니다. Vision 모델을 설치한 후 다시 시도하시겠습니까?",
                icon='warning'
            )
            if response == 'yes':
                self.prompt_install_vision_model()
            return
        
        if "Text 모델 없음" in text_model:
            response = messagebox.askquestion(
                "Text 모델 없음",
                "텍스트 번역을 위한 모델이 없습니다. Text 모델을 설치한 후 다시 시도하시겠습니까?",
                icon='warning'
            )
            if response == 'yes':
                self.status_label.config(text="gemma3:12b 모델 설치 중...")
                threading.Thread(target=lambda: self.ollama_service.install_model("gemma3:12b"), daemon=True).start()
            return
        
        # 이미 번역 중인지 확인
        if self.translation_running:
            messagebox.showinfo("알림", "이미 번역이 진행 중입니다.")
            return
        
        # 파일 분석이 필요한 경우
        if self.total_elements == 0:
            self.analyze_document(self.ppt_path)
            if self.total_elements == 0:
                messagebox.showerror("오류", "번역할 요소가 없습니다.")
                return
        
        # 진행 상태 초기화
        self.progress_var.set(0)
        self.progress_label.config(text="0% (0:00 / 계산 중)")
        self.current_slide_label.config(text="현재 슬라이드: -")
        self.current_task_label.config(text="현재 작업: -")
        self.translated_items_count = 0
        self.translated_items_label.config(text=f"번역된 요소: 0/{self.total_elements}")
        self.remaining_items_label.config(text=f"남은 요소: {self.total_elements}")
        
        # 타이머 초기화
        self.elapsed_time = 0
        self.estimated_total_time = 0
        self.last_progress_update = 0
        
        # 버튼 상태 변경
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 번역 서비스 초기화
        self.ollama_service.url = self.url_var.get()  # URL 업데이트
        translation_service = TranslationService(self.ollama_service)
        
        # 번역 스레드 시작
        self.translation_running = True
        self.start_time = time.time()
        
        # 타이머 시작
        self.timer_running = True
        self.update_timer()
        
        # 번역 옵션 설정
        use_ocr = self.use_ocr_var.get()
        optimize_memory = self.optimize_memory_var.get()
        
        # 번역 스레드 시작
        self.translation_thread = threading.Thread(
            target=self.translation_process,
            args=(translation_service, use_ocr, optimize_memory)
        )
        self.translation_thread.daemon = True
        self.translation_thread.start()
    
    def stop_translation(self):
        """번역 프로세스 중지"""
        self.translation_running = False
        self.timer_running = False  # 타이머 중지
        self.status_label.config(text="번역 중지 중...")
        self.logger.info("사용자에 의한 번역 중지")
    
    def translation_process(self, translation_service, use_ocr=False, optimize_memory=True):
        """번역 프로세스 실행"""
        output_path = None
        
        try:
            # 옵션 가져오기
            source_lang = self.source_lang.get()
            target_lang = self.target_lang.get()
            vision_model = self.vision_model_var.get()
            text_model = self.text_model_var.get()
            
            self.logger.info(f"번역 설정: {source_lang} → {target_lang}, Vision: {vision_model}, Text: {text_model}")
            self.logger.info(f"번역 옵션: OCR 사용: {use_ocr}, 메모리 최적화: {optimize_memory}")
            
            # 추가 옵션을 딕셔너리로 전달
            options = {
                "use_ocr": use_ocr,
                "optimize_memory": optimize_memory,
                "source_lang": source_lang  # OCR 언어 힌트로 사용
            }
            
            # 번역 서비스 호출
            output_path = translation_service.translate_ppt(
                self.ppt_path, 
                source_lang, 
                target_lang, 
                vision_model, 
                text_model,
                self.update_progress,
                self.update_status,
                options
            )
            
            # 타이머 중지
            self.timer_running = False
            
            # 완료 메시지 - 메인 스레드에서 실행하기 위해 after 메서드 사용
            elapsed_time = time.time() - self.start_time
            final_elapsed_time = elapsed_time  # 로컬 변수로 복사
            
            # 메인 스레드에서 메시지 박스 표시
            self.root.after(0, lambda: self.show_completion_message(output_path, final_elapsed_time))
            
        except Exception as e:
            # 타이머 중지
            self.timer_running = False
            self.logger.exception(f"번역 프로세스 오류: {str(e)}")
            
            # 오류 메시지 - 메인 스레드에서 실행
            error_msg = str(e)
            self.root.after(0, lambda: self.show_error_message(error_msg))
            
            # 메모리 정리
            gc.collect()
            
        finally:
            self.translation_running = False
            self.timer_running = False
            
            # 버튼 상태 변경 - 메인 스레드에서 실행
            self.root.after(0, self.reset_ui_after_translation)
            
            # 최종 메모리 정리
            gc.collect()

    def show_completion_message(self, output_path, elapsed_time):
        """번역 완료 메시지 표시 (메인 스레드에서 실행)"""
        self.progress_label.config(text=f"100% (총 소요시간: {self.format_time(elapsed_time)})")
        self.status_label.config(text=f"번역 완료! 파일 저장됨: {output_path}")
        self.logger.info(f"번역 완료: 소요시간 {elapsed_time:.2f}초")
        
        # 결과 파일 열기 옵션 제공
        if messagebox.askyesno("완료", f"번역이 완료되었습니다.\n파일 저장 위치: {output_path}\n\n파일을 열어보시겠습니까?"):
            try:
                if platform.system() == "Windows":
                    os.startfile(output_path)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", output_path])
                else:  # Linux
                    subprocess.run(["xdg-open", output_path])
            except Exception as e:
                self.logger.error(f"파일 열기 오류: {e}")
                messagebox.showwarning("경고", f"파일을 열 수 없습니다: {e}")
        else:
            messagebox.showinfo("완료", f"번역이 완료되었습니다.\n파일 저장 위치: {output_path}")

    def show_error_message(self, error_msg):
        """오류 메시지 표시 (메인 스레드에서 실행)"""
        self.status_label.config(text=f"번역 오류: {error_msg}")
        messagebox.showerror("오류", f"번역 중 오류가 발생했습니다: {error_msg}")

    def reset_ui_after_translation(self):
        """번역 후 UI 상태 초기화 (메인 스레드에서 실행)"""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)