"""
Jira 연동 모듈
Jira API를 통한 공수 산정 데이터 수집
"""

import requests
import logging
import re
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import os
from ..utils.config import DOCS_DIR
from .effort_estimation import EffortEstimation, effort_manager

logger = logging.getLogger(__name__)

class JiraIntegration:
    """Jira API 연동 클래스"""
    
    def __init__(self, jira_url: str, username: str, api_token: str):
        self.jira_url = jira_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.session = requests.Session()
        self.session.auth = (username, api_token)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def test_connection(self) -> bool:
        """Jira 연결 테스트"""
        try:
            # API v3 사용
            response = self.session.get(f"{self.jira_url}/rest/api/3/myself")
            if response.status_code == 200:
                logger.info("✅ Jira 연결 성공")
                return True
            else:
                logger.error(f"❌ Jira 연결 실패: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Jira 연결 오류: {str(e)}")
            return False
    
    def test_epic_subtasks(self, epic_key: str, include_details: bool = False) -> dict:
        """Epic의 하위 Task들 조회 테스트
        
        Args:
            epic_key: Epic 키 (예: ENOMIX-123)
            include_details: description/comments 포함 여부 (WORK 프로젝트용, 느림)
        """
        try:
            logger.info(f"🔍 Epic '{epic_key}' 하위 작업 조회 시작 (상세 정보: {'포함' if include_details else '제외'})")
            
            subtasks_dict = {}  # key를 기준으로 중복 제거용 딕셔너리
            
            # 1단계: Epic의 내부 ID 가져오기
            issue_url = f"{self.jira_url}/rest/api/3/issue/{epic_key}"
            params = {'fields': 'id,key,summary'}
            
            logger.info(f"🔍 1단계: Epic ID 조회")
            epic_response = self.session.get(issue_url, params=params)
            
            epic_id = None
            epic_data = None
            if epic_response.status_code == 200:
                epic_data = epic_response.json()
                epic_id = epic_data.get('id')
                logger.info(f"✅ Epic 내부 ID: {epic_id} (Key: {epic_key})")
            else:
                logger.warning(f"⚠️ Epic 조회 실패: {epic_response.status_code}")
            
            # 2단계: Epic ID를 사용하여 parent 관계로 검색 (가장 확실한 방법)
            logger.info(f"🔍 2단계: Epic ID로 parent 관계 검색")
            
            search_url = f"{self.jira_url}/rest/api/3/search/jql"
            
            # 기본 필드 + description 조회 (comments만 제외)
            fields = 'key,summary,status,issuetype,assignee,customfield_10105,customfield_10124,parent,description'
            logger.info("📝 기본 정보 + description 조회 (comments 제외)")
            
            # 여러 JQL 쿼리 시도 (ID 기반 검색 우선)
            project_key = epic_key.split("-")[0]
            jql_queries = []
            
            # Epic ID가 있으면 ID 기반 검색 우선 (프로젝트 제한 없음)
            if epic_id:
                jql_queries.extend([
                    f'parent = {epic_id}',  # Epic ID로 부모 검색 (가장 정확)
                    f'parent = {epic_id} OR "Epic Link" = {epic_key}',  # ID + Key 조합
                    f'cf[10014] = {epic_key}',  # Epic Link 커스텀 필드 (ID: 10014)
                ])
            
            # 기존 JQL 쿼리들
            jql_queries.extend([
                f'"Epic Link" = {epic_key}',  # 가장 효과적인 Epic 하위 작업 조회
                f'parent = {epic_key}',  # 부모-자식 관계 (Key로)
                f'epic = {epic_key}',  # Epic 필드
                f'project = {project_key} AND "Epic Link" = {epic_key}',  # 프로젝트 + Epic Link
                f'project = {project_key} AND parent = {epic_key}',  # 프로젝트 + 부모
                f'cf[10018] = {epic_key}',  # Parent Link 커스텀 필드 (ID: 10018)
                f'issue in linkedIssues({epic_key})',  # 링크된 이슈
                f'parent in ({epic_key})',  # 부모 IN
                f'"Epic Link" in ({epic_key})',  # Epic Link IN
            ])
            
            if epic_id:
                jql_queries.append(f'parent in ({epic_id})')  # Epic ID IN
            
            jql_results = []  # 각 JQL 결과 기록용
            
            for i, jql in enumerate(jql_queries, 1):
                try:
                    logger.info(f"🔍 JQL {i}/{len(jql_queries)}: {jql}")
                    
                    # Jira API v3 요청 구조
                    headers = {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    }
                    
                    params = {
                        'jql': jql,
                        'maxResults': 200,  # 더 많은 결과 가져오기
                        'fields': fields,
                        'expand': 'changelog'
                    }
                    
                    response = self.session.get(search_url, params=params, headers=headers)
                    
                    if response.status_code == 200:
                        results = response.json()
                        total = results.get('total', 0)
                        issues = results.get('issues', [])
                        issues_count = len(issues)
                        
                        logger.info(f"✅ JQL {i} 성공: total={total}, issues_count={issues_count}, maxResults={params['maxResults']}")
                        
                        if total > issues_count:
                            logger.warning(f"⚠️ JQL {i}: total({total}) > issues_count({issues_count}), maxResults 제한으로 일부만 가져옴")
                        
                        jql_result = {
                            "jql": jql,
                            "status": "success",
                            "total": total,
                            "fetched": issues_count,
                            "added": 0
                        }
                        
                        if issues_count > 0:
                            found_count = 0
                            for issue in issues:
                                try:
                                    issue_key = issue.get('key', 'N/A')
                                    fields = issue.get('fields', {})
                                    
                                    if not fields:
                                        logger.warning(f"⚠️ 필드가 없는 이슈: {issue_key}")
                                        continue
                                    
                                    # issuetype 안전하게 추출
                                    issuetype_obj = fields.get('issuetype')
                                    if not issuetype_obj or not isinstance(issuetype_obj, dict):
                                        logger.warning(f"⚠️ issuetype 필드가 없거나 잘못된 이슈: {issue_key}")
                                        continue
                                    issue_type = issuetype_obj.get('name', 'Unknown')
                                    
                                    # Epic 자체는 제외 (하위 작업만 가져오기)
                                    if issue_key == epic_key:
                                        logger.info(f"⚠️ Epic 자체를 발견하여 제외: {issue_key}")
                                        continue
                                    
                                    # Epic 타입도 제외
                                    if issue_type in ['Epic', '에픽']:
                                        logger.info(f"⚠️ Epic 타입 발견하여 제외: {issue_key} ({issue_type})")
                                        continue
                                    
                                    # status 안전하게 추출
                                    status_obj = fields.get('status')
                                    status_name = 'N/A'
                                    if status_obj and isinstance(status_obj, dict):
                                        status_name = status_obj.get('name', 'N/A')
                                    
                                    # assignee 안전하게 추출
                                    assignee_obj = fields.get('assignee')
                                    assignee_name = 'N/A'
                                    if assignee_obj and isinstance(assignee_obj, dict):
                                        assignee_name = assignee_obj.get('displayName', 'N/A')
                                    
                                    # summary 안전하게 추출
                                    summary = fields.get('summary', 'N/A')
                                    
                                    # story_points 안전하게 추출 (ENOMIX: customfield_10105, WORK: customfield_10124)
                                    story_points_data = self._extract_story_points(fields)
                                    
                                    # description 안전하게 추출 (panel 필터링 적용)
                                    description = fields.get('description', '')
                                    if description and isinstance(description, dict):
                                        description = self._extract_text_from_adf(description)
                                    
                                    # 중복 체크 후 추가 (comments만 제외)
                                    if issue_key not in subtasks_dict:
                                        subtask = {
                                            'key': issue_key,
                                            'summary': summary,
                                            'status': status_name,
                                            'issue_type': issue_type,
                                            'assignee': assignee_name,
                                            'story_points': story_points_data['story_points'],  # M/D 단위
                                            'story_points_original': story_points_data.get('story_points_original'),
                                            'story_points_unit': story_points_data.get('story_points_unit'),
                                            'description': description if description else None
                                        }
                                        subtasks_dict[issue_key] = subtask
                                        found_count += 1
                                        
                                except Exception as issue_error:
                                    logger.warning(f"⚠️ 이슈 처리 중 오류 ({issue.get('key', 'Unknown')}): {str(issue_error)}")
                                    continue
                            
                            jql_result["added"] = found_count
                            
                            # 조기 종료 체크 (found_count와 무관하게 전체 dict 크기로 판단)
                            should_break = False
                            if i == 1 and len(subtasks_dict) >= 1:
                                logger.info(f"✅✅✅ 1번 JQL(Epic ID)에서 {len(subtasks_dict)}개 발견, 즉시 종료 ✅✅✅")
                                should_break = True
                            elif i <= 3 and len(subtasks_dict) >= 5:
                                logger.info(f"✅ Epic ID 기반 JQL에서 {len(subtasks_dict)}개 발견, 조기 종료")
                                should_break = True
                            elif len(subtasks_dict) >= 30:
                                logger.info(f"✅ 충분한 하위 작업({len(subtasks_dict)}개)을 찾아 조기 종료")
                                should_break = True
                            
                            if found_count > 0:
                                logger.info(f"✅ JQL {i}에서 {found_count}개 하위 작업 추가 (현재 총 {len(subtasks_dict)}개)")
                            
                            jql_results.append(jql_result)
                            
                            if should_break:
                                break
                    else:
                        logger.warning(f"JQL {i} 실패: {response.status_code}")
                        jql_results.append({
                            "jql": jql,
                            "status": "failed",
                            "status_code": response.status_code
                        })
                        
                except Exception as e:
                    logger.warning(f"JQL {i} 오류: {str(e)}")
                    jql_results.append({
                        "jql": jql,
                        "status": "error",
                        "error": str(e)
                    })
                    continue
            
            # 모든 검색 완료 후 최종 결과 반환
            if subtasks_dict:
                subtasks_list = list(subtasks_dict.values())
                logger.info(f"✅ 최종 Epic 하위 작업 조회 완료: {len(subtasks_list)}개")
                
                # 디버깅 정보 추가
                debug_info = {
                    "epic_id": epic_id if epic_id else "N/A",
                    "total_jql_tried": len(jql_queries),
                    "final_count": len(subtasks_list),
                    "jql_results": jql_results if 'jql_results' in locals() else []
                }
                
                return {
                    "success": True,
                    "epic_key": epic_key,
                    "subtasks": subtasks_list,
                    "total": len(subtasks_list),
                    "jql_used": "Epic ID-based parent search",
                    "debug": debug_info
                }
            else:
                logger.error(f"❌ 모든 검색 방법 실패: {epic_key}")
                return {
                    "success": False,
                    "epic_key": epic_key,
                    "subtasks": [],
                    "total": 0,
                    "error": f"Epic '{epic_key}'의 하위 작업을 찾을 수 없습니다. Jira 설정을 확인해주세요.",
                    "tried_queries": jql_queries
                }
                
        except Exception as e:
            logger.error(f"❌ Epic 하위 Task 검색 오류: {str(e)}")
            return {
                "success": False,
                "epic_key": epic_key,
                "subtasks": [],
                "total": 0,
                "error": str(e)
            }


    def search_completed_epics(self) -> List[Dict[str, Any]]:
        """완료된 Epic 목록 조회 (구축 관련, ENOMIX 프로젝트만)"""
        try:
            search_url = f"{self.jira_url}/rest/api/3/search/jql"
            
            # JQL: 완료된 Epic만 조회 (ENOMIX 프로젝트만)
            jql = f'''
                project = ENOMIX
                AND issuetype = Epic 
                AND status = Done 
                AND assignee != empty 
                AND textfields ~ "구축*"
                ORDER BY created DESC
            '''
            
            logger.info(f"🔍 ENOMIX 프로젝트의 완료된 Epic 검색 중...")
            
            params = {
                'jql': jql,
                'maxResults': 100,
                'fields': 'key,summary,status,assignee'
            }
            
            logger.info(f"🔍 완료된 Epic 검색 시작")
            response = self.session.get(search_url, params=params)
            
            if response.status_code == 200:
                results = response.json()
                issues = results.get('issues', [])
                logger.info(f"✅ 완료된 Epic 검색 성공: {len(issues)}개")
                
                epics = []
                for issue in issues:
                    epics.append({
                        'key': issue['key'],
                        'summary': issue['fields']['summary'],
                        'status': issue['fields']['status']['name'],
                        'assignee': issue['fields'].get('assignee', {}).get('displayName', 'N/A') if issue['fields'].get('assignee') else 'N/A'
                    })
                
                return epics
            else:
                logger.error(f"❌ 완료된 Epic 검색 실패: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ 완료된 Epic 검색 오류: {str(e)}")
            return []
    
    def test_epic_basic_info(self, epic_key: str) -> Dict[str, Any]:
        """Epic 기본 정보 조회 테스트 - JQL 테스트와 동일한 방식 사용"""
        try:
            search_url = f"{self.jira_url}/rest/api/3/search/jql"
            
            # JQL 테스트와 동일한 방식 사용
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            params = {
                'jql': f'key = {epic_key}',
                'maxResults': 10,
                'fields': 'key,summary,status,issuetype,assignee',
                'expand': 'changelog'
            }
            
            logger.info(f"🔍 Epic 조회 요청 URL: {search_url}")
            logger.info(f"🔍 Epic 조회 요청 파라미터: {params}")
            logger.info(f"🔍 Epic 조회 요청 헤더: {headers}")
            
            response = self.session.get(search_url, params=params, headers=headers)
            
            logger.info(f"🔍 Epic 조회 응답 상태: {response.status_code}")
            logger.info(f"🔍 Epic 조회 응답 내용: {response.text[:500]}...")
            
            if response.status_code == 200:
                results = response.json()
                total = results.get('total', 0)
                issues = results.get('issues', [])
                issues_count = len(issues)
                logger.info(f"🔍 Epic 조회 결과: total={total}, issues_count={issues_count}")
                
                if issues_count > 0:
                    epic_info = issues[0]
                    logger.info(f"✅ Epic 조회 성공: {epic_info['key']} - {epic_info['fields']['summary']}")
                    return epic_info
                else:
                    logger.warning(f"Epic 조회 결과 없음: {epic_key}")
            else:
                logger.error(f"Epic 조회 실패: {response.status_code} - {response.text}")
            
            logger.warning(f"Epic 조회 실패: {epic_key}")
            return None
                
        except Exception as e:
            logger.error(f"Epic 조회 오류: {str(e)}")
            return None
    
    def get_issue_by_key(self, ticket_key: str) -> List[Dict]:
        """특정 티켓 조회"""
        try:
            # API v3 사용
            url = f"{self.jira_url}/rest/api/3/issue/{ticket_key}"
            params = {
                'fields': 'summary,description,status,assignee,created,updated,issuetype,customfield_10105,customfield_10124,customfield_10016,customfield_10020,customfield_10021'
            }
            
            logger.info(f"🔄 Jira API 호출: {url}")
            logger.info(f"🔄 요청 필드: {params['fields']}")
            response = self.session.get(url, params=params)
            
            logger.info(f"🔄 응답 상태 코드: {response.status_code}")
            logger.info(f"🔄 응답 내용: {response.text[:200]}...")
            
            if response.status_code == 200:
                data = response.json()
                fields = data.get('fields', {})
                logger.info(f"🔄 사용 가능한 필드들: {list(fields.keys())}")
                
                # 티켓 타입 검증
                issue_type = fields.get('issuetype', {})
                issue_type_name = issue_type.get('name', '') if issue_type else ''
                logger.info(f"🔄 티켓 타입: {issue_type_name}")
                
                # 허용된 티켓 타입들
                allowed_types = ['작업', '스토리', '버그', 'Story', 'Task', 'Bug']
                
                if issue_type_name not in allowed_types:
                    logger.warning(f"⚠️ 허용되지 않은 티켓 타입: {issue_type_name}")
                    logger.warning(f"⚠️ 허용된 타입: {allowed_types}")
                    logger.warning(f"⚠️ 티켓 '{ticket_key}' 동기화 건너뜀")
                    return []
                
                logger.info(f"✅ 허용된 티켓 타입: {issue_type_name}")
                
                # Story Points 관련 필드들 확인
                for field_key in ['customfield_10105', 'customfield_10124', 'customfield_10016', 'customfield_10020', 'customfield_10021']:
                    if field_key in fields:
                        logger.info(f"🔄 {field_key}: {fields[field_key]} (타입: {type(fields[field_key]).__name__})")
                
                # 숫자 값이 있는 모든 필드 확인
                logger.info(f"🔄 숫자 값이 있는 필드들:")
                for key, value in fields.items():
                    if isinstance(value, (int, float)) and value > 0:
                        logger.info(f"  - {key}: {value} (타입: {type(value).__name__})")
                
                # 단일 이슈를 리스트로 변환
                issues = [data] if data else []
                
                if not issues:
                    logger.warning(f"⚠️ 티켓 '{ticket_key}'를 찾을 수 없습니다")
                    return []
                
                logger.info(f"✅ 티켓 '{ticket_key}' 조회 성공")
                return issues
            else:
                logger.error(f"❌ Jira 티켓 조회 실패: {response.status_code}")
                logger.error(f"❌ 응답 내용: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Jira 티켓 조회 오류: {str(e)}")
            return []
    
    def extract_effort_data(self, issues: List[Dict]) -> List[EffortEstimation]:
        """Jira 이슈에서 공수 산정 데이터 추출"""
        estimations = []
        
        for issue in issues:
            try:
                fields = issue.get('fields', {})
                
                # 기본 정보 추출
                jira_ticket = issue.get('key', '')
                title = fields.get('summary', '')
                
                # Story Points 추출 (M/D 단위로 통일)
                story_points_data = self._extract_story_points(fields)
                logger.info(f"🔄 추출된 Story Points: {story_points_data['story_points']} M/D (원본: {story_points_data['story_points_original']} {story_points_data['story_points_unit']})")
                
                # 담당자 정보
                assignee = fields.get('assignee', {})
                logger.info(f"🔄 assignee 필드: {assignee} (타입: {type(assignee).__name__})")
                
                if assignee:
                    if isinstance(assignee, dict):
                        team_member = assignee.get('displayName', '') or assignee.get('name', '') or assignee.get('emailAddress', '')
                    elif isinstance(assignee, str):
                        team_member = assignee
                    else:
                        team_member = str(assignee)
                else:
                    team_member = None
                
                logger.info(f"🔄 추출된 담당자: {team_member}")
                
                # 상태 정보
                status = fields.get('status', {}).get('name', '')
                
                # Description 추출 및 필터링
                description = fields.get('description', '')
                if description:
                    # ADF(Atlassian Document Format) 형식인 경우 텍스트 추출
                    if isinstance(description, dict):
                        description = self._extract_text_from_adf(description)
                    # TODO: (n), (/) 필터링 로직 추가 필요 (사용자 확인 후)
                
                # Story Point 기반 공수 산정 데이터 생성
                sp_value = story_points_data['story_points'] or 0
                sp_original = story_points_data.get('story_points_original')
                sp_unit = story_points_data.get('story_points_unit')
                
                logger.info(f"📊 EffortEstimation 생성 준비: story_points={sp_value} (원본: {sp_original} {sp_unit})")
                
                estimation = EffortEstimation(
                    jira_ticket=jira_ticket,
                    title=title,
                    story_points=sp_value,
                    estimation_reason=None,  # 수동 입력만 사용
                    team_member=team_member,
                    description=description if description else None,
                    comments=None,  # 파일 용량 절감 (comments는 제외)
                    notes=f"상태: {status}",
                    story_points_original=sp_original,
                    story_points_unit=sp_unit
                )
                
                logger.info(f"✅ EffortEstimation 생성 완료: {jira_ticket} story_points={estimation.story_points}")
                
                estimations.append(estimation)
                
            except Exception as e:
                logger.error(f"❌ 이슈 데이터 추출 실패 ({issue.get('key', 'Unknown')}): {str(e)}")
                continue
        
        return estimations
    
    def _extract_story_points(self, fields: Dict) -> Dict[str, Any]:
        """Jira 필드에서 Story Points 추출 (M/D 단위로 통일)
        
        Returns:
            dict: {
                'story_points': float,  # M/D 단위
                'story_points_original': float,  # 원본 값
                'story_points_unit': str  # 원본 단위 (M/D 또는 M/M)
            }
        """
        try:
            logger.info(f"🔄 Story Points 추출 시작. 사용 가능한 필드: {list(fields.keys())}")
            
            # 우선순위 필드들 (실제 Story Points 필드가 맨 앞)
            priority_fields = [
                'customfield_10105',  # ENOMIX Story Points 필드 (M/D)
                'customfield_10124',  # WORK 프로젝트 "분석 공수(M/M)-work" 필드
                'customfield_10016',  # 일반적인 Story Points 필드
                'customfield_10020', 'customfield_10021', 'customfield_10014', 
                'customfield_10015', 'customfield_10017', 'customfield_10019'
            ]
            
            # 우선순위 필드에서 Story Points 찾기
            for field_key in priority_fields:
                if field_key in fields:
                    field_value = fields[field_key]
                    logger.info(f"🔄 Story Points 필드 확인: {field_key} = {field_value} (타입: {type(field_value).__name__})")
                    
                    if field_value is not None:
                        # 숫자 값인 경우
                        if isinstance(field_value, (int, float)) and field_value > 0:
                            original_value = float(field_value)
                            
                            # WORK 프로젝트의 M/M 필드인 경우 M/D로 변환 (1 M/M = 20 M/D)
                            if field_key == 'customfield_10124':
                                converted_value = original_value * 20
                                logger.info(f"✅ WORK 공수 발견: {original_value} M/M → {converted_value} M/D")
                                return {
                                    'story_points': converted_value,
                                    'story_points_original': original_value,
                                    'story_points_unit': 'M/M'
                                }
                            else:
                                # ENOMIX Story Points (이미 M/D 단위)
                                logger.info(f"✅ Story Points 발견: {field_key} = {original_value} M/D")
                                return {
                                    'story_points': original_value,
                                    'story_points_original': original_value,
                                    'story_points_unit': 'M/D'
                                }
                        # 문자열인 경우
                        elif isinstance(field_value, str) and field_value.strip():
                            try:
                                original_value = float(field_value)
                                if original_value > 0:
                                    # WORK 프로젝트의 M/M 필드인 경우 변환
                                    if field_key == 'customfield_10124':
                                        converted_value = original_value * 20
                                        logger.info(f"✅ WORK 공수 발견: {original_value} M/M → {converted_value} M/D")
                                        return {
                                            'story_points': converted_value,
                                            'story_points_original': original_value,
                                            'story_points_unit': 'M/M'
                                        }
                                    else:
                                        logger.info(f"✅ Story Points 발견: {field_key} = {original_value} M/D")
                                        return {
                                            'story_points': original_value,
                                            'story_points_original': original_value,
                                            'story_points_unit': 'M/D'
                                        }
                            except ValueError:
                                logger.info(f"⚠️ 숫자 변환 실패: {field_key} = {field_value}")
                        # 딕셔너리인 경우
                        elif isinstance(field_value, dict):
                            logger.info(f"🔄 딕셔너리 필드: {field_key} = {field_value}")
                            for sub_key in ['value', 'name', 'id']:
                                if sub_key in field_value:
                                    sub_value = field_value[sub_key]
                                    try:
                                        if isinstance(sub_value, (int, float)) and sub_value > 0:
                                            original_value = float(sub_value)
                                            if field_key == 'customfield_10124':
                                                converted_value = original_value * 20
                                                logger.info(f"✅ WORK 공수 발견: {original_value} M/M → {converted_value} M/D")
                                                return {
                                                    'story_points': converted_value,
                                                    'story_points_original': original_value,
                                                    'story_points_unit': 'M/M'
                                                }
                                            else:
                                                logger.info(f"✅ Story Points 발견: {field_key}.{sub_key} = {original_value} M/D")
                                                return {
                                                    'story_points': original_value,
                                                    'story_points_original': original_value,
                                                    'story_points_unit': 'M/D'
                                                }
                                        elif isinstance(sub_value, str) and sub_value.strip():
                                            original_value = float(sub_value)
                                            if original_value > 0:
                                                if field_key == 'customfield_10124':
                                                    converted_value = original_value * 20
                                                    logger.info(f"✅ WORK 공수 발견: {original_value} M/M → {converted_value} M/D")
                                                    return {
                                                        'story_points': converted_value,
                                                        'story_points_original': original_value,
                                                        'story_points_unit': 'M/M'
                                                    }
                                                else:
                                                    logger.info(f"✅ Story Points 발견: {field_key}.{sub_key} = {original_value} M/D")
                                                    return {
                                                        'story_points': original_value,
                                                        'story_points_original': original_value,
                                                        'story_points_unit': 'M/D'
                                                    }
                                    except (ValueError, TypeError):
                                        pass
                        # 리스트인 경우
                        elif isinstance(field_value, list) and field_value:
                            logger.info(f"🔄 리스트 필드: {field_key} = {field_value}")
                            for item in field_value:
                                if isinstance(item, (int, float)) and item > 0:
                                    original_value = round(float(item), 2)
                                    if field_key == 'customfield_10124':
                                        converted_value = round(original_value * 20, 2)
                                        logger.info(f"✅ WORK 공수 발견: {original_value} M/M → {converted_value} M/D")
                                        return {
                                            'story_points': converted_value,
                                            'story_points_original': original_value,
                                            'story_points_unit': 'M/M'
                                        }
                                    else:
                                        logger.info(f"✅ Story Points 발견: {field_key} = {original_value} M/D")
                                        return {
                                            'story_points': original_value,
                                            'story_points_original': original_value,
                                            'story_points_unit': 'M/D'
                                        }
                                elif isinstance(item, str) and item.strip():
                                    try:
                                        original_value = round(float(item), 2)
                                        if original_value > 0:
                                            if field_key == 'customfield_10124':
                                                converted_value = round(original_value * 20, 2)
                                                logger.info(f"✅ WORK 공수 발견: {original_value} M/M → {converted_value} M/D")
                                                return {
                                                    'story_points': converted_value,
                                                    'story_points_original': original_value,
                                                    'story_points_unit': 'M/M'
                                                }
                                            else:
                                                logger.info(f"✅ Story Points 발견: {field_key} = {original_value} M/D")
                                                return {
                                                    'story_points': original_value,
                                                    'story_points_original': original_value,
                                                    'story_points_unit': 'M/D'
                                                }
                                    except ValueError:
                                        pass
                        # None이 아닌 경우 (0도 포함)
                        elif field_value == 0:
                            logger.info(f"⚠️ Story Points가 0입니다: {field_key} = {field_value}")
                            return {'story_points': 0.0, 'story_points_original': 0.0, 'story_points_unit': 'M/D'}
                        else:
                            logger.info(f"⚠️ 예상치 못한 필드 타입: {field_key} = {field_value} (타입: {type(field_value).__name__})")
            
            # 우선순위 필드에서 찾지 못한 경우 모든 숫자 필드 확인
            logger.info("🔄 우선순위 필드에서 Story Points를 찾지 못함. 모든 숫자 필드 확인 중...")
            for field_key, field_value in fields.items():
                if 'customfield' in field_key and field_value is not None:
                    if isinstance(field_value, (int, float)) and 0.5 <= field_value <= 100:
                        original_value = round(float(field_value), 2)
                        logger.info(f"✅ Story Points 후보 발견: {field_key} = {original_value}")
                        # M/D로 가정
                        return {
                            'story_points': original_value,
                            'story_points_original': original_value,
                            'story_points_unit': 'M/D'
                        }
            
            logger.info(f"⚠️ Story Points 필드를 찾을 수 없습니다.")
            return {'story_points': 0.0, 'story_points_original': 0.0, 'story_points_unit': 'M/D'}
        except Exception as e:
            logger.error(f"❌ Story Points 추출 오류: {str(e)}")
            return {'story_points': 0.0, 'story_points_original': 0.0, 'story_points_unit': 'M/D'}
    
    def _extract_reason_from_description(self, description: str) -> Optional[str]:
        """설명에서 산정 이유 추출"""
        if not description:
            return None
        
        # 간단한 키워드 기반 추출
        reason_keywords = ['산정', '예상', '복잡', '단순', '기존', '새로운']
        for keyword in reason_keywords:
            if keyword in description:
                return f"설명에서 추출: {description[:100]}..."
        
        return None
    
    def _extract_comments(self, fields: Dict) -> Optional[str]:
        """Jira 댓글 추출 및 병합"""
        try:
            comment_obj = fields.get('comment')
            if not comment_obj:
                return None
            
            comments = comment_obj.get('comments', [])
            if not comments:
                return None
            
            # 댓글들을 텍스트로 병합
            comment_texts = []
            for comment in comments:
                try:
                    # 작성자
                    author = comment.get('author', {})
                    author_name = 'Unknown'
                    if isinstance(author, dict):
                        author_name = author.get('displayName', author.get('name', 'Unknown'))
                    
                    # 댓글 본문 (ADF 형식일 수 있음)
                    body = comment.get('body', '')
                    
                    # ADF(Atlassian Document Format) 형식인 경우 텍스트 추출
                    if isinstance(body, dict):
                        body_text = self._extract_text_from_adf(body)
                    elif isinstance(body, str):
                        body_text = body
                    else:
                        body_text = str(body)
                    
                    if body_text and body_text.strip():
                        comment_texts.append(f"[{author_name}]: {body_text.strip()}")
                
                except Exception as comment_error:
                    logger.warning(f"⚠️ 댓글 추출 중 오류: {str(comment_error)}")
                    continue
            
            if comment_texts:
                return " | ".join(comment_texts)
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ 댓글 추출 오류: {str(e)}")
            return None
    
    def _extract_text_from_adf(self, adf_content: Dict) -> str:
        """ADF(Atlassian Document Format)에서 텍스트 추출 (panel 필터링 적용)"""
        try:
            texts = []
            
            def extract_text_recursive(node, skip_content=False):
                if isinstance(node, dict):
                    node_type = node.get('type', '')
                    
                    # panel 타입인 경우 panelType 확인
                    if node_type == 'panel':
                        attrs = node.get('attrs', {})
                        panel_type = attrs.get('panelType', '')
                        
                        # panelType이 "error"이면 건너뜀 (n)
                        if panel_type == 'error':
                            logger.debug(f"⚠️ panel (error) 건너뜀")
                            return  # 이 panel의 content는 무시
                        
                        # panelType이 "success"이면 포함 (/)
                        elif panel_type == 'success':
                            logger.debug(f"✅ panel (success) 포함")
                            # content를 계속 처리
                    
                    # text 타입이면 텍스트 추출
                    if not skip_content and node_type == 'text':
                        text = node.get('text', '')
                        if text:
                            texts.append(text)
                    
                    # hardBreak를 줄바꿈으로 변환
                    if not skip_content and node_type == 'hardBreak':
                        texts.append('\n')
                    
                    # content가 있으면 재귀 탐색
                    if 'content' in node and isinstance(node['content'], list):
                        for child in node['content']:
                            extract_text_recursive(child, skip_content)
                    
                    # 블록 요소 끝에 줄바꿈 추가
                    if not skip_content and node_type in ['paragraph', 'listItem', 'heading', 'codeBlock', 'blockquote']:
                        # 마지막 텍스트가 줄바꿈이 아니면 추가
                        if texts and texts[-1] != '\n':
                            texts.append('\n')
                
                elif isinstance(node, list):
                    for item in node:
                        extract_text_recursive(item, skip_content)
            
            extract_text_recursive(adf_content)
            
            # 텍스트 그대로 합치기 (줄바꿈 보존)
            result = ''.join(texts)
            
            # 연속된 빈 줄 제거 (3개 이상의 연속 줄바꿈을 2개로)
            result = re.sub(r'\n{3,}', '\n\n', result)
            
            return result.strip()
            
        except Exception as e:
            logger.warning(f"⚠️ ADF 텍스트 추출 오류: {str(e)}")
            return str(adf_content)
    
    def sync_ticket_data(self, ticket_key: str, major_category: str = None, minor_category: str = None, sub_category: str = None) -> dict:
        """특정 티켓 데이터 동기화"""
        try:
            logger.info(f"🔄 티켓 '{ticket_key}' 데이터 동기화 시작")
            
            # Jira에서 티켓 조회
            issues = self.get_issue_by_key(ticket_key)
            if not issues:
                logger.warning(f"⚠️ 티켓 '{ticket_key}'를 찾을 수 없거나 허용되지 않은 타입입니다")
                return {"success": False, "reason": "not_found_or_invalid_type"}
            
            # 공수 산정 데이터 추출
            estimations = self.extract_effort_data(issues)
            if not estimations:
                logger.warning(f"⚠️ 티켓 '{ticket_key}'에서 공수 데이터를 추출할 수 없습니다")
                return {"success": False, "reason": "no_estimation_data"}
            
            # 카테고리 정보 추가
            for estimation in estimations:
                if major_category:
                    estimation.major_category = major_category
                if minor_category:
                    estimation.minor_category = minor_category
                if sub_category:
                    estimation.sub_category = sub_category
            
            # 기존 데이터에 추가/업데이트
            added_count = 0
            updated_count = 0
            for estimation in estimations:
                # 기존 데이터 확인
                existing = None
                if estimation.jira_ticket:
                    for existing_est in effort_manager.estimations:
                        if existing_est.jira_ticket == estimation.jira_ticket:
                            existing = existing_est
                            break
                
                if effort_manager.add_estimation(estimation):
                    if existing:
                        updated_count += 1
                    else:
                        added_count += 1
            
            logger.info(f"✅ 티켓 '{ticket_key}' 동기화 완료: {added_count}개 추가, {updated_count}개 업데이트")
            return {"success": True, "added": added_count, "updated": updated_count}
            
        except Exception as e:
            logger.error(f"❌ 티켓 '{ticket_key}' 동기화 실패: {str(e)}")
            return {"success": False, "reason": "error", "error": str(e)}

def create_jira_integration() -> Optional[JiraIntegration]:
    """환경 변수에서 Jira 설정을 읽어 연동 객체 생성"""
    jira_url = os.getenv('JIRA_URL')
    jira_username = os.getenv('JIRA_USERNAME')
    jira_api_token = os.getenv('JIRA_API_TOKEN')
    
    if not all([jira_url, jira_username, jira_api_token]):
        logger.warning("⚠️ Jira 환경 변수가 설정되지 않았습니다")
        return None
    
    return JiraIntegration(jira_url, jira_username, jira_api_token)
