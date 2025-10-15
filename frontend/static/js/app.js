function setStatus(msg) {
  const el = document.getElementById('status');
  if (el) el.textContent = msg;
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

async function processNow() {
  let payload;
  try {
    payload = JSON.parse(document.getElementById('rawJson').value);
  } catch (e) {
    setStatus('Invalid JSON. Please fix and try again.');
    return;
  }
  setStatus('Processing...');
  const r = await fetch('/api/process-product', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  if (!r.ok) {
    setStatus('Processing failed.');
    return;
  }
  const data = await r.json();
  setStatus('Done.');
  document.getElementById('dppOutput').textContent = JSON.stringify(data.dpp, null, 2);
  document.getElementById('links').innerHTML = `<a href="/dpp/${data.product_id}">Open DPP Viewer</a>` +
    ` <a href="/api/product/${data.product_id}/compliance-report" target="_blank">Compliance Report (JSON)</a>`;
  refreshList();
}

document.getElementById('processBtn').addEventListener('click', processNow);
document.getElementById('loadSample').addEventListener('click', loadSampleTextile);
document.getElementById('loadElectronics').addEventListener('click', loadSampleElectronics);
document.addEventListener('DOMContentLoaded', refreshList);

document.getElementById('mockMode').textContent = 'mock (local-first)';
