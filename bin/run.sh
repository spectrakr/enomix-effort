#!/bin/bash

APP_MODULE="backend.api.api:app"
APP_DIR="/home/spectra/enomix-effort"  # HOME 경로 직접 지정
PYTHON_BIN="python3"
# 로그 파일 설정
LOG_FILE="$APP_DIR/logs/uvicorn.log"
PID_FILE="$APP_DIR/uvicorn.pid"

cd "$APP_DIR"

# 기존 실행 중이면 종료
if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE")
  if ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️ 이미 실행 중입니다. PID: $PID"
    echo "🔄 기존 프로세스를 종료하고 재시작합니다..."
    kill "$PID"
    sleep 2
  fi
  rm -f "$PID_FILE"
fi

# 로그 디렉토리 생성
mkdir -p "$APP_DIR/logs"

echo "🚀 서버 시작 중..."
echo "📍 URL: http://0.0.0.0:9010"
echo "📁 작업 디렉토리: $APP_DIR"
echo "📝 로그 파일: $LOG_FILE"
echo "⏹️  종료하려면 Ctrl+C를 누르세요"
echo "----------------------------------------"

# 가상환경 활성화 (존재하는 경우)
if [ -f ".venv/bin/activate" ]; then
    echo "🐍 가상환경 활성화 중..."
    source .venv/bin/activate
    
    # Rust 환경 변수 설정
    source ~/.cargo/env
    export PATH="$HOME/.cargo/bin:$PATH"
    export RUSTUP_HOME="$HOME/.rustup"
    export CARGO_HOME="$HOME/.cargo"
    
    # 환경 변수 확인
    echo "🔧 Rust 환경 변수 설정 완료"
    echo "📍 Rust 경로: $(which rustc)"
    echo "📍 Cargo 경로: $(which cargo)"
fi

# Python 경로 설정
export PYTHONPATH="${PYTHONPATH}:$APP_DIR"

# 현재 디렉토리를 Python 경로에 추가
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 가상환경의 site-packages 경로 추가
if [ -d ".venv/lib/python3.10/site-packages" ]; then
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/.venv/lib/python3.10/site-packages"
fi

# Python 경로 확인
echo "🔍 Python 경로 설정:"
echo "📍 PYTHONPATH: $PYTHONPATH"

# 환경 변수 설정
export ENVIRONMENT=production
export HOST=0.0.0.0
export PORT=9010
export RELOAD=false

# 의존성 확인
echo "📦 의존성 확인 중..."
python3 -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 필요한 패키지가 설치되지 않았습니다."
    echo "💡 다음 명령어를 실행하세요: pip install fastapi uvicorn"
    exit 1
fi

# langchain 패키지 확인
echo "🔍 langchain 패키지 확인 중..."
# 실제 코드에서 사용하는 langchain_classic.chains를 체크
python3 -c "from langchain_classic.chains import RetrievalQA; print('✅ langchain_classic.chains OK')" 2>/dev/null
if [ $? -ne 0 ]; then
    # langchain_classic이 없으면 langchain.chains도 체크 (하위 호환성)
    python3 -c "from langchain.chains import RetrievalQA; print('✅ langchain.chains OK (fallback)')" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "❌ langchain.chains 또는 langchain_classic.chains 모듈을 찾을 수 없습니다."
        echo "💡 다음 명령어를 실행하세요: pip install langchain-classic 또는 pip install langchain"
        exit 1
    fi
fi

python3 -c "from langchain_openai import ChatOpenAI; print('✅ ChatOpenAI OK')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ ChatOpenAI 모듈을 찾을 수 없습니다."
    echo "💡 다음 명령어를 실행하세요: pip install langchain-openai"
    exit 1
fi

# 서버 시작
echo "🚀 Uvicorn 서버 시작..."

# 환경 변수 설정 (서버 실행 전)
source ~/.cargo/env
export PATH="$HOME/.cargo/bin:$PATH"
export RUSTUP_HOME="$HOME/.rustup"
export CARGO_HOME="$HOME/.cargo"

# 환경 변수 확인
echo "🔧 환경 변수 확인:"
echo "📍 Rust 경로: $(which rustc 2>/dev/null || echo 'NOT FOUND')"
echo "📍 Cargo 경로: $(which cargo 2>/dev/null || echo 'NOT FOUND')"
echo "📍 Python 경로: $(which python3)"
echo "📍 PYTHONPATH: $PYTHONPATH"

# 서버 시작 (백그라운드 실행, nohup)
nohup "$PYTHON_BIN" -m uvicorn "$APP_MODULE" --host 0.0.0.0 --port 9010 --log-level info --access-log >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "✅ 서버가 백그라운드로 시작되었습니다."
echo "📝 로그 확인: tail -f $LOG_FILE"
echo "🛑 서버 종료: kill \$(cat $PID_FILE)"
