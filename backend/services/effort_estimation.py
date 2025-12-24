"""
공수 산정 이력 데이터 관리 모듈
Jira 연동 및 수동 데이터 입력을 통한 공수 산정 이력 관리
"""

import os
import json
import logging
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from ..utils.config import DOCS_DIR

logger = logging.getLogger(__name__)

class CategoryManager:
    """카테고리 관리 클래스"""
    
    def __init__(self):
        self.categories_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'docs', 'categories.json')
        self.categories = self.load_categories()
    
    def load_categories(self) -> dict:
        """JSON 파일에서 카테고리 로드"""
        try:
            if os.path.exists(self.categories_file):
                with open(self.categories_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                # 기본 카테고리 생성
                default_categories = {
                    "인증": {
                        "로그인": ["일반로그인", "소셜로그인", "2FA", "자동로그인"],
                        "회원가입": ["일반가입", "소셜가입", "본인인증", "약관동의"],
                        "인증관리": ["비밀번호변경", "계정잠금", "인증토큰", "세션관리"]
                    },
                    "결제": {
                        "카드결제": ["신용카드", "체크카드", "간편결제", "정기결제"],
                        "송금": ["계좌이체", "실시간송금", "정기송금", "해외송금"],
                        "충전": ["계좌충전", "카드충전", "포인트충전", "쿠폰사용"]
                    },
                    "알림": {
                        "푸시알림": ["일반푸시", "마케팅푸시", "긴급알림", "예약알림"],
                        "메시지": ["SMS", "알림톡", "이메일", "인앱메시지"],
                        "알림관리": ["설정", "구독", "차단", "스케줄링"]
                    },
                    "조회": {
                        "계좌조회": ["잔액조회", "거래내역", "계좌목록", "상세조회"],
                        "카드조회": ["카드목록", "승인내역", "한도조회", "포인트조회"],
                        "대시보드": ["메인화면", "차트", "요약정보", "실시간데이터"]
                    },
                    "관리": {
                        "사용자관리": ["권한관리", "프로필관리", "설정관리", "계정관리"],
                        "시스템관리": ["로그관리", "모니터링", "백업", "배포"],
                        "데이터관리": ["데이터수집", "데이터분석", "리포팅", "백업"]
                    }
                }
                self.save_categories(default_categories)
                return default_categories
        except Exception as e:
            logger.error(f"❌ 카테고리 로드 실패: {str(e)}")
            return {}
    
    def save_categories(self, categories: dict = None):
        """JSON 파일에 카테고리 저장"""
        try:
            if categories is None:
                categories = self.categories
            
            with open(self.categories_file, "w", encoding="utf-8") as f:
                json.dump(categories, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 카테고리 저장 완료: {self.categories_file}")
        except Exception as e:
            logger.error(f"❌ 카테고리 저장 실패: {str(e)}")
    
    def get_categories(self) -> dict:
        """전체 카테고리 구조 반환"""
        return self.categories
    
    def get_major_categories(self) -> List[str]:
        """대분류 목록 반환"""
        return list(self.categories.keys())
    
    def get_minor_categories(self, major: str) -> List[str]:
        """특정 대분류의 중분류 목록 반환"""
        return list(self.categories.get(major, {}).keys())
    
    def get_sub_categories(self, major: str, minor: str) -> List[str]:
        """특정 중분류의 소분류 목록 반환"""
        return self.categories.get(major, {}).get(minor, [])
    
    def add_category(self, major: str, minor: str, sub: str):
        """새 카테고리 추가"""
        if major not in self.categories:
            self.categories[major] = {}
        if minor not in self.categories[major]:
            self.categories[major][minor] = []
        if sub not in self.categories[major][minor]:
            self.categories[major][minor].append(sub)
        
        # JSON 파일에 저장
        self.save_categories()
    
    def update_category(self, old_major: str, old_minor: str, old_sub: str, 
                       new_major: str, new_minor: str, new_sub: str):
        """카테고리 수정"""
        # 기존 카테고리 삭제
        if self.validate_category(old_major, old_minor, old_sub):
            self.categories[old_major][old_minor].remove(old_sub)
            
            # 중분류가 비어있으면 삭제
            if not self.categories[old_major][old_minor]:
                del self.categories[old_major][old_minor]
                
            # 대분류가 비어있으면 삭제
            if not self.categories[old_major]:
                del self.categories[old_major]
        
        # 새 카테고리 추가
        self.add_category(new_major, new_minor, new_sub)
    
    def delete_category(self, major: str, minor: str, sub: str):
        """카테고리 삭제"""
        if self.validate_category(major, minor, sub):
            self.categories[major][minor].remove(sub)
            
            # 중분류가 비어있으면 삭제
            if not self.categories[major][minor]:
                del self.categories[major][minor]
                
            # 대분류가 비어있으면 삭제
            if not self.categories[major]:
                del self.categories[major]
            
            # JSON 파일에 저장
            self.save_categories()
    
    def validate_category(self, major: str, minor: str, sub: str) -> bool:
        """카테고리 유효성 검증"""
        if major not in self.categories:
            return False
        if minor not in self.categories[major]:
            return False
        if sub not in self.categories[major][minor]:
            return False
        return True

@dataclass
class EffortEstimation:
    """공수 산정 데이터 모델 (Story Point 기반)"""
    jira_ticket: str  # Jira 티켓 (ENOMIX-XXX)
    title: str  # 제목
    story_points: float  # Story Point (M/D 단위로 통일)
    estimation_reason: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    team_member: Optional[str] = None
    created_date: str = None
    description: Optional[str] = None  # Jira Description
    notes: Optional[str] = None
    # 카테고리 필드 추가
    major_category: Optional[str] = None  # 대분류
    minor_category: Optional[str] = None  # 중분류
    sub_category: Optional[str] = None    # 소분류
    # Epic 필드 추가
    epic_key: Optional[str] = None  # Epic 티켓 (ENOMIX-XXX)
    epic_name: Optional[str] = None  # Epic 제목
    # 댓글 필드 추가
    comments: Optional[str] = None  # Jira 댓글들 (텍스트로 병합)
    # 공수 원본 정보 (WORK 프로젝트용)
    story_points_original: Optional[float] = None  # 원본 값 (예: 0.5 M/M)
    story_points_unit: Optional[str] = None  # 원본 단위 (M/M 또는 M/D)
    
    def __post_init__(self):
        if self.created_date is None:
            self.created_date = datetime.now().isoformat()

class EffortEstimationManager:
    """공수 산정 데이터 관리 클래스"""
    
    def __init__(self):
        self.data_file = os.path.join(DOCS_DIR, "effort_estimations.json")
        self.estimations: List[EffortEstimation] = []
        self.load_data()
    
    def load_data(self):
        """저장된 공수 산정 데이터 로드"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 기존 데이터 마이그레이션 (필드명 변경 대응)
                migrated_data = []
                for item in data:
                    try:
                        # 기존 필드명을 새 필드명으로 매핑
                        if 'project_name' in item and 'feature_name' in item:
                            # 기존 형식: project_name, feature_name
                            migrated_item = {
                                'jira_ticket': item.get('jira_ticket', item.get('project_name', '')),
                                'title': item.get('feature_name', ''),
                                'story_points': item.get('story_points', item.get('estimated_hours', 0)),
                                'estimation_reason': item.get('estimation_reason'),
                                'tech_stack': item.get('tech_stack'),
                                'team_member': item.get('team_member'),
                                'created_date': item.get('created_date'),
                                'notes': item.get('notes')
                            }
                            migrated_data.append(migrated_item)
                            logger.info(f"🔄 데이터 마이그레이션: {item.get('project_name')} -> {migrated_item['jira_ticket']}")
                        else:
                            # 이미 새 형식인 경우
                            migrated_data.append(item)
                    except Exception as e:
                        logger.error(f"❌ 데이터 마이그레이션 실패: {str(e)}")
                        continue
                
                self.estimations = [EffortEstimation(**item) for item in migrated_data]
                logger.info(f"✅ 공수 산정 데이터 로드 완료: {len(self.estimations)}개")
                
                # 마이그레이션이 있었다면 저장
                if migrated_data != data:
                    self.save_data()
                    logger.info("🔄 마이그레이션된 데이터 저장 완료")
            else:
                self.estimations = []
                logger.info("📝 새로운 공수 산정 데이터 파일 생성")
        except Exception as e:
            logger.error(f"❌ 공수 산정 데이터 로드 실패: {str(e)}")
            self.estimations = []
    
    def backup_data(self):
        """데이터 파일 백업 (최신 1개만 유지)"""
        try:
            if not os.path.exists(self.data_file):
                logger.info("ℹ️ 백업할 데이터 파일이 없습니다")
                return True
            
            backup_file = os.path.join(DOCS_DIR, "effort_estimations_backup.json")
            
            # 기존 백업 파일이 있으면 타임스탬프 확인
            if os.path.exists(backup_file):
                backup_time = datetime.fromtimestamp(os.path.getmtime(backup_file))
                logger.info(f"🔄 이전 백업 파일 교체 (생성일: {backup_time.strftime('%Y-%m-%d %H:%M:%S')})")
            
            # 현재 파일을 백업
            shutil.copy2(self.data_file, backup_file)
            
            # 파일 크기 확인
            file_size = os.path.getsize(backup_file)
            file_size_kb = file_size / 1024
            
            logger.info(f"✅ 데이터 백업 완료: {backup_file} ({file_size_kb:.1f}KB, {len(self.estimations)}개 항목)")
            return True
            
        except Exception as e:
            logger.error(f"❌ 데이터 백업 실패: {str(e)}")
            return False
    
    def save_data(self):
        """공수 산정 데이터 저장"""
        try:
            logger.info(f"💾 데이터 저장 시작: {len(self.estimations)}개 항목")
            data = [asdict(estimation) for estimation in self.estimations]
            
            # 파일 경로 확인
            logger.info(f"📁 저장 경로: {self.data_file}")
            
            # 파일 쓰기
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 저장 후 파일 크기 확인
            file_size = os.path.getsize(self.data_file)
            file_size_kb = file_size / 1024
            
            logger.info(f"✅ 공수 산정 데이터 저장 완료: {len(self.estimations)}개 ({file_size_kb:.1f}KB)")
            return True
        except Exception as e:
            logger.error(f"❌ 공수 산정 데이터 저장 실패: {str(e)}")
            import traceback
            logger.error(f"❌ 상세 에러: {traceback.format_exc()}")
            return False
    
    def add_estimation(self, estimation: EffortEstimation) -> bool:
        """새로운 공수 산정 데이터 추가 (중복 체크 및 업데이트)"""
        try:
            # Story Points 반올림 강제 (부동소수점 오차 제거)
            estimation.story_points = round(estimation.story_points, 2) if estimation.story_points else 0
            if estimation.story_points_original is not None:
                estimation.story_points_original = round(estimation.story_points_original, 2)
            
            logger.info(f"🔄 공수 산정 데이터 추가 시도: {estimation.jira_ticket} (story_points={estimation.story_points})")
            
            # Jira 티켓이 있는 경우 중복 체크
            if estimation.jira_ticket:
                existing_index = None
                for i, existing in enumerate(self.estimations):
                    if existing.jira_ticket == estimation.jira_ticket:
                        existing_index = i
                        break
                
                if existing_index is not None:
                    # 기존 데이터 업데이트 (카테고리 정보 보존)
                    existing_data = self.estimations[existing_index]
                    
                    # 변경사항 체크
                    has_changes = False
                    
                    # Story Points 변경 체크
                    if existing_data.story_points != estimation.story_points:
                        logger.info(f"   💰 Story Points 변경: {existing_data.story_points} → {estimation.story_points}")
                        has_changes = True
                    
                    if existing_data.story_points_original != estimation.story_points_original or \
                       existing_data.story_points_unit != estimation.story_points_unit:
                        logger.info(f"   📊 원본 공수 변경: {existing_data.story_points_original} {existing_data.story_points_unit} → {estimation.story_points_original} {estimation.story_points_unit}")
                        has_changes = True
                    
                    # 제목 변경 체크
                    if existing_data.title != estimation.title:
                        logger.info(f"   📝 제목 변경")
                        has_changes = True
                    
                    # 담당자 변경 체크
                    if existing_data.team_member != estimation.team_member:
                        logger.info(f"   👤 담당자 변경: {existing_data.team_member} → {estimation.team_member}")
                        has_changes = True
                    
                    # Epic 정보 변경 체크
                    if existing_data.epic_key != estimation.epic_key or existing_data.epic_name != estimation.epic_name:
                        logger.info(f"   📦 Epic 정보 변경: {existing_data.epic_key} → {estimation.epic_key}")
                        has_changes = True
                    
                    # 변경사항이 없으면 skip
                    if not has_changes:
                        logger.info(f"⏭️  변경사항 없음, skip: {estimation.jira_ticket}")
                        return True
                    
                    logger.info(f"🔄 기존 데이터 업데이트: {estimation.jira_ticket}")
                    
                    # 카테고리가 기존에 있으면 보존, 없으면 새 값 사용
                    if existing_data.major_category:
                        estimation.major_category = existing_data.major_category
                        estimation.minor_category = existing_data.minor_category
                        estimation.sub_category = existing_data.sub_category
                        logger.info(f"   📂 카테고리 보존: {existing_data.major_category}/{existing_data.minor_category}/{existing_data.sub_category}")
                    
                    self.estimations[existing_index] = estimation
                else:
                    # 새 데이터 추가
                    logger.info(f"➕ 새 데이터 추가: {estimation.jira_ticket}")
                    self.estimations.append(estimation)
            else:
                # Jira 티켓이 없는 경우 그냥 추가
                logger.info(f"➕ Jira 티켓 없는 데이터 추가")
                self.estimations.append(estimation)
            
            result = self.save_data()
            logger.info(f"🔄 데이터 저장 결과: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ 공수 산정 데이터 추가 실패: {str(e)}")
            return False
    
    def get_estimations_by_feature(self, feature_name: str) -> List[EffortEstimation]:
        """기능명으로 공수 산정 데이터 검색"""
        feature_lower = feature_name.lower()
        return [
            est for est in self.estimations 
            if feature_lower in est.title.lower()
        ]
    
    def get_all_estimations(self) -> List[EffortEstimation]:
        """모든 공수 산정 데이터 반환"""
        return self.estimations
    
    def format_for_indexing(self) -> str:
        """색인을 위한 텍스트 포맷팅"""
        formatted_data = []
        
        for est in self.estimations:
            # 기본 정보
            info = f"Jira 티켓: {est.jira_ticket}\n"
            info += f"제목: {est.title}\n"
            info += f"Story Points: {est.story_points} M/D"
            
            # 원본 공수 정보 추가 (WORK 프로젝트용)
            if est.story_points_original and est.story_points_unit:
                if est.story_points_unit == 'M/M':
                    info += f" (원본: {est.story_points_original} M/M)"
            info += "\n"
            
            # Epic 정보 추가
            if est.epic_key:
                info += f"Epic: {est.epic_key}"
                if est.epic_name:
                    info += f" ({est.epic_name})"
                info += "\n"
            
            if est.estimation_reason:
                info += f"산정 이유: {est.estimation_reason}\n"
            
            if est.tech_stack:
                info += f"기술 스택: {', '.join(est.tech_stack)}\n"
            
            if est.team_member:
                info += f"담당자: {est.team_member}\n"
            
            if est.description:
                info += f"설명: {est.description}\n"
            
            if est.comments:
                info += f"댓글: {est.comments}\n"
            
            if est.notes:
                info += f"비고: {est.notes}\n"
            
            info += f"등록일: {est.created_date}\n"
            info += "---\n"
            
            formatted_data.append(info)
        
        return "\n".join(formatted_data)
    
    def update_estimation_category(self, jira_ticket: str, major_category: str, minor_category: str, sub_category: str) -> bool:
        """공수 산정 데이터의 카테고리 수정"""
        try:
            for i, estimation in enumerate(self.estimations):
                if estimation.jira_ticket == jira_ticket:
                    # 카테고리 필드 업데이트
                    self.estimations[i].major_category = major_category
                    self.estimations[i].minor_category = minor_category
                    self.estimations[i].sub_category = sub_category
                    
                    # 데이터 저장
                    self.save_data()
                    logger.info(f"✅ 카테고리 수정 완료: {jira_ticket} -> {major_category} > {minor_category} > {sub_category}")
                    return True
            
            logger.warning(f"⚠️ 해당 티켓을 찾을 수 없음: {jira_ticket}")
            return False
        except Exception as e:
            logger.error(f"❌ 카테고리 수정 실패: {str(e)}")
            return False

    def update_estimation_epic(self, jira_ticket: str, epic_key: str, epic_name: str) -> bool:
        """공수 산정 데이터의 Epic 정보 수정"""
        try:
            for i, estimation in enumerate(self.estimations):
                if estimation.jira_ticket == jira_ticket:
                    # Epic 필드 업데이트
                    self.estimations[i].epic_key = epic_key
                    self.estimations[i].epic_name = epic_name
                    
                    # 데이터 저장
                    self.save_data()
                    logger.info(f"✅ Epic 정보 수정 완료: {jira_ticket} -> {epic_key} ({epic_name})")
                    return True
            
            logger.warning(f"⚠️ 해당 티켓을 찾을 수 없음: {jira_ticket}")
            return False
        except Exception as e:
            logger.error(f"❌ Epic 정보 수정 실패: {str(e)}")
            return False

    def get_estimation_by_ticket(self, jira_ticket: str) -> Optional[EffortEstimation]:
        """Jira 티켓으로 공수 산정 데이터 조회"""
        try:
            for estimation in self.estimations:
                if estimation.jira_ticket == jira_ticket:
                    return estimation
            return None
        except Exception as e:
            logger.error(f"❌ 공수 산정 데이터 조회 실패: {str(e)}")
            return None

    def delete_estimation(self, jira_ticket: str) -> bool:
        """공수 산정 데이터 삭제"""
        try:
            original_count = len(self.estimations)
            self.estimations = [est for est in self.estimations if est.jira_ticket != jira_ticket]
            
            if len(self.estimations) < original_count:
                # 데이터 저장
                self.save_data()
                logger.info(f"✅ 공수 산정 데이터 삭제 완료: {jira_ticket}")
                return True
            else:
                logger.warning(f"⚠️ 해당 티켓을 찾을 수 없음: {jira_ticket}")
                return False
        except Exception as e:
            logger.error(f"❌ 공수 산정 데이터 삭제 실패: {str(e)}")
            return False

# 전역 인스턴스
effort_manager = EffortEstimationManager()
