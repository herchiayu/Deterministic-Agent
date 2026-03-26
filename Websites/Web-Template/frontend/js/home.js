window.addEventListener('pageshow', async () => {
    const response = await fetch('/api/check-auth', { credentials: 'same-origin' });
    if (!response.ok) {
        window.location.replace('/');
    } else {
        const data = await response.json();
        document.getElementById('username-display').textContent = data.username;
    }
});

async function logout() {
    await fetch('/api/logout', { method: 'POST' });
    window.location.replace('/');
}
