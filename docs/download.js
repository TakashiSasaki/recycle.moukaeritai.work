const FILES = {
  data: [
    '1-13',
    '1-23',
    '1-43',
    '1-44',
    '1-45',
    '1-46',
    '1-47',
    '2-01',
    '2-10',
    '2-11',
    '2-12',
    '2-13',
    '2-14',
    '2-15',
    '2-16',
    '2-17',
    '2-18',
    '2-19',
    '2-20',
    '2-21',
    '2-22',
    '2-23',
  ],
  latlng: [
    '1-13',
    '1-43',
    '1-44',
    '1-45',
    '1-46',
    '1-47',
    '2-10',
    '2-11',
    '2-12',
    '2-13',
    '2-14',
    '2-15',
    '2-16',
    '2-17',
    '2-18',
    '2-19',
    '2-20',
    '2-21',
    '2-22',
    '2-23',
  ],
};

const sourceSelect = document.getElementById('source-select');
const fileSelect = document.getElementById('file-select');
const status = document.getElementById('status');
const table = document.getElementById('store-table');
const tbody = document.getElementById('store-tbody');
const headRow = document.getElementById('table-head-row');
const downloadJson = document.getElementById('download-json');
const downloadCsv = document.getElementById('download-csv');
const downloadNote = document.getElementById('download-note');

function clearTable() {
  headRow.replaceChildren();
  tbody.replaceChildren();
  table.hidden = true;
}

function createCell(value, tagName = 'td') {
  const el = document.createElement(tagName);
  el.textContent = value == null || value === '' ? '-' : String(value);
  return el;
}

function setDownloadLinks(source, fileName) {
  downloadJson.href = `./${source}/${fileName}.json`;
  downloadJson.download = `${source}-${fileName}.json`;

  const hasCsv = source === 'data';
  if (hasCsv) {
    downloadCsv.href = `./data/${fileName}.csv`;
    downloadCsv.download = `data-${fileName}.csv`;
    downloadCsv.classList.remove('is-disabled');
    downloadCsv.removeAttribute('aria-disabled');
    downloadNote.hidden = true;
  } else {
    downloadCsv.href = '#';
    downloadCsv.removeAttribute('download');
    downloadCsv.classList.add('is-disabled');
    downloadCsv.setAttribute('aria-disabled', 'true');
    downloadNote.hidden = false;
  }
}

function fillFileSelect(source) {
  const files = FILES[source] ?? [];
  fileSelect.replaceChildren();

  for (const fileName of files) {
    const option = document.createElement('option');
    option.value = fileName;
    option.textContent = `${fileName}.json`;
    fileSelect.appendChild(option);
  }
}

function renderRows(headers, rows) {
  for (const header of headers) {
    headRow.appendChild(createCell(header, 'th'));
  }

  const fragment = document.createDocumentFragment();
  for (const row of rows) {
    const tr = document.createElement('tr');
    for (const key of headers) {
      tr.appendChild(createCell(row[key]));
    }
    fragment.appendChild(tr);
  }

  tbody.appendChild(fragment);
  table.hidden = false;
}

function normalizeDataRows(payload) {
  if (!Array.isArray(payload)) {
    throw new Error('data JSON は配列である必要があります。');
  }

  return {
    rows: payload,
    headers: ['category', 'prefecture', 'store_name', 'address', 'phone'],
  };
}

function normalizeLatLngRows(payload) {
  if (!payload || typeof payload !== 'object') {
    throw new Error('latlng JSON はオブジェクトである必要があります。');
  }

  const entries = payload.entries && typeof payload.entries === 'object' ? payload.entries : {};
  const rows = Object.entries(entries).map(([entryKey, value]) => ({
    entry_key: entryKey,
    ...(value && typeof value === 'object' ? value : {}),
  }));

  const headers = [
    'entry_key',
    'status',
    'raw_prefecture',
    'raw_address',
    'normalized_address',
    'lat',
    'lng',
    'formatted_address',
    'updated_at',
    'place_id',
  ];

  return {
    rows,
    headers,
    meta: payload,
  };
}

async function loadSelectedFile() {
  const source = sourceSelect.value;
  const fileName = fileSelect.value;
  clearTable();

  try {
    setDownloadLinks(source, fileName);
    status.textContent = `読み込み中: ./${source}/${fileName}.json`;

    const response = await fetch(`./${source}/${fileName}.json`, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();

    if (source === 'data') {
      const { rows, headers } = normalizeDataRows(payload);
      if (rows.length === 0) {
        status.textContent = `表示できるデータがありません: ${source}/${fileName}`;
        return;
      }

      renderRows(headers, rows);
      status.textContent = `${source}/${fileName}.json を表示中（${rows.length}件）`;
      return;
    }

    const { rows, headers, meta } = normalizeLatLngRows(payload);
    if (rows.length === 0) {
      status.textContent = `表示できるデータがありません: ${source}/${fileName}`;
      return;
    }

    renderRows(headers, rows);
    status.textContent = `${source}/${fileName}.json を表示中（${rows.length}件, version=${meta.version ?? '-'}）`;
  } catch (error) {
    clearTable();
    status.textContent = `データの読み込みに失敗しました: ${error.message}`;
  }
}

sourceSelect.addEventListener('change', () => {
  fillFileSelect(sourceSelect.value);
  loadSelectedFile();
});

fileSelect.addEventListener('change', loadSelectedFile);

fillFileSelect(sourceSelect.value);
loadSelectedFile();
