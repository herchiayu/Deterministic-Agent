// ─── 設定 marked ───
marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: function (code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
    }
});

// ─── DOM 元素 ───
const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebar-overlay');

// ─── 認證檢查 ───
window.addEventListener('pageshow', async () => {
    const response = await fetch('/api/check-auth', { credentials: 'same-origin' });
    if (!response.ok) {
        window.location.replace('/');
    } else {
        const data = await response.json();
        document.getElementById('username-display').textContent = data.username;
        loadHistory();
        loadApps();
    }
});

// ─── Textarea 自動調整高度 ───
messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
});

// ─── Enter 發送，Shift+Enter 換行 ───
messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// ─── 載入聊天歷史 ───
async function loadHistory() {
    try {
        const response = await fetch('/api/chat/history', { credentials: 'same-origin' });
        if (response.ok) {
            const data = await response.json();
            if (data.messages.length === 0) {
                showEmptyState();
                return;
            }
            data.messages.forEach(msg => {
                appendMessage(msg.role, msg.content);
            });
            scrollToBottom();
        }
    } catch (e) {
        console.error('載入歷史失敗:', e);
    }
}

// ─── 顯示空狀態提示 ───
function showEmptyState() {
    chatContainer.innerHTML = '';
    const emptyDiv = document.createElement('div');
    emptyDiv.className = 'empty-state';
    emptyDiv.innerHTML = '<div class="icon">💬</div><p>開始與 AI 助手對話吧！</p>';
    chatContainer.appendChild(emptyDiv);
}

// ─── 發送訊息 ───
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || sendBtn.disabled) return;

    // 移除空狀態提示
    const emptyState = chatContainer.querySelector('.empty-state');
    if (emptyState) emptyState.remove();

    // 顯示使用者訊息
    appendMessage('user', message);
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // 停用發送按鈕
    sendBtn.disabled = true;

    // 建立助手訊息佔位
    const assistantMsg = appendMessage('assistant', '');
    const contentEl = assistantMsg.querySelector('.message-content');

    // 顯示打字指示器
    contentEl.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    scrollToBottom();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ message })
        });

        if (!response.ok) {
            const err = await response.json();
            contentEl.textContent = err.error || '發生錯誤';
            sendBtn.disabled = false;
            return;
        }

        // 串流讀取回應
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';

        contentEl.innerHTML = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            fullText += chunk;
            contentEl.innerHTML = marked.parse(fullText);
            scrollToBottom();
        }

        // 最終渲染（含程式碼高亮）
        contentEl.innerHTML = marked.parse(fullText);
        contentEl.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });
    } catch (e) {
        contentEl.textContent = '連線錯誤，請稍後再試';
    }

    sendBtn.disabled = false;
    messageInput.focus();
    scrollToBottom();
}

// ─── 新增訊息到聊天區域 ───
function appendMessage(role, content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    if (content) {
        if (role === 'assistant') {
            contentDiv.innerHTML = marked.parse(content);
            // 程式碼高亮
            contentDiv.querySelectorAll('pre code').forEach(block => {
                hljs.highlightElement(block);
            });
        } else {
            contentDiv.textContent = content;
        }
    }

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(contentDiv);
    chatContainer.appendChild(msgDiv);
    scrollToBottom();

    return msgDiv;
}

// ─── 滾動到底部 ───
function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// ─── 清除聊天記錄 ───
async function clearChat() {
    if (!confirm('確定要清除所有聊天記錄嗎？')) return;

    try {
        const response = await fetch('/api/chat/clear', {
            method: 'POST',
            credentials: 'same-origin'
        });
        if (response.ok) {
            showEmptyState();
        }
    } catch (e) {
        alert('清除失敗');
    }
}

// ─── 登出 ───
async function logout() {
    await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' });
    window.location.replace('/');
}

// ─── 側邊欄：載入網站清單 ───
async function loadApps() {
    try {
        const response = await fetch('/api/apps', { credentials: 'same-origin' });
        if (!response.ok) return;
        const data = await response.json();
        const appList = document.getElementById('app-list');
        appList.innerHTML = '';

        if (data.apps.length === 0) {
            appList.innerHTML = '<li class="app-list-empty">尚無註冊網站</li>';
            return;
        }

        const currentHost = window.location.hostname;
        data.apps.forEach(app => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = `http://${currentHost}:${app.port}`;
            a.target = '_blank';
            a.textContent = app.name;
            if (app.description) a.title = app.description;
            li.appendChild(a);
            appList.appendChild(li);
        });
    } catch (e) {
        console.error('載入網站清單失敗:', e);
    }
}

// ─── 側邊欄：收合/展開 ───
function toggleSidebar() {
    sidebar.classList.toggle('collapsed');
    const isMobile = window.innerWidth <= 768;
    if (isMobile) {
        sidebarOverlay.classList.toggle('active', !sidebar.classList.contains('collapsed'));
    }
}

// 桌面版視窗縮放時關閉 overlay
window.addEventListener('resize', () => {
    if (window.innerWidth > 768) {
        sidebarOverlay.classList.remove('active');
    }
});
