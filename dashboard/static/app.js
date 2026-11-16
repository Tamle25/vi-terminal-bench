'use strict';
const $ = (id) => document.getElementById(id);
const TASKS = {
  'b001-vn-invoice': ['B001', 'Hóa đơn & số / ngày', 'Đọc số theo quy ước Việt Nam, tiền VND và ngày dd/mm/yyyy.'],
  'b002-unicode-files': ['B002', 'Unicode & tên file', 'Xử lý tên file có dấu, chuẩn hóa NFC/NFD và phân biệt chữ hoa.'],
  'b003-windows1258': ['B003', 'Chuyển mã Windows-1258', 'Chuyển dữ liệu tiếng Việt sang UTF-8 và giữ nguyên nội dung.'],
  'b004-accent-search': ['B004', 'Tìm kiếm không dấu', 'Tìm văn bản tiếng Việt có dấu và không dấu theo cùng quy tắc.'],
  'b005-vietnamese-collation': ['B005', 'Sắp xếp tiếng Việt', 'Sắp xếp theo locale tiếng Việt trên Node / ICU đã khóa phiên bản.'],
  'b006-vietnamese-csv-export': ['B006', 'CSV cho Excel', 'Xuất CSV tiếng Việt với BOM, CRLF và dấu phân cách đúng yêu cầu.'],
};
const STATUS = {queued:'Đang chờ', running:'Đang chạy', completed:'Hoàn tất', failed:'Đã dừng', interrupted:'Cần kiểm tra', incomplete:'Chưa đủ lượt'};
const ACTION = {preview:'Preview', check:'Kiểm backend', smoke:'Smoke · 2 lượt', batch:'Batch · 36 lượt', resume:'Tiếp tục', report:'Dựng lại baseline', status:'Đọc ngân sách'};
let state = null, selected = 'baseline', focusedJob = null, token = '', pending = false, page = 0;
let lastTableKey = '', lastLog = '', toastTimeout, lastStateText = '', lastChartKey = '';
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fold = (value) => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase();
const num = (value, decimals = 2) => value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString('vi-VN', {maximumFractionDigits: decimals, minimumFractionDigits: decimals});
const pct = (value) => value == null ? '—' : num(value * 100) + '%';
const money = (value, places = 4) => value == null ? '—' : num(value, places);
const date = (value) => new Date(value).toLocaleString('vi-VN', {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});

function toast(text) {
  $('toast').textContent = text; $('toast').hidden = false;
  clearTimeout(toastTimeout); toastTimeout = setTimeout(() => { $('toast').hidden = true; }, 4500);
}
function view() {
  const name = ['overview','runner','history','tasks'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'overview';
  const text = {overview:['Tổng quan benchmark','Đo khả năng làm việc với terminal theo ngữ cảnh tiếng Việt.','Tổng quan'],
    runner:['Chạy benchmark','Từ kiểm tra kế hoạch đến kết quả model thật.','Chạy benchmark'],
    history:['Lịch sử đánh giá','Giữ riêng kết quả, dữ liệu và chi phí của mỗi lần chạy.','Lịch sử chạy'],
    tasks:['Bộ tác vụ tiếng Việt','Sáu tác vụ terminal theo quy ước và dữ liệu Việt Nam.','Bộ tác vụ']}[name];
  $('page-title').textContent = text[0]; $('page-description').textContent = text[1]; $('breadcrumb-current').textContent = text[2];
  document.querySelectorAll('[data-view]').forEach((el) => { el.hidden = el.dataset.view !== name || !state; });
  document.querySelectorAll('[data-nav]').forEach((el) => {
    el.classList.toggle('active', el.dataset.nav === name);
    if (el.dataset.nav === name) el.setAttribute('aria-current', 'page'); else el.removeAttribute('aria-current');
  });
}
function bundle() {
  if (selected === 'baseline') return state.baseline;
  const job = state.jobs.find((j) => j.id === selected);
  return job ? {id:job.run_id, summary:job.summary, trials:job.trials || []} : state.baseline;
}
function render() {
  if (!state) return;
  $('loading').hidden = true; view();
  $('history-count').textContent = state.jobs.length + 1;
  const results = state.jobs.filter((j) => j.summary);
  const options = [{id:'baseline', text:'Baseline · 6 tác vụ'}, ...results.map((j) => ({id:j.id, text:ACTION[j.action] + ' · ' + date(j.created_at)}))];
  const optionsKey = options.map((o) => o.id).join(',');
  if ($('run-select').dataset.key !== optionsKey) {
    $('run-select').innerHTML = options.map((o) => `<option value="${esc(o.id)}">${esc(o.text)}</option>`).join('');
    $('run-select').dataset.key = optionsKey;
  }
  $('run-select').value = selected;
  const data = bundle(), s = data.summary, rows = data.trials;
  $('run-label').textContent = data.id;
  const tag = document.querySelector('.overview-toolbar .status-tag');
  tag.textContent = s.complete ? 'Hoàn tất' : 'Chưa đủ lượt'; tag.className = 'status-tag ' + (s.complete ? 'green' : 'amber');
  const valid = rows.filter((r) => r.valid), passed = valid.filter((r) => r.reward === 1).length;
  $('stat-pass').textContent = valid.length ? pct(passed / valid.length) : '—';
  $('stat-pass-detail').textContent = `${passed} đạt · ${valid.length - passed} không đạt`;
  $('stat-coverage').innerHTML = `${num(s.valid_trials,0)} <small>/ ${num(s.planned_trials,0)}</small>`;
  $('stat-coverage-detail').textContent = s.scope === 'development-smoke' ? 'B001 · 2 ngôn ngữ · smoke riêng' : '6 tác vụ · 2 ngôn ngữ · 3 lần';
  $('stat-delta').textContent = s.delta_vi_pp == null ? '—' : (s.delta_vi_pp >= 0 ? '+' : '') + num(s.delta_vi_pp) + ' đpt';
  $('stat-cost').innerHTML = `<small>$</small> ${money(s.conservative_token_estimate_usd)}`;
  $('macro-en').textContent = pct(s.scores?.en?.macro); $('macro-vi').textContent = pct(s.scores?.vi?.macro);
  const chartKey = JSON.stringify(s.scores);
  if (chartKey !== lastChartKey) {
  lastChartKey = chartKey;
  $('comparison-chart').innerHTML = `<div class="chart-inner"><div class="y-axis"><span>100%</span><span>67%</span><span>33%</span><span>0%</span></div><div class="chart-body">${Object.keys(TASKS).map((tid) => {
    const en = s.scores?.en?.tasks?.[tid], vi = s.scores?.vi?.tasks?.[tid];
    return `<div class="chart-group" aria-label="${esc(TASKS[tid][1])}: EN ${pct(en)}, VI ${pct(vi)}"><div class="chart-bar" style="--height:${Math.max(0, Math.min(100,(en || 0)*100))}%" title="EN: ${pct(en)}"></div><div class="chart-bar vi" style="--height:${Math.max(0, Math.min(100,(vi || 0)*100))}%" title="VI: ${pct(vi)}"></div><span class="chart-label">${TASKS[tid][0]}</span></div>`;
  }).join('')}</div></div>`;
  }
  const exportId = selected === 'baseline' ? 'baseline' : selected;
  $('export-csv').href = `/downloads/${exportId}/trials.csv`; $('export-json').href = `/downloads/${exportId}/summary.json`;
  $('results-subtitle').textContent = `${rows.length} lượt đã ghi nhận · ${s.complete ? 'đủ coverage' : 'coverage chưa hoàn tất'}`;
  $('credential-status').textContent = state.credential_file_present ? 'Có file .env trên máy chủ' : 'Chưa có file .env';
  renderTable(); renderHistory(); renderTasks(); renderLive(); renderBudget();
  const busy = state.jobs.some((j) => ['queued','running'].includes(j.status)) || pending;
  document.querySelectorAll('[data-action], #start-run, #resume-run').forEach((el) => { el.disabled = busy; });
  $('sync-label').textContent = 'Đã đồng bộ ' + new Date().toLocaleTimeString('vi-VN', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
}
function renderTable() {
  const all = bundle().trials;
  const query = fold($('search').value), lang = $('language-filter').value, result = $('result-filter').value;
  const rows = all.filter((r) => (lang === 'all' || lang === r.language) &&
    (result === 'all' || (result === 'pass' && r.valid && r.reward === 1) || (result === 'fail' && r.valid && r.reward === 0) || (result === 'infra' && !r.valid)) &&
    (!query || fold(r.task_id + ' ' + (TASKS[r.task_id] || []).join(' ')).includes(query)));
  const maxPage = Math.max(0, Math.ceil(rows.length / 12) - 1); page = Math.min(page, maxPage);
  const key = JSON.stringify([selected, query, lang, result, page, rows.map((r) => [r.trial_id, r.reward, r.status])]);
  if (key === lastTableKey) return;
  lastTableKey = key;
  $('trials-table').innerHTML = rows.slice(page * 12, page * 12 + 12).map((r) => {
    const index = all.indexOf(r), pass = r.valid && r.reward === 1, fail = r.valid && r.reward === 0;
    return `<tr><td><strong>${esc(TASKS[r.task_id]?.[1] || r.task_id)}</strong><span class="task-id">${esc(TASKS[r.task_id]?.[0] || r.task_id)}</span></td><td><span class="lang-tag">${esc(r.language.toUpperCase())}</span></td><td class="mono">${esc(r.repeat)}</td><td><span class="result-chip ${pass ? '' : fail ? 'fail' : 'infra'}">${pass ? '✓ Đạt' : fail ? '× Không đạt' : '· Lỗi hạ tầng'}</span></td><td class="mono">${num(r.duration_sec,1)}s</td><td class="mono">${num(r.input_tokens,0)} / ${num(r.output_tokens,0)}</td><td class="mono">${money(r.cost_usd,6)}</td><td><button class="detail-button" data-trial="${index}" aria-label="Xem ${esc(r.trial_id)}">↗</button></td></tr>`;
  }).join('') || '<tr><td colspan="8" class="empty-row">Không có lượt chạy phù hợp với bộ lọc.</td></tr>';
  $('table-count').innerHTML = `<span>${rows.length ? page * 12 + 1 : 0}–${Math.min(page*12+12, rows.length)} / ${rows.length} lượt</span> <button class="page-button" id="prev-page" ${page===0?'disabled':''} aria-label="Trang trước">←</button><button class="page-button" id="next-page" ${page===maxPage?'disabled':''} aria-label="Trang sau">→</button>`;
  $('prev-page').onclick = () => { page--; renderTable(); }; $('next-page').onclick = () => { page++; renderTable(); };
}
function syncFilters() {
  const url = new URL(location.href);
  for (const [key, value] of [['q',$('search').value],['lang',$('language-filter').value],['result',$('result-filter').value]]) {
    if (value && value !== 'all') url.searchParams.set(key, value); else url.searchParams.delete(key);
  }
  history.replaceState(null, '', url);
}
function renderHistory() {
  const baseline = `<tr><td><strong>Baseline · 6 tác vụ</strong><span class="task-id">stage11-development-001</span></td><td>Batch · 36 lượt</td><td>13/11/2026</td><td><span class="result-chip">✓ Hoàn tất</span></td><td class="mono">35 / 36 đạt</td><td><button class="button secondary" data-result="baseline">Xem kết quả</button></td></tr>`;
  $('history-table').innerHTML = baseline + state.jobs.map((j) => `<tr><td><strong>${esc(j.run_id)}</strong><span class="task-id">${esc(j.id)}</span></td><td>${esc(ACTION[j.action])}</td><td>${esc(date(j.created_at))}</td><td><span class="status-tag ${j.status === 'completed' ? 'green' : ['failed','interrupted'].includes(j.status) ? 'red' : 'amber'}">${esc(STATUS[j.status])}</span></td><td>${j.summary ? `${j.summary.valid_trials} / ${j.summary.planned_trials} hợp lệ` : '—'}</td><td><button class="button secondary" data-job="${esc(j.id)}">Xem tiến độ</button>${j.summary ? ` <button class="button secondary" data-result="${esc(j.id)}">Xem kết quả</button>` : ''}</td></tr>`).join('');
}
function renderTasks() {
  if ($('task-list').childElementCount) return;
  $('task-list').innerHTML = Object.entries(TASKS).map(([id,t]) => `<article class="task-row"><span class="task-number">${t[0].slice(1)}</span><div><h3>${esc(t[1])}</h3><p>${esc(t[2])}</p><div class="task-meta"><span class="tiny-tag mono">${esc(id)}</span><span class="tiny-tag">EN / VI</span><span class="tiny-tag">v0.1.0</span></div></div><span class="task-review">Chờ review độc lập</span></article>`).join('');
}
function renderLive() {
  const active = state.jobs.find((j) => ['queued','running'].includes(j.status));
  const job = state.jobs.find((j) => j.id === focusedJob) || active || state.jobs[0];
  if (!job) return;
  focusedJob = job.id;
  $('live-message').textContent = job.message;
  $('live-status').textContent = STATUS[job.status];
  $('live-status').className = 'status-tag ' + (job.status === 'completed' ? 'green' : ['failed','interrupted'].includes(job.status) ? 'red' : 'amber');
  const progress = job.progress || {}, parts = String(progress.progress || '').split('/');
  const total = progress.total || Number(parts[1]) || job.summary?.planned_trials || (job.action === 'smoke' ? 2 : job.action === 'batch' ? 36 : 0);
  const done = progress.finished ?? (Number(parts[0]) || job.summary?.valid_trials || 0);
  $('progress').max = total || 1; $('progress').value = total ? done : (job.status === 'completed' ? 1 : 0);
  $('live-progress-label').textContent = job.run_id; $('live-progress-count').textContent = total ? `${done} / ${total}` : (job.status === 'completed' ? 'Hoàn tất' : 'Chuẩn bị');
  const logs = job.logs.join('\n') || job.message;
  if (logs !== lastLog) { $('live-log').textContent = logs; $('live-log').scrollTop = $('live-log').scrollHeight; lastLog = logs; }
  const resumable = ['smoke','batch'].includes(job.action) && ['failed','interrupted','incomplete'].includes(job.status);
  $('live-actions').hidden = !job.summary && !resumable;
  $('view-live-results').hidden = !job.summary; $('resume-run').hidden = !resumable;
}
function renderBudget() {
  const ledgerJob = [...state.jobs].filter((j) => j.ledger || j.summary?.ledger).sort((a,b) => (b.ledger_checked_at || b.updated_at).localeCompare(a.ledger_checked_at || a.updated_at))[0];
  const liveLedger = ledgerJob?.ledger || ledgerJob?.summary?.ledger;
  const exposure = liveLedger ? liveLedger.total_exposure_nano / 1e9 : Number(state.budget.total_exposure_usd);
  $('pool-exposure').textContent = money(exposure);
  $('budget-fill').style.width = Math.min(100, exposure / 2 * 100) + '%';
  const available = liveLedger ? liveLedger.available_nano / 1e9 : Number(state.budget.available_usd);
  $('budget-detail').textContent = `Còn có thể phân bổ ${money(available)} USD · ${liveLedger ? 'ledger tại lần chạy gần nhất' : 'snapshot sau giai đoạn 11'}.`;
}
async function refresh() {
  try {
    const response = await fetch('/api/state', {cache:'no-store'});
    if (!response.ok) throw new Error('STATE_UNAVAILABLE');
    const data = await response.json(); token = data.session_token;
    const text = JSON.stringify(data);
    const disconnected = !$('connection-error').hidden;
    $('connection-error').hidden = true;
    if (text !== lastStateText || disconnected) { state = data; lastStateText = text; render(); }
  } catch {
    $('connection-error').textContent = 'Không kết nối được dashboard. Kiểm tra server còn chạy tại 127.0.0.1:8765; dữ liệu trên trang có thể chưa cập nhật.';
    $('connection-error').hidden = false; $('loading').hidden = true;
  }
}
async function start(action, targetId = null) {
  if (pending) return;
  pending = true; $('run-error').hidden = true; if (state) render();
  try {
    const body = {action}; if (targetId) body.target_job_id = targetId;
    const response = await fetch('/api/jobs', {method:'POST', headers:{'Content-Type':'application/json','X-Dashboard-Token':token}, body:JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'REQUEST_FAILED');
    focusedJob = data.id; location.hash = 'runner';
    toast(['smoke','batch','resume'].includes(action) ? 'Đã nhận lệnh chạy model thật. Theo dõi tiến độ bên dưới.' : 'Đã nhận lệnh. Thao tác này không gọi model.');
    await refresh();
    $('live-title').scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  } catch (error) {
    $('run-error').textContent = error.message === 'RUN_ALREADY_ACTIVE' ? 'Đang có một tác vụ chạy. Chờ hoàn tất trước khi tạo lần chạy mới.' : 'Chưa nhận được lệnh: ' + error.message + '. Kiểm tra lịch sử trước khi thử lại.';
    $('run-error').hidden = false;
    toast($('run-error').textContent);
  } finally { pending = false; if (state) render(); }
}
function detail(index) {
  const r = bundle().trials[index]; if (!r) return;
  $('trial-dialog-title').textContent = TASKS[r.task_id]?.[1] || r.task_id;
  $('trial-detail').innerHTML = `<span class="task-id">${esc(r.trial_id)}</span><dl class="detail-grid">${[
    ['Kết quả',r.valid ? r.reward === 1 ? 'Đạt · reward 1' : 'Không đạt · reward 0' : 'Lỗi hạ tầng · reward null'],
    ['Ngôn ngữ / lần',r.language.toUpperCase() + ' / ' + r.repeat],['Thời gian',num(r.duration_sec,1)+' giây'],
    ['Terminal tool calls',num(r.tool_calls,0)],['Model requests',num(r.model_requests,0)],['Token vào / ra',num(r.input_tokens,0)+' / '+num(r.output_tokens,0)],
    ['Ước tính chi phí',money(r.cost_usd,6)+' USD'],['Dừng do',r.stop_reason || r.error_code || '—']
  ].map(([k,v])=>`<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>${r.trial_id === 'b002-unicode-files--en--r1--mini' && selected === 'baseline' ? '<p class="detail-warning">Thiếu artifact output/files/0001--Báo cáo.txt. Chấm lại cùng artifact vẫn reward 0; không chạy lại model để cải thiện điểm.</p>' : ''}<h3>Artifact đã lưu</h3><pre class="artifact-list">${esc(Object.keys(r.artifact_sha256 || {}).join('\n') || 'Chưa có artifact hợp lệ.')}</pre><p class="billing-note">Thời gian gồm điều phối và công cụ. Chi phí là ước tính token; compute local chưa đo.</p>`;
  $('trial-dialog').showModal();
}
$('run-form').addEventListener('submit', (event) => { event.preventDefault(); start(new FormData(event.currentTarget).get('scope')); });
document.querySelectorAll('[name="scope"]').forEach((el) => el.addEventListener('change', () => {
  document.querySelectorAll('.scope-option').forEach((label) => label.classList.toggle('selected', label.querySelector('input').checked));
  $('start-run').innerHTML = el.value === 'smoke' ? '<span aria-hidden="true">▷</span> Chạy smoke · 2 lượt' : '<span aria-hidden="true">▷</span> Chạy batch · 36 lượt';
}));
document.addEventListener('click', (event) => {
  const action = event.target.closest('[data-action]'); if (action) start(action.dataset.action);
  const trial = event.target.closest('[data-trial]'); if (trial) detail(Number(trial.dataset.trial));
  const result = event.target.closest('[data-result]'); if (result) { selected = result.dataset.result; page = 0; render(); location.hash='overview'; }
  const job = event.target.closest('[data-job]'); if (job) { focusedJob=job.dataset.job; renderLive(); location.hash='runner'; }
});
$('view-live-results').onclick = () => { selected=focusedJob; page=0; render(); location.hash='overview'; };
$('resume-run').onclick = () => start('resume', focusedJob);
$('run-select').addEventListener('change', () => { selected=$('run-select').value; page=0; render(); });
['search','language-filter','result-filter'].forEach((id) => $(id).addEventListener(id==='search'?'input':'change', () => { page=0; renderTable(); syncFilters(); }));
$('close-dialog').onclick = () => $('trial-dialog').close();
$('trial-dialog').addEventListener('click', (event) => { if(event.target === $('trial-dialog')) { const box=event.target.getBoundingClientRect(); if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom) event.target.close(); } });
window.addEventListener('hashchange', view);
const initialFilters = new URL(location.href).searchParams;
$('search').value = initialFilters.get('q') || '';
if (['en','vi'].includes(initialFilters.get('lang'))) $('language-filter').value = initialFilters.get('lang');
if (['pass','fail','infra'].includes(initialFilters.get('result'))) $('result-filter').value = initialFilters.get('result');
refresh();
setInterval(refresh, 2000);
