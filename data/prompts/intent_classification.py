"""
의도 분류 프롬프트 관리 모듈
사용자 질문이 공수 산정 관련인지 판단하는 프롬프트를 관리합니다.
"""

import json
import os
from typing import List, Dict
from datetime import datetime

class IntentClassificationPrompt:
    """의도 분류 프롬프트 관리 클래스"""
    
    def __init__(self):
        self.examples_dir = os.path.join(os.path.dirname(__file__), "examples")
        self.related_file = os.path.join(self.examples_dir, "related_examples.json")
        self.unrelated_file = os.path.join(self.examples_dir, "unrelated_examples.json")
        
        # 기본 예시들
        self.default_related = [
            "로그인 기능 개발에 얼마나 걸릴까요?",
            "API 개발 공수는 어떻게 산정하나요?",
            "이 기능의 Story Points는 몇 점인가요?",
            "개발 기간을 예상해주세요",
            "프로그래밍 작업 시간이 얼마나 필요할까요?",
            "메세지 삭제기능 공수 알려줘",
            "상담사 메세지 삭제기능 공수 알려줘",
            "상담사 기능 개발 시간",
            "고객 서비스 시스템 공수",
            "채팅 기능 개발 시간",
            "데이터베이스 설계 공수",
            "웹페이지 만들기 시간",
            "앱 개발 기간",
            "시스템 구축 시간",
            "기능 구현 공수",
            "작업 시간 예상",
            "개발 소요 시간",
            "프로젝트 기간",
            "UI/UX 디자인 작업 시간",
            "백엔드 API 개발 공수",
            "프론트엔드 개발 시간",
            "데이터베이스 마이그레이션 공수",
            "테스트 코드 작성 시간",
            "배포 작업 소요 시간",
            "성능 최적화 작업 시간",
            "보안 기능 구현 공수",
            "모바일 앱 개발 기간",
            "웹 서비스 구축 시간",
            "마이크로서비스 개발 공수",
            "클라우드 인프라 구축 시간",
            "CI/CD 파이프라인 구축 공수",
            "모니터링 시스템 개발 시간",
            "로그 분석 기능 구현 공수",
            "알림 시스템 개발 시간",
            "결제 시스템 연동 공수",
            "사용자 인증 시스템 개발 시간",
            "데이터 시각화 기능 공수"
        ]
        
        self.default_unrelated = [
            "안녕하세요", "hello", "hi",
            "오늘 날씨가 어떤가요?",
            "음식 추천해주세요",
            "게임 추천해주세요",
            "영화 추천해주세요",
            "정치 이야기",
            "경제 뉴스",
            "스포츠 경기",
            "음악 추천",
            "여행지 추천해주세요",
            "책 추천해주세요",
            "영화 평점 알려주세요",
            "주식 투자 조언해주세요",
            "건강 관리 방법 알려주세요",
            "요리 레시피 알려주세요",
            "운동 방법 추천해주세요",
            "학습 방법 조언해주세요",
            "취미 활동 추천해주세요",
            "패션 스타일 조언해주세요",
            "인테리어 디자인 추천해주세요",
            "자동차 추천해주세요",
            "부동산 정보 알려주세요",
            "금융 상품 추천해주세요"
        ]
        
        # 파일 초기화
        self._initialize_files()
    
    def _initialize_files(self):
        """예시 파일들을 초기화합니다."""
        os.makedirs(self.examples_dir, exist_ok=True)
        
        if not os.path.exists(self.related_file):
            self._save_examples(self.related_file, self.default_related)
        
        if not os.path.exists(self.unrelated_file):
            self._save_examples(self.unrelated_file, self.default_unrelated)
    
    def _save_examples(self, file_path: str, examples: List[str]):
        """예시들을 JSON 파일에 저장합니다."""
        data = {
            "examples": examples,
            "last_updated": datetime.now().isoformat(),
            "count": len(examples)
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_examples(self, file_path: str) -> List[str]:
        """JSON 파일에서 예시들을 로드합니다."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("examples", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def get_related_examples(self) -> List[str]:
        """관련 예시들을 반환합니다."""
        return self._load_examples(self.related_file)
    
    def get_unrelated_examples(self) -> List[str]:
        """관련 없는 예시들을 반환합니다."""
        return self._load_examples(self.unrelated_file)
    
    def add_related_example(self, example: str):
        """관련 예시를 추가합니다."""
        examples = self.get_related_examples()
        if example not in examples:
            examples.append(example)
            self._save_examples(self.related_file, examples)
            return True
        return False
    
    def add_unrelated_example(self, example: str):
        """관련 없는 예시를 추가합니다."""
        examples = self.get_unrelated_examples()
        if example not in examples:
            examples.append(example)
            self._save_examples(self.unrelated_file, examples)
            return True
        return False
    
    def remove_related_example(self, example: str):
        """관련 예시를 제거합니다."""
        examples = self.get_related_examples()
        if example in examples:
            examples.remove(example)
            self._save_examples(self.related_file, examples)
            return True
        return False
    
    def remove_unrelated_example(self, example: str):
        """관련 없는 예시를 제거합니다."""
        examples = self.get_unrelated_examples()
        if example in examples:
            examples.remove(example)
            self._save_examples(self.unrelated_file, examples)
            return True
        return False
    
    def generate_prompt(self, question: str) -> str:
        """의도 분류 프롬프트를 생성합니다."""
        related_examples = self.get_related_examples()
        unrelated_examples = self.get_unrelated_examples()
        
        prompt = f"""
다음 질문이 공수 산정, 개발 기간, Story Points, 소프트웨어 개발과 관련된 질문인지 판단해주세요.

질문: "{question}"

**관련된 질문의 예시 (RELATED로 판단):**
"""
        
        for example in related_examples:
            prompt += f"- \"{example}\"\n"
        
        prompt += f"""
**관련 없는 질문의 예시 (UNRELATED로 판단):**
"""
        
        for example in unrelated_examples:
            prompt += f"- \"{example}\"\n"
        
        prompt += """
**명확히 UNRELATED로 판단할 패턴:**
- 숫자만 있는 입력 (111, 2222, 12345 등)
- 무의미한 문자 반복 (aaa, bbb, asdf 등)
- 한글 자음만 있는 입력 (ㄻㄹㄷㅁㄹ 등)
- 특수문자나 기호만 있는 입력 (!!!, ???, ### 등)
- 단순한 테스트 입력

**중요**: 개발, 기능, 공수, 시간, 기간, 작업, 프로젝트, 시스템, 앱, 웹, API, 데이터베이스, 상담사, 상담, 고객, 서비스 등과 관련된 모든 질문은 RELATED로 판단하세요.

다음 중 하나로만 답변해주세요:
- RELATED: 공수 산정, 개발 기간, Story Points, 소프트웨어 개발과 관련된 질문
- UNRELATED: 위와 관련 없는 일반적인 질문

답변 형식: RELATED 또는 UNRELATED
"""
        
        return prompt
    
    def get_stats(self) -> Dict[str, int]:
        """예시 통계를 반환합니다."""
        return {
            "related_count": len(self.get_related_examples()),
            "unrelated_count": len(self.get_unrelated_examples()),
            "total_count": len(self.get_related_examples()) + len(self.get_unrelated_examples())
        }

# 전역 인스턴스
intent_prompt_manager = IntentClassificationPrompt()
