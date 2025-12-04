import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Directory settings
# 환경 변수로 Chroma DB 경로를 설정할 수 있음 (로컬/서버 구분용)
CHROMA_DIR = os.getenv("CHROMA_DIR", "./data/chroma_db")
DOCS_DIR = "./data/docs"
STATIC_DIR = "./frontend"
LOG_DIR = "./logs"

# Create directories if they don't exist
for directory in [CHROMA_DIR, DOCS_DIR, STATIC_DIR, LOG_DIR]:
    os.makedirs(directory, exist_ok=True)

# API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

# Logging configuration
# 로그 파일 경로는 api.py에서 동적으로 생성
# - 기동 로그: app_startup_YYYYMMDD_HHMMSS.log (매번 초기화)
# - 일별 로그: app_YYYYMMDD.log (날짜별 누적) 