@echo off
echo 🛠️ 개발 환경 설정 중...

echo 1️⃣ 가상환경 활성화...
call .venv\Scripts\activate.bat

echo 2️⃣ 의존성 확인...
pip list | findstr uvicorn > nul
if errorlevel 1 (
    echo ⚠️ uvicorn이 설치되지 않았습니다. 설치 중...
    pip install uvicorn
)

echo 3️⃣ 서버 시작...
echo.
echo 🚀 개발 서버가 시작됩니다.
echo 📍 URL: http://localhost:9010
echo 🔄 자동 리로드 활성화
echo ⏹️  종료하려면 Ctrl+C를 누르세요
echo ----------------------------------------

uvicorn backend.main.main:app --host 0.0.0.0 --port 9010 --reload
