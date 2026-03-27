import Fuse from 'https://cdn.jsdelivr.net/npm/fuse.js@7.1.0/dist/fuse.mjs';

const queryEl = document.getElementById('query');
const metaEl = document.getElementById('meta');
const tableEl = document.getElementById('store-table');
const tbodyEl = document.getElementById('store-tbody');

const MAX_ROWS = 300;

function filePaths() {
  const paths = [];
  for (const category of [1, 2]) {
    for (let pref = 1; pref <= 47; pref += 1) {
      paths.push(`./data/${category}-${pref}.json`);
    }
  }
  return paths;
}

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

function debounce(fn, wait = 120) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

async function loadAllStores() {
  const started = performance.now();
  const results = await Promise.allSettled(
    filePaths().map(async (path) => {
      const response = await fetch(path);
      if (!response.ok) {
        throw new Error(`${path}: HTTP ${response.status}`);
      }
      const rows = await response.json();
      return rows.map((row) => ({ ...row, source: path.replace('./data/', '') }));
    })
  );

  const stores = [];
  let loadedFileCount = 0;
  for (const result of results) {
    if (result.status === 'fulfilled') {
      loadedFileCount += 1;
      stores.push(...result.value);
    }
  }

  const elapsed = performance.now() - started;
  return { stores, loadedFileCount, elapsed };
}

async function main() {
  const { stores, loadedFileCount, elapsed } = await loadAllStores();
  const fuse = new Fuse(stores, {
    includeScore: false,
    threshold: 0.32,
    ignoreLocation: true,
    minMatchCharLength: 2,
    keys: [
      { name: 'store_name', weight: 0.5 },
      { name: 'address', weight: 0.25 },
      { name: 'prefecture', weight: 0.15 },
      { name: 'phone', weight: 0.07 },
      { name: 'category', weight: 0.03 },
    ],
  });

  metaEl.textContent = `初回ロード: ${stores.length}件 / ${loadedFileCount}ファイル / ${elapsed.toFixed(0)}ms`;

  const onInput = debounce(() => {
    const q = queryEl.value.trim();
    if (!q) {
      renderRows([]);
      metaEl.textContent = `初回ロード済み ${stores.length}件。2文字以上で検索してください。`;
      return;
    }

    const started = performance.now();
    const matches = fuse.search(q, { limit: MAX_ROWS }).map((x) => x.item);
    const elapsedSearch = performance.now() - started;
    renderRows(matches);
    metaEl.textContent = `「${q}」: ${matches.length}件表示（最大${MAX_ROWS}件） / 検索 ${elapsedSearch.toFixed(1)}ms`;
  }, 120);

  queryEl.addEventListener('input', onInput);
  queryEl.focus();
}

main().catch((error) => {
  metaEl.textContent = `初期化エラー: ${error.message}`;
});
