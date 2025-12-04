// 카테고리 관리 JavaScript

let categories = {};
let expandedStates = {
    major: new Set(),
    minor: new Set()
};

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    resetCategoryStates(); // 페이지 로드 시에만 상태 초기화
    loadCategories();
    setupEventListeners();
});

// 이벤트 리스너 설정
function setupEventListeners() {
    // 모달 닫기
    document.querySelector('.close').addEventListener('click', closeEditModal);
    document.getElementById('editModal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeEditModal();
        }
    });
    
    // 수정 폼
    document.getElementById('editCategoryForm').addEventListener('submit', handleEditCategory);
}

// 카테고리 목록 로드
async function loadCategories() {
    try {
        const response = await fetch('/effort/categories/');
        if (response.ok) {
            categories = await response.json();
            renderCategoryTree();
        } else {
            showToast('카테고리 로드 실패', 'error');
        }
    } catch (error) {
        console.error('카테고리 로드 오류:', error);
        showToast('카테고리 로드 중 오류가 발생했습니다', 'error');
    }
}

// 카테고리 상태 초기화 (새로고침 시에만)
function resetCategoryStates() {
    expandedStates.major.clear();
    expandedStates.minor.clear();
}

// 카테고리 트리 렌더링
function renderCategoryTree() {
    const treeContainer = document.getElementById('categoryTree');
    treeContainer.innerHTML = '';
    
    for (const [major, minorCategories] of Object.entries(categories)) {
        const majorItem = createMajorCategoryItem(major, minorCategories);
        treeContainer.appendChild(majorItem);
    }
}

// 대분류 카테고리 아이템 생성
function createMajorCategoryItem(major, minorCategories) {
    const item = document.createElement('div');
    item.className = 'category-item';
    
    const header = document.createElement('div');
    header.className = 'category-header';
    header.innerHTML = `
        <span>${major}</span>
        <div class="major-actions">
            <span class="category-toggle">▶</span>
        </div>
    `;
    
    const content = document.createElement('div');
    content.className = 'category-content';
    content.style.display = 'none';
    
    // 중분류 렌더링
    for (const [minor, subCategories] of Object.entries(minorCategories)) {
        const minorItem = createMinorCategoryItem(major, minor, subCategories);
        content.appendChild(minorItem);
    }
    
    // 토글 기능
    header.addEventListener('click', function(e) {
        // 버튼 클릭 시에는 토글하지 않음
        if (e.target.tagName === 'BUTTON') return;
        
        const isExpanded = content.style.display !== 'none';
        content.style.display = isExpanded ? 'none' : 'block';
        header.classList.toggle('expanded', !isExpanded);
        header.querySelector('.category-toggle').classList.toggle('expanded', !isExpanded);
        
        // 상태 저장
        if (!isExpanded) {
            expandedStates.major.add(major);
        } else {
            expandedStates.major.delete(major);
        }
    });
    
    // 이전 상태 복원
    if (expandedStates.major.has(major)) {
        content.style.display = 'block';
        header.classList.add('expanded');
        header.querySelector('.category-toggle').classList.add('expanded');
    }
    
    item.appendChild(header);
    item.appendChild(content);
    
    return item;
}

// 중분류 카테고리 아이템 생성
function createMinorCategoryItem(major, minor, subCategories) {
    const item = document.createElement('div');
    item.className = 'minor-category';
    
    const header = document.createElement('div');
    header.className = 'minor-header';
    header.innerHTML = `
        <span>${minor}</span>
        <div class="minor-actions">
            <span class="category-toggle">▶</span>
        </div>
    `;
    
    const content = document.createElement('div');
    content.className = 'minor-content';
    content.style.display = 'none';
    
    // 소분류 렌더링
    subCategories.forEach(sub => {
        const subItem = createSubCategoryItem(major, minor, sub);
        content.appendChild(subItem);
    });
    
    // 토글 기능
    header.addEventListener('click', function(e) {
        // 버튼 클릭 시에는 토글하지 않음
        if (e.target.tagName === 'BUTTON') return;
        
        const isExpanded = content.style.display !== 'none';
        content.style.display = isExpanded ? 'none' : 'block';
        header.classList.toggle('expanded', !isExpanded);
        header.querySelector('.category-toggle').classList.toggle('expanded', !isExpanded);
        
        // 상태 저장
        const minorKey = `${major}-${minor}`;
        if (!isExpanded) {
            expandedStates.minor.add(minorKey);
        } else {
            expandedStates.minor.delete(minorKey);
        }
    });
    
    // 이전 상태 복원
    const minorKey = `${major}-${minor}`;
    if (expandedStates.minor.has(minorKey)) {
        content.style.display = 'block';
        header.classList.add('expanded');
        header.querySelector('.category-toggle').classList.add('expanded');
    }
    
    item.appendChild(header);
    item.appendChild(content);
    
    return item;
}

// 소분류 카테고리 아이템 생성
function createSubCategoryItem(major, minor, sub) {
    const item = document.createElement('span');
    item.className = 'sub-category';
    item.innerHTML = `${sub}`;
    
    return item;
}



// 카테고리 수정 모달 열기
function openEditModal(major, minor, sub) {
    document.getElementById('editOldMajor').value = major;
    document.getElementById('editOldMinor').value = minor;
    document.getElementById('editOldSub').value = sub;
    document.getElementById('editMajorCategory').value = major;
    document.getElementById('editMinorCategory').value = minor;
    document.getElementById('editSubCategory').value = sub;
    document.getElementById('editModal').style.display = 'block';
}

// 카테고리 수정 모달 닫기
function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}

// 카테고리 수정 처리
async function handleEditCategory(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        old_major: formData.get('old_major'),
        old_minor: formData.get('old_minor'),
        old_sub: formData.get('old_sub'),
        new_major: formData.get('new_major'),
        new_minor: formData.get('new_minor'),
        new_sub: formData.get('new_sub')
    };
    
    try {
        const response = await fetch('/effort/categories/', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            showToast('카테고리가 수정되었습니다', 'success');
            closeEditModal();
            await loadCategories();
        } else {
            const error = await response.json();
            showToast(error.error || '카테고리 수정 실패', 'error');
        }
    } catch (error) {
        console.error('카테고리 수정 오류:', error);
        showToast('카테고리 수정 중 오류가 발생했습니다', 'error');
    }
}

// 토스트 메시지 표시
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// 엑셀 파일 업로드 함수
async function uploadExcelCategories() {
    const fileInput = document.getElementById('excelFile');
    const file = fileInput.files[0];
    const uploadResult = document.getElementById('uploadResult');
    
    if (!file) {
        showUploadResult('파일을 선택해주세요.', 'error');
        return;
    }
    
    // 파일 확장자 확인
    const allowedExtensions = ['.xlsx', '.xls'];
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    if (!allowedExtensions.includes(fileExtension)) {
        showUploadResult('엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        showUploadResult('파일 업로드 중...', 'info');
        
        const response = await fetch('/effort/categories/upload-excel', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showUploadResult('✅ 카테고리 업데이트 완료! 페이지를 새로고침합니다...', 'success');
            // 2초 후 페이지 새로고침
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            showUploadResult('❌ 오류: ' + result.error, 'error');
        }
    } catch (error) {
        showUploadResult('❌ 업로드 중 오류가 발생했습니다: ' + error.message, 'error');
    }
}

// 업로드 결과 표시 함수
function showUploadResult(message, type) {
    const uploadResult = document.getElementById('uploadResult');
    
    let className = 'upload-result';
    if (type === 'success') {
        className += ' success';
    } else if (type === 'error') {
        className += ' error';
    } else if (type === 'info') {
        className += ' info';
    }
    
    uploadResult.innerHTML = `<div class="${className}">${message}</div>`;
}

// 엑셀 파일 다운로드 함수
async function downloadExcelCategories() {
    try {
        showUploadResult('엑셀 파일 생성 중...', 'info');
        
        const response = await fetch('/effort/categories/download-excel');
        
        if (response.ok) {
            // 파일 다운로드
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            
            // 파일명 추출 (Content-Disposition 헤더에서)
            const contentDisposition = response.headers.get('content-disposition');
            let filename = 'categories.xlsx';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            }
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showUploadResult('✅ 엑셀 파일 다운로드 완료!', 'success');
        } else {
            const error = await response.json();
            showUploadResult('❌ 다운로드 실패: ' + error.error, 'error');
        }
    } catch (error) {
        showUploadResult('❌ 다운로드 중 오류가 발생했습니다: ' + error.message, 'error');
    }
}
