# 📊 공수 산정 관리 시스템

> **RAG(Retrieval-Augmented Generation) 기반 AI 공수 산정 질의응답 시스템**

과거 프로젝트 데이터를 학습하여 새로운 기능 개발에 필요한 공수를 자동으로 산정하고, 사용자 피드백을 통해 지속적으로 답변 품질을 개선하는 지능형 시스템입니다.

---

## 🎯 주요 기능

### 1. **AI 기반 공수 산정 질의응답**
- GPT-4o-mini + MMR(Maximum Marginal Relevance) 검색으로 정확하고 다양한 답변 제공
- 프롬프트 엔지니어링을 통한 답변 품질 최적화
- 키워드 매칭 및 도메인 특화 검색

### 2. **사용자 피드백 시스템**
- **웹**: 긍정/부정 피드백 버튼
- **Slack**: 이모지 반응 (👍 긍정, 👎 부정)
- 피드백 기반 답변 우선 검색 (매우 유사한 질문에 한함)
- 피드백 데이터 자동 인덱싱 및 벡터 DB 저장

### 3. **Slack 봇 통합**
- 실시간 멘션 및 DM 기반 질의응답
- 이모지 피드백 자동 수집
- Slack 메시지 전처리 (멘션, 링크, 포맷 제거)

### 4. **카테고리 분류 시스템**
- TF-IDF + Naive Bayes 기반 자동 분류
- 대/중/소분류 구조
- Excel 업로드를 통한 카테고리 관리
- 카테고리 변경 시 기존 데이터 자동 재분류 (엄격한 매칭)

### 5. **통계 및 모니터링**
- 주간 긍정 피드백 비율 그래프 (세로 막대형)
- 전체 데이터 수, Story Points, 평균 공수 통계
- QA 로깅 (Slack, Web 분리)

---

## 🛠️ 기술 스택

### **Backend**
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **Uvicorn**: ASGI 웹 서버
- **LangChain**: AI 체인 및 RAG 구현
- **OpenAI GPT-4o-mini**: LLM 모델

### **Database & Search**
- **Chroma DB**: 벡터 데이터베이스 (메인 DB + 피드백 DB)
- **MMR 검색**: k=12, fetch_k=40 (다양성과 관련성 균형)
- **JSON 파일 저장**: 피드백 및 QA 로깅

### **Integration**
- **Slack SDK**: Slack 봇 연동 및 이벤트 처리
- **Jira API**: Jira Epic 데이터 동기화 (티켓 기반 공수 수집)
- **scikit-learn**: 카테고리 분류 (TF-IDF, Multinomial NB)

### **Frontend**
- HTML5, CSS3, JavaScript (Vanilla)
- 실시간 차트 렌더링

---

## 📍 접속 정보

### **운영 서버**
- **웹 인터페이스**: http://211.63.24.116:9010/effort-management/effort-management.html
- **API 문서**: http://211.63.24.116:9010/docs

### **로컬 개발**
- **웹 인터페이스**: http://localhost:9010/effort-management/effort-management.html
- **API 문서**: http://localhost:9010/docs

> 💡 **참고**: `/docs`는 FastAPI가 자동으로 생성하는 Swagger UI 기반 API 문서 페이지입니다.

---

## 🚀 빠른 시작

### 1. **환경 설정**

```bash
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. **환경변수 설정**

`.env` 파일을 생성하고 다음 내용을 입력:

```env
OPENAI_API_KEY=your_openai_api_key_here
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_SIGNING_SECRET=your_slack_signing_secret
SLACK_APP_TOKEN=xapp-your-slack-app-token
```

### 3. **서버 실행**

#### **Windows (개발 환경)**
```cmd
bin\dev.bat
```

#### **Linux (운영 환경)**
```bash
chmod +x bin/*.sh
bin/run.sh
```

### 4. **서버 상태 확인**

```bash
# Linux만 지원
bin/status.sh
```

---

## 📁 프로젝트 구조

```
enomix-effort/
├── backend/
│   ├── api/
│   │   └── api.py                  # FastAPI 엔드포인트
│   ├── services/
│   │   ├── effort_qa.py            # QA 체인 (RAG)
│   │   ├── effort_estimation.py    # 공수 산정 로직
│   │   ├── category_classifier.py  # 카테고리 분류
│   │   ├── jira_integration.py     # Jira 연동
│   │   └── mock_qa.py              # Mock QA
│   ├── data/
│   │   └── database.py             # Chroma DB 관리, 피드백 저장
│   ├── utils/
│   │   ├── config.py               # 설정 관리
│   │   ├── slack.py                # Slack 봇 처리
│   │   └── utils.py                # 공통 유틸리티
│   ├── main/
│   │   └── main.py                 # 서버 진입점
│   └── tests/
│       └── test_env.py             # 환경 테스트
├── frontend/
│   ├── effort-management/          # 공수 관리 웹 UI
│   │   ├── effort-management.html
│   │   ├── effort-management.js
│   │   └── effort-management.css
│   └── category-management/        # 카테고리 관리 웹 UI
│       ├── category-management.html
│       ├── category-management.js
│       └── category-management.css
├── data/
│   ├── chroma_db/                  # 메인 벡터 DB
│   ├── feedback_chroma_db/         # 피드백 벡터 DB
│   ├── docs/
│   │   ├── categories.json         # 카테고리 정보
│   │   ├── effort_estimations.json # 공수 산정 데이터
│   │   ├── positive_feedback.json  # 긍정 피드백
│   │   ├── negative_feedback.json  # 부정 피드백
│   │   ├── slack_qa_mapping.json   # Slack QA 로그
│   │   └── web_qa_mapping.json     # Web QA 로그
│   └── prompts/
│       ├── intent_classification.py
│       └── examples/
├── bin/
│   ├── dev.bat                     # Windows 개발용 스크립트
│   ├── run.sh                      # Linux 실행 스크립트
│   ├── stop.sh                     # Linux 종료 스크립트
│   ├── restart.sh                  # Linux 재시작 스크립트
│   └── status.sh                   # Linux 상태 확인 스크립트
├── logs/
│   ├── app.log                     # 애플리케이션 로그
│   └── uvicorn_YYYYMMDD.log        # Uvicorn 일별 로그
├── USER_MANUAL.md                  # 사용자 매뉴얼
├── ADMIN_MANUAL.md                 # 운영자 매뉴얼
├── requirements.txt                # Python 의존성
├── env.example                     # 환경변수 템플릿
└── README.md                       # 이 파일
```

---

## 🛠️ 서버 관리 명령어

### **Windows (개발 환경)**
```cmd
bin\dev.bat        # 서버 시작
# Ctrl + C로 종료
```

### **Linux (운영 환경)**
```bash
bin/run.sh         # 서버 시작 (백그라운드)
bin/stop.sh        # 서버 종료
bin/restart.sh     # 서버 재시작
bin/status.sh      # 서버 상태 확인
```

---

## 📖 매뉴얼

- **[사용자 매뉴얼](USER_MANUAL.md)**: 시스템 사용법 (공수 조회, 피드백 등)
- **[운영자 매뉴얼](ADMIN_MANUAL.md)**: 서버 관리, Slack 설정, 데이터 관리

---

## 🔑 주요 파라미터

### **QA 체인 (RAG)**
- **LLM**: `gpt-4o-mini`
- **검색 방식**: `MMR` (Maximum Marginal Relevance)
- **메인 검색**: `k=12`, `fetch_k=40`
- **피드백 검색**: `k=3`, `fetch_k=10`

### **서버**
- **포트**: `9010`
- **외부 IP**: `211.63.24.116`
- **프로토콜**: HTTP (SSL 미사용)

---

## 📦 패키지 의존성

### **핵심 패키지**
- `fastapi` - 웹 프레임워크
- `uvicorn` - ASGI 서버
- `langchain`, `langchain-openai`, `langchain-community` - AI 체인
- `chromadb` - 벡터 데이터베이스
- `openai` - OpenAI API

### **통합 및 유틸리티**
- `slack-sdk` - Slack 연동
- `python-dotenv` - 환경변수 관리
- `scikit-learn` - 머신러닝 (카테고리 분류)
- `python-multipart` - 파일 업로드

### **전체 설치**
```bash
pip install -r requirements.txt
```

---

## 🧪 테스트

```bash
# 환경 테스트
python backend/tests/test_env.py
```

---

## 📝 라이선스

Copyright © 2025 Enomix. All rights reserved.

---

## 📧 문의

- **개발팀**: E팀 이형기
