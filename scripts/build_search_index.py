from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'docs' / 'data'
OUT_PATH = DATA_DIR / 'search-index.json'


@dataclass
class SearchRecord:
    id: int
    category: str
    prefecture: str
    store_name: str
    address: str
    phone: str
    source: str
    search_text: str


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for category in (1, 2):
        for pref in range(1, 48):
            path = DATA_DIR / f'{category}-{pref}.json'
            if path.exists():
                files.append(path)
    return files


def normalize(value: str | None) -> str:
    if not value:
        return ''
    return str(value).strip()


def build_records(files: list[Path]) -> tuple[list[SearchRecord], list[str]]:
    records: list[SearchRecord] = []
    errors: list[str] = []
    record_id = 1

    for path in files:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            errors.append(f'{path.name}: invalid JSON ({e.msg} at line {e.lineno}, col {e.colno})')
            continue

        if not isinstance(data, list):
            errors.append(f'{path.name}: root JSON must be an array')
            continue

        non_object_rows = 0
        for row in data:
            if not isinstance(row, dict):
                non_object_rows += 1
                continue
            category = normalize(row.get('category'))
            prefecture = normalize(row.get('prefecture'))
            store_name = normalize(row.get('store_name'))
            address = normalize(row.get('address'))
            phone = normalize(row.get('phone'))
            search_text = ' '.join(filter(None, [category, prefecture, store_name, address, phone]))

            records.append(
                SearchRecord(
                    id=record_id,
                    category=category,
                    prefecture=prefecture,
                    store_name=store_name,
                    address=address,
                    phone=phone,
                    source=path.name,
                    search_text=search_text,
                )
            )
            record_id += 1

        if non_object_rows:
            errors.append(f'{path.name}: {non_object_rows} row(s) were not JSON objects')

    return records, errors


def calc_source_sha256(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode('utf-8'))
        digest.update(b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def main() -> None:
    source_files = iter_source_files()
    records, errors = build_records(source_files)
    if errors:
        print('Input validation failed while building search index:')
        for err in errors:
            print(f'  - {err}')
        raise SystemExit(1)

    payload = {
        'version': 1,
        'total': len(records),
        'source_files': [path.name for path in source_files],
        'source_sha256': calc_source_sha256(source_files),
        'records': [asdict(r) for r in records],
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {OUT_PATH} ({len(records)} records)')


if __name__ == '__main__':
    main()
