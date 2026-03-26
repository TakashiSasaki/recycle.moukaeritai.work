const DATA_PATH = './data/1-13.json';

const status = document.getElementById('status');
const table = document.getElementById('store-table');
const tbody = document.getElementById('store-tbody');

function createCell(value) {
  const td = document.createElement('td');
  td.textContent = value ?? '-';
  return td;
}

async function loadStores() {
  try {
    const response = await fetch(DATA_PATH);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const stores = await response.json();
    if (!Array.isArray(stores) || stores.length === 0) {
      status.textContent = '表示できる店舗データがありません。';
      return;
    }

    const fragment = document.createDocumentFragment();
    for (const store of stores) {
      const tr = document.createElement('tr');
      tr.appendChild(createCell(store.category));
      tr.appendChild(createCell(store.prefecture));
      tr.appendChild(createCell(store.store_name));
      tr.appendChild(createCell(store.address));
      tr.appendChild(createCell(store.phone));
      fragment.appendChild(tr);
    }

    tbody.appendChild(fragment);
    table.hidden = false;
    status.textContent = `全 ${stores.length} 件の店舗データを表示中`;
  } catch (error) {
    status.textContent = `店舗データの読み込みに失敗しました: ${error.message}`;
  }
}

loadStores();
