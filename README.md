# README.md

# PowerPoint 이미지 번역기 (개선 버전)

PowerPoint 파일 내의 텍스트 및 이미지 속 텍스트를 번역하는 도구입니다. 
이 개선 버전은 PaddleOCR을 통해 향상된 이미지 텍스트 인식 및 번역 기능을 제공합니다.

## 주요 기능

- PowerPoint 문서 내 텍스트 요소 (문단, 테이블 셀 등) 번역
- 이미지 내 텍스트 감지 및 자연스러운 번역
- 텍스트 위치, 폰트 크기, 색상, 회전 방향 등 스타일 보존
- PaddleOCR 기반의 정확한 텍스트 영역 감지
- OpenCV 인페인팅 기반의 자연스러운 텍스트 제거 및 재삽입

## 설치 방법

### 1. 기본 요구 사항

```bash
# 필수 패키지 설치
pip install -r requirements.txt
```

### 2. OCR 엔진 설치

#### Tesseract OCR 설치 (기본)

- Windows:
  - [Tesseract OCR 인스톨러](https://github.com/UB-Mannheim/tesseract/wiki) 다운로드 및 설치
  - 설치 시 '추가 언어 데이터' 옵션에서 Korean 및 Japanese 등 필요한 언어 선택

- macOS:
  ```bash
  brew install tesseract
  brew install tesseract-lang
  ```

- Linux:
  ```bash
  sudo apt-get install tesseract-ocr
  sudo apt-get install tesseract-ocr-kor tesseract-ocr-jpn
  ```

#### PaddleOCR 설치 (향상된 성능, 선택적)

```bash
pip install paddlepaddle -U
pip install paddleocr -U
```

### 3. 번역 엔진 설치

이 프로그램은 번역을 위해 Ollama 서비스를 사용합니다.

1. [Ollama 다운로드 페이지](https://ollama.com/download)에서 운영체제에 맞는 버전 설치
2. 번역 모델 설치 (프로그램 내에서 자동으로 설치하거나 아래 명령어 사용)
   ```bash
   ollama pull gemma3:12b
   ```

## 사용 방법

1. 프로그램 실행:
   ```bash
   python main.py
   ```

2. UI 화면에서 '찾아보기' 버튼을 클릭하여 PowerPoint 파일 선택

3. 원본 언어와 번역 언어, 번역 모델 선택

4. '번역 시작' 버튼 클릭

5. 번역이 완료되면 원본 파일 이름에 "_translated" 접미사가 붙은 새 파일이 생성됩니다.

## 주의 사항

- 이미지 번역 기능이 제대로 작동하려면 Tesseract OCR 또는 PaddleOCR이 설치되어 있어야 합니다.
- 번역 품질은 이미지 품질과 OCR 엔진 성능에 따라 달라질 수 있습니다.
- 대용량 이미지나 복잡한 레이아웃의 경우 정확한 번역이 어려울 수 있습니다.
- PaddleOCR 설치 시 첫 번째 실행에서 언어 모델이 자동으로 다운로드됩니다.

## 라이센스

MIT License