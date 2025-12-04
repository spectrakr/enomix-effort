#!/bin/bash

APP_DIR="/home/spectra/enomix-effort"
PID_FILE="$APP_DIR/uvicorn.pid"
DATE=$(date +%Y%m%d)
DAILY_LOG_FILE="$APP_DIR/logs/uvicorn_${DATE}.log"

cd "$APP_DIR"

echo "📊 서버 상태 확인"
echo "=================="

if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE")
  if ps -p "$PID" > /dev/null 2>&1; then
    echo "✅ 서버 실행 중"
    echo "🆔 PID: $PID"
    echo "📁 작업 디렉토리: $APP_DIR"
    echo "📝 일별 로그: $DAILY_LOG_FILE"
    
    # 포트 확인
    if command -v netstat >/dev/null 2>&1; then
      echo "🌐 포트 상태:"
      netstat -tlnp | grep ":9010" || echo "   포트 9010이 열려있지 않습니다."
    fi
    
    # 최근 로그 확인
    if [ -f "$DAILY_LOG_FILE" ]; then
      echo "📝 최근 로그 (마지막 5줄):"
      tail -5 "$DAILY_LOG_FILE"
    fi
  else
    echo "❌ 서버가 실행 중이 아닙니다 (PID 파일은 존재하지만 프로세스 없음)"
    rm -f "$PID_FILE"
  fi
else
  echo "❌ 서버가 실행 중이 아닙니다 (PID 파일 없음)"
fi
