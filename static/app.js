const API = '/v1';

async function fetcher(url, opts = {}) {
  const fullUrl = url.startsWith('/') && !url.startsWith('/v1') ? url : (url.startsWith('/v1') ? url : API + url);
  const res = await fetch(fullUrl, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts
  });
  const text = await res.text();
  if (!res.ok) throw new Error(text || res.statusText);
  try { return JSON.parse(text); } catch { return text; }
}

function showResult(el, data, isError = false) {
  if (!el) return;
  el.className = 'output-content' + (isError ? ' error' : '');
  el.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  el.style.display = 'block';
  el.parentElement.style.display = 'block';
}

function setLoading(el, loading) {
  if (!el) return;
  el.textContent = loading ? 'Loading...' : '';
  el.className = loading ? 'output-content loading' : 'output-content';
  el.style.display = loading ? 'block' : 'none';
  el.parentElement.style.display = loading ? 'block' : 'block';
}

async function loadOverview() {
  const healthEl = document.getElementById('healthStatus');
  const badge = document.getElementById('statusBadge');
  try {
    const health = await fetcher('/health');
    if (healthEl) healthEl.textContent = health.status === 'ok' ? 'OK' : 'Degraded';
    if (badge) {
      badge.textContent = 'Connected';
      badge.className = 'status-badge ok';
    }
  } catch {
    if (healthEl) healthEl.textContent = 'Error';
    if (badge) {
      badge.textContent = 'Offline';
      badge.className = 'status-badge err';
    }
  }
  const apiEl = document.getElementById('apiStatus');
  if (apiEl) apiEl.textContent = 'v1';
}

async function loadSubscriptions() {
  const customerId = document.getElementById('subCustomerId')?.value?.trim();
  if (!customerId) return;
  const out = document.getElementById('subsOutput');
  setLoading(out, true);
  try {
    const data = await fetcher(`/subscriptions/${encodeURIComponent(customerId)}`);
    showResult(out, data);
  } catch (e) {
    showResult(out, e.message, true);
  }
}

async function loadUsage() {
  const customerId = document.getElementById('usageCustomerId')?.value?.trim();
  const meter = document.getElementById('usageMeter')?.value?.trim();
  const days = document.getElementById('usageDays')?.value || 30;
  if (!customerId || !meter) return;
  const out = document.getElementById('usageOutput');
  setLoading(out, true);
  try {
    const data = await fetcher(`/usage/aggregate/${encodeURIComponent(customerId)}?meter_name=${encodeURIComponent(meter)}&days=${days}`);
    showResult(out, data);
  } catch (e) {
    showResult(out, e.message, true);
  }
}

async function createUsage() {
  const cust = document.getElementById('createCust')?.value?.trim();
  const subItem = document.getElementById('createSubItem')?.value?.trim();
  const meter = document.getElementById('createMeter')?.value?.trim();
  const qty = parseInt(document.getElementById('createQty')?.value || 1, 10);
  if (!cust || !subItem || !meter) return;
  const out = document.getElementById('createUsageOutput');
  setLoading(out, true);
  try {
    const data = await fetcher('/usage/records', {
      method: 'POST',
      body: JSON.stringify({ stripe_customer_id: cust, stripe_subscription_item_id: subItem, meter_name: meter, quantity: qty })
    });
    showResult(out, data);
  } catch (e) {
    showResult(out, e.message, true);
  }
}

async function askQuestion() {
  const question = document.getElementById('nlQuestion')?.value?.trim();
  const customerId = document.getElementById('nlCustomer')?.value?.trim() || null;
  if (!question) return;
  const out = document.getElementById('nlOutput');
  setLoading(out, true);
  try {
    const data = await fetcher('/ai/query', {
      method: 'POST',
      body: JSON.stringify({ question, customer_id: customerId || undefined })
    });
    showResult(out, data);
  } catch (e) {
    showResult(out, e.message, true);
  }
}

async function loadChurn() {
  const customerId = document.getElementById('churnCustomer')?.value?.trim();
  if (!customerId) return;
  const out = document.getElementById('churnOutput');
  setLoading(out, true);
  try {
    const data = await fetcher('/ai/churn/score', {
      method: 'POST',
      body: JSON.stringify({ customer_id: customerId })
    });
    showResult(out, data);
  } catch (e) {
    showResult(out, e.message, true);
  }
}

async function detectAnomaly() {
  const customerId = document.getElementById('anomalyCustomer')?.value?.trim();
  if (!customerId) return;
  const out = document.getElementById('anomalyOutput');
  setLoading(out, true);
  try {
    const data = await fetcher('/ai/anomaly/detect', {
      method: 'POST',
      body: JSON.stringify({ customer_id: customerId })
    });
    showResult(out, data);
  } catch (e) {
    showResult(out, e.message, true);
  }
}

async function searchLedger() {
  const query = document.getElementById('searchQuery')?.value?.trim();
  if (!query) return;
  const out = document.getElementById('searchOutput');
  setLoading(out, true);
  try {
    const data = await fetcher('/ai/search/ledger', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: 5 })
    });
    showResult(out, data);
  } catch (e) {
    showResult(out, e.message, true);
  }
}

async function reprocess() {
  const eventId = document.getElementById('reprocessEventId')?.value?.trim();
  if (!eventId) return;
  const out = document.getElementById('reprocessOutput');
  setLoading(out, true);
  try {
    const data = await fetcher(`/admin/reprocess/${encodeURIComponent(eventId)}`, { method: 'POST' });
    showResult(out, data);
  } catch (e) {
    showResult(out, e.message, true);
  }
}

function initTabs() {
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById(tab);
      if (panel) panel.classList.add('active');
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  loadOverview();
  document.getElementById('fetchSubs')?.addEventListener('click', loadSubscriptions);
  document.getElementById('fetchUsage')?.addEventListener('click', loadUsage);
  document.getElementById('createUsage')?.addEventListener('click', createUsage);
  document.getElementById('askQuestion')?.addEventListener('click', askQuestion);
  document.getElementById('fetchChurn')?.addEventListener('click', loadChurn);
  document.getElementById('detectAnomaly')?.addEventListener('click', detectAnomaly);
  document.getElementById('searchLedger')?.addEventListener('click', searchLedger);
  document.getElementById('reprocessBtn')?.addEventListener('click', reprocess);
});
