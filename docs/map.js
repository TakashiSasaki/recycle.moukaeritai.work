const DEFAULT_CATEGORY = '1';
const DEFAULT_PREF = '13';
const GEOLOCATION_OPTIONS = {
  enableHighAccuracy: true,
  timeout: 10000,
  maximumAge: 0,
};

const statusEl = document.getElementById('status');
const mapEl = document.getElementById('map');

function getDataTarget() {
  const params = new URLSearchParams(window.location.search);
  const category = params.get('category') || DEFAULT_CATEGORY;
  const pref = params.get('pref') || DEFAULT_PREF;
  return {
    category,
    pref,
    dataPath: `./data/${category}-${pref}.json`,
    latlngPath: `./latlng/${category}-${pref}.json`,
  };
}

function normalizeAddress(prefecture, address) {
  const value = `${prefecture ?? ''}${address ?? ''}`;
  return value.replace(/\s/g, '').replace(/　/g, '').trim();
}

function getCurrentPositionAsync() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('このブラウザでは位置情報を利用できません。'));
      return;
    }

    navigator.geolocation.getCurrentPosition(resolve, reject, GEOLOCATION_OPTIONS);
  });
}

function describePositionError(error) {
  if (!error || typeof error.code !== 'number') {
    return '現在地の取得に失敗しました。';
  }

  switch (error.code) {
    case error.PERMISSION_DENIED:
      return '位置情報の利用が拒否されました。位置情報を許可してください。';
    case error.POSITION_UNAVAILABLE:
      return '位置情報を取得できませんでした。通信環境をご確認ください。';
    case error.TIMEOUT:
      return '位置情報の取得がタイムアウトしました。再度お試しください。';
    default:
      return '現在地の取得に失敗しました。';
  }
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`${path} の読み込みに失敗しました (HTTP ${response.status})`);
  }
  return response.json();
}

function mergeStoresWithLatLng(stores, latlngPayload) {
  if (!Array.isArray(stores)) {
    throw new Error('店舗データの形式が不正です。');
  }

  const entries = latlngPayload?.entries;
  if (!entries || typeof entries !== 'object') {
    throw new Error('緯度経度データの形式が不正です。');
  }

  const merged = [];
  let skipped = 0;

  for (const store of stores) {
    const key = normalizeAddress(store?.prefecture, store?.address);
    const point = entries[key];
    if (!point || point.status !== 'ok' || point.lat == null || point.lng == null) {
      skipped += 1;
      continue;
    }

    merged.push({
      category: store.category ?? '-',
      prefecture: store.prefecture ?? '-',
      store_name: store.store_name ?? '-',
      address: store.address ?? '-',
      phone: store.phone ?? '-',
      lat: point.lat,
      lng: point.lng,
    });
  }

  return { merged, skipped };
}

function createInfoContent(store) {
  const tel = store.phone && store.phone !== '-' ? store.phone : '未登録';
  return `
    <div style="min-width:220px;line-height:1.5;">
      <strong>${store.store_name}</strong><br />
      <span>${store.category}</span><br />
      <span>${store.prefecture}${store.address}</span><br />
      <span>TEL: ${tel}</span>
    </div>
  `;
}

function renderMarkers(map, currentPos, stores) {
  const infoWindow = new google.maps.InfoWindow();
  const bounds = new google.maps.LatLngBounds();

  const currentMarker = new google.maps.Marker({
    position: currentPos,
    map,
    title: '現在地',
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 8,
      fillColor: '#1769ff',
      fillOpacity: 1,
      strokeColor: '#ffffff',
      strokeWeight: 2,
    },
  });
  bounds.extend(currentMarker.getPosition());

  for (const store of stores) {
    const marker = new google.maps.Marker({
      position: { lat: store.lat, lng: store.lng },
      map,
      title: store.store_name,
    });

    marker.addListener('click', () => {
      infoWindow.setContent(createInfoContent(store));
      infoWindow.open({ anchor: marker, map });
    });

    bounds.extend(marker.getPosition());
  }

  map.fitBounds(bounds);
  if (stores.length === 0) {
    map.setCenter(currentPos);
    map.setZoom(14);
  }
}

async function initMapImpl() {
  if (!window.google?.maps) {
    statusEl.textContent = 'Google Maps API の読み込みに失敗しました。';
    return;
  }

  const currentPosResult = await getCurrentPositionAsync().catch((error) => {
    statusEl.textContent = describePositionError(error);
    mapEl.hidden = true;
    throw error;
  });

  const currentPos = {
    lat: currentPosResult.coords.latitude,
    lng: currentPosResult.coords.longitude,
  };

  mapEl.hidden = false;
  const map = new google.maps.Map(mapEl, {
    center: currentPos,
    zoom: 14,
    mapTypeControl: false,
    streetViewControl: false,
    fullscreenControl: false,
  });

  const target = getDataTarget();
  statusEl.textContent = `データを読み込み中: ${target.category}-${target.pref}`;

  try {
    const [stores, latlng] = await Promise.all([loadJson(target.dataPath), loadJson(target.latlngPath)]);
    const { merged, skipped } = mergeStoresWithLatLng(stores, latlng);

    renderMarkers(map, currentPos, merged);
    statusEl.textContent = `現在地 + ${merged.length}件を地図に表示（座標未登録 ${skipped}件）`;
  } catch (error) {
    statusEl.textContent = `データ読み込みに失敗しました: ${error.message}`;
  }
}

window.initMap = function initMap() {
  initMapImpl().catch(() => {
    // 位置情報の失敗時は status に理由を表示済み。
  });
};
