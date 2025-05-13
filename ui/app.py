# ui/app.py
import os
import logging
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import platform
import subprocess

from config import *
from ui.components import (
    create_top_frame, create_file_frame, create_server_status_frame,
    create_info_frame, create_progress_frame, create_options_frame,
    create_buttons_frame, create_progress_bar_frame, create_log_frame
)
from services.ollama_service import OllamaService
from services.document_analyzer import DocumentAnalyzer
from services.translation import TranslationService
from utils.logging_utils import TextHandler
from utils.paddle_ocr_utils import check_paddleocr, show_paddleocr_install_guide

class PowerPointTranslatorApp:
    def __init__(self, root, debug_mode=False):
        # 기본 설정
        self.logger = logging.getLogger(__name__)
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(DEFAULT_WINDOW_SIZE)
        self.debug_mode = debug_mode
        
        # 서비스 초기화
        self.ollama_service = OllamaService()
        
        # 변수 초기화
        self.ppt_path = None
        self.translation_thread = None
        self.translation_running = False
        self.start_time = 0
        self.translated_items_count = 0
        self.total_text_elements = 0
        self.total_image_elements = 0
        self.total_elements = 0
        self.text_elements = []
        self.image_elements = []
        self.timer_running = False
        self.timer_id = None
        self.elapsed_time = 0
        self.estimated_total_time = 0
        self.models_initialized = False
        
        # UI 초기화
        self.init_ui()
        
        # 초기 상태 확인
        self.check_ollama_status()
        self.check_paddleocr_status()  # Tesseract 확인 제거, PaddleOCR만 확인
        
        self.logger.info(f"애플리케이션 초기화 완료 (디버그 모드: {debug_mode})")
    
    def init_ui(self):
        """UI 컴포넌트 초기화"""
        # 프레임 컴포넌트 생성
        self.top_frame = create_top_frame(self.root)
        self.file_frame, self.file_path_var, self.file_path_entry = create_file_frame(
            self.root, self.select_file
        )
        
        # 서버 상태 프레임
        self.server_status_frame, server_components = create_server_status_frame(
            self.root, self.check_ollama_status, self.check_paddleocr_status
        )
        self.ollama_installed_label = server_components["ollama_installed_label"]
        self.ollama_running_label = server_components["ollama_running_label"]
        self.ollama_port_label = server_components["ollama_port_label"]
        self.paddleocr_status_label = server_components["paddleocr_status_label"]
        
        # 정보 프레임
        self.info_progress_frame = tk.Frame(self.root)
        self.info_progress_frame.grid(row=3, column=0, columnspan=2, padx=DEFAULT_PADDING, pady=DEFAULT_PADDING, sticky="ew")
        self.info_progress_frame.columnconfigure(0, weight=1)
        self.info_progress_frame.columnconfigure(1, weight=1)
        
        # 파일 정보 프레임
        self.info_frame, info_labels = create_info_frame(self.info_progress_frame)
        self.file_name_label = info_labels["file_name_label"]
        self.slide_count_label = info_labels["slide_count_label"]
        self.text_count_label = info_labels["text_count_label"]
        self.image_count_label = info_labels["image_count_label"]
        self.total_elements_label = info_labels["total_elements_label"]
        
        # 진행 상태 프레임
        self.progress_frame, progress_labels = create_progress_frame(self.info_progress_frame)
        self.current_slide_label = progress_labels["current_slide_label"]
        self.current_task_label = progress_labels["current_task_label"]
        self.translated_items_label = progress_labels["translated_items_label"]
        self.remaining_items_label = progress_labels["remaining_items_label"]
        
        # 번역 옵션 프레임
        self.options_frame, options_components = create_options_frame(self.root, SUPPORTED_LANGUAGES)
        self.source_lang = options_components["source_lang"]
        self.target_lang = options_components["target_lang"]
        self.text_model_var = options_components["text_model_var"]
        self.text_model_combo = options_components["text_model_combo"]        
        # 번역 시작/중지 버튼
        self.buttons_frame, self.start_button, self.stop_button = create_buttons_frame(
            self.root, self.start_translation, self.stop_translation
        )
        
        # 진행바 프레임
        self.progress_bar_frame, self.progress_var, self.progress_bar, self.progress_label = create_progress_bar_frame(self.root)
        
        # 상태 레이블
        self.status_label = tk.Label(self.root, text="준비 완료")
        self.status_label.grid(row=7, column=0, columnspan=2, padx=DEFAULT_PADDING, pady=3, sticky="w")
        
        # 로그 프레임
        self.log_frame, self.log_text = create_log_frame(self.root)
        
        # GUI에 로그 출력을 위한 핸들러 추가
        self.text_handler = TextHandler(self.log_text)
        self.text_handler.setLevel(logging.INFO)
        self.text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(self.text_handler)
        
        # 파일 경로 변경 감지
        self.file_path_var.trace_add("write", self.on_file_path_change)
    
    def on_file_path_change(self, *args):
        """파일 경로 변경 시 버튼 색상 업데이트"""
        if self.file_path_var.get().strip():
            self.start_button.config(fg="black")
        else:
            self.start_button.config(fg="white")
    
    def select_file(self):
        """파일 선택 다이얼로그 열기"""
        file_path = filedialog.askopenfilename(
            filetypes=[("PowerPoint 파일", "*.pptx"), ("모든 파일", "*.*")]
        )
        if file_path:
            self.ppt_path = file_path
            self.file_path_var.set(file_path)
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
    
    # def check_tesseract_status(self):
    #     """Tesseract OCR 설치 상태 확인"""
    #     status, kor_available, jpn_available = check_tesseract()
        
    #     if status:
    #         self.tesseract_status_label.config(
    #             text=f"Tesseract OCR: 설치됨",
    #             fg="green"
    #         )
            
    #         # 언어 설치 상태 업데이트
    #         lang_status = f"언어 설치 상태: KOR: {'있음' if kor_available else '없음'}, JPN: {'있음' if jpn_available else '없음'}"
    #         self.tesseract_lang_label.config(
    #             text=lang_status, 
    #             fg="green" if (kor_available and jpn_available) else "orange"
    #         )
            
    #         # 언어 팩이 없는 경우 안내 메시지 표시
    #         if not (kor_available and jpn_available):
    #             self.root.after(1000, self.show_language_pack_missing_warning)
                
    #         return True
    #     else:
    #         self.tesseract_status_label.config(text="Tesseract OCR: 설치되지 않음", fg="red")
    #         self.tesseract_lang_label.config(text="언어 설치 상태: 확인 불가", fg="red")
            
    #         # 미설치 상태일 때 사용자에게 즉시 안내 메시지 표시
    #         self.root.after(1000, self.show_tesseract_missing_warning)
    #         return False

    def check_paddleocr_status(self):
        """PaddleOCR 설치 상태 확인"""
        status = check_paddleocr()
        
        if status:
            self.paddleocr_status_label.config(
                text=f"PaddleOCR: 설치됨",
                fg="green"
            )
            return True
        else:
            self.paddleocr_status_label.config(text="PaddleOCR: 설치되지 않음", fg="red")
            # 미설치 상태일 때 사용자에게 즉시 안내 메시지 표시
            self.root.after(1000, self.show_paddleocr_missing_warning)
            return False
    
    def show_paddleocr_missing_warning(self):
        """PaddleOCR 미설치 경고 메시지 표시"""
        from tkinter import messagebox
        
        response = messagebox.showerror(
            "PaddleOCR 미설치",
            "이 프로그램은 PaddleOCR이 필요합니다.\n"
            "프로그램을 계속 사용하려면 다음 명령어로 설치하세요:\n\n"
            "pip install paddlepaddle -U\n"
            "pip install paddleocr -U\n\n"
            "설치 방법을 확인하시겠습니까?",
            icon='error'
        )
        
        if response == 'yes':
            show_paddleocr_install_guide()
            self.root.quit()
        
    # def show_language_pack_missing_warning(self):
    #     """언어 팩 미설치 경고 메시지 표시"""
    #     from tkinter import messagebox
    #     from utils.tesseract_utils import show_tesseract_install_guide
        
    #     missing_langs = []
    #     status, kor_available, jpn_available = check_tesseract()
        
    #     if not kor_available:
    #         missing_langs.append("한국어(KOR)")
    #     if not jpn_available:
    #         missing_langs.append("일본어(JPN)")
        
    #     if missing_langs:
    #         messagebox.showwarning(
    #             "언어 팩 미설치",
    #             f"Tesseract OCR은 설치되어 있지만, 필요한 언어 데이터({', '.join(missing_langs)})가 설치되어 있지 않습니다.\n" + 
    #             "언어 데이터가 없으면 해당 언어의 이미지 텍스트 인식이 제대로 작동하지 않을 수 있습니다.\n\n" +
    #             "언어 데이터 설치 방법을 확인하시겠습니까?"
    #         )
    #         show_tesseract_install_guide()
    
    # def show_tesseract_missing_warning(self):
    #     """Tesseract 미설치 경고 메시지 표시"""
    #     from utils.tesseract_utils import show_tesseract_install_guide
    #     show_tesseract_install_guide()
    
    def check_ollama_status(self):
        """Ollama 상태 확인"""
        # 설치 확인
        installed = self.ollama_service.is_installed()
        self.ollama_installed_label.config(
            text=f"Ollama 설치 상태: {'설치됨' if installed else '설치되지 않음'}",
            fg="green" if installed else "red"
        )
        
        if not installed:
            self.show_ollama_install_guide()
            return False
        
        # 실행 상태 확인
        running, port = self.ollama_service.is_running()
        self.ollama_running_label.config(
            text=f"Ollama 실행 상태: {'실행 중' if running else '실행되지 않음'}",
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
            
            # 최초 실행 시에만 모델 목록 업데이트
            if not self.models_initialized:
                self.update_models_list()
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
            import webbrowser
            webbrowser.open("https://ollama.com/download")
    
    def update_models_list(self):
        """설치된 모델 목록 가져오기 및 UI 업데이트"""
        try:
            # 현재 선택된 모델 저장
            current_text_model = self.text_model_var.get()
            
            # 모델 목록 가져오기
            text_models = self.ollama_service.get_text_models()
            
            # UI 업데이트
            if text_models:
                self.text_model_combo['values'] = text_models
                if current_text_model in text_models:
                    self.text_model_var.set(current_text_model)
                elif "gemma3:12b" in text_models:
                    self.text_model_var.set("gemma3:12b")
                else:
                    self.text_model_var.set(text_models[0])
            else:
                self.text_model_combo['values'] = ["모델 없음"]
                self.text_model_var.set("모델 없음")
                self.prompt_install_base_models()
            
            return text_models
            
        except Exception as e:
            self.logger.exception(f"모델 목록 가져오기 오류: {e}")
            self.text_model_combo['values'] = ["모델 없음"]
            self.text_model_var.set("모델 없음")
            return []
    
    def prompt_install_base_models(self):
        """기본 모델 설치 권유"""
        response = messagebox.askquestion(
            "기본 모델 설치",
            "사용 가능한 모델이 없습니다. 기본 모델(gemma3:12b)을 설치하시겠습니까?",
            icon='info'
        )
        
        if response == 'yes':
            self.status_label.config(text="기본 모델 설치 중...")
            threading.Thread(target=self.install_base_models, daemon=True).start()
    
    def install_base_models(self):
        """기본 모델 설치"""
        try:
            # Gemma 3:12b 설치
            self.ollama_service.install_model("gemma3:12b")
            
            # 모델 목록 업데이트
            self.update_models_list()
            
            self.status_label.config(text="모델 설치 완료")
            messagebox.showinfo("설치 완료", "기본 모델 설치가 완료되었습니다.")
        except Exception as e:
            self.status_label.config(text=f"모델 설치 오류: {str(e)}")
            messagebox.showerror("설치 오류", f"모델 설치 중 오류가 발생했습니다: {str(e)}")
    
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
            
            # 경과 시간만 업데이트
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
        text_model = self.text_model_var.get()
        
        if "모델 없음" in text_model:
            response = messagebox.askquestion(
                "번역 모델 없음",
                "텍스트 번역을 위한 모델이 없습니다. 모델을 설치한 후 다시 시도하시겠습니까?",
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
        
        # 버튼 상태 변경
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 번역 서비스 초기화
        translation_service = TranslationService(self.ollama_service)
        
        # 번역 스레드 시작
        self.translation_running = True
        self.start_time = time.time()
        
        # 타이머 시작
        self.timer_running = True
        self.update_timer()
        
        # 번역 스레드 시작
        self.translation_thread = threading.Thread(
            target=self.translation_process,
            args=(translation_service, self.debug_mode)
        )
        self.translation_thread.daemon = True
        self.translation_thread.start()
    
    def stop_translation(self):
        """번역 프로세스 중지"""
        self.translation_running = False
        self.timer_running = False  # 타이머 중지
        self.status_label.config(text="번역 중지 중...")
        self.logger.info("사용자에 의한 번역 중지")
    
    def translation_process(self, translation_service, debug_mode=False):
        """번역 프로세스 실행"""
        output_path = None
        
        try:
            # 옵션 가져오기
            source_lang = self.source_lang.get()
            target_lang = self.target_lang.get()
            text_model = self.text_model_var.get()
            
            self.logger.info(f"번역 설정: {source_lang} → {target_lang}, 모델: {text_model}")
            
            # 번역 옵션
            options = {
                "source_lang": source_lang,
                "debug_mode": debug_mode
            }
            
            # 번역 서비스 호출
            output_path = translation_service.translate_ppt(
                self.ppt_path, 
                source_lang, 
                target_lang, 
                text_model,
                self.update_progress,
                self.update_status,
                options
            )
            
            # 타이머 중지
            self.timer_running = False
            
            # 완료 메시지 - 메인 스레드에서 실행
            elapsed_time = time.time() - self.start_time
            final_elapsed_time = elapsed_time
            
            # 메인 스레드에서 메시지 박스 표시
            self.root.after(0, lambda: self.show_completion_message(output_path, final_elapsed_time))
            
        except Exception as e:
            # 타이머 중지
            self.timer_running = False
            self.logger.exception(f"번역 프로세스 오류: {str(e)}")
            
            # 오류 메시지 - 메인 스레드에서 실행
            error_msg = str(e)
            self.root.after(0, lambda: self.show_error_message(error_msg))
            
        finally:
            self.translation_running = False
            self.timer_running = False
            
            # 버튼 상태 변경 - 메인 스레드에서 실행
            self.root.after(0, self.reset_ui_after_translation)
            
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
        
    def show_error_message(self, error_msg):
        """오류 메시지 표시 (메인 스레드에서 실행)"""
        self.status_label.config(text=f"번역 오류: {error_msg}")
        messagebox.showerror("오류", f"번역 중 오류가 발생했습니다: {error_msg}")
        
    def reset_ui_after_translation(self):
        """번역 후 UI 상태 초기화 (메인 스레드에서 실행)"""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)