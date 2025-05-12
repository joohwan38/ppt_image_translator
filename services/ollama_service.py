# services/ollama_service.py
import os
import platform
import subprocess
import time
import requests
import psutil
import json
import logging
import shutil
from typing import Tuple, List, Optional

from config import DEFAULT_OLLAMA_URL, OLLAMA_CONNECT_TIMEOUT, OLLAMA_READ_TIMEOUT

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self, url: str = DEFAULT_OLLAMA_URL):
        self.url = url
        self.connect_timeout = OLLAMA_CONNECT_TIMEOUT
        self.read_timeout = OLLAMA_READ_TIMEOUT
        
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
            logger.error(f"Ollama 상태 확인 오류: {e}")
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
    
    def get_text_models(self) -> List[str]:
        """설치된 텍스트 모델 목록 가져오기"""
        models = []
        
        try:
            # API로 모델 목록 가져오기
            try:
                response = requests.get(f"{self.url}/api/tags", timeout=self.connect_timeout)
                
                if response.status_code == 200:
                    models_data = response.json()
                    if 'models' in models_data:
                        models = [model['name'] for model in models_data['models']]
                        return models
            except Exception:
                pass
            
            # 명령행 방식으로 시도
            try:
                result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=False)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        models = [line.split()[0] for line in lines[1:] if line.split()]
                        return models
            except Exception:
                pass
            
            return models
            
        except Exception as e:
            logger.error(f"모델 목록 가져오기 오류: {e}")
            return []
    
    def translate_text(self, text: str, source_lang: str, target_lang: str, model: str) -> str:
        """텍스트 번역"""
        if not text or text.isspace():
            return text
        
        logger.debug(f"번역 시작: '{text[:50]}...' ({source_lang} → {target_lang})")
        
        # 번역 프롬프트
        prompt = f"You are a translator. Your role is to accurately translate the given {source_lang} text into {target_lang}. Do not provide any explanations, only the translated result. : {text}"
        
        response = None
        try:
            # API 호출
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
            logger.error(f"번역 오류: {e}")
            return text
        finally:
            # 리소스 정리
            if response is not None:
                response.close()
    
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