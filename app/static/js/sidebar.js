/* ═══ Sidebar Renderer ═══ */

function renderSidebar() {
    return `
    <aside class="sidebar">
        <div class="sidebar-logo">
            <h1>YourMove</h1>
            <span>Assessment & Support Platform</span>
        </div>
        <nav class="nav-section">
            <div class="nav-label">الرئيسية</div>
            <a class="nav-item" href="/dashboard">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
                لوحة التحكم
            </a>
            <a class="nav-item" href="/patients">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                المرضى
            </a>
            <a class="nav-item" href="/sessions">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                الجلسات
            </a>
        </nav>
        <nav class="nav-section">
            <div class="nav-label">الحساب</div>
            <a class="nav-item" href="/profile">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                ملف الطبيب
            </a>
            <div class="nav-item" style="padding:8px 12px;">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                <span id="user-name" style="font-size:12.5px;">...</span>
            </div>
            <a class="nav-item" href="#" onclick="API.logout()">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                تسجيل الخروج
            </a>
        </nav>
    </aside>`;
}

/** @returns {boolean} true if user is logged in and shell was rendered */
function initPage() {
    if (!requireAuth()) return false;
    const sidebarEl = document.getElementById('sidebar-container');
    if (sidebarEl) sidebarEl.innerHTML = renderSidebar();
    initSidebar();
    loadUserInfo();
    return true;
}
