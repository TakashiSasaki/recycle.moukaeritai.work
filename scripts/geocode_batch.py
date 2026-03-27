#!/usr/bin/env python3
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path("docs/data")
LATLNG_DIR = Path("docs/latlng")
API_URL = "https://maps.googleapis.com/maps/api/geocode/json"
API_KEY_ENV = "GOOGLE_MAPS_API_KEY"

REQUEST_INTERVAL_SEC = 0.12
MAX_RETRIES = 3


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_address(prefecture: str, address: str) -> str:
    s = f"{prefecture or ''}{address or ''}"
    s = s.replace(" ", "").replace("　", "")
    return s.strip()


def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def geocode(api_key: str, address: str) -> dict:
    params = {"address": address, "key": api_key}
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"

    last_err = None
    for i in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            status = payload.get("status")

            if status == "OK":
                result = payload["results"][0]
                loc = result["geometry"]["location"]
                return {
                    "status": "ok",
                    "lat": loc["lat"],
                    "lng": loc["lng"],
                    "formatted_address": result.get("formatted_address"),
                    "place_id": result.get("place_id"),
                }

            if status in ("ZERO_RESULTS",):
                return {"status": "not_found"}

            if status in ("OVER_QUERY_LIMIT", "UNKNOWN_ERROR"):
                time.sleep((2**i) * 1.2)
                continue

            return {"status": "error", "error_code": status}

        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            time.sleep((2**i) * 1.2)

    return {"status": "error", "error_code": "EXCEPTION", "message": last_err}


def to_cache_path(data_path: Path) -> Path:
    rel = data_path.relative_to(DATA_DIR)
    return LATLNG_DIR / rel


def process_file(data_path: Path, api_key: str) -> tuple[int, int]:
    src = load_json(data_path, default=[])
    if not isinstance(src, list):
        raise ValueError(f"{data_path} is not an array JSON")

    cache_path = to_cache_path(data_path)
    cache_exists = cache_path.exists()
    cache = load_json(
        cache_path,
        default={
            "version": 1,
            "generated_at": now_iso(),
            "source_file": str(data_path).replace("\\", "/"),
            "entries": {},
        },
    )

    entries = cache.setdefault("entries", {})
    updated = 0
    skipped = 0

    for row in src:
        pref = row.get("prefecture", "")
        addr = row.get("address", "")
        key = normalize_address(pref, addr)
        if not key:
            skipped += 1
            continue

        rec = entries.get(key)
        if rec and rec.get("status") == "ok":
            skipped += 1
            continue

        query = f"{pref}{addr}"
        result = geocode(api_key, query)

        new_rec = {
            "normalized_address": key,
            "raw_prefecture": pref,
            "raw_address": addr,
            "status": result.get("status", "error"),
            "updated_at": now_iso(),
        }
        if result.get("status") == "ok":
            new_rec["lat"] = result["lat"]
            new_rec["lng"] = result["lng"]
            if result.get("formatted_address"):
                new_rec["formatted_address"] = result["formatted_address"]
            if result.get("place_id"):
                new_rec["place_id"] = result["place_id"]
        else:
            if "error_code" in result:
                new_rec["error_code"] = result["error_code"]
            if "message" in result:
                new_rec["message"] = result["message"]

        entries[key] = new_rec
        updated += 1
        time.sleep(REQUEST_INTERVAL_SEC)

    # Rewrite cache only if we actually changed entries, or if cache file does not
    # exist yet (initialize empty cache file for future runs).
    if updated > 0 or not cache_exists:
        cache["generated_at"] = now_iso()
        save_json(cache_path, cache)
    return updated, skipped


def iter_target_files() -> tuple[list[Path], list[Path]]:
    data_files = sorted(path for path in DATA_DIR.rglob("*.json") if path.is_file())
    missing = []
    existing = []
    for data_path in data_files:
        # Ignore cache files if LATLNG_DIR is placed under DATA_DIR in the future.
        if LATLNG_DIR in data_path.parents:
            continue
        cache_path = to_cache_path(data_path)
        if cache_path.exists():
            existing.append(data_path)
        else:
            missing.append(data_path)
    return missing, existing


def env_truthy(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main():
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        raise SystemExit(f"Missing environment variable: {API_KEY_ENV}")

    missing_files, existing_files = iter_target_files()
    process_existing = env_truthy("GEOCODE_PROCESS_EXISTING", default=False)
    data_files = missing_files + (existing_files if process_existing else [])
    if not data_files:
        print("No data files found in docs/data")
        return

    print(
        "target files: "
        f"missing={len(missing_files)}, existing={len(existing_files)}, "
        f"process_existing={process_existing}, total={len(data_files)}"
    )

    total_updated = 0
    total_skipped = 0

    for data_file in data_files:
        cache_file = to_cache_path(data_file)
        priority = "HIGH" if not cache_file.exists() else "normal"
        print(f"[{priority}] processing {data_file} -> {cache_file}")
        updated, skipped = process_file(data_file, api_key)
        total_updated += updated
        total_skipped += skipped
        print(f"  updated={updated}, skipped={skipped}")

    print(f"done. total_updated={total_updated}, total_skipped={total_skipped}")


if __name__ == "__main__":
    main()
