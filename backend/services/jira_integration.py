"""
Jira 연동 모듈
Jira API를 통한 공수 산정 데이터 수집
"""

import requests
import logging
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
    
    def test_epic_subtasks(self, epic_key: str) -> dict:
        """Epic의 하위 Task들 조회 테스트"""
        try:
            # 먼저 Epic 자체가 존재하는지 확인 (타입 검증 완화)
            epic_info = self.test_epic_basic_info(epic_key)
            if not epic_info:
                logger.warning(f"⚠️ Epic '{epic_key}' 조회 실패, 직접 하위 작업 조회 시도")
                # Epic 조회가 실패해도 직접 하위 작업 조회 시도
            else:
                logger.info(f"✅ Epic '{epic_key}' 조회 성공, 하위 작업 조회 진행")
            
            search_url = f"{self.jira_url}/rest/api/3/search/jql"
            fields = 'key,summary,status,issuetype,assignee,customfield_10105'
            
            # 여러 JQL 쿼리 시도 (효과적인 것부터)
            project_key = epic_key.split("-")[0]
            jql_queries = [
                f'"Epic Link" = {epic_key}',  # 가장 효과적인 Epic 하위 작업 조회
                f'parent = {epic_key}',  # 부모-자식 관계
                f'epic = {epic_key}',  # Epic 필드
                f'project = {project_key} AND "Epic Link" = {epic_key}',  # 프로젝트 + Epic Link
                f'project = {project_key} AND parent = {epic_key}',  # 프로젝트 + 부모
                f'project = {project_key} AND issuetype in (Task, Story, Bug) AND "Epic Link" = {epic_key}',  # 작업 타입 + Epic Link
                f'project = {project_key} AND issuetype in (Task, Story, Bug) AND parent = {epic_key}',  # 작업 타입 + 부모
                f'parent in ({epic_key})',  # 부모 IN
                f'"Epic Link" in ({epic_key})',  # Epic Link IN
                f'issue in linkedIssues({epic_key}, "is child of")',  # 링크된 이슈 (자식)
                f'issue in linkedIssues({epic_key})',  # 링크된 이슈
                f'key = {epic_key}',  # Epic 자체
                f'project = {project_key} AND key = {epic_key}',  # 프로젝트 + Epic
                f'project = {project_key} AND issuetype = Epic',  # 프로젝트의 모든 Epic
                f'project = {project_key}',  # 프로젝트의 모든 이슈
                f'issue in linkedIssues({epic_key}, "is parent of")',  # 링크된 이슈 (부모)
                f'issue in linkedIssues({epic_key}, "relates to")',  # 링크된 이슈 (관련)
                f'project = {project_key} AND summary ~ "{epic_key}"'  # 제목 검색
            ]
            
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
                        'maxResults': 50,
                        'fields': fields,
                        'expand': 'changelog'
                    }
                    
                    response = self.session.get(search_url, params=params, headers=headers)
                    
                    if response.status_code == 200:
                        results = response.json()
                        total = results.get('total', 0)
                        issues = results.get('issues', [])
                        issues_count = len(issues)
                        
                        logger.info(f"✅ JQL {i} 성공: total={total}, issues_count={issues_count}")
                        
                        if issues_count > 0:
                            subtasks = []
                            for issue in issues:
                                subtask = {
                                    'key': issue['key'],
                                    'summary': issue['fields']['summary'],
                                    'status': issue['fields']['status']['name'],
                                    'issue_type': issue['fields']['issuetype']['name'],
                                    'assignee': issue['fields'].get('assignee', {}).get('displayName', 'N/A'),
                                    'story_points': issue['fields'].get('customfield_10105', 0)
                                }
                                subtasks.append(subtask)
                            
                            logger.info(f"✅ Epic 하위 작업 조회 성공: {len(subtasks)}개")
                            return {
                                "success": True,
                                "epic_key": epic_key,
                                "subtasks": subtasks,
                                "total": len(subtasks),
                                "jql_used": jql
                            }
                        else:
                            logger.info(f"JQL {i}: 하위 작업 없음")
                    else:
                        logger.warning(f"JQL {i} 실패: {response.status_code}")
                        
                except Exception as e:
                    logger.warning(f"JQL {i} 오류: {str(e)}")
                    continue
            
            # 모든 JQL이 실패한 경우
            logger.error(f"❌ 모든 JQL 쿼리 실패: {epic_key}")
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
                'fields': 'summary,description,status,assignee,created,updated,issuetype,customfield_10105,customfield_10016,customfield_10020,customfield_10021'
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
                for field_key in ['customfield_10105', 'customfield_10016', 'customfield_10020', 'customfield_10021']:
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
                
                # Story Points 추출
                story_points = self._extract_story_points(fields)
                logger.info(f"🔄 추출된 Story Points: {story_points}")
                
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
                
                # 설명에서 산정 이유 추출 시도
                description = fields.get('description', '')
                estimation_reason = self._extract_reason_from_description(description)
                
                # Story Point 기반 공수 산정 데이터 생성
                estimation = EffortEstimation(
                    jira_ticket=jira_ticket,
                    title=title,
                    story_points=story_points or 0,
                    estimation_reason=estimation_reason,
                    team_member=team_member,
                    description=description if description else None,
                    notes=f"상태: {status}"
                )
                
                logger.info(f"✅ 생성된 공수 산정 데이터: {estimation}")
                
                estimations.append(estimation)
                
            except Exception as e:
                logger.error(f"❌ 이슈 데이터 추출 실패 ({issue.get('key', 'Unknown')}): {str(e)}")
                continue
        
        return estimations
    
    def _extract_story_points(self, fields: Dict) -> float:
        """Jira 필드에서 Story Points 추출"""
        try:
            logger.info(f"🔄 Story Points 추출 시작. 사용 가능한 필드: {list(fields.keys())}")
            
            # 우선순위 필드들 (실제 Story Points 필드가 맨 앞)
            priority_fields = [
                'customfield_10105',  # 실제 Story Points 필드
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
                            logger.info(f"✅ Story Points 발견: {field_key} = {field_value}")
                            return float(field_value)
                        # 문자열인 경우
                        elif isinstance(field_value, str) and field_value.strip():
                            try:
                                num_value = float(field_value)
                                if num_value > 0:
                                    logger.info(f"✅ Story Points 발견: {field_key} = {field_value}")
                                    return float(num_value)
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
                                            logger.info(f"✅ Story Points 발견: {field_key}.{sub_key} = {sub_value}")
                                            return float(sub_value)
                                        elif isinstance(sub_value, str) and sub_value.strip():
                                            num_value = float(sub_value)
                                            if num_value > 0:
                                                logger.info(f"✅ Story Points 발견: {field_key}.{sub_key} = {sub_value}")
                                                return float(num_value)
                                    except (ValueError, TypeError):
                                        pass
                        # 리스트인 경우
                        elif isinstance(field_value, list) and field_value:
                            logger.info(f"🔄 리스트 필드: {field_key} = {field_value}")
                            for item in field_value:
                                if isinstance(item, (int, float)) and item > 0:
                                    logger.info(f"✅ Story Points 발견: {field_key} = {item}")
                                    return float(item)
                                elif isinstance(item, str) and item.strip():
                                    try:
                                        num_value = float(item)
                                        if num_value > 0:
                                            logger.info(f"✅ Story Points 발견: {field_key} = {item}")
                                            return float(num_value)
                                    except ValueError:
                                        pass
                        # None이 아닌 경우 (0도 포함)
                        elif field_value == 0:
                            logger.info(f"⚠️ Story Points가 0입니다: {field_key} = {field_value}")
                            return 0.0
                        else:
                            logger.info(f"⚠️ 예상치 못한 필드 타입: {field_key} = {field_value} (타입: {type(field_value).__name__})")
            
            # 우선순위 필드에서 찾지 못한 경우 모든 숫자 필드 확인
            logger.info("🔄 우선순위 필드에서 Story Points를 찾지 못함. 모든 숫자 필드 확인 중...")
            for field_key, field_value in fields.items():
                if 'customfield' in field_key and field_value is not None:
                    if isinstance(field_value, (int, float)) and 0.5 <= field_value <= 100:
                        logger.info(f"✅ Story Points 후보 발견: {field_key} = {field_value}")
                        return float(field_value)
            
            logger.info(f"⚠️ Story Points 필드를 찾을 수 없습니다.")
            return 0.0
        except Exception as e:
            logger.error(f"❌ Story Points 추출 오류: {str(e)}")
            return 0.0
    
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
