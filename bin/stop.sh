#!/bin/bash

APP_DIR="/home/spectra/enomix-effort"
PID_FILE="$APP_DIR/uvicorn.pid"

cd "$APP_DIR"

if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE")
  if ps -p "$PID" > /dev/null 2>&1; then
    echo "🛑 서버 종료 중... PID: $PID"
    kill "$PID"
    sleep 2
    
    # 강제 종료 확인
    if ps -p "$PID" > /dev/null 2>&1; then
      echo "⚠️ 강제 종료 중..."
      kill -9 "$PID"
    fi
    
    echo "✅ 서버가 종료되었습니다."
  else
    echo "ℹ️ 서버가 실행 중이 아닙니다."
  fi
  rm -f "$PID_FILE"
else
  echo "ℹ️ PID 파일이 없습니다. 서버가 실행 중이 아닙니다."
fi
