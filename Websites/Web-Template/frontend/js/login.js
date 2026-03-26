// 已登入則直接跳回 home
window.addEventListener('pageshow', async () => {
    const response = await fetch('/api/check-auth', { credentials: 'same-origin' });
    if (response.ok) window.location.replace('/home');
});

async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    if (!username || !password) {
        showMessage('請輸入使用者名稱和密碼', true);
        return;
    }

    const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });

    const data = await response.json();
    if (response.ok) {
        window.location.replace('/home');
    } else {
        showMessage(data.error || '登入失敗', true);
    }
}

function showMessage(text, isError) {
    const msg = document.getElementById('message');
    msg.textContent = text;
    msg.className = 'message ' + (isError ? 'error' : 'success');
}
