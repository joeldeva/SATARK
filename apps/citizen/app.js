/* SATARK Citizen App - strict backend client. No mock fallback. */

const API_BASE = (window.SATARK_API_BASE || 'https://sat-full-one.vercel.app/api').replace(/\/$/, '');
const APP_LOGIN = { username: 'sdrd', password: 'design123' };

const SURVEYS = [];
const HISTORY = [];
const ALERTS = [];
const SERVER_SURVEYS = new Map();

let activeFilter = 'all';
let backendReady = false;
let collectionEnumeratorId = null;
let collectionHouseholdId = null;

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));
}

function setStatus(message, type = 'loading') {
  const node = document.getElementById('app-status');
  if (!node) return;
  node.textContent = message;
  node.className = `app-status ${type}`;
}

function errorMessage(error) {
  if (!error) return 'Unknown backend error';
  return error.message || String(error);
}

async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }

  const token = localStorage.getItem('satark_token');
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    cache: 'no-store',
  });

  if (!response.ok) {
    let detail = '';
    try {
      const payload = await response.json();
      detail = payload.detail || payload.error || JSON.stringify(payload);
    } catch {
      detail = await response.text();
    }
    throw new Error(detail || `SATARK API returned ${response.status}`);
  }

  if (response.status === 204) return {};
  return response.json();
}

async function ensureToken() {
  const existing = localStorage.getItem('satark_token');
  if (existing) return existing;
  const payload = await apiFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify(APP_LOGIN),
  });
  if (!payload?.token) throw new Error('SATARK login did not return a token');
  localStorage.setItem('satark_token', payload.token);
  return payload.token;
}

async function connectBackend() {
  setStatus('Connecting to SATARK backend...', 'loading');
  await ensureToken();
  const ready = await apiFetch('/health/ready');
  if (ready.ready !== true) {
    throw new Error(`Backend is not ready: ${JSON.stringify(ready.checks || ready)}`);
  }
  backendReady = true;
  setStatus('Connected to live SATARK backend', 'ok');
}

async function resolveCollectionEnumerator() {
  const payload = await apiFetch('/enumerators');
  const rows = Array.isArray(payload) ? payload : (payload.enumerators || payload.items || payload.data || []);
  const first = rows.find(row => row?.id || row?.enumerator_id || row?.enumeratorId);
  if (!first) {
    throw new Error('Backend returned no enumerators for live collection');
  }
  collectionEnumeratorId = first.id || first.enumerator_id || first.enumeratorId;
  setStatus(`Connected to live SATARK backend - collection agent ${collectionEnumeratorId}`, 'ok');
  return collectionEnumeratorId;
}

async function resolveCollectionHousehold() {
  const payload = await apiFetch('/households');
  const rows = Array.isArray(payload) ? payload : (payload.households || payload.items || payload.data || []);
  const first = rows.find(row => row?.id || row?.household_id || row?.householdId);
  if (!first) {
    throw new Error('Backend returned no households for live collection');
  }
  collectionHouseholdId = first.id || first.household_id || first.householdId;
  setStatus(`Connected to live SATARK backend - agent ${collectionEnumeratorId}, household ${collectionHouseholdId}`, 'ok');
  return collectionHouseholdId;
}

function titleFromSurvey(raw) {
  if (typeof raw?.title === 'string') return raw.title;
  return raw?.title?.en || raw?.name_en || raw?.metadata?.title || raw?.id || raw?.survey_id || 'SATARK Survey';
}

function normalizeSurveySummary(raw) {
  const id = raw.id || raw.survey_id || raw.surveyId;
  const title = titleFromSurvey(raw);
  const nodeCount = raw.nodes?.length || raw.question_graph?.nodes?.length || raw.questions?.length || 0;
  return {
    id,
    title,
    code: raw.ddi_id || raw.metadata?.ddi_id || raw.metadata?.id_identifier || id,
    ministry: raw.metadata?.organization || 'Ministry of Statistics & Programme Implementation',
    status: String(raw.status || 'published').toLowerCase() === 'published'
      ? 'active'
      : String(raw.status || 'active').toLowerCase(),
    duration: raw.metadata?.duration || `${Math.max(5, Math.ceil((nodeCount || 10) * 1.2))} min`,
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
  const payload = await apiFetch('/surveys');
  const rows = Array.isArray(payload) ? payload : (payload.surveys || payload.items || []);
  const live = rows.map(normalizeSurveySummary).filter(item => item.id);

  SURVEYS.length = 0;
  SERVER_SURVEYS.clear();
  live.forEach(item => {
    SURVEYS.push(item);
    SERVER_SURVEYS.set(item.id, item.raw);
  });

  updateStats();
  renderSurveys(activeFilter);
  renderHomeSurveys();
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
    if (!options.length) {
      return `<select name="${name}" required>
        <option value="yes">Yes</option>
        <option value="no">No</option>
      </select>`;
    }
    return `<select name="${name}" required>${options.map(option => {
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
    : '<p class="empty-state">Backend returned this survey without collectable questions.</p>';

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

  const answers = {};
  new FormData(form).forEach((value, key) => { answers[key] = value; });

  if (!collectionEnumeratorId || !collectionHouseholdId) {
    alert('Backend submission failed: live enumerator or household is not available for this app session');
    return;
  }

  button.disabled = true;
  button.textContent = 'Submitting...';
  try {
    const result = await apiFetch(`/surveys/${encodeURIComponent(modal.dataset.surveyId)}/responses`, {
      method: 'POST',
      body: JSON.stringify({
        householdId: collectionHouseholdId,
        respondent_id: 'citizen_app_user',
        enumeratorId: collectionEnumeratorId,
        channel: 'citizen-app',
        durationSeconds: 90,
        answers,
      }),
    });

    const responseId = result.responseId || result.response_id;
    if (!responseId) throw new Error('Backend accepted the request but did not return a response id');

    HISTORY.unshift({
      title: modal.dataset.surveyTitle,
      code: modal.dataset.surveyId,
      date: new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }),
      ack: responseId,
      ministry: 'Ministry of Statistics & Programme Implementation',
      status: result.status || 'Submitted',
    });
    renderHistory();
    updateStats();
    closeSurveyModal();
    alert(`Response recorded. Acknowledgement: ${responseId}`);
  } catch (error) {
    alert(`Backend submission failed: ${errorMessage(error)}`);
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

function navigateTo(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const target = document.getElementById(`page-${pageId}`);
  if (target) {
    target.classList.add('active');
    window.scrollTo(0, 0);
  }

  document.querySelectorAll('.nav-item').forEach(n => {
    if (n.dataset.page === pageId) n.classList.add('active');
  });
}

function surveyCardHTML(s) {
  return `
    <div class="survey-card" data-survey="${escapeHTML(s.id)}" data-status="${escapeHTML(s.status)}">
      <div class="survey-card-top">
        <div class="survey-card-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6B5B3E" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
        </div>
        <span class="badge badge-active">${escapeHTML(s.status)}</span>
        <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#9E9E9E" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </div>
      <h3 class="survey-card-title">${escapeHTML(s.title)}</h3>
      <p class="survey-card-code">${escapeHTML(s.code)}</p>
      <div class="survey-card-meta">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9E9E9E" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
        <span>${escapeHTML(s.ministry)}</span>
      </div>
      <div class="survey-card-details">
        <span>${escapeHTML(s.duration)}</span>
        <span>${escapeHTML(s.deadline)}</span>
      </div>
    </div>
  `;
}

function renderHomeSurveys() {
  const container = document.getElementById('home-active-surveys');
  if (!container) return;
  const active = SURVEYS.filter(s => s.status === 'active').slice(0, 2);
  container.innerHTML = active.length
    ? active.map(surveyCardHTML).join('')
    : `<p class="empty-state">${backendReady ? 'No active surveys are published in the backend.' : 'Waiting for backend connection.'}</p>`;
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
    : `<p class="empty-state">${backendReady ? 'No surveys returned by backend for this filter.' : 'Backend is not connected.'}</p>`;
}

function historyCardHTML(h) {
  return `
    <div class="history-card">
      <div class="history-card-header">
        <span class="history-card-title">${escapeHTML(h.title)}</span>
        <span class="badge-submitted">${escapeHTML(h.status)}</span>
      </div>
      <p class="history-card-code">${escapeHTML(h.code)}</p>
      <div class="history-card-footer">
        <span>${escapeHTML(h.date)}</span>
        <span>${escapeHTML(h.ack)}</span>
      </div>
      <p class="history-card-ministry">${escapeHTML(h.ministry)}</p>
    </div>
  `;
}

function renderHistory() {
  const container = document.getElementById('history-list');
  container.innerHTML = HISTORY.length
    ? HISTORY.map(historyCardHTML).join('')
    : '<p class="empty-state">No submitted responses from this app session.</p>';
}

function alertCardHTML(a) {
  return `
    <div class="alert-card">
      <div class="alert-icon ${escapeHTML(a.type)}"></div>
      <div class="alert-body">
        <div class="alert-header"><span class="alert-title">${escapeHTML(a.title)}</span></div>
        <p class="alert-desc">${escapeHTML(a.desc)}</p>
        <span class="alert-date">${escapeHTML(a.date)}</span>
      </div>
    </div>
  `;
}

function renderAlerts() {
  const container = document.getElementById('alerts-list');
  container.innerHTML = ALERTS.length
    ? ALERTS.map(alertCardHTML).join('')
    : '<p class="empty-state">No backend notification feed is configured for this app.</p>';
}

async function boot() {
  renderSurveys();
  renderHomeSurveys();
  renderHistory();
  renderAlerts();
  updateStats();

  try {
    await connectBackend();
    await resolveCollectionEnumerator();
    await resolveCollectionHousehold();
    await fetchLiveSurveys();
  } catch (error) {
    backendReady = false;
    setStatus(`Backend connection failed: ${errorMessage(error)}`, 'error');
    renderSurveys();
    renderHomeSurveys();
  }
}

document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => navigateTo(btn.dataset.page));
});

document.getElementById('view-all-surveys')?.addEventListener('click', () => navigateTo('surveys'));
document.getElementById('bell-btn')?.addEventListener('click', () => navigateTo('alerts'));
document.getElementById('survey-modal-close')?.addEventListener('click', closeSurveyModal);
document.getElementById('survey-modal')?.addEventListener('click', e => {
  if (e.target.id === 'survey-modal') closeSurveyModal();
});
document.getElementById('survey-submit-btn')?.addEventListener('click', submitOpenSurvey);

document.getElementById('filter-tabs')?.addEventListener('click', e => {
  const tab = e.target.closest('.tab');
  if (!tab) return;
  document.querySelectorAll('#filter-tabs .tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  renderSurveys(tab.dataset.filter);
});

document.getElementById('survey-search')?.addEventListener('input', () => {
  const activeTab = document.querySelector('#filter-tabs .tab.active');
  renderSurveys(activeTab?.dataset.filter || 'all');
});

document.addEventListener('click', async e => {
  const card = e.target.closest('.survey-card[data-survey]');
  if (!card) return;
  const summary = SURVEYS.find(item => item.id === card.dataset.survey);
  if (!summary || summary.status !== 'active') return;
  try {
    const detail = await getSurveyDetail(summary.id);
    openSurveyModal(summary, detail);
  } catch (error) {
    alert(`Could not load survey from backend: ${errorMessage(error)}`);
  }
});

document.querySelectorAll('.stat-card').forEach((card, i) => {
  card.addEventListener('click', () => {
    const targets = ['surveys', 'history', 'surveys', 'alerts'];
    navigateTo(targets[i]);
  });
});

boot();
