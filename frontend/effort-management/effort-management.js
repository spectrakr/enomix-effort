// 전역 변수
let currentPage = 1;
let currentPageSize = 100;
let currentPagination = null;
let currentSearchTerm = '';
let excludedSourcesForQuestion = new Map(); // 질문별로 제외된 소스 목록 관리

// 탭 전환 함수 (대시보드 스타일)
function switchTab(tabName) {
  console.log('Switching to tab:', tabName);
  
  // 강제로 모든 active 클래스 제거
  const allNavItems = document.querySelectorAll('.nav-item');
  const allTabContents = document.querySelectorAll('.tab-content');
  
  console.log('Found nav items:', allNavItems.length);
  console.log('Found tab contents:', allTabContents.length);
  
  // 모든 네비게이션 아이템 비활성화
  allNavItems.forEach((item, index) => {
    item.classList.remove('active');
    console.log(`Removed active from nav item ${index}:`, item.getAttribute('data-tab'));
  });
  
  // 모든 탭 콘텐츠 비활성화
  allTabContents.forEach((content, index) => {
    content.classList.remove('active');
    console.log(`Removed active from tab content ${index}:`, content.id);
  });
  
  // 잠시 대기 후 활성화 (DOM 업데이트 보장)
  setTimeout(() => {
    // 선택된 네비게이션 아이템 활성화
    const targetNavItem = document.querySelector(`[data-tab="${tabName}"]`);
    if (targetNavItem) {
      targetNavItem.classList.add('active');
      console.log('✅ Activated nav item for:', tabName);
    } else {
      console.log('❌ Nav item not found for:', tabName);
    }
    
    // 선택된 콘텐츠 활성화
    const targetContent = document.getElementById(tabName);
    if (targetContent) {
      targetContent.classList.add('active');
      console.log('✅ Activated content for:', tabName);
    } else {
      console.log('❌ Content not found for:', tabName);
    }
    
    // 탭별 초기화
    if (tabName === 'stats') {
      loadStatistics();
    } else if (tabName === 'list') {
      loadEffortList();
    } else if (tabName === 'add') {
      loadMajorCategories();
    } else if (tabName === 'sync') {
      loadSyncMajorCategories();
    }
  }, 10);
}

// 공수 산정 데이터 추가
async function addEffortData() {
  const jiraTicket = document.getElementById("jiraTicket").value.trim();
  const title = document.getElementById("title").value.trim();
  const storyPoints = parseFloat(document.getElementById("storyPoints").value);
  const teamMember = document.getElementById("teamMember").value.trim();
  const estimationReason = document.getElementById("estimationReason").value.trim();
  const majorCategory = document.getElementById("majorCategory").value;
  const minorCategory = document.getElementById("minorCategory").value;
  const subCategory = document.getElementById("subCategory").value;

  if (!jiraTicket || !title || !storyPoints) {
    alert("필수 필드를 모두 입력하세요.");
    return;
  }

  // 카테고리는 선택사항이므로 검증하지 않음

  try {
    const formData = new FormData();
    formData.append("jira_ticket", jiraTicket);
    formData.append("title", title);
    formData.append("story_points", storyPoints);
    formData.append("team_member", teamMember);
    formData.append("estimation_reason", estimationReason);
    formData.append("major_category", majorCategory);
    formData.append("minor_category", minorCategory);
    formData.append("sub_category", subCategory);

    const res = await fetch("/effort/add/", { method: "POST", body: formData });
    const result = await res.json();

    if (res.ok) {
      alert("✅ " + result.message);
      document.getElementById("effortForm").reset();
      // 카테고리 드롭다운 초기화
      loadMajorCategories();
    } else {
      alert("❌ " + result.error);
    }
  } catch (err) {
    alert("❌ 데이터 추가 실패");
    console.error(err);
  }
}

// Jira 데이터 동기화
async function syncJiraData() {
  const ticketKey = document.getElementById("jiraTicketKey").value.trim();
  const statusDiv = document.getElementById("syncStatus");
  
  if (!ticketKey) return alert("Jira 티켓 키를 입력하세요.");

  // 카테고리 정보 수집 (선택사항)
  const majorCategory = document.getElementById("syncMajorCategory").value;
  const minorCategory = document.getElementById("syncMinorCategory").value;
  const subCategory = document.getElementById("syncSubCategory").value;

  try {
    statusDiv.style.display = "block";
    const formData = new FormData();
    formData.append("ticket_key", ticketKey);
    // 카테고리 정보 추가 (필수)
    formData.append("major_category", majorCategory);
    formData.append("minor_category", minorCategory);
    formData.append("sub_category", subCategory);

    const res = await fetch("/effort/sync-jira/", { method: "POST", body: formData });
    const result = await res.json();
    statusDiv.style.display = "none";

    if (res.ok) {
      alert("✅ " + result.message);
      document.getElementById("jiraTicketKey").value = "";
      // 카테고리 드롭다운 초기화
      loadSyncMajorCategories();
    } else {
      alert("❌ " + result.error);
    }
  } catch (err) {
    statusDiv.style.display = "none";
    alert("❌ Jira 동기화 실패");
    console.error(err);
  }
}

// 질문-답변 매핑 저장 (피드백 저장용)
const questionAnswerMapping = new Map();

// 공수 산정 질문
async function askEffortQuestion() {
  const question = document.getElementById('effortQuestion').value.trim();
  const chatBox = document.getElementById("chatBox");
  const loading = document.getElementById("effortLoading");
  
  if (!question) return alert("질문을 입력하세요.");

  // 새로운 질문이므로 제외된 소스 목록 초기화
  excludedSourcesForQuestion.set(question, new Set());

  const userBubble = document.createElement("div");
  userBubble.className = "chat-bubble user";
  userBubble.innerText = question;
  chatBox.appendChild(userBubble);
  document.getElementById("effortQuestion").value = "";
  
  // 사용자 질문 후 스크롤 하단 이동
  setTimeout(() => {
    chatBox.scrollTop = chatBox.scrollHeight;
  }, 50);

  try {
    loading.style.display = "block";
    const formData = new FormData();
    formData.append("question", question);

    const res = await fetch("/effort/ask/", { method: "POST", body: formData });
    const result = await res.json();
    loading.style.display = "none";

    const aiBubble = document.createElement("div");
    aiBubble.className = "chat-bubble ai";
    
    if (result.error) {
      aiBubble.innerText = "⚠️ 오류: " + result.error;
    } else {
      // 질문-답변 매핑 저장 (피드백 저장용)
      questionAnswerMapping.set(question, {
        answer: result.answer,
        sources: result.sources || []
      });
      
      // aiBubble에 원본 답변을 data 속성으로 저장 (피드백 저장용)
      aiBubble.setAttribute('data-original-answer', result.answer);
      aiBubble.setAttribute('data-question', question);
      
      // 마크다운을 HTML로 변환
      let htmlText = result.answer;
      // 줄바꿈을 <br> 태그로 변환
      htmlText = htmlText.replace(/\n/g, '<br>');
      // **텍스트** -> <strong>텍스트</strong> 변환
      htmlText = htmlText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      // Story Points와 예상공수에 특별한 클래스 추가
      htmlText = htmlText.replace(/\*\*Story Points\*\*/g, '<strong class="highlight-blue">Story Points</strong>');
      htmlText = htmlText.replace(/\*\*예상공수\*\*/g, '<strong class="highlight-blue">예상공수</strong>');
      aiBubble.innerHTML = htmlText;
      
      // 피드백에서 온 답변인지 표시
      if (result.is_from_feedback) {
        const feedbackHeader = document.createElement("div");
        feedbackHeader.className = "feedback-header";
        feedbackHeader.innerHTML = `
          <div style="background: #e8f5e8; padding: 8px 12px; border-radius: 6px; margin-bottom: 10px; font-size: 14px; color: #2e7d32; border-left: 4px solid #4caf50;">
            💡 검증된 답변 (사용자 피드백 기반)
          </div>
        `;
        aiBubble.insertBefore(feedbackHeader, aiBubble.firstChild);
      }
      
      // 피드백 UI 추가 (답변 품질 확인)
      if (result.feedback_enabled) {
        const feedbackContainer = document.createElement('div');
        feedbackContainer.className = 'feedback-container';
        feedbackContainer.innerHTML = `
          <div class="feedback-question">이 답변이 맞나요?</div>
          <div class="feedback-buttons">
            <button class="feedback-btn yes" onclick="handleFeedback('${question}', true, this, '${result.search_session_id}', ${JSON.stringify(result.sources).replace(/"/g, '&quot;')})">
              ✅ 네, 맞습니다
            </button>
            <button class="feedback-btn no" onclick="handleFeedback('${question}', false, this, '${result.search_session_id}', ${JSON.stringify(result.sources).replace(/"/g, '&quot;')})">
              ❌ 아니요, 다른 답변을 원합니다
            </button>
          </div>
        `;
        aiBubble.appendChild(feedbackContainer);
      }
    }
    
    chatBox.appendChild(aiBubble);
    
    // 스크롤을 맨 아래로 이동
    setTimeout(() => {
      chatBox.scrollTop = chatBox.scrollHeight;
    }, 100);
  } catch (err) {
    loading.style.display = "none";
    alert("❌ 질문 처리 실패");
    console.error(err);
  }
}

// 피드백 처리 함수
async function handleFeedback(question, isCorrect, buttonElement, searchSessionId, sources) {
  const feedbackContainer = buttonElement.closest('.feedback-container');
  const feedbackButtons = feedbackContainer.querySelector('.feedback-buttons');
  
  // 버튼 비활성화
  feedbackButtons.querySelectorAll('.feedback-btn').forEach(btn => {
    btn.disabled = true;
  });
  
  if (isCorrect) {
    // 긍정적 피드백 - 백엔드로 피드백 데이터 전송
    feedbackContainer.innerHTML = `
      <div class="feedback-question">✅ 감사합니다! 답변이 도움이 되었다니 기쁩니다.</div>
      <div class="feedback-loading">피드백을 저장하고 있습니다...</div>
    `;
    
    try {
      // aiBubble에서 원본 답변 가져오기 (가장 신뢰할 수 있는 방법)
      const aiBubble = buttonElement.closest('.ai-bubble');
      let answerText = '';
      
      if (aiBubble) {
        // data-original-answer 속성에서 답변 가져오기 (우선)
        answerText = aiBubble.getAttribute('data-original-answer') || '';
        
        // data-original-answer가 없으면 매핑에서 가져오기
        if (!answerText) {
          const qaMapping = questionAnswerMapping.get(question);
          if (qaMapping && qaMapping.answer) {
            answerText = qaMapping.answer;
          }
        }
        
        // 여전히 없으면 DOM에서 추출 시도 (최후의 수단)
        if (!answerText) {
          const clone = aiBubble.cloneNode(true);
          const feedbackHeader = clone.querySelector('.feedback-header');
          const feedbackContainer = clone.querySelector('.feedback-container');
          if (feedbackHeader) clone.removeChild(feedbackHeader);
          if (feedbackContainer) clone.removeChild(feedbackContainer);
          
          answerText = clone.textContent || clone.innerText || '';
          answerText = answerText.trim();
        }
      } else {
        // aiBubble을 찾지 못하면 매핑에서 가져오기
        const qaMapping = questionAnswerMapping.get(question);
        if (qaMapping && qaMapping.answer) {
          answerText = qaMapping.answer;
        }
      }
      
      // 답변 텍스트가 없으면 에러
      if (!answerText || answerText.length < 10) {
        console.error('❌ 답변 텍스트를 추출하지 못함:', { 
          question, 
          hasAiBubble: !!aiBubble,
          hasDataAttr: aiBubble ? aiBubble.getAttribute('data-original-answer') : null,
          answerText 
        });
        feedbackContainer.innerHTML = `
          <div class="feedback-question">❌ 답변 정보를 찾을 수 없습니다.</div>
        `;
        return;
      }
      
      console.log('📝 피드백 저장 시도:', { question, answerLength: answerText.length, sourcesCount: sources.length });
      
      // 백엔드로 긍정 피드백 전송
      const response = await fetch('/effort/feedback/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          answer: answerText,
          sources: sources,
          feedback_type: 'positive'
        })
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        feedbackContainer.innerHTML = `
          <div class="feedback-question">✅ 감사합니다! 답변이 도움이 되었다니 기쁩니다.</div>
          <div style="font-size: 12px; color: #666; margin-top: 5px;">💾 피드백이 저장되었습니다. 향후 유사한 질문에 더 정확한 답변을 제공할 수 있습니다.</div>
        `;
      } else {
        feedbackContainer.innerHTML = `
          <div class="feedback-question">✅ 감사합니다! 답변이 도움이 되었다니 기쁩니다.</div>
        `;
      }
    } catch (error) {
      console.error('피드백 저장 오류:', error);
      feedbackContainer.innerHTML = `
        <div class="feedback-question">✅ 감사합니다! 답변이 도움이 되었다니 기쁩니다.</div>
      `;
    }
  } else {
    // 부정적 피드백 - 재검색 요청
    feedbackContainer.innerHTML = `
      <div class="feedback-question">🔄 다른 답변을 찾아보겠습니다...</div>
      <div class="feedback-loading">AI가 다른 관련 정보를 검색 중입니다.</div>
    `;
    
    try {
      // 현재 질문에 대한 제외된 소스 목록 가져오기
      let excludedSourcesSet = excludedSourcesForQuestion.get(question) || new Set();
      
      // 현재 답변의 소스들을 제외 목록에 추가
      sources.forEach(source => {
        excludedSourcesSet.add(source.source);
      });
      
      // 업데이트된 제외 목록 저장
      excludedSourcesForQuestion.set(question, excludedSourcesSet);
      
      // 배열로 변환
      const excludedSources = Array.from(excludedSourcesSet);
      
      console.log(`🔄 누적 제외 소스 목록 (${excludedSources.length}개):`, excludedSources);
      
      const response = await fetch('/effort/ask-feedback/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          excluded_sources: excludedSources
        })
      });
      
      const result = await response.json();
      
      if (result.error) {
        feedbackContainer.innerHTML = `
          <div class="feedback-question">❌ 재검색 중 오류가 발생했습니다.</div>
          <div class="feedback-retry">
            ${result.error}
            <button class="feedback-retry-btn" onclick="askEffortQuestion()">다시 질문하기</button>
          </div>
        `;
        return;
      }
      
      // 새로운 답변 표시
      const chatBox = document.getElementById("chatBox");
      const newAiBubble = document.createElement("div");
      newAiBubble.className = "chat-bubble ai";
      
      // 피드백 검색임을 표시하는 헤더 추가
      const feedbackHeader = document.createElement("div");
      feedbackHeader.className = "feedback-header";
      feedbackHeader.innerHTML = `
        <div style="background: #e3f2fd; padding: 8px 12px; border-radius: 6px; margin-bottom: 10px; font-size: 14px; color: #1976d2; border-left: 4px solid #2196f3;">
          🔄 피드백 기반 재검색 결과 (이전 ${excludedSources.length}개 답변 제외)
        </div>
      `;
      newAiBubble.appendChild(feedbackHeader);
      
      // 마크다운을 HTML로 변환
      let htmlText = result.answer;
      htmlText = htmlText.replace(/\n/g, '<br>');
      htmlText = htmlText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      htmlText = htmlText.replace(/\*\*Story Points\*\*/g, '<strong class="highlight-blue">Story Points</strong>');
      htmlText = htmlText.replace(/\*\*예상공수\*\*/g, '<strong class="highlight-blue">예상공수</strong>');
      
      const answerDiv = document.createElement("div");
      answerDiv.innerHTML = htmlText;
      newAiBubble.appendChild(answerDiv);
      
      // 새로운 피드백 UI 추가
      if (result.feedback_enabled) {
        const newFeedbackContainer = document.createElement('div');
        newFeedbackContainer.className = 'feedback-container';
        newFeedbackContainer.innerHTML = `
          <div class="feedback-question">이 답변이 맞나요?</div>
          <div class="feedback-buttons">
            <button class="feedback-btn yes" onclick="handleFeedback('${question}', true, this, '${result.search_session_id}', ${JSON.stringify(result.sources).replace(/"/g, '&quot;')})">
              ✅ 네, 맞습니다
            </button>
            <button class="feedback-btn no" onclick="handleFeedback('${question}', false, this, '${result.search_session_id}', ${JSON.stringify(result.sources).replace(/"/g, '&quot;')})">
              ❌ 아니요, 다른 답변을 원합니다
            </button>
          </div>
        `;
        newAiBubble.appendChild(newFeedbackContainer);
      }
      
      chatBox.appendChild(newAiBubble);
      
      // 스크롤을 맨 아래로 이동
      setTimeout(() => {
        chatBox.scrollTop = chatBox.scrollHeight;
      }, 100);
      
      // 기존 피드백 컨테이너 제거
      feedbackContainer.remove();
      
    } catch (error) {
      console.error('피드백 처리 오류:', error);
      feedbackContainer.innerHTML = `
        <div class="feedback-question">❌ 재검색 중 오류가 발생했습니다.</div>
        <div class="feedback-retry">
          네트워크 오류가 발생했습니다.
          <button class="feedback-retry-btn" onclick="askEffortQuestion()">다시 질문하기</button>
        </div>
      `;
    }
  }
}

// Enter 키 처리
function handleKeyPress(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    askEffortQuestion();
  }
}

// 통계 로드
async function loadStatistics() {
  try {
    // 피드백 통계만 로드 (주 단위 긍정 피드백 비율)
    let feedbackHtml = '';
    try {
      const feedbackRes = await fetch("/effort/feedback-statistics/weekly-positive-ratio/");
      const feedbackData = await feedbackRes.json();
      
      if (feedbackData.weekly_trend && feedbackData.weekly_trend.length > 0) {
        feedbackHtml = generateWeeklyPositiveRatioChart(feedbackData.weekly_trend);
      } else {
        feedbackHtml = '<div class="no-data-message">📊 주 단위 피드백 데이터가 없습니다.</div>';
      }
    } catch (err) {
      console.error("피드백 통계 로드 실패:", err);
      feedbackHtml = '<div class="no-data-message">⚠️ 피드백 통계를 불러올 수 없습니다.</div>';
    }

    // 피드백 통계만 표시
    let html = '<div class="feedback-stats-section">';
    html += '<h3>주 단위 긍정 피드백 비율</h3>';
    html += feedbackHtml;
    html += '</div>';
    
    document.getElementById("statisticsContent").innerHTML = html;
  } catch (err) {
    document.getElementById("statisticsContent").innerHTML = 
      `<div class="loading">❌ 통계 로드 실패</div>`;
    console.error(err);
  }
}

// 주 단위 긍정 비율 차트 생성 (세로 막대 그래프)
function generateWeeklyPositiveRatioChart(weeklyTrend) {
  if (!weeklyTrend || weeklyTrend.length === 0) {
    return '<div class="no-data-message">📊 피드백 데이터가 없습니다.</div>';
  }

  // 최대값 찾기 (100% 기준)
  const maxValue = 100;
  
  let html = '<div class="weekly-chart-container-vertical">';
  
  weeklyTrend.forEach(item => {
    const week = item.week;
    const ratio = item.positive_ratio;
    const barHeight = ratio; // 비율이 곧 퍼센트이므로 그대로 사용
    
    // 색상 결정 (80% 이상: 초록, 60-80%: 노랑, 60% 미만: 빨강)
    let barColor = '#4caf50'; // 초록
    if (ratio < 60) {
      barColor = '#f44336'; // 빨강
    } else if (ratio < 80) {
      barColor = '#ff9800'; // 노랑
    }
    
    html += `
      <div class="weekly-chart-item-vertical">
        <div class="weekly-chart-bar-container-vertical">
          <div class="weekly-chart-bar-vertical" style="height: ${barHeight}%; background-color: ${barColor};" title="${ratio}%">
            <span class="weekly-chart-value-vertical">${ratio}%</span>
          </div>
        </div>
        <div class="weekly-chart-label-vertical">${week}</div>
      </div>
    `;
  });
  
  html += '</div>';
  return html;
}

// 데이터 목록 로드
async function loadEffortList(page = 1) {
  try {
    // 검색 파라미터 생성
    const params = new URLSearchParams();
    if (currentSearchTerm) params.append("search", currentSearchTerm);
    params.append("page", page);
    params.append("page_size", currentPageSize);
    
    const url = `/effort/list/?${params.toString()}`;
    const res = await fetch(url);
    const data = await res.json();
    
    if (data.error) {
      document.getElementById("effortListContent").innerHTML = 
        `<div class="loading">❌ ${data.error}</div>`;
      return;
    }

    if (!data.estimations || data.estimations.length === 0) {
      document.getElementById("effortListContent").innerHTML = 
        `<div class="loading">📝 공수 산정 데이터가 없습니다.</div>`;
      return;
    }

    let html = `<table class="data-table">
      <tr>
        <th>번호</th>
        <th>Jira 티켓</th>
        <th>제목</th>
        <th>Story Points</th>
        <th>카테고리 (클릭하여 수정)</th>
        <th>담당자</th>
        <th>등록일</th>
      </tr>`;

    data.estimations.forEach(est => {
      const jiraUrl = data.jira_url || 'https://enomix.atlassian.net';
      const category = est.major_category && est.minor_category && est.sub_category 
        ? `${est.major_category} > ${est.minor_category} > ${est.sub_category}`
        : '카테고리 설정 (클릭)';
      
      html += `<tr>
        <td>${est.sequence_number || ''}</td>
        <td class="jira-ticket-cell">
          <a href="${jiraUrl}/browse/${est.jira_ticket}" target="_blank" style="color: #4a6bff; text-decoration: none; font-weight: 600;">${est.jira_ticket}</a>
          <button class="btn-delete-x" onclick="deleteEffortData('${est.jira_ticket}', '${est.title}')" title="삭제">×</button>
        </td>
        <td>${est.title}</td>
        <td>${est.story_points}</td>
        <td class="category-cell" data-jira="${est.jira_ticket}" data-title="${est.title}" data-major="${est.major_category || ''}" data-minor="${est.minor_category || ''}" data-sub="${est.sub_category || ''}" style="cursor: pointer; color: #4a6bff; text-decoration: underline; font-weight: 500; ${!est.major_category ? 'background-color: #fff3cd; color: #856404;' : ''}">${category}</td>
        <td>${est.team_member || 'N/A'}</td>
        <td>${new Date(est.created_date).toLocaleDateString()}</td>
      </tr>`;
    });

    html += '</table>';
    document.getElementById("effortListContent").innerHTML = `<div class="table-container">${html}</div>`;
    
    // 카테고리 셀 클릭 이벤트 리스너 추가
    document.querySelectorAll('.category-cell').forEach(cell => {
      cell.addEventListener('click', function() {
        const jira = this.getAttribute('data-jira');
        const title = this.getAttribute('data-title');
        const major = this.getAttribute('data-major');
        const minor = this.getAttribute('data-minor');
        const sub = this.getAttribute('data-sub');
        editCategory(jira, title, major, minor, sub);
      });
    });
    
    // 페이징 정보 처리
    if (data.pagination) {
      currentPagination = data.pagination;
      currentPage = page;
      updatePaginationControls();
    }
  } catch (err) {
    document.getElementById("effortListContent").innerHTML = 
      `<div class="loading">❌ 목록 로드 실패</div>`;
    console.error(err);
  }
}

// 카테고리 관련 함수들
async function loadMajorCategories() {
  try {
    const res = await fetch("/effort/categories/major/");
    const data = await res.json();
    
    const select = document.getElementById("majorCategory");
    select.innerHTML = '<option value="">선택하세요</option>';
    data.categories.forEach(category => {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      select.appendChild(option);
    });
    
    // 하위 카테고리 초기화
    document.getElementById("minorCategory").innerHTML = '<option value="">대분류를 먼저 선택하세요</option>';
    document.getElementById("minorCategory").disabled = true;
    document.getElementById("subCategory").innerHTML = '<option value="">중분류를 먼저 선택하세요</option>';
    document.getElementById("subCategory").disabled = true;
  } catch (err) {
    console.error("대분류 로드 실패:", err);
  }
}

async function loadMinorCategories() {
  const majorCategory = document.getElementById("majorCategory").value;
  if (!majorCategory) return;

  try {
    const res = await fetch(`/effort/categories/minor/?major=${encodeURIComponent(majorCategory)}`);
    const data = await res.json();
    
    const select = document.getElementById("minorCategory");
    select.innerHTML = '<option value="">선택하세요</option>';
    data.categories.forEach(category => {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      select.appendChild(option);
    });
    select.disabled = false;
    
    // 소분류 초기화
    document.getElementById("subCategory").innerHTML = '<option value="">중분류를 먼저 선택하세요</option>';
    document.getElementById("subCategory").disabled = true;
  } catch (err) {
    console.error("중분류 로드 실패:", err);
  }
}

async function loadSubCategories() {
  const majorCategory = document.getElementById("majorCategory").value;
  const minorCategory = document.getElementById("minorCategory").value;
  if (!majorCategory || !minorCategory) return;

  try {
    const res = await fetch(`/effort/categories/sub/?major=${encodeURIComponent(majorCategory)}&minor=${encodeURIComponent(minorCategory)}`);
    const data = await res.json();
    
    const select = document.getElementById("subCategory");
    select.innerHTML = '<option value="">선택하세요</option>';
    data.categories.forEach(category => {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      select.appendChild(option);
    });
    select.disabled = false;
  } catch (err) {
    console.error("소분류 로드 실패:", err);
  }
}

// Jira 동기화용 카테고리 함수들
async function loadSyncMajorCategories() {
  try {
    const res = await fetch("/effort/categories/major/");
    const data = await res.json();
    
    const select = document.getElementById("syncMajorCategory");
    select.innerHTML = '<option value="">선택하세요</option>';
    data.categories.forEach(category => {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      select.appendChild(option);
    });
    
    // 하위 카테고리 초기화
    document.getElementById("syncMinorCategory").innerHTML = '<option value="">대분류를 먼저 선택하세요</option>';
    document.getElementById("syncMinorCategory").disabled = true;
    document.getElementById("syncSubCategory").innerHTML = '<option value="">중분류를 먼저 선택하세요</option>';
    document.getElementById("syncSubCategory").disabled = true;
  } catch (err) {
    console.error("대분류 로드 실패:", err);
  }
}

async function loadSyncMinorCategories() {
  const majorCategory = document.getElementById("syncMajorCategory").value;
  if (!majorCategory) return;

  try {
    const res = await fetch(`/effort/categories/minor/?major=${encodeURIComponent(majorCategory)}`);
    const data = await res.json();
    
    const select = document.getElementById("syncMinorCategory");
    select.innerHTML = '<option value="">선택하세요</option>';
    data.categories.forEach(category => {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      select.appendChild(option);
    });
    select.disabled = false;
    
    // 소분류 초기화
    document.getElementById("syncSubCategory").innerHTML = '<option value="">중분류를 먼저 선택하세요</option>';
    document.getElementById("syncSubCategory").disabled = true;
  } catch (err) {
    console.error("중분류 로드 실패:", err);
  }
}

async function loadSyncSubCategories() {
  const majorCategory = document.getElementById("syncMajorCategory").value;
  const minorCategory = document.getElementById("syncMinorCategory").value;
  if (!majorCategory || !minorCategory) return;

  try {
    const res = await fetch(`/effort/categories/sub/?major=${encodeURIComponent(majorCategory)}&minor=${encodeURIComponent(minorCategory)}`);
    const data = await res.json();
    
    const select = document.getElementById("syncSubCategory");
    select.innerHTML = '<option value="">선택하세요</option>';
    data.categories.forEach(category => {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      select.appendChild(option);
    });
    select.disabled = false;
  } catch (err) {
    console.error("소분류 로드 실패:", err);
  }
}


// 피드백 제출 함수
async function submitFeedback(question, feedbackType, buttonElement) {
  try {
    // 버튼 비활성화
    const feedbackButtons = buttonElement.parentElement;
    const allButtons = feedbackButtons.querySelectorAll('.feedback-btn');
    allButtons.forEach(btn => {
      btn.disabled = true;
      btn.classList.add('feedback-given');
    });
    
    // 피드백 데이터 준비
    const feedbackData = {
      question: question,
      feedback_type: feedbackType,
      timestamp: new Date().toISOString()
    };
    
    // API 호출
    const response = await fetch('/feedback/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(feedbackData)
    });
    
    if (response.ok) {
      // 성공 토스트 메시지
      showToast('피드백 감사합니다! 🎉', 'success');
    } else {
      // 실패 토스트 메시지
      showToast('피드백 전송에 실패했습니다. 😢', 'error');
      // 버튼 다시 활성화
      allButtons.forEach(btn => {
        btn.disabled = false;
        btn.classList.remove('feedback-given');
      });
    }
  } catch (error) {
    console.error('피드백 제출 오류:', error);
    showToast('피드백 전송 중 오류가 발생했습니다. 😢', 'error');
    // 버튼 다시 활성화
    const feedbackButtons = buttonElement.parentElement;
    const allButtons = feedbackButtons.querySelectorAll('.feedback-btn');
    allButtons.forEach(btn => {
      btn.disabled = false;
      btn.classList.remove('feedback-given');
    });
  }
}

// 토스트 메시지 표시 함수
function showToast(message, type = 'success') {
  // 기존 토스트 제거
  const existingToast = document.querySelector('.toast');
  if (existingToast) {
    existingToast.remove();
  }
  
  // 새 토스트 생성
  const toast = document.createElement('div');
  toast.className = `toast ${type === 'error' ? 'error' : ''}`;
  toast.textContent = message;
  
  document.body.appendChild(toast);
  
  // 애니메이션 표시
  setTimeout(() => {
    toast.classList.add('show');
  }, 100);
  
  // 3초 후 자동 제거
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => {
      if (toast.parentElement) {
        toast.remove();
      }
    }, 300);
  }, 3000);
}

// 카테고리 수정 모달 열기
async function editCategory(jiraTicket, title, majorCategory, minorCategory, subCategory) {
  // 모달에 데이터 설정
  document.getElementById('editJiraTicket').value = jiraTicket;
  document.getElementById('editJiraTicketDisplay').value = jiraTicket;
  document.getElementById('editTitle').value = title;
  
  // 모든 카테고리 초기화
  document.getElementById('editMajorCategory').innerHTML = '<option value="">선택하세요</option>';
  document.getElementById('editMinorCategory').innerHTML = '<option value="">대분류를 먼저 선택하세요</option>';
  document.getElementById('editMinorCategory').disabled = true;
  document.getElementById('editSubCategory').innerHTML = '<option value="">중분류를 먼저 선택하세요</option>';
  document.getElementById('editSubCategory').disabled = true;
  
  // 대분류 로드 및 선택
  await loadEditMajorCategories(majorCategory);
  
  // 대분류가 있으면 중분류 로드 및 선택
  if (majorCategory) {
    await loadEditMinorCategories(majorCategory, minorCategory);
  }
  
  // 중분류가 있으면 소분류 로드 및 선택
  if (majorCategory && minorCategory) {
    await loadEditSubCategories(majorCategory, minorCategory, subCategory);
  }
  
  // 모달 표시
  document.getElementById('categoryEditModal').style.display = 'block';
}

// 수정 모달용 대분류 로드
async function loadEditMajorCategories(selectedMajor = '') {
  try {
    const res = await fetch("/effort/categories/major/");
    const data = await res.json();
    
    const select = document.getElementById("editMajorCategory");
    select.innerHTML = '<option value="">선택하세요</option>';
    data.categories.forEach(category => {
      const option = document.createElement('option');
      option.value = category;
      option.textContent = category;
      if (category === selectedMajor) {
        option.selected = true;
      }
      select.appendChild(option);
    });
    
    // 대분류가 선택되어 있으면 중분류 로드 (선택된 값 없이)
    if (selectedMajor) {
      await loadEditMinorCategories(selectedMajor, '');
    }
  } catch (err) {
    console.error('대분류 로드 실패:', err);
  }
}

// 수정 모달용 중분류 로드
async function loadEditMinorCategories(selectedMajor = '', selectedMinor = '') {
  const majorSelect = document.getElementById("editMajorCategory");
  const major = selectedMajor || majorSelect.value;
  
  if (!major) {
    const minorSelect = document.getElementById("editMinorCategory");
    minorSelect.innerHTML = '<option value="">대분류를 먼저 선택하세요</option>';
    minorSelect.disabled = true;
    return;
  }
  
  try {
    const res = await fetch(`/effort/categories/minor/?major=${encodeURIComponent(major)}`);
    const data = await res.json();
    
    const select = document.getElementById("editMinorCategory");
    select.innerHTML = '<option value="">선택하세요</option>';
    select.disabled = false;
    
    data.categories.forEach(category => {
      const option = document.createElement('option');
      option.value = category;
      option.textContent = category;
      if (category === selectedMinor) {
        option.selected = true;
      }
      select.appendChild(option);
    });
  } catch (err) {
    console.error('중분류 로드 실패:', err);
  }
}

// 수정 모달용 소분류 로드
async function loadEditSubCategories(selectedMajor = '', selectedMinor = '', selectedSub = '') {
  const majorSelect = document.getElementById("editMajorCategory");
  const minorSelect = document.getElementById("editMinorCategory");
  const major = selectedMajor || majorSelect.value;
  const minor = selectedMinor || minorSelect.value;
  
  if (!major || !minor) {
    const subSelect = document.getElementById("editSubCategory");
    subSelect.innerHTML = '<option value="">중분류를 먼저 선택하세요</option>';
    subSelect.disabled = true;
    return;
  }
  
  try {
    const res = await fetch(`/effort/categories/sub/?major=${encodeURIComponent(major)}&minor=${encodeURIComponent(minor)}`);
    const data = await res.json();
    
    const select = document.getElementById("editSubCategory");
    select.innerHTML = '<option value="">선택하세요</option>';
    select.disabled = false;
    
    data.categories.forEach(category => {
      const option = document.createElement('option');
      option.value = category;
      option.textContent = category;
      if (category === selectedSub) {
        option.selected = true;
      }
      select.appendChild(option);
    });
  } catch (err) {
    console.error('소분류 로드 실패:', err);
  }
}

// 카테고리 수정 처리
async function handleCategoryEdit(e) {
  e.preventDefault();
  
  const formData = new FormData(e.target);
  const data = {
    jira_ticket: formData.get('jira_ticket'),
    major_category: formData.get('major_category'),
    minor_category: formData.get('minor_category'),
    sub_category: formData.get('sub_category')
  };
  
  try {
    const response = await fetch('/effort/update-category/', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    
    if (response.ok) {
      showToast('카테고리가 수정되었습니다', 'success');
      closeCategoryEditModal();
      loadEffortList(currentPage); // 현재 페이지 유지하며 목록 새로고침
    } else {
      const error = await response.json();
      showToast(error.error || '카테고리 수정 실패', 'error');
    }
  } catch (error) {
    console.error('카테고리 수정 오류:', error);
    showToast('카테고리 수정 중 오류가 발생했습니다', 'error');
  }
}

// 카테고리 수정 모달 닫기
function closeCategoryEditModal() {
  document.getElementById('categoryEditModal').style.display = 'none';
}

// Epic 하위 작업 동기화
async function syncEpicData() {
  const epicKey = document.getElementById("epicKey").value.trim();
  const statusDiv = document.getElementById("epicSyncStatus");
  
  if (!epicKey) return alert("Epic 키를 입력하세요.");

  try {
    statusDiv.style.display = "block";
    statusDiv.textContent = "🔄 Epic 하위 작업을 동기화 중입니다...";
    
    const formData = new FormData();
    formData.append("epic_key", epicKey);

    const res = await fetch("/effort/sync-epic/", { method: "POST", body: formData });
    const result = await res.json();
    
    statusDiv.style.display = "none";
    
    if (res.ok) {
      const message = `✅ Epic 동기화 완료!\n\n` +
        `📊 처리 결과:\n` +
        `• 총 작업 수: ${result.total_tasks}\n` +
        `• 추가된 작업: ${result.added_tasks}\n` +
        `• 업데이트된 작업: ${result.updated_tasks}\n` +
        `• 건너뛴 작업: ${result.skipped_tasks}`;
      
      alert(message);
      loadEffortList(); // 목록 새로고침
    } else {
      alert(`❌ Epic 동기화 실패: ${result.error || '알 수 없는 오류'}`);
    }
  } catch (error) {
    statusDiv.style.display = "none";
    console.error('Epic 동기화 오류:', error);
    alert('❌ Epic 동기화 중 오류가 발생했습니다');
  }
}

// 공수 산정 데이터 삭제
async function autoClassifyData() {
  const statusDiv = document.getElementById('autoClassifyStatus');
  statusDiv.innerHTML = '<div class="loading">🤖 자동 분류 실행 중...</div>';
  
  try {
    const response = await fetch('/effort/auto-classify/', {
      method: 'POST'
    });
    
    const result = await response.json();
    
    if (response.ok) {
      let detailHtml = `
        <div style="background: #d4edda; padding: 10px; border-radius: 5px; color: #155724; margin-bottom: 10px;">
          ✅ 자동 분류 완료<br>
          📊 총 미분류: ${result.total_unclassified}개<br><br>
          <strong>신뢰도별 결과:</strong><br>
          ✅ 높은 신뢰도 (0.5 이상): ${result.high_confidence_count}개<br>
          ⚠️ 중간 신뢰도 (0.3~0.5): ${result.medium_confidence_count}개<br>
          📝 낮은 신뢰도 (0.1~0.3): ${result.low_confidence_count}개<br>
          🤖 자동 적용됨: ${result.classified_count}개<br>
          📈 평균 신뢰도: ${result.average_confidence}
        </div>
      `;
      
      // 중간/낮은 신뢰도 제안 표시
      if (result.medium_confidence && result.medium_confidence.length > 0) {
        detailHtml += `
          <div style="background: #fff3cd; padding: 10px; border-radius: 5px; color: #856404; margin-bottom: 10px;">
            <strong>⚠️ 중간 신뢰도 제안 (확인 필요):</strong><br>
        `;
        result.medium_confidence.forEach((item) => {
          const title = item.title || item[0];
          const category = item.category || item[1];
          const conf = item.confidence || item[2];
          detailHtml += `• ${title} → ${category} (신뢰도: ${conf})<br>`;
        });
        detailHtml += `</div>`;
      }
      
      if (result.low_confidence && result.low_confidence.length > 0) {
        detailHtml += `
          <div style="background: #f8d7da; padding: 10px; border-radius: 5px; color: #721c24;">
            <strong>📝 낮은 신뢰도 제안:</strong><br>
        `;
        result.low_confidence.forEach((item) => {
          const title = item.title || item[0];
          const category = item.category || item[1];
          const conf = item.confidence || item[2];
          detailHtml += `• ${title} → ${category} (신뢰도: ${conf})<br>`;
        });
        detailHtml += `</div>`;
      }
      
      statusDiv.innerHTML = detailHtml;
      showToast('✅ 자동 분류가 완료되었습니다', 'success');
      loadEffortList(); // 목록 새로고침
    } else {
      statusDiv.innerHTML = `
        <div style="background: #f8d7da; padding: 10px; border-radius: 5px; color: #721c24;">
          ❌ 자동 분류 실패: ${result.error || '알 수 없는 오류'}
        </div>
      `;
      showToast(`❌ 자동 분류 실패: ${result.error || '알 수 없는 오류'}`, 'error');
    }
  } catch (error) {
    console.error('자동 분류 오류:', error);
    statusDiv.innerHTML = `
      <div style="background: #f8d7da; padding: 10px; border-radius: 5px; color: #721c24;">
        ❌ 자동 분류 중 오류가 발생했습니다
      </div>
    `;
    showToast('❌ 자동 분류 중 오류가 발생했습니다', 'error');
  }
}

async function deleteEffortData(jiraTicket, title) {
  // 확인 대화상자
  const confirmed = confirm(`정말로 삭제하시겠습니까?\n\n티켓: ${jiraTicket}\n제목: ${title}`);
  if (!confirmed) return;
  
  try {
    const response = await fetch(`/effort/delete/${jiraTicket}`, {
      method: 'DELETE'
    });
    
    const result = await response.json();
    
    if (response.ok) {
      showToast('✅ 데이터가 삭제되었습니다', 'success');
      loadEffortList(); // 목록 새로고침
    } else {
      showToast(`❌ 삭제 실패: ${result.error || '알 수 없는 오류'}`, 'error');
    }
  } catch (error) {
    console.error('삭제 오류:', error);
    showToast('❌ 삭제 중 오류가 발생했습니다', 'error');
  }
}

// 페이지 로드 시 초기화
window.onload = function() {
  loadStatistics();
  loadMajorCategories();
  
  // 카테고리 수정 폼 이벤트 리스너
  document.getElementById('categoryEditForm').addEventListener('submit', handleCategoryEdit);
  
  // 모달 외부 클릭으로 닫기
  document.getElementById('categoryEditModal').addEventListener('click', function(e) {
    if (e.target === this) {
      closeCategoryEditModal();
    }
  });
};

// 페이징 관련 함수들
function updatePaginationControls() {
  if (!currentPagination) return;
  
  const paginationControls = document.querySelector('.search-pagination-controls');
  const prevBtn = document.getElementById('prevPageBtn');
  const nextBtn = document.getElementById('nextPageBtn');
  const pageNumbers = document.getElementById('pageNumbers');
  
  // 페이징 컨트롤 표시
  if (paginationControls) {
    paginationControls.style.display = 'flex';
  }
  
  // 이전/다음 버튼 상태 업데이트
  prevBtn.disabled = !currentPagination.has_previous;
  nextBtn.disabled = !currentPagination.has_next;
  
  // 페이지 번호 생성
  pageNumbers.innerHTML = '';
  const totalPages = currentPagination.total_pages;
  const currentPage = currentPagination.current_page;
  
  // 페이지 번호 범위 계산 (현재 페이지 기준 ±2)
  let range = 2;
  let startPage = Math.max(1, currentPage - range);
  let endPage = Math.min(totalPages, currentPage + range);
  
  // 중복 체크를 위한 Set 사용
  const addedPages = new Set();
  
  // 첫 페이지 표시
  if (startPage > 1) {
    addedPages.add(1);
    const span1 = document.createElement('span');
    span1.className = 'page-number';
    span1.textContent = '1';
    span1.style.cursor = 'pointer';
    span1.onclick = () => goToPage(1);
    pageNumbers.appendChild(span1);
    
    if (startPage > 2) {
      const dots = document.createElement('span');
      dots.className = 'page-number disabled';
      dots.textContent = '...';
      pageNumbers.appendChild(dots);
    }
  }
  
  // 페이지 번호들
  for (let i = startPage; i <= endPage; i++) {
    if (!addedPages.has(i)) {
      addedPages.add(i);
      const span = document.createElement('span');
      span.className = `page-number ${i === currentPage ? 'active' : ''}`;
      span.textContent = i.toString();
      span.style.cursor = 'pointer';
      span.onclick = () => goToPage(i);
      pageNumbers.appendChild(span);
    }
  }
  
  // 마지막 페이지 표시
  if (endPage < totalPages) {
    if (endPage < totalPages - 1) {
      const dots = document.createElement('span');
      dots.className = 'page-number disabled';
      dots.textContent = '...';
      pageNumbers.appendChild(dots);
    }
    if (!addedPages.has(totalPages)) {
      addedPages.add(totalPages);
      const spanTotal = document.createElement('span');
      spanTotal.className = 'page-number';
      spanTotal.textContent = totalPages.toString();
      spanTotal.style.cursor = 'pointer';
      spanTotal.onclick = () => goToPage(totalPages);
      pageNumbers.appendChild(spanTotal);
    }
  }
}

function changePage(direction) {
  if (!currentPagination) return;
  
  const newPage = currentPage + direction;
  if (newPage >= 1 && newPage <= currentPagination.total_pages) {
    goToPage(newPage);
  }
}

function goToPage(page) {
  if (page >= 1 && page <= currentPagination.total_pages) {
    loadEffortList(page);
  }
}

// 검색 관련 함수들
function searchByTitle() {
  const searchInput = document.getElementById('titleSearchInput');
  currentSearchTerm = searchInput.value.trim();
  currentPage = 1; // 검색 시 첫 페이지로 이동
  loadEffortList(1);
}

function clearTitleSearch() {
  const searchInput = document.getElementById('titleSearchInput');
  searchInput.value = '';
  currentSearchTerm = '';
  currentPage = 1;
  loadEffortList(1);
}

// Enter 키로 검색
function handleSearchKeyPress(event) {
  if (event.key === 'Enter') {
    searchByTitle();
  }
}
