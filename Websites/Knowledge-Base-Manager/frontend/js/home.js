// ─── 狀態 ───
let currentGroup = null;
let currentFile = null;   // null = 新檔案, string = 編輯中的檔名
let groups = [];
let fileCache = [];       // 當前群組的檔案清單
let isModified = false;

// ─── 初始化 ───
window.addEventListener('pageshow', async () => {
    const response = await fetch('/api/check-auth', { credentials: 'same-origin' });
    if (!response.ok) {
        window.location.replace('/');
        return;
    }
    const data = await response.json();
    document.getElementById('username-display').textContent = data.username;
    groups = data.groups.filter(g => g !== 'default');

    if (groups.length > 0) {
        switchGroup(groups[0]);
    } else {
        renderGroupTabs();
        document.getElementById('file-list').innerHTML = '<div class="no-files">您尚未被分配到任何知識庫群組，<br>請聯絡管理員。</div>';
        document.getElementById('new-file-btn').style.display = 'none';
        document.getElementById('editor-toolbar').style.display = 'none';
        document.getElementById('editor').style.display = 'none';
    }
});

// 追蹤編輯狀態
document.getElementById('editor').addEventListener('input', () => { isModified = true; });

// ─── 群組 Tab ───
function renderGroupTabs() {
    const container = document.getElementById('group-tabs');
    container.innerHTML = groups.map(g =>
        `<button class="group-tab ${g === currentGroup ? 'active' : ''}" onclick="switchGroup('${g}')">${g}</button>`
    ).join('');
}

async function switchGroup(group) {
    if (isModified && !confirm('有未儲存的變更，確定要切換嗎？')) return;
    currentGroup = group;
    currentFile = null;
    isModified = false;
    renderGroupTabs();
    await loadFiles();
    clearEditor();
}

// ─── 檔案清單 ───
async function loadFiles() {
    try {
        const response = await fetch(`/api/files?group=${encodeURIComponent(currentGroup)}`, { credentials: 'same-origin' });
        if (!response.ok) return;
        const data = await response.json();
        fileCache = data.files;
        renderFileList();
    } catch (e) {
        console.error('載入檔案清單失敗:', e);
    }
}

function renderFileList() {
    const container = document.getElementById('file-list');
    if (fileCache.length === 0) {
        container.innerHTML = '<div class="no-files">尚無檔案，點擊下方按鈕新增</div>';
        return;
    }
    container.innerHTML = fileCache.map((f, idx) => {
        const sizeStr = f.size < 1024 ? `${f.size} B` : `${(f.size / 1024).toFixed(1)} KB`;
        const active = currentFile === f.name ? 'active' : '';
        return `<div class="file-item ${active}" onclick="openFile(${idx})">
            <span class="icon">📄</span>
            <span class="name" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</span>
            <span class="size">${sizeStr}</span>
        </div>`;
    }).join('');
}

// ─── 開啟檔案 ───
async function openFile(idx) {
    if (isModified && !confirm('有未儲存的變更，確定要切換嗎？')) return;
    const f = fileCache[idx];
    if (!f) return;

    try {
        const response = await fetch(
            `/api/file/content?group=${encodeURIComponent(currentGroup)}&name=${encodeURIComponent(f.name)}`,
            { credentials: 'same-origin' }
        );
        if (!response.ok) {
            const err = await response.json();
            alert(err.error || '無法載入檔案');
            return;
        }
        const data = await response.json();
        currentFile = f.name;
        document.getElementById('filename-input').value = f.name;
        document.getElementById('editor').value = data.content;
        document.getElementById('delete-btn').style.display = '';
        isModified = false;
        updateStatus(`已載入 ${f.name}`);
        renderFileList();
    } catch (e) {
        alert('載入檔案失敗');
    }
}

// ─── 新增檔案 ───
function createNewFile() {
    if (isModified && !confirm('有未儲存的變更，確定要新增嗎？')) return;
    if (!currentGroup) {
        alert('請先選擇群組');
        return;
    }
    currentFile = null;
    document.getElementById('filename-input').value = '';
    document.getElementById('editor').value = '';
    document.getElementById('delete-btn').style.display = 'none';
    document.getElementById('filename-input').focus();
    isModified = false;
    updateStatus('新增檔案 — 請輸入檔名與內容');
    renderFileList();
}

// ─── 儲存檔案 ───
async function saveFile() {
    const name = document.getElementById('filename-input').value.trim();
    const content = document.getElementById('editor').value;

    if (!name) {
        alert('請輸入檔案名稱');
        document.getElementById('filename-input').focus();
        return;
    }

    if (!name.endsWith('.md') && !name.endsWith('.txt')) {
        alert('檔案名稱必須以 .md 或 .txt 結尾');
        return;
    }

    if (!content.trim()) {
        alert('檔案內容不可為空');
        return;
    }

    const saveBtn = document.querySelector('.save-btn');
    try {
        saveBtn.disabled = true;
        saveBtn.textContent = '儲存中...';
        updateStatus('儲存中，請稍候（包含知識庫重建）...');

        const response = await fetch('/api/file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ group: currentGroup, name, content }),
        });

        const data = await response.json();
        if (response.ok) {
            currentFile = name;
            document.getElementById('delete-btn').style.display = '';
            isModified = false;
            updateStatus(data.message || '儲存成功');
            await loadFiles();
        } else {
            alert(data.error || '儲存失敗');
            updateStatus('儲存失敗');
        }
    } catch (e) {
        alert('儲存失敗，請稍後再試');
        updateStatus('儲存失敗');
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = '💾 儲存';
    }
}

// ─── 刪除檔案 ───
async function deleteFile() {
    if (!currentFile) {
        alert('請先選擇要刪除的檔案');
        return;
    }
    if (!confirm(`確定要刪除「${currentFile}」嗎？此操作無法復原。`)) return;

    try {
        updateStatus('刪除中...');
        const response = await fetch('/api/file', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ group: currentGroup, name: currentFile }),
        });

        const data = await response.json();
        if (response.ok) {
            updateStatus(data.message || '已刪除');
            currentFile = null;
            clearEditor();
            await loadFiles();
        } else {
            alert(data.error || '刪除失敗');
        }
    } catch (e) {
        alert('刪除失敗，請稍後再試');
    }
}

// ─── 工具函式 ───
function clearEditor() {
    document.getElementById('filename-input').value = '';
    document.getElementById('editor').value = '';
    document.getElementById('delete-btn').style.display = 'none';
    isModified = false;
    updateStatus('就緒');
}

function updateStatus(msg) {
    document.getElementById('status-bar').textContent = msg;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

async function logout() {
    await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' });
    window.location.replace('/');
}
