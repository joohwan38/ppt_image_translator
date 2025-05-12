ppt_image_translator/
├── main.py                  # 메인 진입점
├── utils/
│   ├── __init__.py
│   ├── logging_utils.py     # 로깅 관련 기능
│   └── image_utils.py       # 이미지 처리 유틸리티
├── services/
│   ├── __init__.py
│   ├── ollama_service.py    # Ollama 관련 기능
│   ├── document_analyzer.py # 문서 분석 기능
│   └── translator.py        # 번역 처리 로직
└── ui/
    ├── __init__.py
    └── app.py               # UI 컴포넌트