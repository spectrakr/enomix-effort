import requests
import logging
import json
import os
import re
from datetime import datetime
from ..utils.config import SLACK_BOT_TOKEN, DOCS_DIR
from .utils import format_sources
from ..services.effort_qa import run_effort_qa_chain
from ..services.mock_qa import mock_qa_response, mock_effort_qa_response
from ..data.database import save_feedback_to_file

logger = logging.getLogger(__name__)

# 질문-답변 매핑 저장 (메시지 타임스탬프 기반)
# 형식: {message_ts: {"question": "...", "answer": "...", "sources": [...]}}
_slack_qa_mapping = {}

def load_slack_qa_mapping():
    """슬랙 질문-답변 매핑 로드"""
    global _slack_qa_mapping
    try:
        mapping_file = os.path.join(DOCS_DIR, "slack_qa_mapping.json")
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r', encoding='utf-8') as f:
                _slack_qa_mapping = json.load(f)
            logger.info(f"📂 슬랙 QA 매핑 로드: {len(_slack_qa_mapping)}개")
    except Exception as e:
        logger.warning(f"⚠️ 슬랙 QA 매핑 로드 실패: {e}")
        _slack_qa_mapping = {}

def save_slack_qa_mapping():
    """슬랙 질문-답변 매핑 저장"""
    try:
        mapping_file = os.path.join(DOCS_DIR, "slack_qa_mapping.json")
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(_slack_qa_mapping, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"❌ 슬랙 QA 매핑 저장 오류: {str(e)}")

# 시작 시 매핑 로드
load_slack_qa_mapping()

def clean_mention(text: str) -> str:
    """슬랙 멘션 제거"""
    return re.sub(r'<@[^>]+>', '', text).strip()

def clean_slack_text(text: str) -> str:
    """슬랙 텍스트 정제 (멘션, 포맷팅 제거)"""
    # 멘션 제거
    text = re.sub(r'<@[^>]+>', '', text)
    # 채널 링크 제거 (<#C123456|channel> -> channel)
    text = re.sub(r'<#[^|>]+\|([^>]+)>', r'\1', text)
    # 링크 제거 (<http://example.com|text> -> text 또는 URL)
    text = re.sub(r'<([^|>]+)\|([^>]+)>', r'\2', text)
    text = re.sub(r'<([^>]+)>', r'\1', text)
    # 포맷팅 제거 (*bold*, _italic_, ~strikethrough~, `code`)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # bold
    text = re.sub(r'_([^_]+)_', r'\1', text)  # italic
    text = re.sub(r'~([^~]+)~', r'\1', text)  # strikethrough
    text = re.sub(r'`([^`]+)`', r'\1', text)  # code
    # 공백 정리
    text = ' '.join(text.split())
    return text.strip()

def post_slack_reply(channel: str, thread_ts: str, text: str, question: str = None, answer: str = None, sources: list = None):
    """슬랙 메시지 전송 및 질문-답변 매핑 저장"""
    try:
        headers = {
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # 이모지 피드백 안내 추가 (공수 산정 답변인 경우만)
        if question and answer and "공수 산정 답변" in text:
            feedback_hint = "\n\n💡 *피드백*: 이 답변이 도움이 되셨나요? 👍 (thumbsup) = 도움됨, 👎 (thumbsdown) = 도움 안됨"
            text = text + feedback_hint
        
        data = {
            "channel": channel,
            "thread_ts": thread_ts,
            "text": text
        }
        
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json=data,
            verify=False  # SSL 검증 비활성화
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                message_ts = result.get("ts")  # 메시지 타임스탬프
                
                # 질문-답변 매핑 저장 (공수 산정 답변인 경우만)
                if question and answer and message_ts:
                    _slack_qa_mapping[message_ts] = {
                        "question": question,
                        "answer": answer,
                        "sources": sources or [],
                        "channel": channel,
                        "thread_ts": thread_ts,
                        "timestamp": datetime.now().isoformat()
                    }
                    save_slack_qa_mapping()
                    logger.info(f"💾 슬랙 QA 매핑 저장: {message_ts} -> {question[:30]}...")
                
                logger.info("✅ Slack message sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send Slack message: {result.get('error')}")
                return False
        else:
            logger.error(f"❌ Failed to send Slack message: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error sending Slack message: {str(e)}")
        return False 


async def handle_slack_message(text: str, channel: str, thread_ts: str, message_ts: str):
    try:
        clean_text = text.strip().lower()

        # 도움말 명령어 처리
        if clean_text in ['도움말', 'help', '명령어', 'commands']:
            help_message = """🤖 *공수 산정 봇 도움말*

*사용 가능한 명령어:*
• `공수 산정` - 공수 산정 관련 질문
• `통계` - 공수 산정 통계 조회
• `도움말` - 이 도움말 표시

*예시 질문:*
• "로그인 기능 개발에 얼마나 걸릴까?"
• "사용자 관리 시스템 공수는?"
• "API 개발 시간이 얼마나 필요해?"

*키워드:* 공수, 산정, 개발시간, 작업시간, 예상시간, 소요시간"""
            post_slack_reply(channel, thread_ts, help_message)
            return

        # 통계 조회 명령어 처리
        if clean_text in ['통계', 'stats', '현황']:
            try:
                from ..services.effort_qa import get_effort_statistics
                stats = get_effort_statistics()
                stats_message = f"""📊 *공수 산정 통계*

• 총 데이터 수: {stats.get('total_estimations', 0)}개
• 총 Story Points: {stats.get('total_story_points', 0)}점
• 평균 Story Points: {stats.get('average_story_points', 0)}점"""
                post_slack_reply(channel, thread_ts, stats_message)
                return
            except Exception as e:
                post_slack_reply(channel, thread_ts, "❌ 통계 조회 중 오류가 발생했습니다.")
                return

        # 공수 산정 QA 처리 (키워드 필터링 제거 - run_effort_qa_chain 내부에서 처리)
        # 슬랙에서는 모든 질문을 공수 산정 QA로 처리하고, 내부에서 필터링하도록 변경
        try:
            # 슬랙 텍스트 정제 (멘션, 포맷팅 제거)
            cleaned_text = clean_slack_text(text)
            logger.info(f"🔍 슬랙 텍스트 정제: '{text}' -> '{cleaned_text}'")
            # 정제된 텍스트 사용
            result = run_effort_qa_chain(cleaned_text)
        except Exception as e:
            if "quota" in str(e).lower() or "insufficient_quota" in str(e).lower():
                logger.warning("⚠️ OpenAI API 할당량 초과, 공수 산정 모의 응답 사용")
                result = mock_effort_qa_response(text)
            else:
                raise e
        
        # run_effort_qa_chain 내부에서 필터링된 경우 error 또는 answer에 특정 메시지 반환
        answer = result.get("answer", "공수 산정 답변을 생성하지 못했습니다.")
        
        # error 키 확인
        if "error" in result:
            error_msg = result.get("error", "")
            if "공수 산정 데이터를 기반으로 답변할 수 없는 질문" in error_msg:
                # 키워드 필터링된 경우 - 모의 응답 사용
                result = mock_qa_response(clean_text)
                answer = result.get("answer", "답변을 생성하지 못했습니다.")
                sources = result.get("sources", [])
                sources_text = format_sources(sources)
                final_message = f"{answer}{sources_text}"
                post_slack_reply(channel, thread_ts, final_message)
            else:
                # 실제 오류인 경우
                post_slack_reply(channel, thread_ts, f"📊 {error_msg}")
            return
        
        # answer에 필터링 메시지가 포함되어 있는지 확인 (키워드 필터링에 걸린 경우)
        if "공수 산정 데이터를 기반으로 답변할 수 없는 질문" in answer:
            # 키워드 필터링된 경우 - 모의 응답 사용
            logger.info(f"🔍 슬랙에서 필터링 메시지 감지: '{answer[:50]}...'")
            result = mock_qa_response(clean_text)
            answer = result.get("answer", "답변을 생성하지 못했습니다.")
            sources = result.get("sources", [])
            sources_text = format_sources(sources)
            final_message = f"{answer}{sources_text}"
            post_slack_reply(channel, thread_ts, final_message)
            return
        
        # 정상적인 답변인 경우
        sources = result.get("sources", [])
        sources_text = format_sources(sources)
        final_message = f"📊 *공수 산정 답변*\n{answer}{sources_text}"
        
        # 질문-답변 매핑 저장을 위해 정보 전달 (정제된 텍스트 사용)
        post_slack_reply(channel, thread_ts, final_message, question=cleaned_text, answer=answer, sources=sources)

    except Exception as e:
        logger.error(f"❌ Error handling Slack message: {str(e)}")
        post_slack_reply(channel, thread_ts, "❌ 오류가 발생했습니다. 다시 시도해주세요.")

def handle_slack_reaction(event: dict):
    """슬랙 이모지 리액션 처리 (피드백 수집) - 봇 메시지만 처리"""
    try:
        reaction = event.get("reaction", "")
        item = event.get("item", {})
        item_ts = item.get("ts")  # 메시지 타임스탬프
        user = event.get("user", "알 수 없음")
        channel = item.get("channel", "")
        
        logger.info(f"👍 이모지 리액션 수신: reaction='{reaction}' on message {item_ts} by {user}")
        
        # 이모지 타입 확인 (더 많은 형식 지원)
        # 슬랙에서 실제로 전달되는 reaction 값은 이모지 이름 (예: "thumbsup", "+1")
        positive_emojis = ["+1", "thumbsup", "👍", "thumbs_up", "white_check_mark", "heavy_check_mark"]
        negative_emojis = ["-1", "thumbsdown", "👎", "thumbs_down", "x", "negative_squared_cross_mark"]
        
        # reaction 값 정규화 (앞뒤 공백 제거, 소문자 변환)
        reaction_normalized = reaction.strip().lower()
        
        if reaction_normalized not in [e.lower() for e in positive_emojis + negative_emojis]:
            logger.info(f"ℹ️ 피드백 관련 이모지가 아님: '{reaction}' (정규화: '{reaction_normalized}')")
            return
        
        # 질문-답변 매핑에서 찾기 (봇이 보낸 메시지만 매핑에 있음)
        qa_data = _slack_qa_mapping.get(item_ts)
        if not qa_data:
            # 매핑이 없으면 봇 메시지가 아니므로 조용히 무시
            logger.info(f"ℹ️ 메시지 {item_ts}는 봇 메시지가 아니거나 피드백 대상이 아닙니다. (무시)")
            return
        
        question = qa_data.get("question", "")
        answer = qa_data.get("answer", "")
        sources = qa_data.get("sources", [])
        thread_ts = qa_data.get("thread_ts")
        
        # 피드백 타입 결정
        if reaction_normalized in [e.lower() for e in positive_emojis]:
            feedback_type = "positive"
            emoji_display = "👍"
            logger.info(f"✅ 긍정 피드백: {question[:30]}...")
        else:
            feedback_type = "negative"
            emoji_display = "👎"
            logger.info(f"❌ 부정 피드백: {question[:30]}...")
        
        # 피드백 데이터 저장
        feedback_data = {
            "question": question,
            "answer": answer,
            "sources": sources,
            "timestamp": datetime.now().isoformat(),
            "feedback_type": feedback_type,
            "source": "slack",
            "reaction": reaction,
            "user": user
        }
        
        # 피드백 저장 시도
        result = save_feedback_to_file(feedback_data)
        
        if result.get("saved"):
            feedback_count = result.get("feedback_count", 1)
            is_new = result.get("is_new", True)
            
            if is_new:
                logger.info(f"💾 슬랙 피드백 저장 완료 (새로운 세트): {feedback_type} - {question[:30]}...")
                if channel:
                    feedback_message = f"{emoji_display} 피드백이 저장되었습니다. 감사합니다!"
                    post_slack_reply(channel, thread_ts, feedback_message)
            else:
                logger.info(f"📊 슬랙 피드백 카운트 증가: {feedback_type} - {question[:30]}... (총 {feedback_count}회)")
                if channel:
                    feedback_message = f"{emoji_display} 피드백이 반영되었습니다. (총 {feedback_count}회) 감사합니다!"
                    post_slack_reply(channel, thread_ts, feedback_message)
        else:
            logger.info(f"ℹ️ 슬랙 피드백 저장 실패: {feedback_type} - {question[:30]}...")
            if channel:
                feedback_message = f"{emoji_display} 피드백 저장 중 오류가 발생했습니다."
                post_slack_reply(channel, thread_ts, feedback_message)
        
    except Exception as e:
        logger.error(f"❌ 슬랙 이모지 리액션 처리 오류: {str(e)}")
        import traceback
        logger.error(f"❌ 상세 오류: {traceback.format_exc()}")