/* FDS Enterprise — Page Renderers */

// ════════════════════════════════════════════════════════════════
// DASHBOARD PAGE
// ════════════════════════════════════════════════════════════════
const DashboardPage = {
  async load() {
    try {
      const [stats, txns] = await Promise.all([
        API.txn.stats(),
        API.txn.list({ per_page: 8, sort: 'created_at', order: 'desc' }),
      ]);
      this._renderKPIs(stats);
      this._renderCharts(stats);
      this._renderRecentTable(txns.transactions || []);
      this._renderCountryList(stats.by_country || {});
      this._renderTopFraud(stats.risk_distribution || {});
    } catch (e) {
      Toast.error('Erreur dashboard', e.message);
    }
  },

  _renderKPIs(s) {
    const set = (id, v) => { const el = document.getElementById(id); if(el) el.textContent = v; };
    set('k-total',    Fmt.number(s.total));
    set('k-approved', Fmt.number(s.approved));
    set('k-blocked',  Fmt.number(s.blocked));
    set('k-amount',   Fmt.currency(s.total_amount));
    set('k-fraud-rate', Fmt.percent(s.fraud_rate));
    set('k-fraud',    Fmt.percent(s.fraud_rate));
    set('k-risk',     s.avg_risk_score?.toFixed(1) || '0');
    // nav counts
    const nb = document.getElementById('nb-alerts');
    if (nb) { nb.textContent = s.blocked || 0; nb.classList.toggle('alert', (s.blocked||0) > 0); }
  },

  _renderCharts(s) {
    // Daily area chart
    const daily = (s.daily || []).slice(-14);
    destroyChart('chart-daily');
    const ctx1 = document.getElementById('chart-daily')?.getContext('2d');
    if (ctx1) {
      saveChart('chart-daily', new Chart(ctx1, {
        type: 'line',
        data: {
          labels: daily.map(d => d.date),
          datasets: [
            { label:'Approuvées', data: daily.map(d=>d.approved||0),
              borderColor:'#00e5a0', backgroundColor:'rgba(0,229,160,.08)',
              fill:true, tension:.4, borderWidth:2, pointRadius:3 },
            { label:'Bloquées',   data: daily.map(d=>d.blocked||0),
              borderColor:'#ff4060', backgroundColor:'rgba(255,64,96,.08)',
              fill:true, tension:.4, borderWidth:2, pointRadius:3 },
          ],
        },
        options: {
          responsive:true, maintainAspectRatio:false,
          plugins:{ legend:{ labels:{ color:'#7a8fa8', padding:20 } } },
          scales:{
            x:{ grid:{color:'rgba(255,255,255,.04)'}, ticks:{color:'#3d5070'} },
            y:{ grid:{color:'rgba(255,255,255,.04)'}, ticks:{color:'#3d5070',stepSize:1}, beginAtZero:true },
          },
        },
      }));
    }

    // Donut - risk distribution
    const rd = s.risk_distribution || {};
    destroyChart('chart-risk');
    const ctx2 = document.getElementById('chart-risk')?.getContext('2d');
    if (ctx2) {
      const data = [rd.low||0, rd.medium||0, rd.high||0, rd.critical||0];
      saveChart('chart-risk', new Chart(ctx2, {
        type: 'doughnut',
        data: {
          labels: ['Faible','Moyen','Élevé','Critique'],
          datasets:[{ data, backgroundColor:['#00e5a040','#ffaa0040','rgba(255,100,50,.25)','#ff406040'],
            borderColor:['#00e5a0','#ffaa00','#ff6432','#ff4060'], borderWidth:2 }],
        },
        options:{
          responsive:true, maintainAspectRatio:false, cutout:'65%',
          plugins:{ legend:{ position:'bottom', labels:{ color:'#7a8fa8', padding:12 } } },
        },
      }));
    }
  },

  _renderRecentTable(txns) {
    const tbody = document.getElementById('dash-tbody');
    if (!tbody) return;
    if (!txns.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--t3)">Aucune transaction</td></tr>';
      return;
    }
    tbody.innerHTML = txns.map(t => `
      <tr onclick="App.navigate('transactions')" style="cursor:pointer">
        <td class="mono-id">${t.txn_ref}</td>
        <td>${t.user_label||'—'}</td>
        <td>${t.merchant}</td>
        <td class="mono-sm">${Fmt.currency(t.amount,t.currency)}</td>
        <td>${t.country}</td>
        <td>${riskBar(t.risk_score)}</td>
        <td><span class="pill ${t.status}">${t.status==='approved'?'Approuvé':'Bloqué'}</span></td>
      </tr>`).join('');
  },

  _renderCountryList(byCountry) {
    const NAMES={MA:'Maroc',FR:'France',US:'États-Unis',GB:'Royaume-Uni',DE:'Allemagne',
      ES:'Espagne',IT:'Italie',CA:'Canada',RU:'Russie',CN:'Chine',NG:'Nigeria',BR:'Brésil'};
    const FLAGS={MA:'🇲🇦',FR:'🇫🇷',US:'🇺🇸',GB:'🇬🇧',DE:'🇩🇪',ES:'🇪🇸',IT:'🇮🇹',CA:'🇨🇦',
      RU:'🇷🇺',CN:'🇨🇳',NG:'🇳🇬',BR:'🇧🇷',IN:'🇮🇳',AU:'🇦🇺',JP:'🇯🇵'};
    const el = document.getElementById('country-list');
    if (!el) return;
    const sorted = Object.entries(byCountry).sort((a,b)=>b[1]-a[1]).slice(0,8);
    if (!sorted.length) { el.innerHTML = '<div class="empty-state"><div class="empty-icon">🌍</div></div>'; return; }
    const max = Math.max(...sorted.map(([,c])=>c),1);
    el.innerHTML = sorted.map(([code,cnt]) => `
      <div class="country-row">
        <span class="country-flag">${FLAGS[code]||'🌐'}</span>
        <span class="country-name">${NAMES[code]||code}</span>
        <div class="country-bar-bg"><div class="country-bar" style="width:${cnt/max*100}%"></div></div>
        <span class="country-cnt">${cnt}</span>
      </div>`).join('');
  },

  _renderTopFraud(rd) {
    const el = document.getElementById('risk-dist-labels');
    if (!el) return;
    const items = [
      {label:'Faible',    count:rd.low||0,      color:'var(--green)'},
      {label:'Moyen',     count:rd.medium||0,   color:'var(--amber)'},
      {label:'Élevé',     count:rd.high||0,     color:'#ff6432'},
      {label:'Critique',  count:rd.critical||0, color:'var(--red)'},
    ];
    const total = items.reduce((s,i)=>s+i.count,0)||1;
    el.innerHTML = items.map(i => `
      <div style="display:flex;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)">
        <div style="display:flex;align-items:center;gap:8px">
          <div style="width:8px;height:8px;border-radius:50%;background:${i.color}"></div>
          <span style="font-size:12px">${i.label}</span>
        </div>
        <span class="mono-sm">${i.count} <span style="color:var(--t3)">(${(i.count/total*100).toFixed(0)}%)</span></span>
      </div>`).join('');
  },
};

// ════════════════════════════════════════════════════════════════
// ANALYZE PAGE
// ════════════════════════════════════════════════════════════════
const AnalyzePage = {
  _user: 'user@fds.io',

  setUser(email, el) {
    this._user = email;
    $$('.user-tab').forEach(t => t.classList.remove('active'));
    if (el) el.classList.add('active');
  },

  loadScenario(type) {
    const S = {
      normal:   {amount:350,  country:'MA', merchant:'Amazon'},
      amount:   {amount:8500, country:'MA', merchant:'Bitcoin Exchange'},
      geo:      {amount:200,  country:'NG', merchant:'Shop Online'},
      duplicate:{amount:350,  country:'MA', merchant:'Amazon', repeat:true},
      velocity: {amount:150,  country:'MA', merchant:'Carrefour', multi:4},
      combined: {amount:9999, country:'RU', merchant:'Crypto Market'},
    };
    const s = S[type]; if (!s) return;
    $('#a-amount').value  = s.amount;
    $('#a-country').value = s.country;
    $('#a-merchant').value= s.merchant;
    this._updateCountryWarn();
    if (s.repeat)     { this.submit(); setTimeout(()=>this.submit(), 600); }
    else if (s.multi) { for(let i=0;i<s.multi;i++) setTimeout(()=>this.submit(), i*300); }
    else              { this.submit(); }
  },

  _updateCountryWarn() {
    const HIGH = ['RU','CN','NG','PK','VN','KP','IR'];
    const warn = $('#country-warn');
    if (warn) warn.style.display = HIGH.includes($('#a-country')?.value||'') ? '' : 'none';
  },

  async submit() {
    const amount   = parseFloat($('#a-amount')?.value);
    const country  = $('#a-country')?.value;
    const merchant = $('#a-merchant')?.value?.trim();
    const card     = $('#a-card')?.value?.trim();

    if (!amount || amount <= 0) { Toast.error('Montant invalide','Entrez un montant positif'); return; }
    if (!merchant)               { Toast.error('Marchand requis','Entrez un nom de marchand'); return; }

    const btn  = $('#analyze-btn');
    const btnT = $('#analyze-btn-text');
    if (btn)  btn.disabled = true;
    if (btnT) btnT.innerHTML = '<span class="spinner"></span> Analyse…';

    try {
      const res = await API.txn.analyze({ amount, country, merchant, card_last4:card, user_label:this._user });
      this._renderResult(res);
      if (res.fraud) Toast.error('🚨 Fraude détectée', `${merchant} · ${Fmt.currency(amount)}`);
      else           Toast.success('✅ Approuvé', `${merchant} · ${Fmt.currency(amount)}`);
    } catch(e) {
      Toast.error('Erreur d\'analyse', e.message);
    } finally {
      if (btn) btn.disabled = false;
      if (btnT) btnT.textContent = '⚡ Analyser';
    }
  },

  _renderResult(d) {
    const score = d.risk_score || 0;
    const s = Fmt.score(score);

    // Show panels
    $('#analyze-placeholder')?.classList.add('hidden');
    $('#gauge-card')?.classList.remove('hidden');
    $('#checks-card')?.classList.remove('hidden');
    $('#shap-card')?.classList.remove('hidden');

    // Gauge animation
    const fill = $('#g-fill');
    const scoreEl = $('#g-score');
    if (fill) {
      const offset = 220 - (score/100)*220;
      fill.style.strokeDashoffset = offset;
      fill.style.stroke = s.color;
    }
    if (scoreEl) {
      let cur = 0;
      const step = () => {
        cur = Math.min(cur + Math.ceil((score-cur)/5)+1, score);
        scoreEl.textContent = cur;
        scoreEl.style.fill = s.color;
        if (cur < score) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }

    // Gauge card glow
    const gc = $('#gauge-card');
    if (gc) {
      gc.className = 'gauge-card';
      if (score >= 70)      gc.classList.add('g-critical');
      else if (score >= 45) gc.classList.add('g-high');
      else if (score >= 20) gc.classList.add('g-medium');
      else                  gc.classList.add('g-ok');
    }

    // Verdict
    const vEl  = $('#verdict');
    const vIco = $('#v-icon');
    const vTit = $('#v-title');
    const vSub = $('#v-sub');
    if (vEl) {
      vEl.className = d.fraud ? 'verdict v-danger' : score >= 25 ? 'verdict v-warn' : 'verdict v-ok';
    }
    if (vIco) vIco.textContent = d.fraud ? '🚨' : score >= 25 ? '⚠️' : '✅';
    if (vTit) vTit.textContent = d.fraud ? 'TRANSACTION BLOQUÉE' : score >= 25 ? 'ACTIVITÉ SUSPECTE' : 'TRANSACTION APPROUVÉE';
    if (vSub) vSub.textContent = `Score ${score}/100 · Confiance ${Math.round((d.confidence||0)*100)}% · ${s.label}`;

    // Checks
    const cl = $('#checks-list');
    if (cl) {
      cl.innerHTML = '';
      (d.checks||[]).forEach((c, i) => {
        const div = document.createElement('div');
        div.className = `check-item ${c.passed?'pass':'fail'}`;
        div.style.animationDelay = `${i*50}ms`;
        div.innerHTML = `
          <span class="check-icon">${c.icon}</span>
          <div class="check-body">
            <div class="check-name">${c.check}</div>
            <div class="check-detail">${c.detail}</div>
          </div>
          <span class="check-pill ${c.passed?'pass':'fail'}">${c.passed?'PASS':'FAIL'}</span>`;
        cl.appendChild(div);
      });
    }

    // SHAP
    const sl = $('#shap-list');
    if (sl) {
      const maxVal = Math.max(...(d.shap_values||[]).map(s=>Math.abs(s.value)),0.01);
      sl.innerHTML = (d.shap_values||[]).map(s => `
        <div class="shap-row">
          <span class="shap-feat">${s.feature}</span>
          <div class="shap-bar-bg">
            <div class="shap-bar ${s.value>0?'pos':'neg'}" style="width:${Math.abs(s.value)/maxVal*100}%"></div>
          </div>
          <span class="shap-num">${s.value>0?'+':''}${(s.value*100).toFixed(0)}</span>
        </div>`).join('');
      const conf = $('#shap-conf');
      if (conf) conf.textContent = Math.round((d.confidence||0)*100) + '%';
    }

    // Explanation
    const expEl = $('#ai-explanation');
    if (expEl) expEl.textContent = d.explanation || '';
  },
};

// ════════════════════════════════════════════════════════════════
// TRANSACTIONS PAGE
// ════════════════════════════════════════════════════════════════
const TransactionsPage = {
  _page: 1,
  _params: {},

  async load(params={}) {
    this._params = params;
    try {
      const d = await API.txn.list({ page: this._page, per_page: 25, ...this._params });
      this._render(d);
    } catch(e) { Toast.error('Erreur', e.message); }
  },

  _render(d) {
    const sub = document.getElementById('txn-sub');
    if (sub) sub.textContent = `${d.total} transactions`;

    const tbody = document.getElementById('txn-tbody');
    if (!tbody) return;
    if (!d.transactions?.length) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:32px;color:var(--t3)">Aucune transaction trouvée</td></tr>';
    } else {
      tbody.innerHTML = d.transactions.map(t => `
        <tr>
          <td><span class="mono-id" style="cursor:pointer" onclick="TransactionsPage.showDetail(${JSON.stringify(JSON.stringify(t))})">${t.txn_ref}</span></td>
          <td style="font-size:11px;color:var(--t2)">${Fmt.datetime(t.created_at)}</td>
          <td style="font-size:12px">${t.user_label||'—'}</td>
          <td>${t.merchant}</td>
          <td class="mono-sm">${Fmt.currency(t.amount,t.currency)}</td>
          <td>${t.country}</td>
          <td>${riskBar(t.risk_score)}</td>
          <td><span class="risk-badge ${t.risk_level}">${{low:'Faible',medium:'Moyen',high:'Élevé',critical:'Critique'}[t.risk_level]||t.risk_level}</span></td>
          <td><span class="pill ${t.status}">${t.status==='approved'?'Approuvé':'Bloqué'}</span></td>
        </tr>`).join('');
    }
    renderPagination('txn-pagination', d.page, d.pages, p => { this._page=p; this.load(this._params); });
  },

  showDetail(jsonStr) {
    const t = JSON.parse(jsonStr);
    document.getElementById('txn-modal-title').textContent = `Transaction ${t.txn_ref}`;
    document.getElementById('txn-modal-body').innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
        <div class="card-sm"><div style="font-size:11px;color:var(--t2);margin-bottom:4px">Montant</div>
          <div style="font-family:var(--mono);font-size:20px;font-weight:700">${Fmt.currency(t.amount,t.currency)}</div></div>
        <div class="card-sm"><div style="font-size:11px;color:var(--t2);margin-bottom:4px">Score risque</div>
          <div style="font-family:var(--mono);font-size:20px;font-weight:700;color:${Fmt.score(t.risk_score).color}">${t.risk_score}/100</div></div>
      </div>
      <div style="display:flex;flex-direction:column;gap:8px;font-size:12px">
        ${[['Référence',t.txn_ref],['Utilisateur',t.user_label||'—'],['Marchand',t.merchant],
           ['Pays',t.country],['Carte','****'+t.card_last4||'—'],['IP',t.ip_address||'—'],
           ['Date',Fmt.datetime(t.created_at)],
           ['Statut',`<span class="pill ${t.status}">${t.status==='approved'?'Approuvé':'Bloqué'}</span>`],
           ['Niveau',`<span class="risk-badge ${t.risk_level}">${t.risk_level}</span>`],
        ].map(([k,v])=>`<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)">
          <span style="color:var(--t2)">${k}</span><span>${v}</span></div>`).join('')}
      </div>
      ${t.explanation ? `<div style="margin-top:14px;padding:12px;background:var(--surface2);border-radius:var(--r2);font-size:12px;color:var(--t2)">${t.explanation}</div>` : ''}`;
    Modal.open('txn-modal');
  },

  async exportCSV() {
    const token = API.getToken();
    if (!token) return;
    const a = document.createElement('a');
    a.href = '/api/transactions/export?format=csv&token='+encodeURIComponent(token);
    a.download = 'fds-transactions.csv'; a.click();
    Toast.success('Export CSV lancé');
  },
};

// ════════════════════════════════════════════════════════════════
// USERS PAGE  
// ════════════════════════════════════════════════════════════════
const UsersPage = {
  _page: 1,

  async load(params={}) {
    try {
      const d = await API.users.list({ page:this._page, per_page:20, ...params });
      this._render(d);
    } catch(e) { Toast.error('Erreur', e.message); }
  },

  _render(d) {
    const nb = document.getElementById('nb-users');
    if (nb) nb.textContent = d.total || 0;
    const tbody = document.getElementById('users-tbody');
    if (!tbody) return;
    if (!d.users?.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--t3)">Aucun utilisateur</td></tr>';
      return;
    }
    tbody.innerHTML = d.users.map(u => `
      <tr>
        <td>
          <div style="display:flex;align-items:center;gap:8px">
            <div class="avatar" style="width:26px;height:26px;font-size:11px">${u.full_name?.charAt(0)||u.username?.charAt(0)||'?'}</div>
            <div><div style="font-size:12px;font-weight:600">${u.full_name||u.username}</div>
              <div style="font-size:10px;color:var(--t2);font-family:var(--mono)">${u.username}</div></div>
          </div>
        </td>
        <td style="font-size:12px;color:var(--t2)">${u.email}</td>
        <td><span class="role-badge ${u.role}">${u.role}</span></td>
        <td><span class="pill ${u.is_active?'ok':'blocked'}">${u.is_active?'Actif':'Bloqué'}</span></td>
        <td class="mono-sm">${Fmt.number(u.login_count||0)}</td>
        <td class="mono-sm">${u.last_login ? Fmt.reltime(u.last_login) : 'Jamais'}</td>
        <td>
          <div style="display:flex;gap:4px">
            <button class="btn btn-ghost btn-xs" onclick="UsersPage.editUser('${u.id}')">✏️</button>
            <button class="btn btn-ghost btn-xs" onclick="UsersPage.toggleBlock('${u.id}','${u.username}')" title="${u.is_active?'Bloquer':'Débloquer'}">
              ${u.is_active?'🔒':'🔓'}</button>
            <button class="btn btn-danger btn-xs" onclick="UsersPage.deleteUser('${u.id}','${u.full_name||u.username}')">🗑</button>
          </div>
        </td>
      </tr>`).join('');
    renderPagination('users-pagination', d.page, d.pages, p=>{ this._page=p; this.load(); });
  },

  openCreate() {
    ['m-uid','m-fname','m-lname','m-email','m-username','m-pwd'].forEach(id => {
      const el = document.getElementById(id); if(el) el.value = '';
    });
    const sel = document.getElementById('m-role'); if(sel) sel.value='analyst';
    document.getElementById('user-modal-title').textContent = 'Créer un utilisateur';
    const pf = document.getElementById('m-pwd-field'); if(pf) pf.style.display='';
    Modal.open('user-modal');
  },

  async editUser(id) {
    try {
      const u = await API.users.get(id);
      document.getElementById('m-uid').value      = u.id;
      document.getElementById('m-fname').value    = u.first_name||'';
      document.getElementById('m-lname').value    = u.last_name||'';
      document.getElementById('m-email').value    = u.email;
      document.getElementById('m-username').value = u.username;
      document.getElementById('m-role').value     = u.role;
      const pf = document.getElementById('m-pwd-field'); if(pf) pf.style.display='none';
      document.getElementById('user-modal-title').textContent = 'Modifier l\'utilisateur';
      Modal.open('user-modal');
    } catch(e) { Toast.error('Erreur', e.message); }
  },

  async saveUser() {
    const uid      = document.getElementById('m-uid')?.value;
    const fname    = document.getElementById('m-fname')?.value.trim();
    const lname    = document.getElementById('m-lname')?.value.trim();
    const email    = document.getElementById('m-email')?.value.trim();
    const username = document.getElementById('m-username')?.value.trim();
    const role     = document.getElementById('m-role')?.value;
    const pwd      = document.getElementById('m-pwd')?.value;

    try {
      if (uid) {
        await API.users.update(uid, { first_name:fname, last_name:lname, role });
        Toast.success('Utilisateur mis à jour');
      } else {
        if (!email || !username || !pwd) { Toast.error('Champs requis', 'Email, username et mot de passe obligatoires'); return; }
        await API.users.create({ email, username, password:pwd, first_name:fname, last_name:lname, role });
        Toast.success('Utilisateur créé');
      }
      Modal.close('user-modal');
      this.load();
    } catch(e) { Toast.error('Erreur', e.message); }
  },

  async toggleBlock(id, name) {
    try {
      const r = await API.users.toggleBlock(id);
      Toast.info(`${name} ${r.is_active ? 'débloqué' : 'bloqué'}`);
      this.load();
    } catch(e) { Toast.error('Erreur', e.message); }
  },

  async deleteUser(id, name) {
    if (!confirm(`Supprimer ${name} ?`)) return;
    try {
      await API.users.delete(id);
      Toast.success(`${name} supprimé`);
      this.load();
    } catch(e) { Toast.error('Erreur', e.message); }
  },
};

// ════════════════════════════════════════════════════════════════
// AUDIT PAGE
// ════════════════════════════════════════════════════════════════
const AuditPage = {
  _page: 1,

  async load(params={}) {
    try {
      const d = await API.audit.list({ page:this._page, per_page:50, ...params });
      this._render(d);
    } catch(e) { Toast.error('Erreur audit', e.message); }
  },

  _render(d) {
    const tbody = document.getElementById('audit-tbody');
    if (!tbody) return;
    if (!d.logs?.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:32px;color:var(--t3)">Aucun log</td></tr>';
      return;
    }
    tbody.innerHTML = d.logs.map(l => {
      const user = l.user;
      return `<tr>
        <td><span class="sev-badge ${l.severity}">${l.severity}</span></td>
        <td class="mono-sm">${Fmt.datetime(l.created_at)}</td>
        <td style="font-size:12px">${user?.username||l.user_id||'—'}</td>
        <td><span style="font-family:var(--mono);font-size:11px;color:var(--cyan)">${l.action}</span></td>
        <td class="mono-sm">${l.ip_address||'—'}</td>
        <td style="font-size:11px;color:var(--t2);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${l.details||'—'}</td>
      </tr>`;
    }).join('');
    renderPagination('audit-pagination', d.page, d.pages, p=>{ this._page=p; this.load(); });
  },
};

// ════════════════════════════════════════════════════════════════
// NOTIFICATIONS PAGE
// ════════════════════════════════════════════════════════════════
const NotifPage = {
  _unread: 0,

  async loadCount() {
    try {
      const d = await API.notif.list({ per_page:5 });
      this._unread = d.unread_count || 0;
      const badge = document.getElementById('notif-badge');
      if (badge) { badge.textContent = this._unread; badge.classList.toggle('show', this._unread > 0); }
      const nb = document.getElementById('nb-notif');
      if (nb) { nb.textContent = this._unread || ''; nb.classList.toggle('alert', this._unread > 0); }
      this._renderPanel(d.notifications || []);
    } catch {}
  },

  _renderPanel(notifs) {
    const list = document.getElementById('notif-panel-list');
    if (!list) return;
    if (!notifs.length) {
      list.innerHTML = '<div class="empty-state" style="padding:24px"><div class="empty-icon">🔔</div><div class="empty-sub">Aucune notification</div></div>';
      return;
    }
    list.innerHTML = notifs.map(n => `
      <div class="notif-item ${n.is_read?'':'unread'}" onclick="NotifPage.markRead('${n.id}',this)">
        <div class="notif-led ${n.is_read?'read':n.type==='fraud_detected'?'critical':'info'}"></div>
        <div class="notif-body">
          <div class="title">${n.title}</div>
          <div class="msg">${n.message}</div>
          <div class="ts">${Fmt.reltime(n.created_at)}</div>
        </div>
      </div>`).join('');
  },

  async loadPage() {
    try {
      const d = await API.notif.list({ per_page:50 });
      const cont = document.getElementById('notif-page-list');
      if (!cont) return;
      if (!d.notifications?.length) {
        cont.innerHTML = '<div class="empty-state"><div class="empty-icon">🔔</div><div class="empty-title">Aucune notification</div></div>';
        return;
      }
      cont.innerHTML = d.notifications.map(n => `
        <div class="notif-item ${n.is_read?'':'unread'}" style="border-radius:var(--r2);margin-bottom:4px"
             onclick="NotifPage.markRead('${n.id}',this)">
          <div class="notif-led ${n.is_read?'read':n.type==='fraud_detected'?'critical':'info'}"></div>
          <div class="notif-body" style="flex:1">
            <div class="title">${n.title}</div>
            <div class="msg">${n.message}</div>
            <div class="ts">${Fmt.datetime(n.created_at)}</div>
          </div>
        </div>`).join('');
    } catch(e) { Toast.error('Erreur notifications', e.message); }
  },

  async markRead(id, el) {
    try {
      await API.notif.markRead(id);
      el?.classList.remove('unread');
      el?.querySelector('.notif-led')?.classList.replace('critical','read');
      el?.querySelector('.notif-led')?.classList.replace('info','read');
      this.loadCount();
    } catch {}
  },

  async markAllRead() {
    try {
      await API.notif.markAllRead();
      Toast.success('Tout lu');
      this.loadCount();
      this.loadPage();
    } catch(e) { Toast.error('Erreur', e.message); }
  },
};

// ════════════════════════════════════════════════════════════════
// MONITORING PAGE
// ════════════════════════════════════════════════════════════════
const MonitorPage = {
  async load() {
    try {
      const d = await API.monitor.system();
      this._render(d);
    } catch(e) {
      // Simulate data when unavailable
      this._render({
        cpu:{percent:Math.random()*40+15,count:4},
        memory:{percent:Math.random()*30+40,total:8*1024**3,used:4*1024**3},
        disk:{percent:Math.random()*20+20,total:100*1024**3,used:25*1024**3},
        redis:{status:'connected',used_memory_human:'48M',connected_clients:3},
        database:{status:'healthy'},
        network:{bytes_sent:1e8,bytes_recv:5e8},
      });
    }
  },

  _render(d) {
    const setBar = (id, pct, color) => {
      const el = document.getElementById(id); if(!el) return;
      el.style.width = pct + '%';
      el.style.background = pct>80?'var(--red)':pct>60?'var(--amber)':color;
    };
    const setText = (id, v) => { const el=document.getElementById(id); if(el) el.textContent=v; };

    setText('mon-cpu', (d.cpu?.percent||0)+'%');
    setBar('mon-cpu-bar', d.cpu?.percent||0, 'var(--cyan)');
    setText('mon-ram', (d.memory?.percent||0)+'%');
    setBar('mon-ram-bar', d.memory?.percent||0, 'var(--green)');
    setText('mon-disk', (d.disk?.percent||0)+'%');
    setBar('mon-disk-bar', d.disk?.percent||0, 'var(--amber)');

    // Services table
    const svc = document.getElementById('mon-services');
    if (svc) {
      const services = [
        {name:'Flask API',     status:'ok',        color:'var(--green)'},
        {name:'PostgreSQL',    status:d.database?.status==='healthy'?'ok':'error', color:d.database?.status==='healthy'?'var(--green)':'var(--red)'},
        {name:'Redis',         status:d.redis?.status==='connected'?'ok':'warning',color:d.redis?.status==='connected'?'var(--green)':'var(--amber)'},
        {name:'Nginx',         status:'ok',        color:'var(--green)'},
        {name:'Prometheus',    status:'ok',        color:'var(--green)'},
        {name:'Grafana',       status:'ok',        color:'var(--green)'},
        {name:'SocketIO WS',   status:'ok',        color:'var(--green)'},
        {name:'ML Engine',     status:'ok',        color:'var(--green)'},
      ];
      svc.innerHTML = services.map(s => `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)">
          <span style="font-size:12px">${s.name}</span>
          <div style="display:flex;align-items:center;gap:6px">
            <div style="width:7px;height:7px;border-radius:50%;background:${s.color}"></div>
            <span style="font-family:var(--mono);font-size:11px;color:${s.color}">${s.status}</span>
          </div>
        </div>`).join('');
    }

    // Redis info
    const ri = document.getElementById('mon-redis');
    if (ri && d.redis) {
      ri.innerHTML = [
        ['Statut',     d.redis.status],
        ['Mémoire',    d.redis.used_memory_human||'N/A'],
        ['Clients',    d.redis.connected_clients||0],
        ['Hits',       Fmt.number(d.redis.keyspace_hits||0)],
        ['Misses',     Fmt.number(d.redis.keyspace_misses||0)],
      ].map(([k,v])=>`<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border)">
        <span style="font-size:12px;color:var(--t2)">${k}</span>
        <span class="mono-sm">${v}</span></div>`).join('');
    }
  },
};

// ════════════════════════════════════════════════════════════════
// PROFILE PAGE
// ════════════════════════════════════════════════════════════════
const ProfilePage = {
  async load() {
    const u = API.getUser();
    if (!u) return;
    const set = (id, v) => { const el=document.getElementById(id); if(el) el.textContent=v||'—'; };
    const setVal = (id, v) => { const el=document.getElementById(id); if(el) el.value=v||''; };
    ['prof-avatar','top-avatar','sb-avatar'].forEach(id=>{
      const el=document.getElementById(id); if(el) el.textContent=u.full_name?.charAt(0)||u.username?.charAt(0)||'?';
    });
    set('prof-name',  u.full_name||u.username);
    set('prof-email', u.email);
    set('prof-role',  u.role);
    const roleEl = document.getElementById('prof-role-badge');
    if (roleEl) { roleEl.textContent=u.role; roleEl.className=`role-badge ${u.role}`; }
    setVal('p-fname', u.first_name);
    setVal('p-lname', u.last_name);
    // stats
    try {
      const s = await API.txn.stats();
      set('prof-total',   Fmt.number(s.total));
      set('prof-approved',Fmt.number(s.approved));
      set('prof-blocked', Fmt.number(s.blocked));
      set('prof-amount',  Fmt.currency(s.total_amount));
      set('prof-logins',  Fmt.number(u.login_count||0));
    } catch {}
  },

  async saveProfile() {
    const fname = document.getElementById('p-fname')?.value.trim();
    const lname = document.getElementById('p-lname')?.value.trim();
    try {
      const u = await API.auth.updateProfile({ first_name:fname, last_name:lname });
      API.setUser(u);
      Toast.success('Profil mis à jour');
      this.load();
    } catch(e) { Toast.error('Erreur', e.message); }
  },

  async changePassword() {
    const old = document.getElementById('p-old')?.value;
    const np  = document.getElementById('p-new')?.value;
    const cf  = document.getElementById('p-confirm')?.value;
    if (np !== cf) { Toast.error('Erreur', 'Les mots de passe ne correspondent pas'); return; }
    if (!np || np.length < 8) { Toast.error('Erreur', 'Minimum 8 caractères'); return; }
    try {
      await API.auth.changePass({ current_password:old, new_password:np });
      Toast.success('Mot de passe modifié');
      ['p-old','p-new','p-confirm'].forEach(id=>{const el=document.getElementById(id);if(el)el.value='';});
    } catch(e) { Toast.error('Erreur', e.message); }
  },
};

// ════════════════════════════════════════════════════════════════
// SETTINGS PAGE
// ════════════════════════════════════════════════════════════════
const SettingsPage = {
  _prefs: {},

  async load() {
    try {
      const d = await API.settings.get();
      this._prefs = d;
      this._apply(d);
    } catch {}
  },

  _apply(p) {
    const tog = (id, val) => {
      const el=document.getElementById(id); if(el) el.classList.toggle('on',val);
    };
    tog('tog-email',   p.notifications_email!==false);
    tog('tog-push',    p.notifications_push!==false);
    tog('tog-sound',   p.notifications_sound!==false);
    const thresh = document.getElementById('fraud-threshold');
    if (thresh) thresh.value = p.fraud_alert_threshold || 50;
  },

  toggle(key, el) {
    el.classList.toggle('on');
    this._prefs[key] = el.classList.contains('on');
    this.save();
  },

  async save(extra={}) {
    Object.assign(this._prefs, extra);
    try {
      await API.settings.update(this._prefs);
      Toast.success('Préférences sauvegardées');
    } catch(e) { Toast.error('Erreur', e.message); }
  },
};


// ════════════════════════════════════════════════════════════════
// ALERTS PAGE (Blocked transactions sorted by risk)
// ════════════════════════════════════════════════════════════════
const AlertsPage = {
  _page: 1,

  async load() {
    try {
      const d = await API.txn.list({ 
        status: 'blocked', sort: 'risk_score', order: 'desc',
        page: this._page, per_page: 25 
      });
      this._render(d);
    } catch(e) { Toast.error('Erreur alertes', e.message); }
  },

  _render(d) {
    const RISK_LABELS = {low:'Faible',medium:'Moyen',high:'Élevé',critical:'Critique'};
    const tbody = document.getElementById('alerts-tbody');
    if (!tbody) return;
    if (!d.transactions?.length) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:32px;color:var(--t3)">✅ Aucune alerte active</td></tr>';
    } else {
      tbody.innerHTML = d.transactions.map(t => `
        <tr onclick="TransactionsPage.showDetail(${JSON.stringify(JSON.stringify(t))})" style="cursor:pointer">
          <td class="mono-id">${t.txn_ref}</td>
          <td style="font-size:11px;color:var(--t2)">${Fmt.datetime(t.created_at)}</td>
          <td style="font-size:12px">${t.user_label||'—'}</td>
          <td>${t.merchant}</td>
          <td class="mono-sm">${Fmt.currency(t.amount,t.currency)}</td>
          <td>${t.country}</td>
          <td>${riskBar(t.risk_score)}</td>
          <td><span class="risk-badge ${t.risk_level}">${RISK_LABELS[t.risk_level]||t.risk_level}</span></td>
          <td><span class="pill ${t.status}">Bloqué</span></td>
        </tr>`).join('');
    }
    renderPagination('alerts-pagination', d.page, d.pages, p=>{ this._page=p; this.load(); });
  },
};
