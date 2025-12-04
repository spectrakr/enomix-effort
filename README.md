# 📊 공수 산정 관리 시스템

## 🚀 서버 관리 명령어

### **Windows 개발 환경**
```cmd
bin\start.bat      # 서버 시작
bin\stop.bat       # 서버 종료
bin\restart.bat    # 서버 재시작
bin\status.bat     # 서버 상태 확인
bin\dev.bat        # 개발용 통합 스크립트
```

### **리눅스 서버 배포**
```bash
# 실행 권한 부여 (최초 1회)
chmod +x bin/*.sh

# 서버 관리
bin/start.sh     # 서버 시작
bin/stop.sh      # 서버 종료
bin/restart.sh   # 서버 재시작
bin/status.sh    # 서버 상태 확인
```

## 📁 프로젝트 구조

```
enomix-qa-main/
├── 📁 backend/                    # 백엔드
│   ├── 📁 api/                   # API 레이어
│   ├── 📁 services/              # 비즈니스 로직
│   ├── 📁 data/                  # 데이터 레이어
│   ├── 📁 utils/                 # 유틸리티
│   ├── 📁 tests/                 # 테스트
│   └── 📁 main/                  # 메인 실행 파일
│       └── main.py               # 서버 진입점
├── 📁 frontend/                  # 프론트엔드
│   └── 📁 static/                # 정적 파일
├── 📁 data/                      # 데이터 저장소
│   ├── 📁 json/                  # JSON 데이터
│   ├── 📁 chroma_db/             # 벡터 DB
│   ├── 📁 docs/                  # 문서
│   └── 📁 prompts/               # AI 프롬프트 관리
│       ├── intent_classification.py
│       └── examples/             # 프롬프트 예시 데이터
├── 📁 bin/                        # 실행 스크립트
│   ├── start.sh                   # 서버 시작 (Linux)
│   ├── stop.sh                    # 서버 종료 (Linux)
│   ├── restart.sh                 # 서버 재시작 (Linux)
│   ├── status.sh                  # 서버 상태 확인 (Linux)
│   ├── start.bat                  # 서버 시작 (Windows)
│   ├── stop.bat                   # 서버 종료 (Windows)
│   ├── restart.bat                # 서버 재시작 (Windows)
│   ├── status.bat                 # 서버 상태 확인 (Windows)
│   └── dev.bat                    # 개발용 통합 스크립트 (Windows)
```

## 🔧 개발 환경 설정

1. **가상환경 생성**
```bash
python -m venv .venv
```

2. **가상환경 활성화**
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

3. **의존성 설치**
```bash
# 기본 패키지 설치
pip install uvicorn fastapi

# AI 및 벡터 데이터베이스 패키지
pip install langchain langchain-openai langchain-community chromadb

# 웹 스크래핑 및 HTTP 요청
pip install requests beautifulsoup4

# 환경변수 관리 및 Slack 연동
pip install python-dotenv slack-sdk

# 또는 한 번에 설치
pip install uvicorn fastapi langchain langchain-openai langchain-community chromadb python-dotenv requests beautifulsoup4 slack-sdk python-multipart
```

4. **서버 실행**
```bash
# Windows
bin\start.bat

# Linux
bin/start.sh
```

## 📦 설치된 패키지 목록

### **핵심 패키지**
- **uvicorn**: ASGI 웹 서버
- **fastapi**: 고성능 웹 프레임워크
- **python-dotenv**: 환경변수 관리

### **AI 및 벡터 데이터베이스**
- **langchain**: AI 체인 프레임워크
- **langchain-openai**: OpenAI 연동
- **langchain-community**: 커뮤니티 도구
- **chromadb**: 벡터 데이터베이스

### **웹 및 통신**
- **requests**: HTTP 요청 라이브러리
- **beautifulsoup4**: HTML 파싱
- **slack-sdk**: Slack API 연동
- **python-multipart**: FastAPI form data 처리

## 📍 접속 URL

- **웹 인터페이스**: http://localhost:7070
- **API 문서**: http://localhost:7070/docs

## 🛠️ 서버 관리

### **Windows 개발 환경**
- **시작**: `bin\start.bat` 또는 `bin\dev.bat`
- **종료**: `Ctrl + C` 또는 `bin\stop.bat`
- **재시작**: `bin\restart.bat`
- **상태 확인**: `bin\status.bat`

### **리눅스 서버 배포**
- **시작**: `bin/start.sh`
- **종료**: `bin/stop.sh`
- **재시작**: `bin/restart.sh`
- **상태 확인**: `bin/status.sh`

### **PyCharm에서 실행 (권장)**
1. **Run → Edit Configurations**
2. **Script path**: `backend/main/main.py`
3. **Working directory**: 프로젝트 루트
4. **Python interpreter**: `.venv\Scripts\python.exe` 선택
5. **Run 버튼 클릭**

## 🔧 개발 환경 설정

### **가상환경 활성화**
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### **패키지 설치**
```bash
# 전체 패키지 한 번에 설치
pip install uvicorn fastapi langchain langchain-openai langchain-community chromadb python-dotenv requests beautifulsoup4 slack-sdk python-multipart
```

### **환경변수 설정**
`.env` 파일을 생성하고 다음 변수들을 설정하세요:
```env
OPENAI_API_KEY=your_openai_api_key_here
SLACK_BOT_TOKEN=your_slack_bot_token_here
```
