/* FDS Enterprise — Utilities */

// ── Formatting ────────────────────────────────────────────────
const Fmt = {
  number: n => (n||0).toLocaleString('fr-FR'),
  currency: (n, c='MAD') => `${(n||0).toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2})} ${c}`,
  percent: n => `${(n||0).toFixed(1)}%`,
  date: iso => { if(!iso) return '—'; const d=new Date(iso); return d.toLocaleDateString('fr-FR'); },
  datetime: iso => { if(!iso) return '—'; const d=new Date(iso); return d.toLocaleDateString('fr-FR')+' '+d.toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'}); },
  reltime: iso => {
    if(!iso) return '—';
    const s = (Date.now()-new Date(iso))/1000;
    if(s<60)    return 'À l\'instant';
    if(s<3600)  return Math.floor(s/60)+'m';
    if(s<86400) return Math.floor(s/3600)+'h';
    return Math.floor(s/86400)+'j';
  },
  score: s => {
    if(s>=70) return {color:'var(--red)',  label:'Critique'};
    if(s>=45) return {color:'#ff6432',    label:'Élevé'};
    if(s>=20) return {color:'var(--amber)',label:'Moyen'};
    return {color:'var(--green)',          label:'Faible'};
  },
};

// ── DOM Helpers ───────────────────────────────────────────────
const $ = (sel, ctx=document) => ctx.querySelector(sel);
const $$ = (sel, ctx=document) => [...ctx.querySelectorAll(sel)];
const el = (tag, cls, html) => { const e=document.createElement(tag); if(cls) e.className=cls; if(html) e.innerHTML=html; return e; };

// ── Debounce ──────────────────────────────────────────────────
function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(()=>fn(...a), ms); };
}

// ── Toast ─────────────────────────────────────────────────────
const Toast = {
  _stack: null,
  _init() { if(!this._stack) { this._stack=document.getElementById('toast-container'); } },
  show(title, msg, type='info', dur=5000) {
    this._init();
    if(!this._stack) return;
    const icons={success:'✅',error:'🚨',warn:'⚠️',info:'ℹ️'};
    const d = el('div',`toast ${type}`);
    d.innerHTML = `<span class="toast-icon">${icons[type]||'ℹ️'}</span>
      <div class="toast-msg"><div class="toast-title">${title}</div>${msg?`<div>${msg}</div>`:''}</div>
      <span class="toast-close" onclick="this.parentElement.remove()">✕</span>`;
    this._stack.appendChild(d);
    if(dur>0) setTimeout(()=>d.remove(), dur);
    return d;
  },
  success: (t,m) => Toast.show(t,m,'success'),
  error:   (t,m) => Toast.show(t,m,'error'),
  warn:    (t,m) => Toast.show(t,m,'warn'),
  info:    (t,m) => Toast.show(t,m,'info'),
};

// ── Modal ─────────────────────────────────────────────────────
const Modal = {
  open:  id => document.getElementById(id)?.classList.add('open'),
  close: id => document.getElementById(id)?.classList.remove('open'),
};
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) e.target.classList.remove('open');
});

// ── Theme ─────────────────────────────────────────────────────
const Theme = {
  current: () => localStorage.getItem('fds_theme')||'dark',
  set(t) { localStorage.setItem('fds_theme',t); document.documentElement.setAttribute('data-theme',t); },
  toggle() { this.set(this.current()==='dark'?'light':'dark'); },
};

// ── Risk bar HTML ─────────────────────────────────────────────
function riskBar(score) {
  const s = Fmt.score(score||0);
  return `<div class="risk-bar-wrap">
    <div class="risk-bar-bg"><div class="risk-bar" style="width:${score}%;background:${s.color}"></div></div>
    <span class="risk-val">${score}</span></div>`;
}

// ── Pagination ────────────────────────────────────────────────
function renderPagination(containerId, page, pages, onChange) {
  const el = document.getElementById(containerId);
  if (!el || pages<=1) { if(el) el.innerHTML=''; return; }
  let h = `<button class="pag-btn" onclick="(${onChange})(${page-1})" ${page<=1?'disabled':''}>‹</button>`;
  for (let p=Math.max(1,page-2); p<=Math.min(pages,page+2); p++)
    h += `<button class="pag-btn ${p===page?'active':''}" onclick="(${onChange})(${p})">${p}</button>`;
  h += `<button class="pag-btn" onclick="(${onChange})(${page+1})" ${page>=pages?'disabled':''}>›</button>`;
  h += `<span class="pag-info">${page}/${pages}</span>`;
  el.innerHTML = h;
}

// ── Skeleton KPI ──────────────────────────────────────────────
function skeletonKpi() {
  return `<div class="kpi"><div class="skeleton" style="height:10px;width:60%;margin-bottom:10px"></div>
    <div class="skeleton" style="height:26px;width:40%;margin-bottom:6px"></div>
    <div class="skeleton" style="height:10px;width:50%"></div></div>`;
}

// ── Chart defaults ─────────────────────────────────────────────
Chart.defaults.color = '#7a8fa8';
Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';
Chart.defaults.font.family = "'IBM Plex Mono', monospace";
Chart.defaults.font.size = 11;

const chartInstances = {};
function destroyChart(id) { if(chartInstances[id]) { chartInstances[id].destroy(); delete chartInstances[id]; } }
function saveChart(id, chart) { chartInstances[id] = chart; return chart; }
