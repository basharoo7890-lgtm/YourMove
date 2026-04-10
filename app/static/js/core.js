/* ═══ YourMove — Core JS ═══ */

const API = {
    base: '',
    /** Primary storage key (legacy) */
    TOKEN_KEY: 'ym_token',
    /** Mirror for OAuth2-style clients */
    ALT_TOKEN_KEY: 'access_token',

    getToken() {
        return localStorage.getItem(this.TOKEN_KEY) || localStorage.getItem(this.ALT_TOKEN_KEY);
    },

    setToken(t) {
        if (!t) {
            this.clearToken();
            return null;
        }
        const v = String(t).trim();
        localStorage.setItem(this.TOKEN_KEY, v);
        localStorage.setItem(this.ALT_TOKEN_KEY, v);
        return v;
    },

    clearToken() {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.ALT_TOKEN_KEY);
    },

    isLoggedIn() {
        return !!this.getToken();
    },

    _isPublicApiPath(path) {
        return path === '/api/auth/login' || path === '/api/auth/register';
    },

    _formatErrorDetail(data) {
        const d = data && data.detail;
        if (Array.isArray(d)) {
            return d.map((e) => (e && e.msg) || JSON.stringify(e)).join('; ');
        }
        if (typeof d === 'object' && d !== null) {
            return JSON.stringify(d);
        }
        if (typeof d === 'string' && d.length) return d;
        return 'Request failed';
    },

    /**
     * @param {string} method
     * @param {string} path
     * @param {object|null} body
     * @param {{ auth?: boolean }} [options]
     */
    async request(method, path, body = null, options = {}) {
        const auth = options.auth !== false;
        const sendAuth = auth && !this._isPublicApiPath(path);

        const opts = { method, headers: {} };

        const hasJsonBody = body !== null && body !== undefined && typeof body === 'object' && !(body instanceof FormData);
        if (hasJsonBody) {
            opts.headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(body);
        }

        if (sendAuth) {
            const token = this.getToken();
            if (token) opts.headers['Authorization'] = `Bearer ${token}`;
        }

        const res = await fetch(this.base + path, opts);

        const ct = res.headers.get('content-type') || '';
        let data;
        if (ct.includes('application/json')) {
            try {
                data = await res.json();
            } catch {
                data = { detail: res.statusText };
            }
        } else {
            const text = await res.text();
            data = { detail: text || res.statusText };
        }

        if (res.status === 401 && sendAuth) {
            this.clearToken();
            if (!window.location.pathname.startsWith('/login')) {
                window.location.href = '/login';
            }
            throw new Error(this._formatErrorDetail(data));
        }

        if (!res.ok) {
            if (res.status === 429) {
                const msg = this._formatErrorDetail(data);
                throw new Error(
                    msg && msg !== 'Request failed'
                        ? msg
                        : 'تم تجاوز الحد المسموح للطلبات — انتظر دقيقة ثم أعد المحاولة'
                );
            }
            throw new Error(this._formatErrorDetail(data));
        }

        return data;
    },

    get: (p, o) => API.request('GET', p, null, o),
    post: (p, b, o) => API.request('POST', p, b, o),
    put: (p, b, o) => API.request('PUT', p, b, o),
    del: (p, o) => API.request('DELETE', p, null, o),

    _sessionStartInFlight: false,

    /**
     * Start a VR session using only the patient's access_key (server expects { access_key }).
     * Guarded so rapid double-clicks do not trigger rate limiting (429).
     */
    async startSession(accessKey) {
        const key = (accessKey || '').trim();
        if (!key) throw new Error('مفتاح الدخول (access_key) مطلوب');
        if (key.length < 5 || key.length > 20) {
            throw new Error('مفتاح الدخول يجب أن يكون بين 5 و 20 رمزاً (انسخه من صفحة المرضى)');
        }
        if (this._sessionStartInFlight) {
            throw new Error('جاري بدء الجلسة بالفعل');
        }
        this._sessionStartInFlight = true;
        try {
            return await this.post('/api/sessions/start', { access_key: key });
        } finally {
            this._sessionStartInFlight = false;
        }
    },

    logout() {
        this.clearToken();
        window.location.href = '/login';
    },
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
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
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
    document.querySelectorAll('.nav-item').forEach((item) => {
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
    } catch {
        /* ignore */
    }
}
