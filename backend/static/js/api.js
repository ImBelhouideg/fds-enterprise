/* FDS Enterprise — API Client */
const API = (() => {
  const BASE = '/api';
  let _access  = localStorage.getItem('fds_token')   || null;
  let _refresh = localStorage.getItem('fds_refresh') || null;

  function setTokens(a, r) {
    _access  = a; _refresh = r;
    if (a) localStorage.setItem('fds_token',   a); else localStorage.removeItem('fds_token');
    if (r) localStorage.setItem('fds_refresh', r); else localStorage.removeItem('fds_refresh');
  }
  function clearTokens() { setTokens(null,null); localStorage.removeItem('fds_user'); }
  function getUser()  { try { return JSON.parse(localStorage.getItem('fds_user')||'null'); } catch { return null; } }
  function setUser(u) { if(u) localStorage.setItem('fds_user', JSON.stringify(u)); else localStorage.removeItem('fds_user'); }

  async function _refresh_token() {
    try {
      const r = await fetch(BASE+'/auth/refresh', {method:'POST',
        headers:{'Content-Type':'application/json','Authorization':'Bearer '+_refresh}});
      if (!r.ok) return false;
      const d = await r.json();
      _access = d.access_token;
      localStorage.setItem('fds_token', _access);
      return true;
    } catch { return false; }
  }

  async function req(method, path, body=null, retry=true) {
    const headers = {'Content-Type':'application/json'};
    if (_access) headers['Authorization'] = 'Bearer '+_access;
    const opts = {method, headers};
    if (body && method !== 'GET') opts.body = JSON.stringify(body);
    try {
      const r = await fetch(BASE+path, opts);
      if (r.status === 401 && retry && _refresh) {
        if (await _refresh_token()) return req(method, path, body, false);
        clearTokens(); window.location.reload(); return null;
      }
      const data = await r.json().catch(()=>({}));
      if (!r.ok) throw {status:r.status, message:data.error||'Request failed', data};
      return data;
    } catch(e) {
      if (e.status) throw e;
      throw {status:0, message:'Network error', data:{}};
    }
  }

  function buildQ(p) {
    if (!p) return '';
    const q = Object.entries(p).filter(([,v])=>v!=null&&v!==undefined&&v!=='')
      .map(([k,v])=>`${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
    return q ? '?'+q : '';
  }

  return {
    isAuthenticated: ()=>!!_access,
    getUser, setUser, setTokens, clearTokens, getToken:()=>_access,
    get:    p        => req('GET',    p),
    post:   (p,b)    => req('POST',   p, b),
    put:    (p,b)    => req('PUT',    p, b),
    patch:  (p,b)    => req('PATCH',  p, b),
    delete: p        => req('DELETE', p),
    auth: {
      login:         d  => req('POST', '/auth/login', d),
      register:      d  => req('POST', '/auth/register', d),
      logout:        ()  => req('POST', '/auth/logout'),
      me:            ()  => req('GET',  '/auth/me'),
      updateProfile: d  => req('PUT',  '/auth/me', d),
      changePass:    d  => req('POST', '/auth/change-password', d),
      refresh:       ()  => _refresh_token(),
    },
    txn: {
      analyze: d       => req('POST', '/transactions/analyze', d),
      list:    p       => req('GET',  '/transactions/'+buildQ(p)),
      stats:   ()      => req('GET',  '/transactions/stats'),
      mapData: ()      => req('GET',  '/transactions/map'),
      export:  ()      => _access, // returns token for download link
    },
    users: {
      list:        p        => req('GET',    '/users/'+buildQ(p)),
      get:         id       => req('GET',    `/users/${id}`),
      create:      d        => req('POST',   '/users/', d),
      update:      (id,d)   => req('PUT',    `/users/${id}`, d),
      delete:      id       => req('DELETE', `/users/${id}`),
      toggleBlock: id       => req('POST',   `/users/${id}/toggle-block`),
      changeRole:  (id,r)   => req('POST',   `/users/${id}/change-role`, {role:r}),
    },
    notif: {
      list:       p  => req('GET',  '/notifications/'+buildQ(p)),
      markRead:   id => req('POST', `/notifications/${id}/read`),
      markAllRead:() => req('POST', '/notifications/read-all'),
    },
    audit: {
      list: p => req('GET', '/audit/'+buildQ(p)),
    },
    monitor: {
      system: () => req('GET', '/monitoring/system'),
      health: () => req('GET', '/monitoring/health'),
    },
    settings: {
      get:    () => req('GET', '/settings/'),
      update: d  => req('PUT', '/settings/', d),
    },
  };
})();
