/* === YourMove — Live Session Dashboard JS === */

initPage();

// ─── Session State ────────────────────────────────────
const SESSION_ID = parseInt(window.location.pathname.split('/').pop());
let ws = null;
let gameStats = { correct: 0, wrong: 0, omissions: 0, activity: '\u2014' };
let startTime = null;
let alerts = [];
let wsReconnectAttempts = 0;
const MAX_RECONNECT_DELAY = 30000; // 30s cap
const MAX_WS_RECONNECT_ATTEMPTS = 8;

document.getElementById('session-id').textContent = SESSION_ID;

// ─── Charts Setup ─────────────────────────────────────
const chartOpts = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 200 },
    scales: {
        x: { display: false },
        y: { grid: { color: 'rgba(55,65,81,0.2)', drawBorder: false }, ticks: { color: '#6B7280', font: { size: 10, family: 'JetBrains Mono' } } }
    },
    plugins: { legend: { display: false } },
    elements: { point: { radius: 0 }, line: { tension: 0.35, borderWidth: 2 } }
};

const movementChart = new Chart(document.getElementById('chart-movement'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            data: [],
            borderColor: '#06B6D4',
            backgroundColor: 'rgba(6,182,212,0.08)',
            fill: true,
        }]
    },
    options: { ...chartOpts }
});

const rtChart = new Chart(document.getElementById('chart-rt'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            data: [],
            borderColor: '#8B5CF6',
            backgroundColor: 'rgba(139,92,246,0.08)',
            fill: true,
        }]
    },
    options: { ...chartOpts }
});

const MAX_POINTS = 60;

function pushChartData(chart, value) {
    chart.data.labels.push('');
    chart.data.datasets[0].data.push(value);
    if (chart.data.labels.length > MAX_POINTS) {
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
    }
    chart.update('none');
}

// ─── Gaze Canvas ──────────────────────────────────────
const gazeCanvas = document.getElementById('gaze-canvas');
const gazeCtx = gazeCanvas.getContext('2d');
let gazeHistory = [];

function drawGaze(angle, isLooking) {
    gazeHistory.push({ angle, isLooking, t: Date.now() });
    if (gazeHistory.length > 60) gazeHistory.shift();

    const w = gazeCanvas.width;
    const h = gazeCanvas.height;
    gazeCtx.clearRect(0, 0, w, h);

    const cx = w / 2, cy = h / 2;

    // Rings
    gazeCtx.strokeStyle = 'rgba(55,65,81,0.3)';
    gazeCtx.lineWidth = 1;
    [30, 60].forEach(r => {
        gazeCtx.beginPath();
        gazeCtx.arc(cx, cy, r, 0, Math.PI * 2);
        gazeCtx.stroke();
    });

    // Threshold
    gazeCtx.strokeStyle = 'rgba(245,158,11,0.2)';
    gazeCtx.setLineDash([4, 4]);
    gazeCtx.beginPath();
    gazeCtx.arc(cx, cy, 80, 0, Math.PI * 2);
    gazeCtx.stroke();
    gazeCtx.setLineDash([]);

    // Trail
    gazeHistory.forEach((g, i) => {
        const alpha = (i / gazeHistory.length) * 0.5;
        const r = (g.angle / 45) * 80;
        const t = (i / gazeHistory.length) * Math.PI * 2;
        const x = cx + Math.cos(t) * r;
        const y = cy + Math.sin(t) * r;
        gazeCtx.fillStyle = g.isLooking ? `rgba(16,185,129,${alpha})` : `rgba(239,68,68,${alpha})`;
        gazeCtx.beginPath();
        gazeCtx.arc(x, y, 3, 0, Math.PI * 2);
        gazeCtx.fill();
    });

    // Current
    const last = gazeHistory[gazeHistory.length - 1];
    if (last) {
        const r = (last.angle / 45) * 80;
        const color = last.isLooking ? '#10B981' : '#EF4444';
        gazeCtx.fillStyle = color;
        gazeCtx.beginPath();
        gazeCtx.arc(cx, cy + r * 0.3, 6, 0, Math.PI * 2);
        gazeCtx.fill();
        gazeCtx.strokeStyle = color;
        gazeCtx.lineWidth = 2;
        gazeCtx.beginPath();
        gazeCtx.arc(cx, cy + r * 0.3, 11, 0, Math.PI * 2);
        gazeCtx.stroke();

        // Glow
        gazeCtx.shadowColor = color;
        gazeCtx.shadowBlur = 12;
        gazeCtx.fillStyle = color;
        gazeCtx.beginPath();
        gazeCtx.arc(cx, cy + r * 0.3, 4, 0, Math.PI * 2);
        gazeCtx.fill();
        gazeCtx.shadowBlur = 0;
    }
}

// ─── State Display ────────────────────────────────────
const STATE_EMOJIS = { CALM: '\uD83D\uDE0A', ENGAGED: '\uD83C\uDFAF', STRESSED: '\uD83D\uDE30', OVERWHELMED: '\uD83D\uDEA8' };

function updateStateDisplay(classification) {
    if (!classification) return;
    const state = classification.state;
    const color = STATE_COLORS[state] || '#9CA3AF';
    const emoji = STATE_EMOJIS[state] || '\u2753';

    const circle = document.getElementById('state-circle');
    circle.style.background = color + '15';
    circle.style.color = color;
    circle.style.borderColor = color;
    circle.innerHTML = emoji;
    document.getElementById('state-label').style.color = color;
    document.getElementById('state-label').textContent = STATE_LABELS[state] || state;
    document.getElementById('state-confidence').textContent = '\u0627\u0644\u062B\u0642\u0629: ' + Math.round(classification.confidence * 100) + '%';
}

function updatePSI(psi) {
    if (!psi) return;
    const score = psi.score;
    let color = '#10B981';
    if (score < 40) color = '#EF4444';
    else if (score < 60) color = '#F59E0B';
    else if (score < 80) color = '#3B82F6';

    document.getElementById('psi-value').textContent = Math.round(score);
    document.getElementById('psi-value').style.color = color;

    const bar = document.getElementById('psi-bar');
    bar.style.width = score + '%';
    bar.style.background = score >= 60
        ? 'linear-gradient(90deg, #10B981, #06B6D4)'
        : score >= 40
        ? 'linear-gradient(90deg, #F59E0B, #3B82F6)'
        : 'linear-gradient(90deg, #EF4444, #F59E0B)';

    if (psi.components) {
        document.getElementById('psi-components').innerHTML = Object.entries(psi.components)
            .map(([k, v]) => `<div style="display:flex;justify-content:space-between;padding:3px 0;"><span>${k}</span><span class="mono">${Math.round(v)}</span></div>`)
            .join('');
    }
}

// ─── Alerts ───────────────────────────────────────────
function addAlert(msg, type) {
    type = type || 'info';
    const now = new Date();
    const time = now.toLocaleTimeString('ar-JO', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    alerts.unshift({ msg, type, time });
    if (alerts.length > 25) alerts.pop();

    document.getElementById('alerts-feed').innerHTML = alerts
        .map(a => `<div class="alert-item ${a.type}"><span class="alert-time">${a.time}</span><span>${a.msg}</span></div>`)
        .join('');
}

// ─── Doctor Commands ──────────────────────────────────
function sendCmd(command, value) {
    value = value || '';
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showToast('\u063A\u064A\u0631 \u0645\u062A\u0635\u0644 \u0628\u0627\u0644\u062C\u0644\u0633\u0629', 'error');
        return;
    }
    ws.send(JSON.stringify({ type: 'doctor_command', command, value }));
    addAlert('\u0623\u0631\u0633\u0644 \u0623\u0645\u0631: ' + command + ' ' + value, 'info');
}

function updateSlider(type, value) {
    document.getElementById('val-' + type).textContent = value;
    var cmdMap = { brightness: 'SET_BRIGHTNESS', volume: 'SET_VOLUME', difficulty: 'SET_DIFFICULTY' };
    sendCmd(cmdMap[type], value);
}

// ─── Timer ────────────────────────────────────────────
function updateElapsed() {
    if (!startTime) return;
    const diff = Math.floor((Date.now() - startTime) / 1000);
    const m = Math.floor(diff / 60);
    const s = diff % 60;
    document.getElementById('elapsed').textContent = m.toString().padStart(2,'0') + ':' + s.toString().padStart(2,'0');
}
setInterval(updateElapsed, 1000);

// ─── Load Session Info ────────────────────────────────
async function loadSession() {
    try {
        const session = await API.get('/api/sessions/' + SESSION_ID);
        startTime = new Date(session.started_at).getTime();
        document.getElementById('session-status-badge').innerHTML = getStatusBadge(session.status);

        const patients = await API.get('/api/patients/');
        const p = patients.find(x => x.id === session.patient_id);
        if (p) document.getElementById('patient-name').textContent = p.full_name;

    } catch (e) {
        console.error(e);
        showToast('\u0644\u0645 \u064A\u062A\u0645 \u0627\u0644\u0639\u062B\u0648\u0631 \u0639\u0644\u0649 \u0627\u0644\u062C\u0644\u0633\u0629', 'error');
    }
}

// ─── WebSocket Connection (token in query — matches server authenticate_ws_token) ──
function connectWS() {
    const token = typeof API !== 'undefined' && API.getToken ? API.getToken() : localStorage.getItem('ym_token');
    if (!token) {
        showToast('\u063A\u064A\u0631 \u0645\u0633\u062C\u0644 \u0627\u0644\u062F\u062E\u0648\u0644', 'error');
        window.location.href = '/login';
        return;
    }

    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url =
        proto +
        '://' +
        location.host +
        '/ws/dashboard/' +
        SESSION_ID +
        '?token=' +
        encodeURIComponent(token);

    ws = new WebSocket(url);

    ws.onopen = function() {
        wsReconnectAttempts = 0;
        document.getElementById('ws-dot').className = 'connection-dot online';
        document.getElementById('ws-status').textContent = '\u0645\u062A\u0635\u0644';
        addAlert('\u062A\u0645 \u0627\u0644\u0627\u062A\u0635\u0627\u0644 \u0628\u0627\u0644\u062C\u0644\u0633\u0629', 'success');
    };

    ws.onclose = function (ev) {
        document.getElementById('ws-dot').className = 'connection-dot offline';
        document.getElementById('ws-status').textContent = '\u063A\u064A\u0631 \u0645\u062A\u0635\u0644';

        // 4001 = auth failure — do not retry (avoids reconnect storms)
        if (ev && ev.code === 4001) {
            addAlert('\u0641\u0634\u0644 \u0627\u0644\u0645\u0635\u0627\u062F\u0642\u0629 \u2014 \u0623\u0639\u062F \u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062F\u062E\u0648\u0644', 'error');
            return;
        }

        if (wsReconnectAttempts >= MAX_WS_RECONNECT_ATTEMPTS) {
            addAlert('\u062A\u0648\u0642\u0641 \u0625\u0639\u0627\u062F\u0629 \u0627\u0644\u0627\u062A\u0635\u0627\u0644 \u0628\u0639\u062F \u0639\u062F\u0629 \u0645\u062D\u0627\u0648\u0644\u0627\u062A', 'error');
            return;
        }

        // Exponential backoff: 1s, 2s, 4s, ... cap 30s
        var delay = Math.min(1000 * Math.pow(2, wsReconnectAttempts), MAX_RECONNECT_DELAY);
        wsReconnectAttempts++;
        addAlert('\u0627\u0646\u0642\u0637\u0639 \u0627\u0644\u0627\u062A\u0635\u0627\u0644 \u2014 \u0625\u0639\u0627\u062F\u0629 \u0627\u0644\u0645\u062D\u0627\u0648\u0644\u0629 \u062E\u0644\u0627\u0644 ' + Math.round(delay/1000) + '\u062B...', 'warning');
        setTimeout(connectWS, delay);
    };

    ws.onmessage = function(e) {
        try {
            var data = JSON.parse(e.data);
            handleMessage(data);
        } catch (err) { console.error(err); }
    };
}

// ─── Message Handler ──────────────────────────────────
function handleMessage(data) {
    var type = data.type;

    if (type === 'motion_data') {
        var ml = data.ml || {};
        var stat = ml.statistical || {};
        var ewma = stat.ewma_movement || 0;
        pushChartData(movementChart, ewma);
        document.getElementById('movement-val').textContent = ewma.toFixed(2);

        updateStateDisplay(ml.classification);
        updatePSI(ml.psi);

        var motion = ml.motion || {};
        document.getElementById('m-rms').textContent = (motion.rms_total || 0).toFixed(3);
        document.getElementById('m-entropy').textContent = (motion.entropy_total || 0).toFixed(3);
        document.getElementById('m-freq').textContent = (motion.dominant_freq_hz || 0).toFixed(3) + ' Hz';
        document.getElementById('m-ratio').textContent = (motion.upper_lower_ratio || 0).toFixed(2);
        document.getElementById('m-state').textContent = motion.motion_state || '\u2014';

        if (ml.ai_command) {
            addAlert('AI: ' + ml.ai_command.command + ' \u2014 ' + ml.ai_command.reason, 'critical');
        }
    }

    else if (type === 'game_event') {
        if (data.is_correct === true) gameStats.correct++;
        else if (data.is_correct === false) gameStats.wrong++;
        if (data.event_type === 'omission') gameStats.omissions++;
        if (data.activity_type) gameStats.activity = data.activity_type;

        document.getElementById('g-correct').textContent = gameStats.correct;
        document.getElementById('g-wrong').textContent = gameStats.wrong;
        document.getElementById('g-omissions').textContent = gameStats.omissions;
        document.getElementById('g-activity').textContent = gameStats.activity;

        var ml = data.ml || {};
        var stat = ml.statistical || {};
        if (stat.ewma_rt) {
            pushChartData(rtChart, stat.ewma_rt);
            document.getElementById('rt-val').textContent = Math.round(stat.ewma_rt) + ' ms';
        }

        updateStateDisplay(ml.classification);
    }

    else if (type === 'head_gaze') {
        var angle = data.angle_to_target || 0;
        var looking = data.is_looking_at_target || false;
        drawGaze(angle, looking);

        document.getElementById('gaze-angle').textContent = angle.toFixed(1) + '\u00B0';
        document.getElementById('gaze-status').innerHTML = looking
            ? '<span style="color:var(--calm);">\u25CF \u064A\u0646\u0638\u0631</span>'
            : '<span style="color:var(--overwhelmed);">\u25CF \u0644\u0627 \u064A\u0646\u0638\u0631</span>';

        if (data.ml_gaze) {
            document.getElementById('gaze-ewma').textContent = (data.ml_gaze.ewma_gaze_angle || 0).toFixed(1);
        }
    }

    else if (type === 'session_event') {
        addAlert('\u062D\u062F\u062B: ' + data.event + ' ' + (data.activity_type || ''), 'info');
        if (data.event === 'session_end') {
            document.getElementById('session-status-badge').innerHTML = getStatusBadge('completed');
            addAlert('\u0627\u0646\u062A\u0647\u062A \u0627\u0644\u062C\u0644\u0633\u0629', 'success');
        }
        if (data.event === 'baseline_start') addAlert('\u0628\u062F\u0623\u062A \u0645\u0631\u062D\u0644\u0629 Baseline', 'info');
        if (data.event === 'baseline_end') addAlert('\u0627\u0646\u062A\u0647\u0649 Baseline \u2014 \u0628\u062F\u0621 \u0627\u0644\u0644\u0639\u0628 \u0627\u0644\u0639\u0627\u062F\u064A', 'success');
    }

    else if (type === 'ai_command') {
        addAlert('AI Command: ' + data.command + ' \u2014 ' + data.reason, 'critical');
    }

    else if (type === 'system') {
        if (data.event === 'ue5_connected') addAlert('UE5 \u0645\u062A\u0635\u0644', 'success');
        if (data.event === 'ue5_disconnected') addAlert('UE5 \u0627\u0646\u0642\u0637\u0639 \u0627\u0644\u0627\u062A\u0635\u0627\u0644', 'warning');
    }
}

// ─── Init ─────────────────────────────────────────────
loadSession();
connectWS();
