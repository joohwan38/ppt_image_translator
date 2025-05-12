import os
import platform
import subprocess
import time
import requests
import psutil
import json
import logging
import base64
import shutil
from typing import Tuple, List, Dict, Optional, Any, Union

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self, url: str = "http://localhost:11434"):
        self.url = url
        self.connect_timeout = 5
        self.read_timeout = 30
        
        # 비전 모델 키워드 목록
        self.vision_keywords = ["llava", "bakllava", "vision", "vl", "multimodal", "visual"]
    
    def is_installed(self) -> bool:
        """Ollama 설치 여부 확인"""
        try:
            if shutil.which('ollama'):
                return True
                
            system = platform.system()
            if system == "Windows":
                return os.path.exists("C:\\Program Files\\Ollama\\ollama.exe") or \
                       os.path.exists(os.path.expanduser("~\\AppData\\Local\\Ollama\\ollama.exe"))
            elif system == "Darwin":
                return os.path.exists("/usr/local/bin/ollama") or \
                       os.path.exists("/opt/homebrew/bin/ollama")
            elif system == "Linux":
                result = subprocess.run(["which", "ollama"], capture_output=True, text=True)
                return result.returncode == 0
            
            return False
        except Exception as e:
            logger.error(f"Ollama 설치 확인 오류: {e}")
            return False
    
    def is_running(self) -> Tuple[bool, Optional[str]]:
        """Ollama 실행 상태 및 포트 확인"""
        try:
            # API 호출로 확인
            try:
                response = requests.get(f"{self.url}/api/tags", timeout=self.connect_timeout)
                if response.status_code == 200:
                    port = self.url.split(':')[-1]
                    return True, port
            except requests.RequestException:
                pass
            
            # 프로세스로 확인
            for proc in psutil.process_iter(['pid', 'name']):
                proc_name = proc.info.get('name', '').lower()
                if proc_name and 'ollama' in proc_name:
                    return True, "11434"
            
            return False, None
        except Exception as e:
            logger.exception(f"Ollama 상태 확인 오류: {e}")
            return False, None
    
    def start_ollama(self) -> bool:
        """Ollama 서버 시작"""
        try:
            logger.info("Ollama 시작 시도")
            
            # 플랫폼별 실행 방식
            if platform.system() == "Windows":
                proc = subprocess.Popen(
                    ["ollama", "serve"],
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                proc = subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            # 시작 대기
            for attempt in range(1, 11):
                time.sleep(1)
                running, _ = self.is_running()
                if running:
                    logger.info(f"Ollama 시작 성공 (시도: {attempt})")
                    return True
            
            logger.warning("Ollama 시작 실패: 시간 초과")
            return False
        except Exception as e:
            logger.error(f"Ollama 시작 오류: {e}")
            return False
    
    def get_models_list(self) -> Tuple[List[str], List[str]]:
        """설치된 모델 목록 가져오기"""
        text_models = []
        vision_models = []
        
        try:
            # API로 모델 목록 가져오기
            try:
                response = requests.get(f"{self.url}/api/tags", timeout=self.connect_timeout)
                
                if response.status_code == 200:
                    models_data = response.json()
                    if 'models' in models_data:
                        all_models = [model['name'] for model in models_data['models']]
                        
                        # 모델 분류 - 이름 기반 분류
                        for model_name in all_models:
                            # 강제 지정 모델 확인
                            if model_name in ["llava", "llama3.2-vision"]:
                                vision_models.append(model_name)
                                continue
                                
                            # 이름에 비전 키워드가 있으면 비전 모델로 분류
                            if any(keyword in model_name.lower() for keyword in self.vision_keywords):
                                vision_models.append(model_name)
                            else:
                                text_models.append(model_name)
                        
                        return text_models, vision_models
            except Exception:
                pass
            
            # 명령행 방식으로 시도
            try:
                result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=False)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        all_models = [line.split()[0] for line in lines[1:] if line.split()]
                        
                        # 모델 분류
                        for model in all_models:
                            if model in ["llava", "llama3.2-vision"] or \
                               any(keyword in model.lower() for keyword in self.vision_keywords):
                                vision_models.append(model)
                            else:
                                text_models.append(model)
                        
                        return text_models, vision_models
            except Exception:
                pass
            
            return [], []
            
        except Exception as e:
            logger.exception(f"모델 목록 가져오기 오류: {e}")
            return [], []
    
    def extract_text_from_image(self, image_base64: str, model_name: str) -> str:
        """Vision 모델을 사용하여 이미지에서 텍스트 추출"""
        response = None
        try:
            logger.info(f"Vision API 호출 시작: {model_name}")
            
            # 이미지 크기 확인 및 제한
            if len(image_base64) > 1000000:  # 약 1MB 제한
                logger.warning(f"이미지 크기가 너무 큽니다: {len(image_base64)} 바이트")
                return "이미지 크기 초과"
            
            # 요청 데이터 준비
            request_data = {
                "model": model_name,
                "prompt": "Extract all visible text from this image. Only return the text, nothing else.",
                "images": [image_base64]
            }
            
            # 스트리밍 API 호출
            response = requests.post(
                f"{self.url}/api/generate",
                json=request_data,
                timeout=(self.connect_timeout, self.read_timeout),
                stream=True
            )
            
            if response.status_code == 200:
                # 스트리밍 응답 처리
                full_text = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            line_data = json.loads(line.decode('utf-8'))
                            if 'response' in line_data:
                                full_text += line_data['response']
                            
                            if line_data.get('done', False):
                                break
                        except json.JSONDecodeError:
                            pass
                
                logger.info(f"텍스트 추출 완료: {len(full_text)} 글자")
                return full_text.strip()
            else:
                logger.error(f"Vision API 오류 (HTTP {response.status_code})")
                return f"API 오류: {response.status_code}"
            
        except requests.exceptions.ConnectTimeout:
            logger.error("Vision API 연결 타임아웃")
            return "연결 타임아웃"
        except requests.exceptions.ReadTimeout:
            logger.error("Vision API 응답 타임아웃")
            return "응답 타임아웃"
        except Exception as e:
            logger.exception(f"텍스트 추출 오류: {e}")
            return f"오류: {str(e)}"
        finally:
            # 리소스 정리
            if response is not None:
                try:
                    response.close()
                except:
                    pass
            
            # 메모리 정리 힌트
            import gc
            gc.collect()
    
    def translate_text(self, text: str, source_lang: str, target_lang: str, model: str) -> str:
        """텍스트 번역"""
        if not text or text.isspace():
            return text
        
        logger.debug(f"번역 시작: '{text[:50]}...'")
        
        # 번역 프롬프트 - 수정하지 않음
        prompt = f"You are a translator. Your role is to accurately translate the given {source_lang} text into {target_lang}. Do not provide any explanations, only the translated result. : {text}"
        
        try:
            # 스트리밍 API 호출
            response = requests.post(
                f"{self.url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True
                },
                timeout=(self.connect_timeout, self.read_timeout)
            )
            
            if response.status_code == 200:
                # 스트리밍 응답 처리
                translated_text = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            line_data = json.loads(line.decode('utf-8'))
                            if 'response' in line_data:
                                translated_text += line_data['response']
                            
                            if line_data.get('done', False):
                                break
                        except json.JSONDecodeError:
                            continue
                
                logger.info(f"번역 완료: '{text[:30]}...' → '{translated_text[:30]}...'")
                return translated_text.strip()
            else:
                logger.error(f"번역 API 오류 (HTTP {response.status_code})")
                return text
                
        except requests.exceptions.Timeout:
            logger.error("번역 API 타임아웃")
            return text
        except Exception as e:
            logger.exception(f"번역 오류: {e}")
            return text
    
    def install_model(self, model_name: str) -> bool:
        """모델 설치"""
        try:
            logger.info(f"{model_name} 설치 시작")
            
            result = subprocess.run(
                ["ollama", "pull", model_name], 
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                logger.info(f"{model_name} 설치 완료")
                return True
            else:
                logger.error(f"{model_name} 설치 실패: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"{model_name} 설치 오류: {e}")
            return False
    
    def check_ollama_model_status(self, model_name: str) -> Tuple[bool, Optional[Dict]]:
        """모델 상태 확인"""
        try:
            response = requests.post(
                f"{self.url}/api/show",
                json={"name": model_name},
                timeout=self.connect_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if "modelfile" in data:
                    logger.info(f"모델 {model_name} 로드됨")
                    return True, data
                else:
                    logger.warning(f"모델 {model_name} 아직 로드되지 않음")
                    return False, data
            else:
                logger.error(f"모델 상태 확인 실패: HTTP {response.status_code}")
                return False, None
        except Exception as e:
            logger.error(f"모델 상태 확인 오류: {e}")
            return False, None
    
    def warmup_vision_model(self, model_name: str) -> bool:
        """비전 모델 사전 로드 (비활성화)"""
        logger.info(f"모델 {model_name} 웜업 기능이 비활성화되었습니다")
        return True