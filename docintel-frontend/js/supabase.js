/**
 * DocIntel AI — Supabase Real-Time Client
 * =========================================
 * Auth · API wrapper · Realtime subscriptions
 */

// ── Config ────────────────────────────────────────────────────────────────────
const SUPABASE_URL  = 'https://YOUR_SUPABASE_PROJECT.supabase.co';
const SUPABASE_ANON = 'YOUR_SUPABASE_ANON_KEY';
const API_BASE      = 'http://localhost:8000';

// ── Supabase JS client ────────────────────────────────────────────────────────
let supabaseClient = null;

function initSupabase() {
  if (typeof window.supabase !== 'undefined' && !supabaseClient) {
    try {
      supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON, {
        realtime: { params: { eventsPerSecond: 10 } },
      });
    } catch (e) {
      console.warn('[Supabase] init failed:', e);
    }
  }
  return supabaseClient;
}

// ── Path helper — works whether served via HTTP or opened as file:// ──────────
function _loginPath() {
  const p = window.location.pathname;
  // If we're already in /pages/ just go to login.html
  if (p.includes('/pages/')) return 'login.html';
  // Served from root
  return 'pages/login.html';
}

// ── Auth ──────────────────────────────────────────────────────────────────────
const Auth = {
  getToken()    { return localStorage.getItem('docintel_token'); },
  setToken(t)   { localStorage.setItem('docintel_token', t); },
  removeToken() { localStorage.removeItem('docintel_token'); },
  isLoggedIn()  { return !!this.getToken(); },

  async login(email, password) {
    const res = await API.post('/auth/login', { email, password });
    if (res && res.access_token) this.setToken(res.access_token);
    return res;
  },

  async register(email, password, full_name, organization_id) {
    const res = await API.post('/auth/register', { email, password, full_name, organization_id });
    if (res && res.access_token) this.setToken(res.access_token);
    return res;
  },

  logout() {
    this.removeToken();
    RealtimeManager.unsubscribeAll();
    window.location.href = _loginPath();
  },

  async me() {
    return API.get('/auth/me');
  },
};

// ── API wrapper ───────────────────────────────────────────────────────────────
const API = {
  _headers(isFormData = false) {
    const h = {};
    if (!isFormData) h['Content-Type'] = 'application/json';
    const t = Auth.getToken();
    if (t) h['Authorization'] = `Bearer ${t}`;
    return h;
  },

  async _fetch(method, path, body, isFormData = false) {
    const opts = { method, headers: this._headers(isFormData) };
    if (body) opts.body = isFormData ? body : JSON.stringify(body);

    let res;
    try {
      res = await fetch(`${API_BASE}${path}`, opts);
    } catch (_) {
      throw new Error('Cannot reach server — make sure the backend is running on port 8000.');
    }

    // 401 → clear token and redirect to login
    if (res.status === 401) {
      Auth.removeToken();
      window.location.href = _loginPath();
      return;
    }

    if (!res.ok) {
      let detail = `Server error ${res.status}`;
      try {
        const j = await res.json();
        detail = j.detail || j.message || detail;
      } catch (_) {}
      throw new Error(detail);
    }

    if (res.status === 204) return null;
    return res.json();
  },

  get(path)              { return this._fetch('GET',    path); },
  post(path, body)       { return this._fetch('POST',   path, body); },
  delete(path)           { return this._fetch('DELETE', path); },
  upload(path, formData) { return this._fetch('POST',   path, formData, true); },
};

// ── Realtime ──────────────────────────────────────────────────────────────────
const RealtimeManager = {
  _channels: {},

  onTable(table, callback) {
    if (!supabaseClient) return null;
    const key = `table:${table}`;
    if (this._channels[key]) { try { this._channels[key].unsubscribe(); } catch (_) {} }

    const ch = supabaseClient
      .channel(`public:${table}`)
      .on('postgres_changes', { event: '*', schema: 'public', table }, callback)
      .subscribe();

    this._channels[key] = ch;
    return ch;
  },

  onBroadcast(channelName, event, callback) {
    if (!supabaseClient) return null;
    const key = `broadcast:${channelName}:${event}`;
    if (this._channels[key]) { try { this._channels[key].unsubscribe(); } catch (_) {} }

    const ch = supabaseClient
      .channel(`db-${channelName}`)
      .on('broadcast', { event }, (payload) => callback(payload.payload || payload))
      .subscribe();

    this._channels[key] = ch;
    return ch;
  },

  unsubscribeAll() {
    Object.values(this._channels).forEach(ch => { try { ch.unsubscribe(); } catch (_) {} });
    this._channels = {};
  },
};

// ── Auth guard ────────────────────────────────────────────────────────────────
function requireAuth() {
  if (!Auth.isLoggedIn()) {
    window.location.href = _loginPath();
    return false;
  }
  return true;
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initSupabase();
  _autoLoadUser();
});

// Auto-load user avatar on every authenticated page
async function _autoLoadUser() {
  if (!Auth.isLoggedIn()) return;
  try {
    const user = await API.get('/auth/me');
    if (!user) return;
    const name = user.full_name || user.email || '';
    const initials = name.split(' ').filter(Boolean).map(w => w[0]).join('').slice(0, 2).toUpperCase() || '?';
    // Update ALL avatar elements on the page
    document.querySelectorAll('.user-avatar, #user-avatar').forEach(el => {
      el.textContent = initials;
    });
    // Update user name display if present (dashboard)
    const nameEl = document.getElementById('user-name');
    if (nameEl) nameEl.textContent = user.full_name || user.email;
    // Update role if present
    const roleEl = document.querySelector('.user-info .role');
    if (roleEl) roleEl.textContent = user.organization_id ? user.organization_id : 'Member';
    // Update welcome message if present (dashboard)
    const welcomeEl = document.querySelector('h2[style*="font-size:1.875rem"]');
    if (welcomeEl && welcomeEl.textContent.includes('Welcome back')) {
      welcomeEl.textContent = `Welcome back, ${(user.full_name || user.email).split(' ')[0]}`;
    }
    // Store for other scripts
    window._currentUser = user;
  } catch (_) {}
}
