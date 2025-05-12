import os
import platform
import subprocess
import time
import requests
import psutil
import json
import logging

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self, url="http://localhost:11434"):
        self.url = url
    
    def is_installed(self):
        """Ollama 설치 여부 확인"""
        try:
            system = platform.system()
            if system == "Windows":
                return os.path.exists("C:\\Program Files\\Ollama\\ollama.exe") or \
                       os.path.exists(os.path.expanduser("~\\AppData\\Local\\Ollama\\ollama.exe"))
            elif system == "Darwin":  # macOS
                return os.path.exists("/usr/local/bin/ollama") or \
                       os.path.exists("/opt/homebrew/bin/ollama")
            elif system == "Linux":
                result = subprocess.run(["which", "ollama"], capture_output=True, text=True)
                return result.returncode == 0
            return False
        except Exception as e:
            logger.error(f"Ollama 설치 확인 오류: {e}")
            return False
    
    def is_running(self):
        """Ollama 실행 상태 및 포트 확인"""
        try:
            # API 호출 시도
            try:
                logger.debug(f"Ollama API 호출: {self.url}/api/tags")
                response = requests.get(f"{self.url}/api/tags", timeout=2)
                if response.status_code == 200:
                    port = self.url.split(':')[-1]
                    logger.debug(f"Ollama 실행 중: 포트 {port}")
                    return True, port
            except Exception as e:
                logger.debug(f"API 호출 실패: {e}")
                pass
            
            # 프로세스 확인
            for proc in psutil.process_iter(['pid', 'name']):
                if 'ollama' in proc.info['name'].lower():
                    logger.debug("Ollama 프로세스 발견")
                    return True, "11434"  # 기본 포트
            
            logger.debug("Ollama가 실행 중이 아님")
            return False, None
        except Exception as e:
            logger.exception(f"Ollama 실행 상태 확인 오류: {e}")
            return False, None
    
    def start_ollama(self):
        """Ollama 시작"""
        try:
            logger.info("Ollama 시작 시도")
            
            if platform.system() == "Windows":
                subprocess.Popen(["ollama", "serve"], shell=True, creationflags=subprocess.DETACHED_PROCESS)
            else:  # macOS 또는 Linux
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Ollama가 시작될 때까지 대기
            for _ in range(10):  # 최대 10초 대기
                time.sleep(1)
                running, _ = self.is_running()
                if running:
                    logger.info("Ollama 시작 성공")
                    return True
            
            logger.warning("Ollama 시작 실패: 시간 초과")
            return False
        except Exception as e:
            logger.error(f"Ollama 시작 오류: {e}")
            return False
    
    def install_model(self, model_name):
        """모델 설치"""
        try:
            logger.info(f"{model_name} 설치 시작")
            
            if platform.system() == "Windows":
                subprocess.run(["ollama", "pull", model_name], shell=True, check=True)
            else:  # macOS 또는 Linux
                subprocess.run(["ollama", "pull", model_name], check=True)
            
            logger.info(f"{model_name} 설치 완료")
            return True
        except Exception as e:
            logger.error(f"{model_name} 설치 오류: {e}")
            return False
    
    def get_models_list(self):
        """설치된 모델 목록 가져오기"""
        try:
            text_models = []
            vision_models = []
            
            # API로 모델 목록 가져오기
            logger.debug(f"모델 목록 가져오기: {self.url}/api/tags")
            response = requests.get(f"{self.url}/api/tags", timeout=5)
            if response.status_code == 200:
                models_data = response.json()
                if 'models' in models_data:
                    all_models = [model['name'] for model in models_data['models']]
                    logger.debug(f"발견된 모델: {all_models}")
                    
                    # 모델 분류
                    for model in all_models:
                        if any(vm in model.lower() for vm in ["llava", "bakllava", "vision", "vl", "multimodal"]):
                            vision_models.append(model)
                        else:
                            text_models.append(model)
                    
                    return text_models, vision_models
            
            # API 방식이 실패한 경우 명령행 방식 시도
            if platform.system() != "Windows":
                logger.debug("명령행으로 모델 목록 가져오기 시도")
                result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:  # 헤더 제외
                        all_models = []
                        for line in lines[1:]:
                            parts = line.split()
                            if parts:
                                all_models.append(parts[0])
                        
                        logger.debug(f"명령행으로 발견된 모델: {all_models}")
                        
                        # 모델 분류
                        for model in all_models:
                            if any(vm in model.lower() for vm in ["llava", "bakllava", "vision", "vl", "multimodal"]):
                                vision_models.append(model)
                            else:
                                text_models.append(model)
                        
                        return text_models, vision_models
            
            # 모두 실패한 경우 빈 목록 반환
            logger.warning("모델 목록을 가져올 수 없음")
            return [], []
            
        except Exception as e:
            logger.exception(f"모델 목록 가져오기 오류: {e}")
            return [], []
    
    # services/ollama_service.py 파일 내 extract_text_from_image 메소드 수정
    def extract_text_from_image(self, image_base64, model_name):
        """Vision 모델을 사용하여 이미지에서 텍스트 추출 (시간 측정 추가)"""
        try:
            # 단계 1: API 요청 준비 시간 측정
            prep_start = time.time()
            
            # API 요청 JSON 준비
            request_data = {
                "model": model_name,
                "prompt": "Extract all visible text from this image. Only return the text, nothing else.",
                "images": [image_base64]
            }
            
            prep_end = time.time()
            logger.debug(f"API 요청 준비 시간: {prep_end - prep_start:.3f}초")
            
            # 단계 2: 네트워크 연결 및 요청 전송 시간 측정
            conn_start = time.time()
            logger.info(f"Vision API 호출 시작: {model_name}")
            
            # 연결 타임아웃과 읽기 타임아웃 분리
            session = requests.Session()
            response = session.post(
                f"{self.url}/api/generate",
                json=request_data,
                timeout=(10, 120)  # (연결 타임아웃 10초, 읽기 타임아웃 120초)
            )
            
            conn_end = time.time()
            logger.debug(f"API 요청 전송 및 응답 수신 시간: {conn_end - conn_start:.3f}초")
            
            # 응답 처리
            if response.status_code == 200:
                # 단계 3: 응답 처리 시간 측정
                process_start = time.time()
                
                result = response.json()
                if 'response' in result:
                    extracted_text = result['response'].strip()
                    logger.info(f"추출된 텍스트 길이: {len(extracted_text)} 글자")
                    
                    process_end = time.time()
                    logger.debug(f"응답 처리 시간: {process_end - process_start:.3f}초")
                    
                    # 전체 소요 시간 기록
                    total_time = process_end - prep_start
                    logger.info(f"텍스트 추출 전체 소요 시간: {total_time:.3f}초")
                    
                    return extracted_text
                else:
                    logger.error(f"API 응답에 'response' 필드 없음: {result}")
                    return ""
            else:
                logger.error(f"Vision API 오류 (HTTP {response.status_code}): {response.text}")
                return ""
                
        except requests.exceptions.ConnectTimeout:
            logger.error("Vision API 연결 타임아웃 (서버 연결 실패)")
            return ""
        except requests.exceptions.ReadTimeout:
            logger.error("Vision API 읽기 타임아웃 (응답 대기 시간 초과)")
            return ""
        except Exception as e:
            logger.exception(f"텍스트 추출 오류: {e}")
            return ""

    # services/ollama_service.py 파일에 새 메소드 추가
    def check_ollama_model_status(self, model_name):
        """Ollama 모델 상태 확인 (로드 여부, 메모리 사용량 등)"""
        try:
            response = requests.get(f"{self.url}/api/show", 
                                params={"name": model_name},
                                timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"모델 상태: {data}")
                
                # 모델이 이미 로드되었는지 확인
                if "modelfile" in data:
                    logger.info(f"모델 {model_name} 로드됨")
                    return True, data
                else:
                    logger.warning(f"모델 {model_name} 아직 로드되지 않음")
                    return False, data
            else:
                logger.error(f"모델 상태 확인 실패: {response.status_code}")
                return False, None
        except Exception as e:
            logger.exception(f"모델 상태 확인 오류: {e}")
            return False, None
        
    # services/ollama_service.py 파일에 새 메소드 추가
    def warmup_vision_model(self, model_name):
        """비전 모델 사전 로드 및 웜업"""
        logger.info(f"모델 {model_name} 웜업 시작")
        
        try:
            # 간단한 테스트 이미지 생성 (1x1 픽셀 투명 이미지)
            from PIL import Image
            import io
            
            test_img = Image.new('RGBA', (1, 1), (255, 255, 255, 0))
            img_byte = io.BytesIO()
            test_img.save(img_byte, format='PNG')
            img_byte.seek(0)
            
            test_base64 = base64.b64encode(img_byte.read()).decode('utf-8')
            
            # 웜업 요청 (짧은 타임아웃으로 실제 응답은 기다리지 않음)
            logger.info("웜업 요청 전송")
            try:
                requests.post(
                    f"{self.url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": "Warmup request",
                        "images": [test_base64]
                    },
                    timeout=2
                )
            except requests.exceptions.Timeout:
                # 타임아웃은 예상된 결과 - 모델 로드만 되면 됨
                logger.info("웜업 요청 타임아웃 (정상)")
            
            logger.info(f"모델 {model_name} 웜업 완료")
            return True
        except Exception as e:
            logger.exception(f"모델 웜업 오류: {e}")
            return False
    
    def translate_text(self, text, source_lang, target_lang, model):
        """Text 모델을 사용하여 텍스트 번역"""
        if not text or text.isspace():
            return text
        
        logger.debug(f"번역 시작: '{text[:50]}...'")
        
        # 번역 프롬프트
        prompt = f"You are a translator. Your role is to accurately translate the given {source_lang} text into {target_lang}. Do not provide any explanations, only the translated result. : {text}"
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30  # 30초 타임아웃
            )
            
            elapsed = time.time() - start_time
            logger.debug(f"번역 API 응답 시간: {elapsed:.2f}초")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    translated_text = result.get("response", "").strip()
                    
                    logger.info(f"번역 완료: '{text[:30]}...' → '{translated_text[:30]}...'")
                    return translated_text
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 파싱 오류: {e}")
                    return text
            else:
                logger.error(f"번역 API 오류 (HTTP {response.status_code}): {response.text[:100]}")
                return text
        except requests.exceptions.Timeout:
            logger.error("번역 API 타임아웃")
            return text
        except Exception as e:
            logger.exception(f"번역 오류: {e}")
            return text