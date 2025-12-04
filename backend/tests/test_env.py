#!/usr/bin/env python3
"""
환경 변수 및 API 키 확인 스크립트
"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def check_env_variables():
    """환경 변수 확인"""
    print("🔍 환경 변수 확인 중...")
    
    # OpenAI API 키 확인
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print(f"✅ OpenAI API Key: {openai_key[:10]}...{openai_key[-4:]}")
    else:
        print("❌ OpenAI API Key가 설정되지 않았습니다.")
    
    # Slack 설정 확인
    slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
    slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")
    
    if slack_bot_token:
        print(f"✅ Slack Bot Token: {slack_bot_token[:10]}...{slack_bot_token[-4:]}")
    else:
        print("⚠️ Slack Bot Token이 설정되지 않았습니다.")
    
    if slack_signing_secret:
        print(f"✅ Slack Signing Secret: {slack_signing_secret[:10]}...{slack_signing_secret[-4:]}")
    else:
        print("⚠️ Slack Signing Secret이 설정되지 않았습니다.")
    
    # Jira 설정 확인
    jira_url = os.getenv("JIRA_URL")
    jira_username = os.getenv("JIRA_USERNAME")
    jira_api_token = os.getenv("JIRA_API_TOKEN")
    
    if jira_url and jira_username and jira_api_token:
        print(f"✅ Jira URL: {jira_url}")
        print(f"✅ Jira Username: {jira_username}")
        print(f"✅ Jira API Token: {jira_api_token[:10]}...{jira_api_token[-4:]}")
    else:
        print("⚠️ Jira 설정이 완전하지 않습니다.")
        if not jira_url:
            print("  - JIRA_URL 누락")
        if not jira_username:
            print("  - JIRA_USERNAME 누락")
        if not jira_api_token:
            print("  - JIRA_API_TOKEN 누락")

def test_openai_connection():
    """OpenAI API 연결 테스트"""
    print("\n🤖 OpenAI API 연결 테스트...")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # 간단한 테스트 요청
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        
        print("✅ OpenAI API 연결 성공!")
        print(f"   응답: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"❌ OpenAI API 연결 실패: {str(e)}")
        if "quota" in str(e).lower():
            print("   💡 OpenAI API 할당량을 확인해주세요.")
        elif "api_key" in str(e).lower():
            print("   💡 OpenAI API 키를 확인해주세요.")

def test_slack_connection():
    """Slack API 연결 테스트"""
    print("\n💬 Slack API 연결 테스트...")
    
    try:
        import requests
        
        bot_token = os.getenv("SLACK_BOT_TOKEN")
        if not bot_token:
            print("⚠️ Slack Bot Token이 없습니다.")
            return
        
        # Slack API 테스트
        response = requests.get(
            "https://slack.com/api/auth.test",
            headers={"Authorization": f"Bearer {bot_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                print("✅ Slack API 연결 성공!")
                print(f"   봇 이름: {data.get('user')}")
                print(f"   팀 이름: {data.get('team')}")
            else:
                print(f"❌ Slack API 오류: {data.get('error')}")
        else:
            print(f"❌ Slack API 연결 실패: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Slack API 연결 실패: {str(e)}")

def test_jira_connection():
    """Jira API 연결 테스트"""
    print("\n🔧 Jira API 연결 테스트...")
    
    try:
        import requests
        
        jira_url = os.getenv("JIRA_URL")
        username = os.getenv("JIRA_USERNAME")
        api_token = os.getenv("JIRA_API_TOKEN")
        
        if not all([jira_url, username, api_token]):
            print("⚠️ Jira 설정이 완전하지 않습니다.")
            return
        
        # Jira API 테스트
        response = requests.get(
            f"{jira_url}/rest/api/3/myself",
            auth=(username, api_token),
            headers={"Accept": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Jira API 연결 성공!")
            print(f"   사용자: {data.get('displayName')}")
            print(f"   이메일: {data.get('emailAddress')}")
        else:
            print(f"❌ Jira API 연결 실패: HTTP {response.status_code}")
            print(f"   응답: {response.text}")
            
    except Exception as e:
        print(f"❌ Jira API 연결 실패: {str(e)}")

if __name__ == "__main__":
    print("🚀 공수 산정 관리 시스템 연동 확인")
    print("=" * 50)
    
    check_env_variables()
    test_openai_connection()
    test_slack_connection()
    test_jira_connection()
    
    print("\n" + "=" * 50)
    print("✅ 연동 확인 완료!")

