# 공수산정기 운영자 매뉴얼

## 목차
1. [시스템 개요](#시스템-개요)
2. [시스템 설치 및 설정](#시스템-설치-및-설정)
3. [서버 관리](#서버-관리)
4. [데이터 관리](#데이터-관리)
5. [카테고리 관리](#카테고리-관리)
6. [피드백 데이터 관리](#피드백-데이터-관리)
7. [모니터링 및 로그](#모니터링-및-로그)
8. [문제 해결](#문제-해결)
9. [백업 및 복구](#백업-및-복구)
10. [시스템 최적화](#시스템-최적화)

---

## 시스템 개요

### 아키텍처

```
┌─────────────────────────────────────────────┐
│              사용자 인터페이스                │
├──────────────────┬──────────────────────────┤
│   웹 브라우저     │      슬랙 클라이언트      │
└────────┬─────────┴──────────┬───────────────┘
         │                    │
         v                    v
┌─────────────────────────────────────────────┐
│            FastAPI 서버 (Port 9010)         │
├─────────────────────────────────────────────┤
│  API Layer (api.py)                         │
│  - 공수 산정 엔드포인트                      │
│  - 피드백 수집                               │
│  - 데이터 관리                               │
├─────────────────────────────────────────────┤
│  Service Layer                              │
│  - effort_qa.py: QA 체인 실행               │
│  - category_classifier.py: 카테고리 분류     │
│  - jira_integration.py: Jira 연동           │
├─────────────────────────────────────────────┤
│  Data Layer (database.py)                   │
│  - Chroma DB 관리                           │
│  - 피드백 저장/검색                          │
│  - 문서 인덱싱                               │
└────────┬────────────────────┬───────────────┘
         │                    │
         v                    v
┌──────────────────┐  ┌──────────────────────┐
│   Chroma DB      │  │  JSON 파일 저장소     │
│   (벡터 DB)      │  │  - 공수 산정 데이터   │
│                  │  │  - 피드백 데이터       │
│  - 메인 DB       │  │  - 카테고리 정보       │
│  - 피드백 DB     │  └──────────────────────┘
└──────────────────┘
         │
         v
┌──────────────────────────────────────────────┐
│            OpenAI API (GPT-4o-mini)          │
│  - 임베딩 생성                                │
│  - 답변 생성                                  │
└──────────────────────────────────────────────┘
```

### 핵심 기술 스택

- **Backend**: Python 3.9+, FastAPI
- **AI/ML**: LangChain, OpenAI API (GPT-4o-mini)
- **Vector DB**: Chroma DB
- **Classification**: scikit-learn (TF-IDF + Naive Bayes)
- **Frontend**: HTML, CSS, JavaScript
- **Integration**: Jira API, Slack SDK

### 주요 구성 요소

1. **RAG (Retrieval-Augmented Generation)**
   - 벡터 DB에서 관련 문서 검색
   - GPT-4o-mini로 답변 생성

2. **MMR (Maximum Marginal Relevance)**
   - 다양성과 관련성 균형
   - k=12, fetch_k=40

3. **피드백 시스템**
   - 긍정/부정 피드백 수집
   - JSON 파일 + 벡터 DB 이중 저장
   - 빠른 검색을 위한 키워드 매칭

4. **카테고리 분류**
   - 로컬 ML 모델 (빠른 응답)
   - 대중소 3단계 분류

---

## 시스템 설치 및 설정

### 사전 요구사항

```bash
# Python 버전 확인
python --version  # 3.9 이상

# 필수 패키지 확인
pip list | grep -E "(fastapi|langchain|chromadb|openai)"
```

### 초기 설정

#### 1. 환경 변수 설정

```bash
# env.example 파일을 .env로 복사
cp env.example .env

# .env 파일 편집
nano .env
```

**필수 환경 변수:**

```env
# OpenAI API
OPENAI_API_KEY=sk-...

# Slack (선택)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_SIGNING_SECRET=...

# Jira (선택)
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=...

# 서버 설정
HOST=0.0.0.0
PORT=9010
```

#### 2. 의존성 설치

```bash
# 전체 패키지 설치
pip install -r requirements.txt

# 또는 최소 패키지만 설치
pip install -r requirements-minimal.txt
```

#### 3. SSL 인증서 생성 (선택사항)

**현재 HTTP만 사용 중이므로 생략 가능**

```bash
# HTTPS가 필요한 경우에만 실행
cd ssl
python make_ssl_data.py

# 생성된 파일 확인
ls -la
# cert.pem
# key.pem
```

#### 4. 디렉토리 구조 확인

```bash
tree -L 2
```

**예상 구조:**
```
enomix-effort/
├── backend/
│   ├── api/
│   ├── data/
│   ├── main/
│   ├── services/
│   └── utils/
├── data/
│   ├── chroma_db/
│   ├── docs/
│   └── prompts/
├── frontend/
│   ├── category-management/
│   └── effort-management/
├── logs/
├── bin/
└── .env
```

---

## 서버 관리

### 서버 시작

#### 방법 1: 스크립트 사용 (권장)

```bash
# 백그라운드로 서버 시작
./bin/run.sh

# 로그 확인
tail -f logs/app.log
tail -f logs/uvicorn_$(date +%Y%m%d).log
```

#### 방법 2: 직접 실행

```bash
# HTTP (9010 포트)
python -m backend.main.main

# HTTPS 포함 (필요 시)
python -m backend.main.main --ssl
```

### 서버 상태 확인

```bash
# 스크립트로 상태 확인
./bin/status.sh

# 또는 직접 확인
ps aux | grep uvicorn
netstat -tlnp | grep 9010
```

**출력 예시:**
```
✅ Uvicorn is running (PID: 12345)
   Port 9010: LISTENING
   Log file: logs/uvicorn_20241203.log (size: 1.2MB)
```

### 서버 중지

```bash
# 스크립트로 중지
./bin/stop.sh

# 또는 직접 중지
pkill -f uvicorn
```

### 서버 재시작

```bash
# 스크립트로 재시작
./bin/restart.sh

# 또는 수동으로
./bin/stop.sh
sleep 2
./bin/run.sh
```

### 프로세스 관리

#### systemd 서비스 등록 (Linux)

```bash
# 서비스 파일 생성
sudo nano /etc/systemd/system/effort-estimator.service
```

**내용:**
```ini
[Unit]
Description=Effort Estimator Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/enomix-effort
ExecStart=/path/to/enomix-effort/bin/run.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**서비스 관리:**
```bash
# 서비스 활성화
sudo systemctl enable effort-estimator

# 서비스 시작
sudo systemctl start effort-estimator

# 상태 확인
sudo systemctl status effort-estimator

# 로그 확인
sudo journalctl -u effort-estimator -f
```

---

## 데이터 관리

### 공수 산정 데이터

#### 데이터 형식

**JSON 파일 예시** (`data/docs/effort_estimations.json`):

```json
[
  {
    "ticket": "ENOMIX-123",
    "title": "로그인 기능 개발",
    "description": "사용자 인증 및 세션 관리...",
    "story_points": 5,
    "assignee": "홍길동",
    "major_category": "사용자 관리",
    "minor_category": "인증",
    "sub_category": "로그인",
    "source": "ENOMIX-123_로그인_기능_개발.json"
  }
]
```

#### 데이터 추가

**웹 인터페이스:**
1. `http://211.63.24.116:9010` 접속
2. "데이터 관리" 탭 선택
3. "새 데이터 추가" 클릭
4. 폼 작성 후 저장

**API 직접 호출:**
```bash
curl -X POST http://211.63.24.116:9010/effort/add/ \
  -H "Content-Type: application/json" \
  -d '{
    "ticket": "ENOMIX-123",
    "title": "로그인 기능 개발",
    "story_points": 5
  }'
```

**JSON 파일 직접 편집:**
```bash
# 파일 편집
nano data/docs/effort_estimations.json

# 벡터 DB 재인덱싱 필요
curl -X POST http://211.63.24.116:9010/effort/reindex/
```

#### 데이터 수정

```bash
# API로 수정
curl -X PUT http://211.63.24.116:9010/effort/update/ENOMIX-123 \
  -H "Content-Type: application/json" \
  -d '{
    "story_points": 7
  }'
```

#### 데이터 삭제

```bash
# API로 삭제
curl -X DELETE http://211.63.24.116:9010/effort/delete/ENOMIX-123
```

#### 벡터 DB 재인덱싱

```bash
# 전체 재인덱싱
curl -X POST http://211.63.24.116:9010/effort/reindex/

# 또는 Python으로
python -c "
from backend.data.database import index_all_documents
index_all_documents()
"
```

### Jira 연동

#### Jira 데이터 가져오기

```bash
# API로 Epic 조회
curl http://211.63.24.116:9010/jira/epics/

# Epic 상세 조회
curl http://211.63.24.116:9010/jira/epic/ENOMIX-123
```

#### 자동 동기화 설정

```bash
# cron 작업 추가
crontab -e
```

**매일 새벽 2시에 동기화:**
```cron
0 2 * * * cd /path/to/enomix-effort && curl -X POST http://211.63.24.116:9010/jira/sync/ >> logs/jira_sync.log 2>&1
```

---

## 카테고리 관리

### 카테고리 구조

```
대분류 (Major Category)
├── 중분류 (Minor Category)
│   ├── 소분류 (Sub Category)
│   └── 소분류 (Sub Category)
└── 중분류 (Minor Category)
```

### 카테고리 파일

**위치**: `data/docs/categories.json`

**형식:**
```json
{
  "사용자 관리": {
    "인증": ["로그인", "로그아웃", "2FA"],
    "권한": ["역할 관리", "권한 설정"]
  },
  "데이터 관리": {
    "조회": ["목록 조회", "상세 조회"],
    "등록": ["신규 등록", "일괄 등록"]
  }
}
```

### 카테고리 수정

#### 웹에서 수정

1. "카테고리 관리" 탭 접속
2. Excel 파일 업로드 또는 직접 편집
3. "저장" 클릭

#### Excel로 수정

**형식:**
```
대분류     | 중분류 | 소분류
-------------------------------
사용자 관리 | 인증   | 로그인
사용자 관리 | 인증   | 로그아웃
데이터 관리 | 조회   | 목록 조회
```

**업로드:**
```bash
curl -X POST http://211.63.24.116:9010/effort/categories/upload/ \
  -F "file=@categories.xlsx"
```

### 카테고리 변경 시 데이터 처리

**자동 마이그레이션 규칙:**
- 대중소 분류가 모두 일치: 유지
- 하나라도 불일치: 카테고리 초기화 (수동 재분류 필요)

**수동 재분류:**
```bash
# 미분류 데이터 조회
curl http://211.63.24.116:9010/effort/list/?uncategorized=true

# 데이터 재분류
curl -X PUT http://211.63.24.116:9010/effort/update/ENOMIX-123 \
  -H "Content-Type: application/json" \
  -d '{
    "major_category": "사용자 관리",
    "minor_category": "인증",
    "sub_category": "로그인"
  }'
```

---

## 피드백 데이터 관리

### 피드백 파일

**위치:**
- `data/docs/positive_feedback.json` (긍정 피드백)
- `data/docs/negative_feedback.json` (부정 피드백)

**형식:**
```json
[
  {
    "question": "로그인 기능 공수",
    "answer": "Jira 티켓: ENOMIX-123...",
    "sources": [...],
    "timestamp": "2024-12-03T10:30:00",
    "feedback_type": "positive",
    "source": "web",
    "user": "user123",
    "qa_hash": "abc123def456",
    "feedback_count": 3,
    "feedback_users": ["user1", "user2", "user3"],
    "first_feedback_time": "2024-12-01T09:00:00",
    "last_feedback_time": "2024-12-03T10:30:00"
  }
]
```

### 피드백 통계 조회

```bash
# 주간 긍정 피드백 비율
curl http://211.63.24.116:9010/effort/feedback-statistics/weekly-positive-ratio/
```

**응답:**
```json
{
  "12(1W)": 85.5,
  "12(2W)": 90.2,
  "12(3W)": 88.7
}
```

### 피드백 데이터 초기화

```bash
# 긍정 피드백 백업
cp data/docs/positive_feedback.json \
   data/docs/positive_feedback.json.bak$(date +%Y%m%d)

# 파일 삭제 (초기화)
rm data/docs/positive_feedback.json
rm -rf data/feedback_chroma_db/

# 서비스 재시작
./bin/restart.sh
```

### 피드백 벡터 DB 재인덱싱

```python
# Python에서 수동 실행
from backend.data.database import index_feedback_data
index_feedback_data("data/docs/positive_feedback.json")
```

---

## 모니터링 및 로그

### 로그 파일

#### 애플리케이션 로그

**위치**: `logs/app.log`

**로그 레벨:**
- `INFO`: 일반 정보
- `WARNING`: 경고 (처리 가능한 오류)
- `ERROR`: 오류 (처리 필요)

**주요 로그 패턴:**
```
🔍 QA 체인 시작: '로그인 기능 공수'
✅ 피드백 데이터에서 답변 발견: 로그인...
📊 피드백 카운트 증가: 로그인... (총 3회)
❌ 오류: ...
```

#### Uvicorn 로그

**위치**: `logs/uvicorn_YYYYMMDD.log`

**내용:**
- HTTP 요청/응답
- 서버 시작/종료
- 연결 오류

#### 로그 확인 명령어

```bash
# 실시간 로그 확인
tail -f logs/app.log

# 오류만 확인
grep "ERROR" logs/app.log

# 특정 질문 검색
grep "로그인 기능" logs/app.log

# 오늘 로그 통계
grep -c "QA 체인 시작" logs/app.log
```

### 로그 로테이션

```bash
# logrotate 설정
sudo nano /etc/logrotate.d/effort-estimator
```

**내용:**
```
/path/to/enomix-effort/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 your-user your-group
}
```

### 성능 모니터링

#### 시스템 리소스

```bash
# CPU, 메모리 확인
top -p $(pgrep -f uvicorn)

# 디스크 사용량
du -sh data/chroma_db/
du -sh data/docs/
```

#### API 응답 시간

```bash
# 응답 시간 측정
time curl -X POST http://211.63.24.116:9010/effort/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question": "로그인 기능 공수"}'
```

#### 벡터 DB 통계

```python
from backend.data.database import get_vectordb

vectordb = get_vectordb()
collection = vectordb.get()
print(f"총 문서 수: {len(collection['ids'])}")
```

---

## 문제 해결

### 일반적인 문제

#### 1. 서버가 시작되지 않음

**증상:**
```
Error: Address already in use
```

**해결:**
```bash
# 포트 사용 중인 프로세스 확인
lsof -i :9010

# 프로세스 종료
kill -9 <PID>

# 서버 재시작
./bin/run.sh
```

#### 2. OpenAI API 오류

**증상:**
```
❌ OpenAI API error: insufficient_quota
```

**해결:**
1. API 키 확인: `echo $OPENAI_API_KEY`
2. 사용량 확인: https://platform.openai.com/usage
3. 청구 정보 확인
4. 필요시 요금제 업그레이드

#### 3. 벡터 DB 오류

**증상:**
```
❌ Chroma DB error: Collection not found
```

**해결:**
```bash
# 벡터 DB 재생성
rm -rf data/chroma_db/
curl -X POST http://211.63.24.116:9010/effort/reindex/
```

#### 4. 슬랙 봇 미응답

**증상:**
슬랙에서 봇이 응답하지 않음

**해결:**
```bash
# 환경 변수 확인
echo $SLACK_BOT_TOKEN
echo $SLACK_APP_TOKEN

# 서버 로그 확인
grep "Slack" logs/app.log

# 슬랙 앱 설정 확인
# - Event Subscriptions 활성화
# - OAuth 권한 확인
# - Request URL 확인
```

#### 5. 답변이 너무 느림

**원인:**
- 첫 질문: 벡터 검색 + LLM 호출
- 피드백 후: 빠른 캐시 검색

**해결:**
```bash
# MMR k값 조정 (database.py)
k=8, fetch_k=30  # 기본 k=12에서 감소

# 또는 피드백 수집 강화
# → 사용자에게 피드백 요청
```

### 데이터베이스 문제

#### Chroma DB 손상

```bash
# 백업에서 복구
cp -r data/chroma_db.backup data/chroma_db

# 또는 재인덱싱
rm -rf data/chroma_db/
curl -X POST http://localhost:8000/effort/reindex/
```

#### JSON 파일 손상

```bash
# JSON 유효성 검사
python -m json.tool data/docs/effort_estimations.json

# 오류 시 백업에서 복구
cp data/docs/effort_estimations.json.bak20241203 \
   data/docs/effort_estimations.json
```

### 디버그 모드 실행

```bash
# 디버그 로그 활성화
export LOG_LEVEL=DEBUG

# 서버 재시작
./bin/restart.sh

# 상세 로그 확인
tail -f logs/app.log
```

---

## 백업 및 복구

### 백업 대상

1. **데이터 파일**
   - `data/docs/`
   - `data/chroma_db/`

2. **설정 파일**
   - `.env`
   - `data/docs/categories.json`

3. **로그 (선택)**
   - `logs/`

### 백업 스크립트

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/effort-estimator"
DATE=$(date +%Y%m%d_%H%M%S)

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR/$DATE

# 데이터 백업
cp -r data/docs $BACKUP_DIR/$DATE/
cp -r data/chroma_db $BACKUP_DIR/$DATE/
cp .env $BACKUP_DIR/$DATE/

# 압축
cd $BACKUP_DIR
tar -czf backup_$DATE.tar.gz $DATE/
rm -rf $DATE/

# 30일 이상 된 백업 삭제
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +30 -delete

echo "✅ 백업 완료: $BACKUP_DIR/backup_$DATE.tar.gz"
```

### 자동 백업 설정

```bash
# cron 추가
crontab -e

# 매일 새벽 3시 백업
0 3 * * * /path/to/backup.sh >> /path/to/backup.log 2>&1
```

### 복구 절차

```bash
# 서버 중지
./bin/stop.sh

# 백업 파일 압축 해제
cd /backup/effort-estimator
tar -xzf backup_20241203_030000.tar.gz

# 데이터 복구
cp -r 20241203_030000/docs/* /path/to/data/docs/
cp -r 20241203_030000/chroma_db/* /path/to/data/chroma_db/

# 서버 시작
./bin/run.sh

# 정상 동작 확인
curl http://211.63.24.116:9010/test/simple
```

---

## 시스템 최적화

### 성능 튜닝

#### 1. MMR 파라미터 조정

**현재 설정:** `k=12, fetch_k=40`

**조정 가이드:**
```python
# backend/services/effort_qa.py

# 정확도 우선 (느림)
retriever_kwargs = {"k": 15, "fetch_k": 50}

# 균형 (권장)
retriever_kwargs = {"k": 12, "fetch_k": 40}

# 속도 우선 (빠름)
retriever_kwargs = {"k": 8, "fetch_k": 30}
```

#### 2. 피드백 검색 최적화

피드백 데이터는 이미 최적화되어 있습니다:
- JSON 파일 직접 검색 (1단계)
- 벡터 DB 검색 (2단계)

#### 3. 프롬프트 최적화

```python
# 프롬프트 길이 확인
with open("backend/services/effort_qa.py") as f:
    content = f.read()
    prompt_start = content.find("template=")
    prompt_end = content.find('"""', prompt_start + 100)
    prompt_length = prompt_end - prompt_start
    print(f"프롬프트 길이: {prompt_length}자")
```

### 리소스 관리

#### 메모리 사용량 제한

```bash
# ulimit 설정
ulimit -v 4000000  # 4GB 제한
```

#### 동시 요청 제한

```python
# backend/main/main.py

# Uvicorn 설정
config = uvicorn.Config(
    app,
    host=HOST,
    port=PORT,
    workers=4,  # 워커 수 조정
    limit_concurrency=100  # 동시 요청 제한
)
```

### 데이터베이스 최적화

#### Chroma DB 정리

```bash
# 미사용 인덱스 제거
python -c "
from backend.data.database import get_vectordb
vectordb = get_vectordb()
# 정리 로직
"
```

#### JSON 파일 압축

```bash
# 주기적 압축
cd data/docs
gzip -k effort_estimations.json
```

---

## 보안 관리

### SSL/TLS 인증서

**현재 HTTP만 사용 중이므로 해당 없음**

#### HTTPS 설정이 필요한 경우

```bash
# Let's Encrypt 인증서 갱신 (자동)
certbot renew

# 수동 인증서 생성
cd ssl
python make_ssl_data.py
./bin/restart.sh
```

### API 키 관리

```bash
# 환경 변수 암호화
ansible-vault encrypt .env

# 복호화
ansible-vault decrypt .env
```

### 방화벽 설정

```bash
# UFW (Ubuntu)
sudo ufw allow 9010/tcp
sudo ufw enable
```

---

## 업데이트 및 유지보수

### 시스템 업데이트

```bash
# 코드 업데이트
git pull origin main

# 의존성 업데이트
pip install -r requirements.txt --upgrade

# 데이터베이스 마이그레이션
curl -X POST http://211.63.24.116:9010/effort/reindex/

# 서버 재시작
./bin/restart.sh
```

### 정기 점검 체크리스트

**일일:**
- [ ] 서버 상태 확인
- [ ] 로그 오류 확인
- [ ] 디스크 사용량 확인

**주간:**
- [ ] 백업 확인
- [ ] 성능 모니터링
- [ ] 피드백 통계 리뷰

**월간:**
- [ ] 시스템 업데이트
- [ ] 데이터베이스 최적화
- [ ] 보안 점검

---

## 긴급 상황 대응

### 서버 다운

```bash
# 1. 로그 확인
tail -n 100 logs/app.log

# 2. 프로세스 확인
ps aux | grep uvicorn

# 3. 포트 확인
netstat -tlnp | grep 8000

# 4. 서버 재시작
./bin/restart.sh

# 5. 헬스체크
curl http://211.63.24.116:9010/test/simple
```

### 데이터 손실

```bash
# 1. 최근 백업 확인
ls -lh /backup/effort-estimator/

# 2. 복구 실행
./restore.sh backup_20241203_030000.tar.gz

# 3. 검증
curl -X POST http://211.63.24.116:9010/effort/ask/ \
  -d '{"question": "test"}'
```

### OpenAI API 장애

```bash
# Mock QA 활성화 (코드 수정 필요)
# backend/services/effort_qa.py
USE_MOCK_QA = True
```

---

## 부록

### API 엔드포인트 목록

#### 공수 산정

- `POST /effort/ask/` - 질문하기
- `GET /effort/list/` - 데이터 목록
- `POST /effort/add/` - 데이터 추가
- `PUT /effort/update/{ticket}` - 데이터 수정
- `DELETE /effort/delete/{ticket}` - 데이터 삭제
- `POST /effort/reindex/` - 재인덱싱

#### 피드백

- `POST /effort/feedback/` - 피드백 저장
- `GET /effort/feedback-statistics/weekly-positive-ratio/` - 주간 통계

#### 카테고리

- `GET /effort/categories/` - 카테고리 조회
- `POST /effort/categories/upload/` - 카테고리 업로드
- `POST /effort/categories/migrate/` - 카테고리 마이그레이션

#### Jira 연동

- `GET /jira/epics/` - Epic 목록
- `GET /jira/epic/{epic_key}` - Epic 상세

#### 시스템

- `GET /test/simple` - 헬스체크
- `GET /` - 메인 페이지

### 설정 파일 예시

**categories.json:**
```json
{
  "사용자 관리": {
    "인증": ["로그인", "로그아웃", "회원가입"],
    "권한": ["역할 관리", "권한 설정"]
  }
}
```

**effort_estimations.json:**
```json
[
  {
    "ticket": "ENOMIX-123",
    "title": "로그인 기능 개발",
    "story_points": 5
  }
]
```

### 문의 및 지원

**기술 지원:**
- 이메일: [admin@company.com]
- 슬랙: #effort-estimator-support

**버그 리포트:**
- GitHub Issues: [repository-url]/issues

---

## 버전 정보

- **버전**: 1.0.0
- **최종 수정일**: 2024-12-03
- **문서 작성**: AI Assistant

---

**Happy Operating! 🚀**

