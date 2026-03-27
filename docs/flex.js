const queryEl = document.getElementById('query');
const metaEl = document.getElementById('meta');
const tableEl = document.getElementById('store-table');
const tbodyEl = document.getElementById('store-tbody');

const MAX_ROWS = 300;

function createCell(v) {
  const td = document.createElement('td');
  td.textContent = v || '-';
  return td;
}

function renderRows(rows) {
  tbodyEl.textContent = '';
  if (!rows.length) {
    tableEl.hidden = true;
    return;
  }
  const frag = document.createDocumentFragment();
  for (const store of rows) {
    const tr = document.createElement('tr');
    tr.appendChild(createCell(store.category));
    tr.appendChild(createCell(store.prefecture));
    tr.appendChild(createCell(store.store_name));
    tr.appendChild(createCell(store.address));
    tr.appendChild(createCell(store.phone));
    tr.appendChild(createCell(store.source));
    frag.appendChild(tr);
  }
  tbodyEl.appendChild(frag);
  tableEl.hidden = false;
}

function debounce(fn, wait = 100) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

async function main() {
  const loadStart = performance.now();
  const response = await fetch('./data/search-index.json');
  if (!response.ok) {
    throw new Error(`search-index.json: HTTP ${response.status}`);
  }
  const payload = await response.json();
  const records = Array.isArray(payload.records) ? payload.records : [];

  const index = new window.FlexSearch.Index({
    tokenize: 'full',
    resolution: 9,
    cache: true,
    encode: 'icase',
  });
  const byId = new Map();

  for (const record of records) {
    byId.set(record.id, record);
    index.add(record.id, record.search_text || '');
  }

  const loadElapsed = performance.now() - loadStart;
  metaEl.textContent = `初回ロード: ${records.length}件 / ${loadElapsed.toFixed(0)}ms`;

  const onInput = debounce(() => {
    const q = queryEl.value.trim();
    if (!q) {
      renderRows([]);
      metaEl.textContent = `初回ロード済み ${records.length}件。2文字以上で検索してください。`;
      return;
    }

    const searchStart = performance.now();
    const ids = index.search(q, MAX_ROWS);
    const rows = ids.map((id) => byId.get(id)).filter(Boolean);
    const searchElapsed = performance.now() - searchStart;

    renderRows(rows);
    metaEl.textContent = `「${q}」: ${rows.length}件表示（最大${MAX_ROWS}件） / 検索 ${searchElapsed.toFixed(1)}ms`;
  }, 80);

  queryEl.addEventListener('input', onInput);
  queryEl.focus();
}

main().catch((error) => {
  metaEl.textContent = `初期化エラー: ${error.message}`;
});
