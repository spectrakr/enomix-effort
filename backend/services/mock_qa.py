"""
OpenAI API 할당량 초과 시 사용할 모의 QA 시스템
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def mock_qa_response(question: str) -> Dict[str, Any]:
    """모의 QA 응답 생성"""
    
    # 사전 필터링: 명확히 무의미한 입력들
    question_clean = question.strip()
    
    # 1. 빈 문자열이나 공백만 있는 경우
    if not question_clean:
        return {
            "question": question,
            "answer": "죄송합니다. 공수 산정 데이터를 기반으로 답변할 수 없는 질문입니다. 공수 산정, 개발 기간, Story Points 등과 관련된 질문을 해주세요.",
            "sources": [{"source": "시스템 메시지", "page": "N/A", "content": "빈 질문"}]
        }
    
    # 2. 숫자만 있는 경우 (111, 2222, 12345 등)
    if question_clean.isdigit():
        return {
            "question": question,
            "answer": "죄송합니다. 공수 산정 데이터를 기반으로 답변할 수 없는 질문입니다. 공수 산정, 개발 기간, Story Points 등과 관련된 질문을 해주세요.",
            "sources": [{"source": "시스템 메시지", "page": "N/A", "content": "숫자만 있는 질문"}]
        }
    
    # 3. 무의미한 문자 반복 (aaa, bbb, asdf 등)
    if len(question_clean) <= 5 and question_clean.isalpha() and len(set(question_clean)) <= 2:
        return {
            "question": question,
            "answer": "죄송합니다. 공수 산정 데이터를 기반으로 답변할 수 없는 질문입니다. 공수 산정, 개발 기간, Story Points 등과 관련된 질문을 해주세요.",
            "sources": [{"source": "시스템 메시지", "page": "N/A", "content": "무의미한 문자 반복"}]
        }
    
    # 4. 특수문자나 기호만 있는 경우
    if all(not c.isalnum() for c in question_clean):
        return {
            "question": question,
            "answer": "죄송합니다. 공수 산정 데이터를 기반으로 답변할 수 없는 질문입니다. 공수 산정, 개발 기간, Story Points 등과 관련된 질문을 해주세요.",
            "sources": [{"source": "시스템 메시지", "page": "N/A", "content": "특수문자만 있는 질문"}]
        }
    
    # 5. 한글 자음만 있는 경우 (ㄻㄹㄷㅁㄹ 등)
    if question_clean and all(ord('ㄱ') <= ord(c) <= ord('ㅎ') for c in question_clean):
        return {
            "question": question,
            "answer": "죄송합니다. 공수 산정 데이터를 기반으로 답변할 수 없는 질문입니다. 공수 산정, 개발 기간, Story Points 등과 관련된 질문을 해주세요.",
            "sources": [{"source": "시스템 메시지", "page": "N/A", "content": "한글 자음만 있는 질문"}]
        }
    
    # 간단한 키워드 기반 의도 판단 (Mock에서는 단순화)
    effort_keywords = [
        '공수', '산정', '개발시간', '작업시간', '예상시간', '소요시간', '걸릴까', '얼마나', 
        'story', 'point', '개발', '기능', '작업', '프로그래밍', '코딩', '시스템', '앱', '웹', 
        '서버', '데이터베이스', 'API', '메세지', '삭제', '채팅', '알림', '푸시', '결제', 
        '로그인', '회원가입', '인증', '시간', '기간', '프로젝트', '구현', '설계', '만들기',
        '상담사', '상담', '고객', '서비스'
    ]
    is_effort_question = any(keyword in question.lower() for keyword in effort_keywords)
    
    # 명확히 관련 없는 키워드들만 체크 (Mock에서는 최소한만)
    clearly_unrelated = ['안녕', 'hello', 'hi', '날씨', '음식', '게임', '영화', '음악', '스포츠', '정치', '경제']
    is_clearly_unrelated = any(keyword in question.lower() for keyword in clearly_unrelated)
    
    if is_clearly_unrelated:
        return {
            "question": question,
            "answer": "죄송합니다. 공수 산정 데이터를 기반으로 답변할 수 없는 질문입니다. 공수 산정, 개발 기간, Story Points 등과 관련된 질문을 해주세요.",
            "sources": [{"source": "시스템 메시지", "page": "N/A", "content": "공수 산정과 관련 없는 질문"}]
        }
    
    if is_effort_question:
        # 공수 산정 관련 모의 응답 (Story Points 기반)
        mock_effort_data = [
            {
                "jira_ticket": "ENOMIX-123",
                "title": "로그인 기능",
                "story_points": 5,
                "estimation_reason": "기존 인증 로직 재사용",
                "tech_stack": ["React", "Node.js", "JWT"],
                "team_member": "김개발",
                "description": "사용자 인증 시스템 구현. JWT 토큰 기반 인증, 세션 관리, 비밀번호 암호화 기능 포함",
                "created_date": "2024-01-15"
            },
            {
                "jira_ticket": "ENOMIX-124",
                "title": "결제 처리",
                "story_points": 8,
                "estimation_reason": "외부 API 연동 복잡도",
                "tech_stack": ["Spring Boot", "MySQL", "Redis"],
                "team_member": "박개발",
                "description": "PG사 연동 결제 시스템. 카드/계좌이체 지원, 결제 실패 처리, 환불 기능, 결제 내역 관리",
                "created_date": "2024-02-01"
            },
            {
                "jira_ticket": "ENOMIX-125",
                "title": "푸시 알림",
                "story_points": 3,
                "estimation_reason": "기존 푸시 서비스 활용",
                "tech_stack": ["Firebase", "Node.js"],
                "team_member": "이개발",
                "description": "실시간 푸시 알림 시스템. 사용자별 알림 설정, 알림 히스토리 관리, 알림 템플릿 관리",
                "created_date": "2024-01-20"
            },
            {
                "jira_ticket": "ENOMIX-7579",
                "title": "[경남은행] 상담사 메세지 회수",
                "story_points": 5,
                "estimation_reason": "타 사이트에 적용된 기능 포팅으로 실제 작업시간 3일로 감소",
                "tech_stack": null,
                "team_member": "이형기",
                "description": "타 사이트에 적용된 기능 포팅으로 실제 작업시간 3일로 감소",
                "created_date": "2025-09-25"
            }
        ]
        
        # 질문에 따라 관련 데이터 필터링 (부분 일치 포함)
        relevant_data = []
        question_lower = question.lower()
        
        for data in mock_effort_data:
            title_lower = data['title'].lower()
            jira_lower = data['jira_ticket'].lower()
            
            # 정확한 매칭
            if any(keyword in question_lower for keyword in [title_lower, jira_lower]):
                relevant_data.append(data)
            # 부분 매칭 (예: "메세지 회수" -> "상담사 메세지 회수")
            elif any(keyword in title_lower for keyword in question_lower.split() if len(keyword) > 2):
                relevant_data.append(data)
        
        # 응답 생성
        if not relevant_data:
            # 특정 기능에 대한 데이터가 없는 경우
            response_text = "죄송합니다. 해당 기능에 대한 공수 산정 데이터가 현재 등록되어 있지 않습니다. 해당 기능의 공수 산정 데이터를 먼저 추가해주세요."
        else:
            response_text = "📊 *공수 산정 답변* (모의 데이터)\n\n"
            for data in relevant_data:
                response_text += f"**Jira 티켓**: {data['jira_ticket']}\n"
                response_text += f"**제목**: {data['title']}\n"
                response_text += f"**Story Points**: {data['story_points']}\n"
                response_text += f"**예상공수**: {data['story_points']}일\n"
                response_text += f"**산정이유**: {data['estimation_reason']}\n"
                response_text += f"**담당자**: {data['team_member']}\n"
                if data.get('description'):
                    response_text += f"**개발 요구사항**: {data['description']}\n"
                response_text += f"**등록일**: {data['created_date']}\n\n"
        
        return {
            "question": question,
            "answer": response_text,
            "sources": [{"source": "모의 데이터", "page": "N/A", "content": "OpenAI API 할당량 초과로 인한 모의 응답"}]
        }
    
    else:
        # 공수 산정과 관련 없는 질문에 대한 응답
        return {
            "question": question,
            "answer": "죄송합니다. 공수 산정 데이터를 기반으로 답변할 수 없는 질문입니다. 공수 산정, 개발 기간, Story Points 등과 관련된 질문을 해주세요.",
            "sources": [{"source": "시스템 메시지", "page": "N/A", "content": "공수 산정과 관련 없는 질문"}]
        }

def mock_effort_qa_response(question: str) -> Dict[str, Any]:
    """공수 산정 전용 모의 QA 응답"""
    return mock_qa_response(question)
