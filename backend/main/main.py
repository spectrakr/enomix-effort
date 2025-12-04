"""
메인 실행 파일
새로운 폴더 구조에 맞춘 서버 실행
"""

import uvicorn
import os
from backend.api.api import app
from backend.data.database import index_json_data

def ensure_effort_data_indexed():
    """effort_estimations.json 파일이 벡터 DB에 인덱싱되었는지 확인하고 필요시 재인덱싱"""
    try:
        json_file_path = os.path.join("data", "docs", "effort_estimations.json")
        if os.path.exists(json_file_path):
            print("🔄 effort_estimations.json 파일 재인덱싱 중...")
            try:
                if index_json_data(json_file_path, force=True):
                    print("✅ effort_estimations.json 재인덱싱 완료")
                else:
                    print("❌ effort_estimations.json 재인덱싱 실패")
            except Exception as e:
                print(f"❌ 벡터 DB 재인덱싱 중 오류 발생: {e}")
                print("⚠️ 서버는 계속 시작되지만 인덱싱은 나중에 자동으로 시도됩니다.")
        else:
            print("⚠️ effort_estimations.json 파일을 찾을 수 없습니다")
    except Exception as e:
        print(f"❌ 벡터 DB 재인덱싱 오류: {e}")
        print("⚠️ 서버는 계속 시작되지만 인덱싱은 나중에 자동으로 시도됩니다.")

if __name__ == "__main__":
    # 서버 시작 전 벡터 DB 재인덱싱은 비활성화 (크래시 방지)
    # 인덱싱은 get_vectordb() 호출 시 자동으로 시도됩니다.
    # 필요시 아래 주석을 해제하여 활성화할 수 있습니다.
    # try:
    #     ensure_effort_data_indexed()
    # except Exception as e:
    #     print(f"⚠️ 인덱싱 초기화 중 오류 발생: {e}")
    #     print("⚠️ 서버는 계속 시작됩니다. 인덱싱은 get_vectordb() 호출 시 자동으로 시도됩니다.")
    
    # 환경 변수에서 설정 읽기
    port = int(os.getenv("PORT", 9010))
    host = os.getenv("HOST", "127.0.0.1")  # 기본값은 localhost
    reload = os.getenv("RELOAD", "true").lower() == "true"
    environment = os.getenv("ENVIRONMENT", "development")
    
    # 운영 환경에서는 보안을 위해 localhost만 허용
    if environment == "production":
        host = "127.0.0.1"
        reload = False
    
    print(f"🌍 환경: {environment}")
    print(f"🔗 서버 주소: http://{host}:{port}")
    print(f"🔄 리로드: {'활성화' if reload else '비활성화'}")
    
    uvicorn.run(
        "backend.api.api:app",
        host=host,
        port=port,
        reload=reload
    )
