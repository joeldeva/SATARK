/* ============================================================
   SATARK Citizen App — Application Logic
   ============================================================ */

// ---- DATA ----
const SURVEYS = [
  {
    id: 'plfs-2026',
    title: 'Periodic Labour Force Survey (PLFS) 2026',
    code: 'DDI-IND-MOSPI-PLFS-2026',
    ministry: 'Ministry of Statistics & Programme Implementation',
    status: 'active',
    duration: '12 min',
    deadline: '31 Mar 2026',
  },
  {
    id: 'nhs-2026',
    title: 'National Health Survey 2026',
    code: 'DDI-IND-MOHFW-NHS-2026',
    ministry: 'Ministry of Health & Family Welfare',
    status: 'active',
    duration: '15 min',
    deadline: '30 Jun 2026',
  },
  {
    id: 'aces-2026',
    title: 'Agriculture Census & Enumeration Survey 2026',
    code: 'DDI-IND-MOAFW-ACES-2026',
    ministry: 'Ministry of Agriculture & Farmers Welfare',
    status: 'upcoming',
    duration: '20 min',
    deadline: '15 Aug 2026',
  },
  {
    id: 'edus-2025',
    title: 'National Education Survey 2025',
    code: 'DDI-IND-MOE-EDUS-2025',
    ministry: 'Ministry of Education',
    status: 'closed',
    duration: '10 min',
    deadline: '31 Dec 2025',
  },
];

function generateAckId() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let id = 'ACK-MQJ';
  for (let i = 0; i < 4; i++) id += chars[Math.floor(Math.random() * chars.length)];
  return id;
}

const HISTORY = [
  {
    title: 'Periodic Labour Force Survey (PLFS) 2026',
    code: 'DDI-IND-MOSPI-PLFS-2026',
    date: '18 Jun 2026',
    ack: generateAckId(),
    ministry: 'Ministry of Statistics & Programme Implementation',
    status: 'Submitted',
  },
  {
    title: 'Periodic Labour Force Survey (PLFS) 2026',
    code: 'DDI-IND-MOSPI-PLFS-2026',
    date: '18 Jun 2026',
    ack: generateAckId(),
    ministry: 'Ministry of Statistics & Programme Implementation',
    status: 'Submitted',
  },
  {
    title: 'Periodic Labour Force Survey (PLFS) 2026',
    code: 'DDI-IND-MOSPI-PLFS-2026',
    date: '18 Jun 2026',
    ack: generateAckId(),
    ministry: 'Ministry of Statistics & Programme Implementation',
    status: 'Submitted',
  },
];

const ALERTS = [
  {
    type: 'info',
    title: 'New Survey Assigned',
    desc: 'You have been assigned the Periodic Labour Force Survey (PLFS) 2026. Please complete i…',
    date: '18 Jun 2026, 04:32 AM',
    read: true,
  },
  {
    type: 'warn',
    title: 'Survey Deadline Approaching',
    desc: 'The National Health Survey 2026 is due in 30 days. Please complete your responses at…',
    date: '18 Jun 2026, 04:32 AM',
    read: true,
  },
  {
    type: 'danger',
    title: 'Important: Verify Survey Authenticity',
    desc: 'Several fake surveys have been reported in your district. Always verify the Survey ID on…',
    date: '18 Jun 2026, 04:32 AM',
    read: true,
  },
  {
    type: 'info',
    title: 'Thank You for Participating',
    desc: 'Your response to the Agriculture Census has been recorded. Acknowledgement ID: ACK-…',
    date: '18 Jun 2026, 04:32 AM',
    read: true,
  },
];

// ---- LIVE SATARK API ----
const API_BASE = (window.SATARK_API_BASE || 'https://sat-full-one.vercel.app/api').replace(/\/$/, '');
const DEMO_LOGIN = { username: 'sdrd', password: 'design123' };
const SERVER_SURVEYS = new Map();
let activeFilter = 'all';

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));
}

async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData)) headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  const token = localStorage.getItem('satark_token');
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 401 && path !== '/auth/login') {
    localStorage.removeItem('satark_token');
    await ensureToken();
    return apiFetch(path, options);
  }
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `SATARK API returned ${response.status}`);
  }
  return response.json();
}

async function ensureToken() {
  if (localStorage.getItem('satark_token')) return localStorage.getItem('satark_token');
  const payload = await apiFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify(DEMO_LOGIN),
  });
  if (payload?.token) localStorage.setItem('satark_token', payload.token);
  return payload?.token;
}

function titleFromSurvey(raw) {
  if (typeof raw?.title === 'string') return raw.title;
  return raw?.title?.en || raw?.name_en || raw?.metadata?.title || raw?.id || 'SATARK Survey';
}

function normalizeSurveySummary(raw) {
  const id = raw.id || raw.survey_id || raw.surveyId;
  const title = titleFromSurvey(raw);
  return {
    id,
    title,
    code: raw.ddi_id || raw.metadata?.ddi_id || raw.metadata?.id_identifier || id,
    ministry: raw.metadata?.organization || 'Ministry of Statistics & Programme Implementation',
    status: String(raw.status || 'published').toLowerCase() === 'published' ? 'active' : String(raw.status || 'active').toLowerCase(),
    duration: raw.metadata?.duration || `${Math.max(5, Math.ceil((raw.nodes?.length || raw.questions?.length || 10) * 1.2))} min`,
    deadline: raw.metadata?.deadline || 'Open',
    raw,
  };
}

function extractQuestionNodes(survey) {
  const nodes = survey?.survey?.nodes || survey?.nodes || survey?.question_graph?.nodes || survey?.questions || [];
  return nodes
    .filter(node => !['adaptive', 'end', 'logic'].includes(String(node.type || '').toLowerCase()))
    .map((node, index) => ({
      id: node.id || node.code || `q_${index + 1}`,
      code: node.code || node.id || `Q${index + 1}`,
      text: node.q?.en || node.text_en || node.text || node.label || `Question ${index + 1}`,
      type: node.type || node.answer_type || 'text',
      options: node.options || [],
      source: node.sourceTrace?.source_document || node.source_trace?.source_document || node.source || 'SATARK',
    }));
}

async function fetchLiveSurveys() {
  try {
    await ensureToken();
    const payload = await apiFetch('/surveys');
    const live = (payload.surveys || payload.items || payload || []).map(normalizeSurveySummary).filter(item => item.id);
    if (!live.length) return;
    SURVEYS.length = 0;
    live.forEach(item => {
      SURVEYS.push(item);
      SERVER_SURVEYS.set(item.id, item.raw);
    });
    updateStats();
    renderSurveys(activeFilter);
  } catch (error) {
    console.warn('SATARK API unavailable, using bundled citizen surveys:', error);
  }
}

async function getSurveyDetail(surveyId) {
  if (SERVER_SURVEYS.has(surveyId) && extractQuestionNodes(SERVER_SURVEYS.get(surveyId)).length) {
    return SERVER_SURVEYS.get(surveyId);
  }
  const payload = await apiFetch(`/surveys/${encodeURIComponent(surveyId)}`);
  const detail = payload.survey || payload;
  SERVER_SURVEYS.set(surveyId, detail);
  return detail;
}

function inputForQuestion(question) {
  const name = escapeHTML(question.id);
  const type = String(question.type || '').toLowerCase();
  const options = Array.isArray(question.options) ? question.options : [];
  if (options.length || type.includes('choice') || type === 'single') {
    const opts = options.length ? options : ['Yes', 'No'];
    return `<select name="${name}" required>${opts.map(option => {
      const label = typeof option === 'string' ? option : option.label || option.value;
      const value = typeof option === 'string' ? option : option.value || option.label;
      return `<option value="${escapeHTML(value)}">${escapeHTML(label)}</option>`;
    }).join('')}</select>`;
  }
  if (type.includes('number')) return `<input name="${name}" type="number" inputmode="decimal" required />`;
  if (type.includes('date')) return `<input name="${name}" type="date" required />`;
  return `<textarea name="${name}" required></textarea>`;
}

function openSurveyModal(summary, detail) {
  const modal = document.getElementById('survey-modal');
  const title = document.getElementById('survey-modal-title');
  const code = document.getElementById('survey-modal-code');
  const body = document.getElementById('survey-modal-body');
  const questions = extractQuestionNodes(detail);
  title.textContent = summary.title;
  code.textContent = summary.code;
  body.innerHTML = questions.length
    ? `<form id="citizen-response-form">${questions.map((question, index) => `
        <div class="survey-question">
          <label>${index + 1}. ${escapeHTML(question.text)}</label>
          ${inputForQuestion(question)}
          <span class="survey-source">Source: ${escapeHTML(question.source)}</span>
        </div>
      `).join('')}</form>`
    : '<p class="subtitle">This survey has no collectable questions yet.</p>';
  modal.dataset.surveyId = summary.id;
  modal.dataset.surveyTitle = summary.title;
  modal.classList.add('open');
  modal.setAttribute('aria-hidden', 'false');
}

function closeSurveyModal() {
  const modal = document.getElementById('survey-modal');
  modal.classList.remove('open');
  modal.setAttribute('aria-hidden', 'true');
}

async function submitOpenSurvey() {
  const modal = document.getElementById('survey-modal');
  const form = document.getElementById('citizen-response-form');
  const button = document.getElementById('survey-submit-btn');
  if (!form || !modal.dataset.surveyId) return;
  const formData = new FormData(form);
  const answers = {};
  formData.forEach((value, key) => { answers[key] = value; });
  button.disabled = true;
  button.textContent = 'Submitting...';
  try {
    const payload = {
      householdId: `HH-CIT-${Date.now()}`,
      respondent_id: 'citizen_app_user',
      enumeratorId: 'CITIZEN-APP',
      channel: 'citizen-app',
      durationSeconds: 90,
      answers,
    };
    const result = await apiFetch(`/surveys/${encodeURIComponent(modal.dataset.surveyId)}/responses`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    HISTORY.unshift({
      title: modal.dataset.surveyTitle,
      code: modal.dataset.surveyId,
      date: new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }),
      ack: result.responseId || result.response_id || generateAckId(),
      ministry: 'Ministry of Statistics & Programme Implementation',
      status: 'Submitted',
    });
    renderHistory();
    updateStats();
    alert(`Response recorded. Acknowledgement: ${HISTORY[0].ack}`);
    closeSurveyModal();
  } catch (error) {
    alert(`Could not submit response: ${error.message}`);
  } finally {
    button.disabled = false;
    button.textContent = 'Submit response';
  }
}

function updateStats() {
  const active = SURVEYS.filter(s => s.status === 'active').length;
  const completed = HISTORY.length;
  const pending = Math.max(0, active - completed);
  const stats = document.querySelectorAll('.stat-num');
  if (stats[0]) stats[0].textContent = String(active);
  if (stats[1]) stats[1].textContent = String(completed);
  if (stats[2]) stats[2].textContent = String(pending);
  if (stats[3]) stats[3].textContent = String(ALERTS.length);
}

// ---- NAVIGATION ----
const pages = document.querySelectorAll('.page');
const navItems = document.querySelectorAll('.nav-item');

function navigateTo(pageId) {
  pages.forEach(p => p.classList.remove('active'));
  navItems.forEach(n => n.classList.remove('active'));

  const target = document.getElementById(`page-${pageId}`);
  if (target) {
    target.classList.add('active');
    window.scrollTo(0, 0);
  }

  navItems.forEach(n => {
    if (n.dataset.page === pageId) n.classList.add('active');
  });
}

navItems.forEach(btn => {
  btn.addEventListener('click', () => navigateTo(btn.dataset.page));
});

// View all button on home → surveys tab
document.getElementById('view-all-surveys')?.addEventListener('click', () => {
  navigateTo('surveys');
});

// Bell → alerts
document.getElementById('bell-btn')?.addEventListener('click', () => {
  navigateTo('alerts');
});

// ---- RENDER SURVEYS ----
function surveyCardHTML(s) {
  const statusClass = s.status === 'active' ? 'badge-active' :
                      s.status === 'upcoming' ? 'badge badge-upcoming' : 'badge badge-closed';
  return `
    <div class="survey-card" data-survey="${s.id}" data-status="${s.status}">
      <div class="survey-card-top">
        <div class="survey-card-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6B5B3E" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
        </div>
        <span class="badge badge-active">${s.status}</span>
        <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#9E9E9E" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </div>
      <h3 class="survey-card-title">${s.title}</h3>
      <p class="survey-card-code">${s.code}</p>
      <div class="survey-card-meta">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9E9E9E" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
        <span>${s.ministry}</span>
      </div>
      <div class="survey-card-details">
        <span>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#9E9E9E" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          ${s.duration}
        </span>
        <span>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#9E9E9E" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          ${s.deadline}
        </span>
      </div>
    </div>
  `;
}

function renderSurveys(filter = 'all') {
  activeFilter = filter;
  const container = document.getElementById('surveys-list');
  const searchVal = document.getElementById('survey-search')?.value?.toLowerCase() || '';
  const filtered = SURVEYS.filter(s => {
    const matchFilter = filter === 'all' || s.status === filter;
    const matchSearch = !searchVal || s.title.toLowerCase().includes(searchVal) || s.code.toLowerCase().includes(searchVal);
    return matchFilter && matchSearch;
  });
  container.innerHTML = filtered.length
    ? filtered.map(surveyCardHTML).join('')
    : '<p style="text-align:center;color:#9E9E9E;padding:40px 0;">No surveys found.</p>';
}

document.addEventListener('click', async e => {
  const card = e.target.closest('.survey-card[data-survey]');
  if (!card) return;
  const summary = SURVEYS.find(item => item.id === card.dataset.survey);
  if (!summary || summary.status !== 'active') return;
  try {
    const detail = await getSurveyDetail(summary.id);
    openSurveyModal(summary, detail);
  } catch (error) {
    alert(`Could not load survey from SATARK: ${error.message}`);
  }
});

document.getElementById('survey-modal-close')?.addEventListener('click', closeSurveyModal);
document.getElementById('survey-modal')?.addEventListener('click', e => {
  if (e.target.id === 'survey-modal') closeSurveyModal();
});
document.getElementById('survey-submit-btn')?.addEventListener('click', submitOpenSurvey);

// Filter tabs
document.getElementById('filter-tabs')?.addEventListener('click', e => {
  const tab = e.target.closest('.tab');
  if (!tab) return;
  document.querySelectorAll('#filter-tabs .tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  renderSurveys(tab.dataset.filter);
});

// Search
document.getElementById('survey-search')?.addEventListener('input', () => {
  const activeTab = document.querySelector('#filter-tabs .tab.active');
  renderSurveys(activeTab?.dataset.filter || 'all');
});

// ---- RENDER HISTORY ----
function historyCardHTML(h) {
  return `
    <div class="history-card">
      <div class="history-card-header">
        <span class="history-card-title">${h.title}</span>
        <span class="badge-submitted">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#43A047" stroke-width="3"><circle cx="12" cy="12" r="10"/><polyline points="9 12 11.5 14.5 16 9"/></svg>
          ${h.status}
        </span>
      </div>
      <p class="history-card-code">${h.code}</p>
      <div class="history-card-footer">
        <span>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#9E9E9E" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          ${h.date}
        </span>
        <span>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#9E9E9E" stroke-width="2"><line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/></svg>
          ${h.ack}
        </span>
      </div>
      <p class="history-card-ministry">${h.ministry}</p>
    </div>
  `;
}

function renderHistory() {
  document.getElementById('history-list').innerHTML = HISTORY.map(historyCardHTML).join('');
}

// ---- RENDER ALERTS ----
function alertIconSVG(type) {
  if (type === 'info') return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1976D2" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
  if (type === 'warn') return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#E8772E" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
  if (type === 'danger') return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#D32F2F" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
  return '';
}

function alertCardHTML(a) {
  return `
    <div class="alert-card">
      <div class="alert-icon ${a.type}">${alertIconSVG(a.type)}</div>
      <div class="alert-body">
        <div class="alert-header">
          <span class="alert-title">${a.title}</span>
          ${a.read ? '<svg class="alert-check" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#43A047" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>' : ''}
        </div>
        <p class="alert-desc">${a.desc}</p>
        <span class="alert-date">${a.date}</span>
      </div>
    </div>
  `;
}

function renderAlerts() {
  document.getElementById('alerts-list').innerHTML = ALERTS.map(alertCardHTML).join('');
}

// ---- INIT ----
renderSurveys();
renderHistory();
renderAlerts();
updateStats();
fetchLiveSurveys();

// ---- STAT CARD SHORTCUTS ----
document.querySelectorAll('.stat-card').forEach((card, i) => {
  card.addEventListener('click', () => {
    // 0=Assigned→surveys, 1=Completed→history, 2=Pending→surveys, 3=Notifications→alerts
    const targets = ['surveys', 'history', 'surveys', 'alerts'];
    navigateTo(targets[i]);
  });
});

// Scroll to top on every page switch
const origNavigateTo = navigateTo;
