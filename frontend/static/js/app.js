function setStatus(msg) {
  const el = document.getElementById('status');
  if (el) el.textContent = msg;
}
function showOverlay(show) {
  document.getElementById('processingOverlay').classList.toggle('hidden', !show);
}

async function refreshList() {
  const ul = document.getElementById('productList');
  ul.innerHTML = '<li>Loading...</li>';
  const r = await fetch('/api/products/');
  const data = await r.json();
  ul.innerHTML = '';
  data.products.forEach(p => {
    const li = document.createElement('li');
    const left = document.createElement('span');
    left.textContent = `${p.product_name} (${p.product_id})`;
    const view = document.createElement('a');
    view.href = `/dpp/${p.product_id}`;
    view.textContent = 'View';
    view.className = 'link';
    li.appendChild(left);
    li.appendChild(view);
    ul.appendChild(li);
  });
}

function loadSampleTextile() {
  const sample = {
    product_name: "Eco Tee",
    manufacturer: "GreenThreads",
    description: "Material: Cotton 60%, Polyester 40%. Recycled content ~ 25%. CO2 ~ 2.4 kg CO2e.",
    notes: "Repair score 7/10; Wash cold; Recycle fabric.",
    suppliers: ["Acme Textiles Ltd", "EcoPack Co"]
  };
  document.getElementById('rawJson').value = JSON.stringify(sample, null, 2);
}
function loadSampleElectronics() {
  const sample = {
    product_name: "EcoPhone X",
    manufacturer: "CircuLab",
    bom_text: "Frame: Aluminium 40%; Glass 30%; Plastics (ABS) 30% recycled 15%. Total CO2 18.5 kg CO2e.",
    specs: "Repair score 6/10; Battery removable; End-of-life: return to store."
  };
  document.getElementById('rawJson').value = JSON.stringify(sample, null, 2);
}

// --- Visuals ---
function updateRadial(percent) {
  const el = document.getElementById('recycledRadial');
  const deg = Math.max(0, Math.min(100, percent)) * 3.6;
  el.style.background = `conic-gradient(var(--accent) 0deg, var(--accent) ${deg}deg, #23325a ${deg}deg)`;
  el.setAttribute('data-label', `${Math.round(percent)}%`);
}
function updateBar(id, value, max=100) {
  const el = document.getElementById(id);
  const pct = Math.max(0, Math.min(100, (value/max)*100));
  el.style.width = `${pct}%`;
}
function drawMaterialsChart(materials) {
  const c = document.getElementById('materialsChart');
  const ctx = c.getContext('2d');
  ctx.clearRect(0,0,c.width,c.height);
  // simple donut
  const total = materials.reduce((s,m)=>s + (m.percentage||0), 0) || 1;
  const cx = c.width/2, cy = c.height/2, r = Math.min(cx, cy) - 10;
  let start = -Math.PI/2;
  const palette = ['#68c6ff','#9fd17d','#ffc857','#ff8a7a','#c8a6ff','#85e0d0','#f2a3ff'];
  materials.forEach((m,i)=>{
    const frac = (m.percentage||0)/total;
    const end = start + frac * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(cx,cy);
    ctx.arc(cx,cy,r,start,end);
    ctx.closePath();
    ctx.fillStyle = palette[i % palette.length];
    ctx.fill();
    start = end;
  });
  // inner hole
  ctx.beginPath();
  ctx.arc(cx,cy,r*0.55,0,Math.PI*2);
  ctx.fillStyle = '#0a1122';
  ctx.fill();
}

let lastProductId = null;
let lastDpp = null;

async function processNow() {
  let payload;
  try {
    payload = JSON.parse(document.getElementById('rawJson').value);
  } catch (e) {
    setStatus('Invalid JSON. Please fix and try again.');
    return;
  }
  showOverlay(true);
  setStatus('Processing...');
  const r = await fetch('/api/process-product', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  showOverlay(false);
  if (!r.ok) {
    setStatus('Processing failed.');
    return;
  }
  const data = await r.json();
  setStatus('Done.');
  lastProductId = data.product_id;
  lastDpp = data.dpp;
  document.getElementById('dppOutput').textContent = JSON.stringify(data.dpp, null, 2);
  document.getElementById('links').innerHTML =
    `<a href="/dpp/${data.product_id}">Open DPP Viewer</a>` +
    ` <a href="/api/product/${data.product_id}/compliance-report" target="_blank">Compliance Report (JSON)</a>`;
  refreshList();

  // Insights + visuals
  const ins = await fetch('/api/insights', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data.dpp)}).then(r=>r.json());
  document.getElementById('insightText').textContent = ins.summary || '—';
  updateRadial(data.dpp.recycled_content_percentage || 0);
  drawMaterialsChart(data.dpp.materials_composition || []);
  updateBar('scoreBar', ins.score || 0, 100);
  updateBar('co2Bar', data.dpp.co2_footprint_kg || 0, 50); // simple 0..50kg scale
}

async function detectMode() {
  try {
    const cfg = await fetch('/api/config').then(r=>r.json());
    const badge = document.getElementById('modeBadge');
    if (cfg.ai_backend === 'openai' && cfg.openai_configured) {
      badge.textContent = '🧠 Mode: OpenAI Live';
      badge.style.boxShadow = '0 0 12px rgba(100,255,180,.45)';
    } else {
      badge.textContent = '⚙️ Mode: Local Mock';
      badge.style.boxShadow = '0 0 12px rgba(91,209,255,.35)';
    }
  } catch {
    document.getElementById('modeBadge').textContent = 'Mode: Unknown';
  }
}

function appendMsg(role, text) {
  const box = document.getElementById('chatBox');
  const wrap = document.createElement('div');
  wrap.className = `msg ${role}`;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  wrap.appendChild(bubble);
  box.appendChild(wrap);
  box.scrollTop = box.scrollHeight;
}

async function sendChat() {
  const q = document.getElementById('chatQuestion').value.trim();
  if (!q) return;
  appendMsg('user', q);
  document.getElementById('chatQuestion').value = '';
  if (!lastProductId) {
    appendMsg('ai', 'Process a product first, then ask questions about it.');
    return;
  }
  const r = await fetch('/api/assistant', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({product_id: lastProductId, question: q})
  });
  const data = await r.json();
  appendMsg('ai', data.answer || 'No answer available.');
}

// Export CSV (download from JSON response)
async function exportCsv() {
  if (!lastProductId) { setStatus('Process a product first.'); return; }
  const r = await fetch(`/api/product/${lastProductId}/export.csv`);
  const data = await r.json();
  const blob = new Blob([data.csv], {type: 'text/csv;charset=utf-8;'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${lastProductId}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

document.getElementById('processBtn').addEventListener('click', processNow);
document.getElementById('loadSample').addEventListener('click', loadSampleTextile);
document.getElementById('loadElectronics').addEventListener('click', loadSampleElectronics);
document.getElementById('chatSend').addEventListener('click', sendChat);
document.getElementById('btnExportCsv').addEventListener('click', exportCsv);
document.addEventListener('DOMContentLoaded', () => { refreshList(); detectMode(); });
