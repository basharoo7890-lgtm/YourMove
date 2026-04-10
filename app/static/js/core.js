/* ═══ YourMove — Core JS ═══ */

const API = {
    base: '',
    token: localStorage.getItem('ym_token'),

    async request(method, path, body = null) {
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };
        if (this.token) opts.headers['Authorization'] = `Bearer ${this.token}`;
        if (body) opts.body = JSON.stringify(body);

        const res = await fetch(this.base + path, opts);
        if (res.status === 401) {
            localStorage.removeItem('ym_token');
            window.location.href = '/login';
            return null;
        }
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Request failed');
        return data;
    },

    get: (p) => API.request('GET', p),
    post: (p, b) => API.request('POST', p, b),
    put: (p, b) => API.request('PUT', p, b),
    del: (p) => API.request('DELETE', p),

    setToken(t) {
        this.token = t;
        localStorage.setItem('ym_token', t);
    },

    logout() {
        this.token = null;
        localStorage.removeItem('ym_token');
        window.location.href = '/login';
    },

    isLoggedIn() {
        return !!this.token;
    }
};

// ─── Auth Guard ───────────────────────────────────────
function requireAuth() {
    if (!API.isLoggedIn()) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

// ─── Toast ────────────────────────────────────────────
function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const icons = { info: '💡', success: '✅', error: '❌', warning: '⚠️' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || '💡'}</span> ${message}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ─── Time formatting ──────────────────────────────────
function timeAgo(dateStr) {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - d) / 1000);
    if (diff < 60) return 'الآن';
    if (diff < 3600) return `منذ ${Math.floor(diff / 60)} دقيقة`;
    if (diff < 86400) return `منذ ${Math.floor(diff / 3600)} ساعة`;
    return `منذ ${Math.floor(diff / 86400)} يوم`;
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('ar-JO', {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
}

function formatDuration(start, end) {
    if (!start || !end) return '—';
    const diff = Math.floor((new Date(end) - new Date(start)) / 1000);
    const m = Math.floor(diff / 60);
    const s = diff % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
}

// ─── State colors ─────────────────────────────────────
const STATE_COLORS = {
    CALM: '#10B981',
    ENGAGED: '#3B82F6',
    STRESSED: '#F59E0B',
    OVERWHELMED: '#EF4444',
};

const STATE_LABELS = {
    CALM: 'هادئ',
    ENGAGED: 'متفاعل',
    STRESSED: 'متوتر',
    OVERWHELMED: 'مرهق',
};

function getStateBadge(state) {
    const cls = (state || '').toLowerCase();
    return `<span class="badge badge-${cls}">${STATE_LABELS[state] || state}</span>`;
}

function getStatusBadge(status) {
    if (status === 'active' || status === 'baseline') return '<span class="badge badge-active">نشطة</span>';
    if (status === 'completed') return '<span class="badge badge-completed">مكتملة</span>';
    if (status === 'pending') return '<span class="badge badge-pending">معلّقة</span>';
    return `<span class="badge badge-completed">${status}</span>`;
}

// ─── Sidebar active state ─────────────────────────────
function initSidebar() {
    const path = window.location.pathname;
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.getAttribute('href') === path) {
            item.classList.add('active');
        }
    });
}

// ─── Load user info in sidebar ────────────────────────
async function loadUserInfo() {
    try {
        const user = await API.get('/api/auth/me');
        const el = document.getElementById('user-name');
        if (el) el.textContent = user.full_name;
    } catch (e) { /* ignore */ }
}
