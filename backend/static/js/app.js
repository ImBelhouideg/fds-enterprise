/* FDS Enterprise — Application Shell & Router */

const App = {
  _page: 'dashboard',
  _wsSocket: null,
  _notifInterval: null,

  async init() {
    // Check auth
    if (!API.isAuthenticated() || !API.getUser()) {
      AuthPage.show(); return;
    }
    this._boot();
  },

  _boot() {
    const u = API.getUser();
    // Update UI identity
    const initial = u?.full_name?.charAt(0) || u?.username?.charAt(0) || '?';
    ['top-avatar','sb-avatar'].forEach(id => {
      const el = document.getElementById(id); if(el) el.textContent=initial;
    });
    const tn = document.getElementById('top-name'); if(tn) tn.textContent = u?.full_name||u?.username||'';
    const tr = document.getElementById('top-role'); if(tr) tr.textContent = u?.role||'';
    const sn = document.getElementById('sb-name');  if(sn) sn.textContent = (u?.full_name||u?.username||'').split(' ')[0];
    const sr = document.getElementById('sb-role');  if(sr) sr.textContent = u?.role||'';

    // Admin nav
    if (['admin','manager'].includes(u?.role)) {
      document.querySelectorAll('.admin-only').forEach(e => e.style.display='');
    }

    // Show app
    document.getElementById('auth-shell')?.classList.remove('visible');
    document.getElementById('app-shell')?.classList.add('visible');

    // Navigate to dashboard
    this.navigate('dashboard');

    // Start periodic notification refresh
    NotifPage.loadCount();
    this._notifInterval = setInterval(() => NotifPage.loadCount(), 30000);

    // WebSocket
    this._initWS();

    // Keyboard shortcut
    document.addEventListener('keydown', e => {
      if ((e.metaKey||e.ctrlKey) && e.key==='k') { e.preventDefault(); document.getElementById('top-search-input')?.focus(); }
      if (e.key==='Escape') { this._closeAll(); }
    });
  },

  _initWS() {
    try {
      if (typeof io !== 'undefined') {
        this._wsSocket = io({ transports: ['websocket','polling'] });
        this._wsSocket.on('connect', () => console.log('[WS] connected'));
        this._wsSocket.on('new_transaction', txn => {
          if (this._page === 'dashboard') DashboardPage.load();
          if (txn.status === 'blocked') {
            Toast.error('🚨 Fraude temps réel', `${txn.merchant} · ${Fmt.currency(txn.amount, txn.currency)}`);
            NotifPage.loadCount();
          }
        });
      }
    } catch {}
  },

  navigate(page) {
    this._closeAll();
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const pageEl = document.getElementById('page-'+page);
    const navEl  = document.getElementById('nav-'+page);
    if (pageEl) pageEl.classList.add('active');
    if (navEl)  navEl.classList.add('active');
    this._page = page;
    // Load page data
    const loaders = {
      dashboard:     () => DashboardPage.load(),
      transactions:  () => TransactionsPage.load(),
      alerts:        () => AlertsPage.load(),
      users:         () => UsersPage.load(),
      audit:         () => AuditPage.load(),
      notifications: () => NotifPage.loadPage(),
      monitoring:    () => MonitorPage.load(),
      profile:       () => ProfilePage.load(),
      settings:      () => SettingsPage.load(),
    };
    if (loaders[page]) loaders[page]();
  },

  _closeAll() {
    document.getElementById('notif-panel')?.classList.remove('open');
    document.getElementById('user-dropdown')?.classList.remove('open');
  },

  logout() {
    if (this._notifInterval) clearInterval(this._notifInterval);
    if (this._wsSocket) this._wsSocket.disconnect();
    API.auth.logout().catch(()=>{});
    API.clearTokens();
    document.getElementById('app-shell')?.classList.remove('visible');
    AuthPage.show();
    Toast.info('Déconnecté');
  },

  toggleNotifPanel() {
    const p = document.getElementById('notif-panel');
    const isOpen = p?.classList.toggle('open');
    if (isOpen) NotifPage.loadCount();
  },

  toggleUserDropdown() {
    document.getElementById('user-dropdown')?.classList.toggle('open');
  },

  globalSearch(q) {
    if (!q?.trim()) return;
    this.navigate('transactions');
    setTimeout(() => {
      const s = document.getElementById('txn-search');
      if (s) { s.value = q; TransactionsPage.load({ search:q }); }
    }, 100);
  },
};

// ════════════════════════════════════════════════════════════════
// AUTH PAGE
// ════════════════════════════════════════════════════════════════
const AuthPage = {
  show() {
    document.getElementById('auth-shell')?.classList.add('visible');
    document.getElementById('app-shell')?.classList.remove('visible');
  },

  switchTab(tab, el) {
    document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
    el?.classList.add('active');
    document.getElementById('auth-login').style.display    = tab==='login'    ? '' : 'none';
    document.getElementById('auth-register').style.display = tab==='register' ? '' : 'none';
  },

  async login() {
    const email = document.getElementById('l-email')?.value.trim();
    const pwd   = document.getElementById('l-pwd')?.value;
    const rem   = document.getElementById('l-remember')?.checked;
    const errEl = document.getElementById('login-error');
    if (errEl) errEl.style.display = 'none';

    const btn = document.getElementById('login-btn');
    if (btn) { btn.disabled=true; btn.innerHTML='<span class="spinner"></span> Connexion…'; }

    try {
      const d = await API.auth.login({ email, password:pwd, remember_me:rem });
      API.setTokens(d.access_token, d.refresh_token);
      API.setUser(d.user);
      Toast.success(`Bienvenue, ${d.user.full_name||d.user.username}!`);
      App._boot();
    } catch(e) {
      if (errEl) { errEl.textContent = e.message||'Identifiants incorrects'; errEl.style.display='block'; }
    } finally {
      if (btn) { btn.disabled=false; btn.textContent='Connexion'; }
    }
  },

  async register() {
    const email    = document.getElementById('r-email')?.value.trim();
    const username = document.getElementById('r-username')?.value.trim();
    const pwd      = document.getElementById('r-pwd')?.value;
    const fname    = document.getElementById('r-fname')?.value.trim();
    const lname    = document.getElementById('r-lname')?.value.trim();
    const errEl    = document.getElementById('register-error');
    if (errEl) errEl.style.display = 'none';

    const btn = document.getElementById('register-btn');
    if (btn) { btn.disabled=true; btn.innerHTML='<span class="spinner"></span>'; }

    try {
      const d = await API.auth.register({ email, username, password:pwd, first_name:fname, last_name:lname });
      API.setTokens(d.access_token, d.refresh_token);
      API.setUser(d.user);
      Toast.success('Compte créé avec succès !');
      App._boot();
    } catch(e) {
      if (errEl) { errEl.textContent = e.message||'Erreur inscription'; errEl.style.display='block'; }
    } finally {
      if (btn) { btn.disabled=false; btn.textContent='Créer un compte'; }
    }
  },
};

// Boot
document.addEventListener('DOMContentLoaded', () => App.init());
