# ui/components.py
import tkinter as tk
from tkinter import ttk
from config import DEFAULT_PADDING
import logging

def create_top_frame(root):
    """상단 프레임 생성 (로고와 제목)"""
    top_frame = tk.Frame(root)
    top_frame.grid(row=0, column=0, columnspan=2, padx=DEFAULT_PADDING, pady=DEFAULT_PADDING, sticky="ew")
    
    # 그리드 설정
    top_frame.columnconfigure(0, weight=1)
    top_frame.columnconfigure(1, weight=2)
    top_frame.columnconfigure(2, weight=1)
    
    # LINE studio 로고 로드
    logger = logging.getLogger(__name__)
    try:
        logo_photo = tk.PhotoImage(file="line-studio-logo.png")
        logo_label = tk.Label(top_frame, image=logo_photo)
        logo_label.image = logo_photo  # 참조 유지를 위해 필요
        logo_label.grid(row=0, column=0, sticky="w")
    except Exception as e:
        logger.warning(f"로고 로드 오류: {e}")
        logo_label = tk.Label(top_frame, text="LINE studio", fg="#8CC63F", font=("Arial", 20, "bold"))
        logo_label.grid(row=0, column=0, sticky="w")
    
    # 제목
    title_label = tk.Label(top_frame, text="Powerpoint Image Translator", font=("Arial", 20))
    title_label.grid(row=0, column=1)
    
    return top_frame

def create_file_frame(root, select_file_callback):
    """파일 경로 프레임 생성"""
    file_frame = tk.Frame(root, highlightbackground="#ddd", highlightthickness=1, padx=8, pady=8)
    file_frame.grid(row=1, column=0, columnspan=2, padx=DEFAULT_PADDING, pady=DEFAULT_PADDING, sticky="ew")
    
    # 파일 경로 레이블
    file_path_label = tk.Label(file_frame, text="파일 경로:")
    file_path_label.grid(row=0, column=0, padx=(0, 8), pady=5, sticky="w")
    
    # 파일 경로 입력 상자
    file_path_var = tk.StringVar()
    file_path_entry = tk.Entry(file_frame, textvariable=file_path_var, width=60)
    file_path_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    
    # 찾아보기 버튼
    browse_button = tk.Button(file_frame, text="찾아보기", command=select_file_callback)
    browse_button.grid(row=0, column=2, padx=5, pady=5)
    
    # 그리드 컬럼 설정
    file_frame.columnconfigure(1, weight=1)
    
    return file_frame, file_path_var, file_path_entry

def create_server_status_frame(root, check_ollama_callback, check_paddleocr_callback):
    """서버 상태 프레임 생성 (행 기준 레이아웃)"""
    server_status_frame = tk.LabelFrame(root, text="서버 상태", padx=8, pady=8)
    server_status_frame.grid(row=2, column=0, columnspan=2, padx=DEFAULT_PADDING, pady=DEFAULT_PADDING, sticky="ew")
    
    # 그리드 컬럼 설정 (4 컬럼)
    server_status_frame.columnconfigure(0, weight=2)  # 설치 상태
    server_status_frame.columnconfigure(1, weight=2)  # 실행 상태
    server_status_frame.columnconfigure(2, weight=2)  # 포트/언어
    server_status_frame.columnconfigure(3, weight=1)  # 버튼
    
    # 1행: Ollama 관련 정보 및 버튼
    # Ollama 설치 상태
    ollama_installed_label = tk.Label(server_status_frame, text="Ollama 설치 상태: 확인 중...")
    ollama_installed_label.grid(row=0, column=0, sticky="w", pady=2)
    
    # Ollama 실행 상태
    ollama_running_label = tk.Label(server_status_frame, text="Ollama 실행 상태: 확인 중...")
    ollama_running_label.grid(row=0, column=1, sticky="w", pady=2)
    
    # Ollama 포트
    ollama_port_label = tk.Label(server_status_frame, text="Ollama 포트: 확인 중...")
    ollama_port_label.grid(row=0, column=2, sticky="w", pady=2)
    
    # Ollama 확인 버튼
    check_ollama_button = tk.Button(server_status_frame, text="Ollama 확인", 
                                  width=12, command=check_ollama_callback)
    check_ollama_button.grid(row=0, column=3, pady=2, padx=5, sticky="e")
    
    # 2행: PaddleOCR 관련 정보 및 버튼 (Tesseract 대신)
    # PaddleOCR 상태
    paddleocr_status_label = tk.Label(server_status_frame, text="PaddleOCR: 확인 중...")
    paddleocr_status_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=2)
    
    # PaddleOCR 확인 버튼
    check_paddleocr_button = tk.Button(server_status_frame, text="PaddleOCR 확인", 
                                     width=12, command=check_paddleocr_callback)
    check_paddleocr_button.grid(row=1, column=3, pady=2, padx=5, sticky="e")
    
    components = {
        "ollama_installed_label": ollama_installed_label,
        "ollama_running_label": ollama_running_label,
        "ollama_port_label": ollama_port_label,
        "paddleocr_status_label": paddleocr_status_label
    }
    
    return server_status_frame, components

def create_info_frame(parent):
    """파일 정보 프레임 생성"""
    info_frame = tk.LabelFrame(parent, text="파일 정보", padx=8, pady=5)
    info_frame.grid(row=0, column=0, padx=(0, 3), pady=2, sticky="nsew")
    
    # 파일 정보 라벨들
    file_name_label = tk.Label(info_frame, text="파일 이름: 선택된 파일 없음")
    file_name_label.grid(row=0, column=0, sticky="w", pady=1)
    
    slide_count_label = tk.Label(info_frame, text="슬라이드 수: -")
    slide_count_label.grid(row=1, column=0, sticky="w", pady=1)
    
    text_count_label = tk.Label(info_frame, text="텍스트 요소 수: -")
    text_count_label.grid(row=2, column=0, sticky="w", pady=1)
    
    image_count_label = tk.Label(info_frame, text="이미지 요소 수: -")
    image_count_label.grid(row=3, column=0, sticky="w", pady=1)
    
    total_elements_label = tk.Label(info_frame, text="총 번역 요소: -")
    total_elements_label.grid(row=4, column=0, sticky="w", pady=1)
    
    labels = {
        "file_name_label": file_name_label,
        "slide_count_label": slide_count_label,
        "text_count_label": text_count_label,
        "image_count_label": image_count_label,
        "total_elements_label": total_elements_label
    }
    
    return info_frame, labels

def create_progress_frame(parent):
    """진행 상황 프레임 생성"""
    progress_frame = tk.LabelFrame(parent, text="진행 상황", padx=8, pady=5)
    progress_frame.grid(row=0, column=1, padx=(3, 0), pady=2, sticky="nsew")
    
    # 진행상황 라벨
    current_slide_label = tk.Label(progress_frame, text="현재 슬라이드: -")
    current_slide_label.grid(row=0, column=0, sticky="w", pady=1)
    
    current_task_label = tk.Label(progress_frame, text="현재 작업: -")
    current_task_label.grid(row=1, column=0, sticky="w", pady=1)
    
    translated_items_label = tk.Label(progress_frame, text="번역된 요소: -")
    translated_items_label.grid(row=2, column=0, sticky="w", pady=1)
    
    remaining_items_label = tk.Label(progress_frame, text="남은 요소: -")
    remaining_items_label.grid(row=3, column=0, sticky="w", pady=1)
    
    labels = {
        "current_slide_label": current_slide_label,
        "current_task_label": current_task_label,
        "translated_items_label": translated_items_label,
        "remaining_items_label": remaining_items_label
    }
    
    return progress_frame, labels

def create_options_frame(root, languages):
    """번역 옵션 프레임 생성"""
    options_frame = tk.LabelFrame(root, text="번역 옵션", padx=8, pady=5)
    options_frame.grid(row=4, column=0, columnspan=2, padx=DEFAULT_PADDING, pady=DEFAULT_PADDING, sticky="ew")
    
    # 프레임 너비 꽉 차게 설정
    options_frame.columnconfigure(0, weight=1)  # 원본 언어 레이블
    options_frame.columnconfigure(1, weight=2)  # 원본 언어 콤보박스
    options_frame.columnconfigure(2, weight=1)  # 화살표
    options_frame.columnconfigure(3, weight=1)  # 번역 언어 레이블
    options_frame.columnconfigure(4, weight=2)  # 번역 언어 콤보박스
    options_frame.columnconfigure(5, weight=0)  # 여백
    
    # 번역 옵션 그리드 배치
    source_label = tk.Label(options_frame, text="원본 언어:")
    source_label.grid(row=0, column=0, padx=5, pady=3, sticky="e")
    
    source_lang = tk.StringVar(value="일본어")
    source_combo = ttk.Combobox(options_frame, textvariable=source_lang, 
                              values=languages, width=10)
    source_combo.grid(row=0, column=1, padx=2, pady=3, sticky="w")
    
    # 양방향 화살표 버튼 (클릭 가능)
    def swap_languages():
        # 언어 교체 함수
        source_val = source_lang.get()
        target_val = target_lang.get()
        source_lang.set(target_val)
        target_lang.set(source_val)
    
    arrow_button = tk.Button(options_frame, text="⟷", command=swap_languages, 
                           borderwidth=0, relief="flat", bg=options_frame.cget("bg"))
    arrow_button.grid(row=0, column=2, padx=2, pady=3)
    
    target_label = tk.Label(options_frame, text="번역 언어:")
    target_label.grid(row=0, column=3, padx=5, pady=3, sticky="e")
    
    target_lang = tk.StringVar(value="한국어")
    target_combo = ttk.Combobox(options_frame, textvariable=target_lang, 
                              values=languages, width=10)
    target_combo.grid(row=0, column=4, padx=2, pady=3, sticky="w")
    
    # 번역 모델
    text_model_label = tk.Label(options_frame, text="번역 모델:")
    text_model_label.grid(row=1, column=0, padx=5, pady=3, sticky="e")
    
    text_model_var = tk.StringVar(value="gemma3:12b")
    text_model_combo = ttk.Combobox(options_frame, textvariable=text_model_var, 
                                  state="readonly", width=40)
    text_model_combo.grid(row=1, column=1, columnspan=4, padx=2, pady=3, sticky="ew")
    
    # Ollama URL 부분 삭제
    
    components = {
        "source_lang": source_lang,
        "target_lang": target_lang,
        "text_model_var": text_model_var,
        "text_model_combo": text_model_combo,
        "swap_button": arrow_button
    }
    
    return options_frame, components

def create_buttons_frame(root, start_callback, stop_callback):
    """버튼 프레임 생성"""
    buttons_frame = tk.Frame(root)
    buttons_frame.grid(row=5, column=0, columnspan=2, padx=DEFAULT_PADDING, pady=DEFAULT_PADDING)
    
    start_button = tk.Button(buttons_frame, text="번역 시작", 
                           bg="#4999E9", fg="white", width=15, height=2,
                           command=start_callback)
    start_button.grid(row=0, column=0, padx=5)
    
    stop_button = tk.Button(buttons_frame, text="번역 중지", 
                          bg="#CCCCCC", fg="white", width=15, height=2,
                          command=stop_callback,
                          state=tk.DISABLED)
    stop_button.grid(row=0, column=1, padx=5)
    
    return buttons_frame, start_button, stop_button

def create_progress_bar_frame(root):
    """진행 상황 표시 프레임 생성"""
    progress_bar_frame = tk.Frame(root)
    progress_bar_frame.grid(row=6, column=0, columnspan=2, padx=DEFAULT_PADDING, pady=3, sticky="ew")
    
    # 진행 상황 막대
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_bar_frame, variable=progress_var, maximum=100, length=600)
    progress_bar.grid(row=0, column=0, sticky="ew")
    
    # 진행율과 시간 표시 레이블
    progress_label = tk.Label(progress_bar_frame, text="0% (0:00 / 계산 중)")
    progress_label.grid(row=0, column=1, padx=5)
    
    # 그리드 설정
    progress_bar_frame.columnconfigure(0, weight=1)
    
    return progress_bar_frame, progress_var, progress_bar, progress_label

def create_log_frame(root):
    """로그 프레임 생성"""
    log_frame = tk.LabelFrame(root, text="로그", padx=8, pady=5)
    log_frame.grid(row=8, column=0, columnspan=2, padx=DEFAULT_PADDING, pady=DEFAULT_PADDING, sticky="ew")
    
    # 로그 텍스트 영역
    log_text = tk.Text(log_frame, height=8, width=80, wrap=tk.WORD)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # 스크롤바
    log_scrollbar = tk.Scrollbar(log_frame, command=log_text.yview)
    log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.config(yscrollcommand=log_scrollbar.set)
    
    return log_frame, log_text