"""
공수 산정 전용 QA 모듈
공수 산정 이력 데이터에 대한 질의응답 처리
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import logging
from typing import List, Dict, Any
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from ..data.database import get_vectordb, search_positive_feedback
from ..utils.config import DOCS_DIR
from .effort_estimation import effort_manager

logger = logging.getLogger(__name__)

def run_effort_qa_chain(question: str) -> dict:
    """공수 산정 전용 QA 체인 실행"""
    try:
        logger.info(f"🔍 QA 체인 시작: '{question}'")
        
        # 1. 먼저 긍정 피드백 데이터에서 검색
        feedback_result = search_positive_feedback(question)
        if feedback_result:
            logger.info(f"✅ 피드백 데이터에서 답변 발견: {feedback_result['question'][:50]}...")
            return {
                "question": question,
                "answer": feedback_result["answer"],
                "sources": feedback_result["sources"],
                "is_from_feedback": True,
                "feedback_question": feedback_result["question"],
                "feedback_enabled": True  # 피드백 답변도 피드백 버튼 노출 (부정 피드백으로 개선 가능)
            }
        
        # 질문 의도 카테고리 분류 (속도 향상을 위해 선택적 실행)
        predicted_category = None
        confidence = 0.0
        # 카테고리 분류는 신뢰도가 높을 때만 유용하므로, 빠른 응답을 위해 선택적으로 실행
        # 필요시 주석 해제: from .category_classifier import auto_classify
        # predicted_category, confidence = auto_classify(question)
        
        # 사전 필터링: 명확히 무의미한 입력들
        question_clean = question.strip()
        
        # 1. 빈 문자열이나 공백만 있는 경우
        if not question_clean:
            logger.info(f"🚫 빈 질문으로 필터링됨: '{question}'")
            return {
                "question": question,
                "answer": "죄송합니다. 공수 산정 데이터를 기반으로 답변할 수 없는 질문입니다. 공수 산정, 개발 기간, Story Points 등과 관련된 질문을 해주세요.",
                "sources": [{"source": "시스템 메시지", "page": "N/A", "content": "빈 질문"}]
            }
        
        # 2. 숫자만 있는 경우 (111, 2222, 12345 등)
        if question_clean.isdigit():
            logger.info(f"🚫 숫자만 있는 질문으로 필터링됨: '{question}'")
            return {
                "question": question,
                "answer": "죄송합니다. 공수 산정 데이터를 기반으로 답변할 수 없는 질문입니다. 공수 산정, 개발 기간, Story Points 등과 관련된 질문을 해주세요.",
                "sources": [{"source": "시스템 메시지", "page": "N/A", "content": "숫자만 있는 질문"}]
            }
        
        # 3. 무의미한 문자 반복 (aaa, bbb, asdf 등)
        if len(question_clean) <= 5 and question_clean.isalpha() and len(set(question_clean)) <= 2:
            logger.info(f"🚫 무의미한 문자 반복으로 필터링됨: '{question}'")
            return {
                "question": question,
                "answer": "죄송합니다. 공수 산정 데이터를 기반으로 답변할 수 없는 질문입니다. 공수 산정, 개발 기간, Story Points 등과 관련된 질문을 해주세요.",
                "sources": [{"source": "시스템 메시지", "page": "N/A", "content": "무의미한 문자 반복"}]
            }
        
        # 4. 특수문자나 기호만 있는 경우
        if all(not c.isalnum() for c in question_clean):
            logger.info(f"🚫 특수문자만 있는 질문으로 필터링됨: '{question}'")
            return {
                "question": question,
                "answer": "죄송합니다. 공수 산정 데이터를 기반으로 답변할 수 없는 질문입니다. 공수 산정, 개발 기간, Story Points 등과 관련된 질문을 해주세요.",
                "sources": [{"source": "시스템 메시지", "page": "N/A", "content": "특수문자만 있는 질문"}]
            }
        
        # 5. 한글 자음만 있는 경우 (ㄻㄹㄷㅁㄹ 등)
        if question_clean and all(ord('ㄱ') <= ord(c) <= ord('ㅎ') for c in question_clean):
            logger.info(f"🚫 한글 자음만 있는 질문으로 필터링됨: '{question}'")
            return {
                "question": question,
                "answer": "죄송합니다. 공수 산정 데이터를 기반으로 답변할 수 없는 질문입니다. 공수 산정, 개발 기간, Story Points 등과 관련된 질문을 해주세요.",
                "sources": [{"source": "시스템 메시지", "page": "N/A", "content": "한글 자음만 있는 질문"}]
            }
        
        # 간단한 키워드 기반 의도 판단
        effort_keywords = ['공수', 'story points', '개발', '기간', '일정', '작업', '기능', '개발시간', '소요시간', '예상시간', '추가', '수정', '삭제', '등록', '관리', '화면', '통계', '모니터링', '상담', 'api', '연동', '시스템', '회수', '전송', '발송', '배분', '자동', '템플릿', '파일', '이미지', '통화', '녹음', '대기열', 'faq', '지식', '검색', '분류', '버전', '공유', '배치', '스케줄', '자동화', '실행', '알림', '가이드', '연동', '동기화', '인터페이스', '조회', '업데이트', '프론트', 'ui', 'ux', '호환성', '서버', '설정', '이관', '백업', '복구', '산출물', '커스터마이징', '회의', '분석', '이행', '테스트', '버그', '소스', '지원', '교육', '환경', '채널', '이력', '모니터', '대시보드']
        question_lower = question_clean.lower()
        
        # 키워드가 하나라도 있으면 공수 산정 관련으로 판단 (부분 문자열 매칭)
        # 예: "채널추가"에 "추가" 또는 "채널"이 포함되어 있으면 매칭
        has_effort_keyword = any(keyword in question_lower for keyword in effort_keywords)
        
        # 키워드 필터링 완화: 질문이 2글자 이상이고 의미있는 문자(영문, 한글, 숫자 조합)를 포함하면 통과
        # 예: "UQ", "TOPS", "UQ연동" 같은 시스템명/약어도 검색 가능하도록
        is_meaningful_query = (
            len(question_clean) >= 2 and  # 2글자 이상
            not question_clean.isdigit() and  # 숫자만이 아님
            any(c.isalnum() for c in question_clean)  # 영문/한글/숫자 포함
        )
        
        logger.info(f"🔍 키워드 체크: '{question}' -> '{question_lower}'")
        logger.info(f"🔍 감지된 키워드: {[kw for kw in effort_keywords if kw in question_lower]}")
        logger.info(f"🔍 키워드 존재 여부: {has_effort_keyword}")
        logger.info(f"🔍 의미있는 질문 여부: {is_meaningful_query} (길이={len(question_clean)}, 숫자만={question_clean.isdigit()})")
        
        # 키워드가 없고 의미있는 질문도 아니면 필터링 (피드백 검색은 이미 위에서 수행했으므로, 여기서는 키워드 필터링만)
        if not has_effort_keyword and not is_meaningful_query:
            logger.info(f"🚫 공수 산정 관련 키워드 없음: '{question}'")
            return {
                "question": question,
                "answer": "죄송합니다. 공수 산정 데이터를 기반으로 답변할 수 없는 질문입니다. 공수 산정, 개발 기간, Story Points 등과 관련된 질문을 해주세요.",
                "sources": [{"source": "시스템 메시지", "page": "N/A", "content": "공수 산정과 관련 없는 질문"}]
            }
        
        vectordb = get_vectordb()
        
        if vectordb._collection.count() == 0:
            return {"error": "색인된 공수 산정 데이터가 없습니다. 먼저 데이터를 추가해주세요."}
        
        # 다중 검색 전략: 키워드 기반 + 카테고리 기반 + 전체 검색
        # MMR 검색으로 다양성 고려하여 관련 문서 검색 품질 향상
        retriever_kwargs = {"k": 12, "fetch_k": 40}  # k=12, fetch_k=40으로 관련 문서 검색 품질 향상
        
        # 1. 키워드 기반 유사 기능 검색
        question_words = question_clean.split()
        similar_functions = []
        
        # 질문에서 핵심 키워드 추출 (스마트 추출)
        core_keywords = []
        stop_words = [
            '공수', '의', '에', '을', '를', '이', '가', '은', '는', '에', '에서', '로', '으로', '와', '과', '도', '만', '까지', '부터', 
            '때문에', '위해', '대한', '관련', '기능', '개발', '작업',
            # 조사/동사 추가
            '알려줘', '알려주세요', '알려줍시다', '알려주시면', '알려',
            '분석해줘', '분석해주세요', '분석',
            '얼마야', '얼마예요', '얼마인가요', '얼마',
            '어떻게', '어떤', '어떠한',
            '돼', '되', '되어', '되는',
            '해줘', '해주세요', '해주시면', '해',
            '뭐야', '뭐예요', '무엇', '무엇인가'
        ]
        
        # 영문-한글 분리 함수
        def split_mixed_word(word):
            """영문과 한글을 분리 (예: 'UQ연동' -> ['UQ', '연동'])"""
            if not word:
                return []
            
            parts = []
            current_part = ""
            current_type = None  # 'en' or 'ko'
            
            for char in word:
                char_type = 'en' if char.isascii() and char.isalnum() else 'ko'
                
                if current_type is None:
                    current_type = char_type
                    current_part = char
                elif current_type == char_type:
                    current_part += char
                else:
                    # 타입이 바뀌면 현재 부분 저장하고 새로 시작
                    if len(current_part) > 0:
                        parts.append(current_part)
                    current_type = char_type
                    current_part = char
            
            # 마지막 부분 추가
            if len(current_part) > 0:
                parts.append(current_part)
            
            return parts if parts else [word]
        
        for word in question_words:
            if len(word) > 1 and word not in stop_words:
                # 영문-한글 혼합 단어 분리 (예: "UQ연동" -> ["UQ", "연동"])
                if any(c.isascii() and c.isalnum() for c in word) and any(ord('가') <= ord(c) <= ord('힣') for c in word):
                    # 영문과 한글이 혼합된 경우 분리
                    split_words = split_mixed_word(word)
                    for split_word in split_words:
                        if len(split_word) > 0 and split_word not in stop_words:
                            core_keywords.append(split_word)
                else:
                    # 일반 단어는 그대로 추가
                    core_keywords.append(word)
        
        # 핵심 키워드 우선순위 설정 (더 중요한 키워드 우선)
        priority_keywords = []
        secondary_keywords = []
        
        for keyword in core_keywords:
            # 도메인 키워드 (가장 중요)
            if any(domain in keyword for domain in ['전화', '메세지', '상담', '통계', '모니터링', 'api', '시스템', '화면', '배치', 'faq', '지식', '챗봇', '연동', '이력', '톡', '메일', 'cs']):
                priority_keywords.append(keyword)
            # 액션 키워드 (두 번째 중요)
            elif any(action in keyword for action in ['추가', '수정', '삭제', '등록', '관리', '전송', '발송', '배분', '회수', '검색', '조회', '업데이트']):
                secondary_keywords.append(keyword)
            else:
                secondary_keywords.append(keyword)
        
        # 우선순위대로 정렬
        final_keywords = priority_keywords + secondary_keywords
        
        # 핵심 키워드만으로 검색 질문 생성 (stop_words 제거)
        # 띄어쓰기 차이를 고려하여 공백 제거 버전도 생성
        search_question = " ".join(final_keywords) if final_keywords else question_clean
        search_question_no_space = "".join(final_keywords) if final_keywords else question_clean.replace(" ", "")
        
        # 공백 제거 버전이 다르면 두 버전 모두 시도 (더 나은 결과 선택)
        if search_question_no_space != search_question:
            logger.info(f"🔍 검색 질문 (공백 제거 버전): '{search_question_no_space}'")
        
        logger.info(f"🔍 핵심 키워드: {final_keywords}")
        logger.info(f"🔍 우선순위 키워드: {priority_keywords}")
        logger.info(f"🔍 보조 키워드: {secondary_keywords}")
        logger.info(f"🔍 검색 질문 (핵심 키워드만): '{search_question}' (원본: '{question_clean}')")
        
        # 2. 카테고리 분류가 성공한 경우 해당 카테고리 데이터 우선 검색
        if predicted_category and confidence > 0.2:  # 신뢰도 기준 낮춤
            try:
                category_parts = predicted_category.split(' > ')
                if len(category_parts) >= 3:
                    major_cat, minor_cat, sub_cat = category_parts[0], category_parts[1], category_parts[2]
                    
                    # 해당 카테고리의 데이터만 검색 (Chroma DB 필터 문법)
                    category_filter = {
                        "$and": [
                            {"major_category": major_cat},
                            {"minor_category": minor_cat},
                            {"sub_category": sub_cat}
                        ]
                    }
                    
                    logger.info(f"🎯 카테고리 필터 적용: {category_filter}")
                    retriever_kwargs["filter"] = category_filter
                        
            except Exception as e:
                logger.warning(f"⚠️ 카테고리 필터링 오류: {e}, 전체 검색으로 전환")
        
        # MMR 검색으로 다양성을 고려하여 관련 문서 검색 품질 향상
        # 핵심 키워드만으로 검색 (stop_words 제거된 질문 사용)
        retriever = vectordb.as_retriever(
            search_type="mmr",  # MMR로 복원 (다양성 고려로 검색 품질 향상)
            search_kwargs=retriever_kwargs
        )
        
        # gpt-4o-mini로 복원 (프롬프트 이해도 향상)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        # 공수 산정 전용 프롬프트 (Story Points 기반) - 키워드 매칭 강화
        prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""다음은 공수 산정 이력 데이터입니다:
---------------------
{context}
---------------------

질문: {question}

위 데이터를 바탕으로 질문에 답변해주세요.

**중요**: 답변 우선순위를 정확히 따라주세요.

1. **정확한 매칭 우선**: 질문과 정확히 일치하는 제목이나 티켓이 있으면 그것을 우선 답변하세요.
2. **부분 문자열 매칭**: 정확한 매칭이 없으면 질문의 주요 단어들이 포함된 데이터를 찾아 답변하세요.
   - 예: "전화예약 전송 추가 요건 개발" 질문 → "전화예약 전송", "전송 추가", "추가 요건" 등 연속된 단어 조합이 포함된 데이터 찾기
4. **키워드 매칭**: 부분 문자열 매칭도 없으면 질문의 핵심 키워드가 포함된 데이터를 찾아 답변하세요.
   - 예: "전화예약 전송 추가 요건 개발" 질문 → "전화예약", "전송", "추가", "요건", "개발" 키워드가 포함된 데이터 찾기
   - 예: "로그인 기능" 질문 → "로그인" 키워드가 포함된 모든 데이터 찾기
5. **유사 기능**: 키워드 매칭도 없으면 유사한 기능의 데이터를 참고하여 답변하세요.

**키워드 매칭 예시**:
- "전화예약 전송" → "전화예약 배분", "전화예약 관리", "전화예약 추가" 등 전화예약 관련 모든 기능
- "메세지 삭제" → "메세지 회수", "메세지 관리", "상담사 메세지 삭제" 등 메세지 관련 모든 기능
- "통계 화면" → "통계 화면 추가", "통계 화면 수정", "통계 대시보드" 등 통계 관련 모든 기능

**절대 금지사항**:
- 제공된 데이터에 없는 티켓 번호를 임의로 생성하지 마세요.
- 다른 티켓의 Description을 섞어서 사용하지 마세요.
- 실제 데이터에 없는 정보를 추가하지 마세요.

답변 시 다음 사항을 고려해주세요:
1. 구체적인 Jira 티켓과 제목을 명시 (반드시 제공된 데이터에서만)
2. Story Points는 일 단위로 해석하여 표시 (예: Story Points: 5 → "5일", 범위가 있으면 "3~5일")
3. 산정 이유가 있다면 포함
4. Description은 해당 티켓의 Description만 사용하고, 다른 티켓의 Description은 절대 사용하지 마세요
5. 여러 프로젝트에서 동일한 기능이 개발된 경우 일 단위 범위로 제시 (예: "3~5일")
6. **매우 중요**: 제공된 데이터에서 질문의 핵심 키워드가 포함된 제목이나 설명이 있으면 반드시 답변하세요. 키워드가 부분적으로라도 일치하면 관련 데이터로 간주하고 답변하세요.
   - 질문의 핵심 키워드가 모두 포함된 데이터를 최우선으로 선택하세요.
   - 질문의 일부 키워드만 포함된 데이터도 관련 데이터로 간주하세요.
   - 예: "A B" 질문 → "A B C", "A B 가이드", "A B step1" 등 A와 B가 모두 포함된 데이터를 찾으세요.
7. **매우 중요**: 질문에 시스템명, 약어, 기능명이 포함되어 있고, 제공된 데이터에 해당 키워드가 포함된 제목이 있으면 반드시 해당 데이터를 찾아 답변하세요.
   - 질문의 핵심 키워드가 제목의 일부로 포함되어 있으면 매칭으로 간주하세요.
   - 예: "X연동" 질문 → "X연동 및 ...", "X연동 가이드", "X연동 step3" 등 X와 연동이 모두 포함된 데이터를 찾으세요.
8. **매우 중요**: 제공된 데이터가 있으면 반드시 답변하세요. 문서가 검색되었는데도 답변할 수 없다고 하지 마세요. 제공된 데이터에서 질문과 관련된 내용을 찾아 답변하세요.
9. 데이터가 전혀 없을 때만 "해당 기능에 대한 공수 산정 데이터가 현재 등록되어 있지 않습니다."라고 답변하세요.

답변 형식:
- Jira 티켓: [실제 티켓번호]
- 제목: [실제 기능명]
- Story Points: [실제 숫자]
- 예상공수: [X일] 또는 [X~Y일] (Story Points를 일 단위로 해석)
- 산정이유: [실제 이유] (있는 경우)
- 담당자: [실제 담당자] (있는 경우)
- 개발 요구사항: [실제 Description 요약] (있는 경우)
"""
        )
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt_template}
        )
        
        # 핵심 키워드만으로 검색 질문 생성 (위에서 이미 생성됨)
        # search_question이 없으면 원본 질문 사용
        query_for_search = search_question if 'search_question' in locals() else question_clean
        
        # 띄어쓰기 차이를 고려하여 원본과 공백 제거 버전 모두 검색
        query_for_search_no_space = query_for_search.replace(" ", "")
        if query_for_search_no_space != query_for_search:
            logger.info(f"🔍 QA 체인 실행 중: '{query_for_search}' (원본: '{question_clean}')")
            logger.info(f"🔍 QA 체인 실행 중 (공백 제거): '{query_for_search_no_space}' (원본: '{question_clean}')")
            # 원본 버전으로 먼저 검색
            result = qa_chain({"query": query_for_search})
            answer = result.get("result", "").strip()
            source_docs = result.get("source_documents", [])
            
            # 답변 유효성 검사: 문서가 있는데 답변이 없거나 부적절한 경우
            is_invalid_answer = (
                not answer or 
                "등록되어 있지 않습니다" in answer or
                "찾을 수 없습니다" in answer
            )
            
            # 결과가 없거나 부족하거나 답변이 유효하지 않으면 공백 제거 버전도 검색
            if is_invalid_answer or len(source_docs) < 3:
                logger.info(f"🔍 원본 검색 결과 부족 또는 답변 부적절, 공백 제거 버전으로 추가 검색")
                result_no_space = qa_chain({"query": query_for_search_no_space})
                answer_no_space = result_no_space.get("result", "").strip()
                source_docs_no_space = result_no_space.get("source_documents", [])
                
                # 공백 제거 버전의 결과가 더 좋으면 사용
                # 조건: 답변이 유효하고 문서가 더 많거나, 원본이 유효하지 않은데 공백 제거 버전이 유효한 경우
                if (answer_no_space and 
                    "등록되어 있지 않습니다" not in answer_no_space and
                    "찾을 수 없습니다" not in answer_no_space and
                    (is_invalid_answer or len(source_docs_no_space) > len(source_docs))):
                    result = result_no_space
                    answer = answer_no_space
                    source_docs = source_docs_no_space
                    logger.info(f"✅ 공백 제거 버전 결과 사용 (문서: {len(source_docs)}개)")
        else:
            logger.info(f"🔍 QA 체인 실행 중: '{query_for_search}' (원본: '{question_clean}')")
            result = qa_chain({"query": query_for_search})
        
        answer = result.get("result", "").strip()
        source_docs = result.get("source_documents", [])
        
        # 답변 유효성 검사: 문서가 있는데 답변이 부적절한 경우 원본 질문으로 재검색
        if source_docs and (
            not answer or 
            "등록되어 있지 않습니다" in answer or
            "찾을 수 없습니다" in answer
        ):
            logger.info(f"🔍 문서는 있으나 답변 부적절, 원본 질문으로 재검색: '{question_clean}'")
            result_original = qa_chain({"query": question_clean})
            answer_original = result_original.get("result", "").strip()
            source_docs_original = result_original.get("source_documents", [])
            
            # 원본 질문 결과가 더 좋으면 사용
            if (answer_original and 
                "등록되어 있지 않습니다" not in answer_original and
                "찾을 수 없습니다" not in answer_original):
                result = result_original
                answer = answer_original
                source_docs = source_docs_original
                logger.info(f"✅ 원본 질문 재검색 결과 사용 (문서: {len(source_docs)}개)")
        
        logger.info(f"✅ QA 체인 실행 완료. 답변 길이: {len(answer)}자, 참조 문서: {len(source_docs)}개")
        
        # 참조 문서 정보 추출
        sources = []
        for doc in source_docs:
            metadata = doc.metadata
            source = metadata.get("source", "알 수 없음")
            page = metadata.get("page", "N/A")
            sources.append({
                "source": source,
                "page": page,
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            })
        
        return {
            "question": question,
            "answer": answer if answer else "공수 산정 데이터에서 해당 정보를 찾을 수 없습니다.",
            "sources": sources,
            "feedback_enabled": True,
            "search_session_id": f"qa_{hash(question)}_{len(sources)}"
        }
        
    except Exception as e:
        logger.error(f"❌ 공수 산정 QA 처리 오류: {str(e)}")
        return {
            "question": question,
            "error": f"공수 산정 질의응답 처리 중 오류가 발생했습니다: {str(e)}"
        }

def run_effort_qa_with_feedback(question: str, excluded_sources: List[str] = None) -> dict:
    """피드백 기반 공수 산정 QA 체인 실행 (제외된 소스 제외하고 재검색)"""
    try:
        logger.info(f"🔄 피드백 기반 QA 재검색: '{question}'")
        
        # 제외할 소스가 있으면 필터링
        if excluded_sources:
            logger.info(f"🚫 제외할 소스: {excluded_sources}")
        
        # 벡터 DB에서 관련 문서 검색 (제외 소스 필터링)
        vectordb = get_vectordb()
        
        if vectordb._collection.count() == 0:
            return {"error": "색인된 공수 산정 데이터가 없습니다. 먼저 데이터를 추가해주세요."}
        
        # 제외 소스 필터링
        # MMR 검색으로 다양성 고려하여 관련 문서 검색 품질 향상
        retriever_kwargs = {"k": 12, "fetch_k": 40}  # k=12, fetch_k=40으로 관련 문서 검색 품질 향상
        
        if excluded_sources:
            # 중복 제거
            excluded_sources = list(set(excluded_sources))
            # 제외할 소스가 포함된 문서 필터링
            exclude_filter = {
                "source": {"$nin": excluded_sources}
            }
            retriever_kwargs["filter"] = exclude_filter
            logger.info(f"🔍 제외 필터 적용: {exclude_filter}")
        
        # MMR 검색으로 다양성을 고려하여 관련 문서 검색 품질 향상
        retriever = vectordb.as_retriever(
            search_type="mmr",  # MMR로 복원 (다양성 고려로 검색 품질 향상)
            search_kwargs=retriever_kwargs
        )
        
        # gpt-4o-mini로 복원 (프롬프트 이해도 향상)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        # 피드백 기반 프롬프트 (더 관대한 매칭)
        prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""다음은 공수 산정 이력 데이터입니다 (이전 답변이 부정확했으므로 다른 관련 데이터를 찾았습니다):
---------------------
{context}
---------------------

질문: {question}

**중요**: 이전 답변이 부정확했으므로 다른 관점에서 답변해주세요.

답변 우선순위:
1. **정확한 매칭 우선**: 질문과 정확히 일치하는 제목이나 티켓이 있으면 그것을 우선 답변하세요.
2. **부분 문자열 매칭**: 정확한 매칭이 없으면 질문의 주요 단어들이 포함된 데이터를 찾아 답변하세요.
   - 예: "전화예약 전송 추가 요건 개발" 질문 → "전화예약 전송", "전송 추가", "추가 요건" 등 연속된 단어 조합이 포함된 데이터 찾기
3. **키워드 매칭**: 부분 문자열 매칭도 없으면 질문의 핵심 키워드가 포함된 데이터를 찾아 답변하세요.
   - 예: "전화예약 전송 추가 요건 개발" 질문 → "전화예약", "전송", "추가", "요건", "개발" 키워드가 포함된 데이터 찾기
   - 예: "로그인 기능" 질문 → "로그인" 키워드가 포함된 모든 데이터 찾기
4. **유사 기능**: 키워드 매칭도 없으면 유사한 기능의 데이터를 참고하여 답변하세요.

**키워드 매칭 예시**:
- "전화예약 전송" → "전화예약 배분", "전화예약 관리", "전화예약 추가" 등 전화예약 관련 모든 기능
- "메세지 삭제" → "메세지 회수", "메세지 관리", "상담사 메세지 삭제" 등 메세지 관련 모든 기능
- "통계 화면" → "통계 화면 추가", "통계 화면 수정", "통계 대시보드" 등 통계 관련 모든 기능

**절대 금지사항**:
- 제공된 데이터에 없는 티켓 번호를 임의로 생성하지 마세요.
- 다른 티켓의 Description을 섞어서 사용하지 마세요.
- 실제 데이터에 없는 정보를 추가하지 마세요.

답변 시 다음 사항을 고려해주세요:
1. 구체적인 Jira 티켓과 제목을 명시 (반드시 제공된 데이터에서만)
2. Story Points는 일 단위로 해석하여 표시 (예: Story Points: 5 → "5일", 범위가 있으면 "3~5일")
3. 산정 이유가 있다면 포함
4. Description은 해당 티켓의 Description만 사용하고, 다른 티켓의 Description은 절대 사용하지 마세요
5. 여러 프로젝트에서 동일한 기능이 개발된 경우 일 단위 범위로 제시 (예: "3~5일")
6. **매우 중요**: 제공된 데이터에서 질문의 핵심 키워드가 포함된 제목이나 설명이 있으면 반드시 답변하세요. 키워드가 부분적으로라도 일치하면 관련 데이터로 간주하고 답변하세요.
   - 질문의 핵심 키워드가 모두 포함된 데이터를 최우선으로 선택하세요.
   - 질문의 일부 키워드만 포함된 데이터도 관련 데이터로 간주하세요.
   - 예: "A B" 질문 → "A B C", "A B 가이드", "A B step1" 등 A와 B가 모두 포함된 데이터를 찾으세요.
7. **매우 중요**: 질문에 시스템명, 약어, 기능명이 포함되어 있고, 제공된 데이터에 해당 키워드가 포함된 제목이 있으면 반드시 해당 데이터를 찾아 답변하세요.
   - 질문의 핵심 키워드가 제목의 일부로 포함되어 있으면 매칭으로 간주하세요.
   - 예: "X연동" 질문 → "X연동 및 ...", "X연동 가이드", "X연동 step3" 등 X와 연동이 모두 포함된 데이터를 찾으세요.
8. **매우 중요**: 제공된 데이터가 있으면 반드시 답변하세요. 문서가 검색되었는데도 답변할 수 없다고 하지 마세요. 제공된 데이터에서 질문과 관련된 내용을 찾아 답변하세요.
9. 데이터가 전혀 없을 때만 "해당 기능에 대한 공수 산정 데이터가 현재 등록되어 있지 않습니다."라고 답변하세요.

답변 형식:
- Jira 티켓: [실제 티켓번호]
- 제목: [실제 기능명]
- Story Points: [실제 숫자]
- 예상공수: [X일] 또는 [X~Y일] (Story Points를 일 단위로 해석)
- 산정이유: [실제 이유] (있는 경우)
- 담당자: [실제 담당자] (있는 경우)
- 개발 요구사항: [실제 Description 요약] (있는 경우)
"""
        )
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt_template}
        )
        
        logger.info(f"🔄 피드백 기반 QA 체인 실행 중: '{question}'")
        result = qa_chain({"query": question})
        answer = result["result"].strip()
        source_docs = result.get("source_documents", [])
        
        logger.info(f"✅ 피드백 기반 QA 체인 실행 완료. 답변 길이: {len(answer)}자, 참조 문서: {len(source_docs)}개")
        
        # 참조 문서 정보 추출
        sources = []
        for doc in source_docs:
            metadata = doc.metadata
            source = metadata.get("source", "알 수 없음")
            page = metadata.get("page", "N/A")
            sources.append({
                "source": source,
                "page": page,
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            })
        
        return {
            "question": question,
            "answer": answer if answer else "공수 산정 데이터에서 해당 정보를 찾을 수 없습니다.",
            "sources": sources,
            "feedback_enabled": True,
            "search_session_id": f"qa_feedback_{hash(question)}_{len(sources)}",
            "is_feedback_search": True
        }
        
    except Exception as e:
        logger.error(f"❌ 피드백 기반 QA 처리 오류: {str(e)}")
        return {
            "question": question,
            "error": f"피드백 기반 공수 산정 질의응답 처리 중 오류가 발생했습니다: {str(e)}"
        }

def get_feedback_weekly_positive_ratio() -> Dict[str, Any]:
    """주 단위 긍정 피드백 비율 통계
    
    Returns:
        dict: {
            "weekly_trend": [
                {"week": "2025-W48", "positive_ratio": 85.5},
                ...
            ]
        }
        피드백이 없는 주는 제외됨
    """
    try:
        import json
        from datetime import datetime
        from collections import defaultdict
        
        # 분자: 긍정 피드백 파일
        positive_file = os.path.join(DOCS_DIR, "positive_feedback.json")
        
        # 분모: 슬랙 QA 매핑 파일 + 웹 QA 매핑 파일 (전체 QA 응답 수)
        slack_mapping_file = os.path.join(DOCS_DIR, "slack_qa_mapping.json")
        web_mapping_file = os.path.join(DOCS_DIR, "web_qa_mapping.json")
        
        # 긍정 피드백 로드
        positive_feedbacks = []
        if os.path.exists(positive_file):
            with open(positive_file, 'r', encoding='utf-8') as f:
                positive_feedbacks = json.load(f)
        
        # 슬랙 QA 매핑 로드 (전체 QA 응답)
        slack_qa_mapping = {}
        if os.path.exists(slack_mapping_file):
            with open(slack_mapping_file, 'r', encoding='utf-8') as f:
                slack_qa_mapping = json.load(f)
        
        # 웹 QA 매핑 로드 (전체 QA 응답)
        web_qa_mapping = {}
        if os.path.exists(web_mapping_file):
            with open(web_mapping_file, 'r', encoding='utf-8') as f:
                web_qa_mapping = json.load(f)
        
        # 주별 긍정 피드백 카운트 집계 (분자)
        weekly_positive = defaultdict(int)
        
        # 긍정 피드백 처리
        for feedback in positive_feedbacks:
            timestamp = feedback.get("timestamp") or feedback.get("first_feedback_time") or feedback.get("last_feedback_time")
            if not timestamp:
                continue
            
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                # ISO 주 번호 계산 (년도-주 형식)
                year, week, _ = dt.isocalendar()
                week_key = f"{year}-W{week:02d}"
                
                # feedback_count가 있으면 그만큼 카운트, 없으면 1
                count = feedback.get("feedback_count", 1)
                weekly_positive[week_key] += count
            except (ValueError, AttributeError) as e:
                logger.warning(f"⚠️ 피드백 타임스탬프 파싱 오류: {timestamp} - {e}")
                continue
        
        # 주별 전체 QA 응답 카운트 집계 (분모)
        weekly_total_qa = defaultdict(int)
        
        # 슬랙 QA 매핑 처리 (전체 QA 응답 수)
        for message_ts, qa_data in slack_qa_mapping.items():
            timestamp = qa_data.get("timestamp")
            if not timestamp:
                continue
            
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                year, week, _ = dt.isocalendar()
                week_key = f"{year}-W{week:02d}"
                weekly_total_qa[week_key] += 1
            except (ValueError, AttributeError) as e:
                logger.warning(f"⚠️ 슬랙 QA 타임스탬프 파싱 오류: {timestamp} - {e}")
                continue
        
        # 웹 QA 매핑 처리 (전체 QA 응답 수)
        for qa_id, qa_data in web_qa_mapping.items():
            timestamp = qa_data.get("timestamp")
            if not timestamp:
                continue
            
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                year, week, _ = dt.isocalendar()
                week_key = f"{year}-W{week:02d}"
                weekly_total_qa[week_key] += 1
            except (ValueError, AttributeError) as e:
                logger.warning(f"⚠️ 웹 QA 타임스탬프 파싱 오류: {timestamp} - {e}")
                continue
        
        # 주별 긍정 비율 계산
        weekly_trend = []
        # 긍정 피드백이 있거나 전체 QA 응답이 있는 주만 포함
        all_weeks = set(list(weekly_positive.keys()) + list(weekly_total_qa.keys()))
        
        for week_key in sorted(all_weeks):
            positive_count = weekly_positive.get(week_key, 0)
            total_qa_count = weekly_total_qa.get(week_key, 0)
            
            # 전체 QA 응답이 없으면 제외 (피드백만 있어도 의미 없음)
            if total_qa_count == 0:
                continue
            
            # 긍정 비율 계산: 긍정 피드백 수 / 전체 QA 응답 수
            positive_ratio = round((positive_count / total_qa_count) * 100, 1)
            
            # 주 표기 형식 변경: "2025-W48" → "11(1W)" 형식
            # week_key는 "2025-W48" 형식
            try:
                from datetime import datetime, timedelta
                
                year, week_num = week_key.split('-W')
                week_num = int(week_num)
                year_int = int(year)
                
                # ISO 주 번호로부터 해당 주의 월요일 날짜 계산
                # ISO 주 1번은 1월 4일이 포함된 주
                jan4 = datetime(year_int, 1, 4)
                # 1월 4일이 속한 주의 월요일 찾기
                # weekday(): 0=월요일, 6=일요일
                days_to_monday = (jan4.weekday()) % 7
                iso_week1_monday = jan4 - timedelta(days=days_to_monday)
                
                # 해당 ISO 주의 월요일 계산
                target_monday = iso_week1_monday + timedelta(weeks=week_num - 1)
                
                # 해당 주의 월 추출
                month = target_monday.month
                
                # 해당 월의 1일
                month_start = datetime(year_int, month, 1)
                
                # 해당 월의 첫 번째 월요일 찾기
                days_to_first_monday = (month_start.weekday()) % 7
                month_first_monday = month_start - timedelta(days=days_to_first_monday)
                
                # 해당 주가 해당 월의 몇 번째 주인지 계산
                if target_monday >= month_first_monday:
                    week_in_month = ((target_monday - month_first_monday).days // 7) + 1
                else:
                    # 이전 달의 마지막 주인 경우
                    # 이전 달의 첫 번째 월요일 찾기
                    if month == 1:
                        prev_month_start = datetime(year_int - 1, 12, 1)
                    else:
                        prev_month_start = datetime(year_int, month - 1, 1)
                    
                    days_to_first_monday_prev = (prev_month_start.weekday()) % 7
                    prev_month_first_monday = prev_month_start - timedelta(days=days_to_first_monday_prev)
                    
                    week_in_month = ((target_monday - prev_month_first_monday).days // 7) + 1
                    month = prev_month_start.month  # 이전 달로 표시
                
                # 주 표기: "11(1W)" 형식
                week_display = f"{month}({week_in_month}W)"
            except Exception as e:
                logger.warning(f"⚠️ 주 표기 형식 변환 오류: {week_key} - {e}")
                import traceback
                logger.warning(f"⚠️ 상세 오류: {traceback.format_exc()}")
                week_display = week_key  # 변환 실패 시 원본 사용
            
            weekly_trend.append({
                "week": week_display,
                "week_key": week_key,  # 정렬을 위해 원본 키도 유지
                "positive_ratio": positive_ratio
            })
        
        return {
            "weekly_trend": weekly_trend
        }
        
    except Exception as e:
        logger.error(f"❌ 주 단위 피드백 통계 생성 오류: {str(e)}")
        import traceback
        logger.error(f"❌ 상세 오류: {traceback.format_exc()}")
        return {"weekly_trend": []}

def get_effort_statistics() -> Dict[str, Any]:
    """공수 산정 통계 정보 반환"""
    try:
        estimations = effort_manager.get_all_estimations()
        
        if not estimations:
            return {"error": "공수 산정 데이터가 없습니다."}
        
        # 기본 통계
        total_estimations = len(estimations)
        total_story_points = sum(est.story_points for est in estimations if est.story_points is not None)
        
        # Jira 티켓별 통계
        tickets = {}
        for est in estimations:
            if est.jira_ticket not in tickets:
                tickets[est.jira_ticket] = {
                    "count": 0,
                    "story_points": 0
                }
            tickets[est.jira_ticket]["count"] += 1
            if est.story_points is not None:
                tickets[est.jira_ticket]["story_points"] += est.story_points
        
        # 제목별 통계
        titles = {}
        for est in estimations:
            if est.title not in titles:
                titles[est.title] = {
                    "count": 0,
                    "story_points": []
                }
            titles[est.title]["count"] += 1
            if est.story_points is not None:
                titles[est.title]["story_points"].append(est.story_points)
        
        # 제목별 평균 Story Points 계산
        title_averages = {}
        for title, data in titles.items():
            if data["story_points"]:
                # None 값 제거 후 평균 계산
                valid_story_points = [sp for sp in data["story_points"] if sp is not None]
                if valid_story_points:
                    avg_story_points = sum(valid_story_points) / len(valid_story_points)
                    title_averages[title] = {
                        "avg_story_points": round(avg_story_points, 1),
                        "count": data["count"]
                    }
        
        # 전체 평균 Story Points 계산 (None 값이 있는 경우 고려)
        valid_estimations = [est for est in estimations if est.story_points is not None]
        average_story_points = round(total_story_points / len(valid_estimations), 1) if valid_estimations else 0
        
        return {
            "total_estimations": total_estimations,
            "total_story_points": round(total_story_points, 1),
            "average_story_points": average_story_points,
            "tickets": tickets,
            "title_averages": title_averages
        }
        
    except Exception as e:
        logger.error(f"❌ 공수 산정 통계 생성 오류: {str(e)}")
        return {"error": f"통계 생성 중 오류가 발생했습니다: {str(e)}"}

def search_similar_features(feature_name: str) -> List[Dict[str, Any]]:
    """유사한 기능 검색"""
    try:
        estimations = effort_manager.get_estimations_by_feature(feature_name)
        
        if not estimations:
            return []
        
        # 결과 정리 (Story Points 기반)
        results = []
        for est in estimations:
            result = {
                "jira_ticket": est.jira_ticket,
                "title": est.title,
                "story_points": est.story_points,
                "estimation_reason": est.estimation_reason,
                "tech_stack": est.tech_stack,
                "team_member": est.team_member,
                "created_date": est.created_date
            }
            results.append(result)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ 유사 기능 검색 오류: {str(e)}")
        return []
