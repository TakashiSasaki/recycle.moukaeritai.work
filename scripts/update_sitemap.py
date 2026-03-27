from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / 'docs'
SITEMAP_PATH = DOCS_DIR / 'sitemap.xml'
CNAME_PATH = DOCS_DIR / 'CNAME'
SITEMAP_NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'


def normalize_base_url(raw: str) -> str:
    host = raw.strip().strip('/')
    if not host:
        raise ValueError('docs/CNAME is empty; cannot build sitemap base URL')
    if host.startswith('http://') or host.startswith('https://'):
        return host.rstrip('/')
    return f'https://{host}'


def iter_sitemap_targets() -> list[Path]:
    targets: list[Path] = []
    for path in DOCS_DIR.rglob('*'):
        if not path.is_file():
            continue

        rel = path.relative_to(DOCS_DIR)
        name = rel.name

        if name in {'CNAME', 'sitemap.xml'}:
            continue

        if name.endswith('.html') or name.endswith('.json') or name.endswith('.csv') or name.endswith('.mets.xml'):
            targets.append(rel)

    return sorted(targets, key=lambda p: p.as_posix())


def render_sitemap(base_url: str, targets: list[Path]) -> bytes:
    ET.register_namespace('', SITEMAP_NS)
    urlset = ET.Element(f'{{{SITEMAP_NS}}}urlset')

    for rel in targets:
        url = ET.SubElement(urlset, f'{{{SITEMAP_NS}}}url')
        loc = ET.SubElement(url, f'{{{SITEMAP_NS}}}loc')
        loc.text = f'{base_url}/{rel.as_posix()}'

    raw_xml = ET.tostring(urlset, encoding='utf-8')
    return minidom.parseString(raw_xml).toprettyxml(indent='  ', encoding='utf-8')


def main() -> None:
    base_url = normalize_base_url(CNAME_PATH.read_text(encoding='utf-8'))
    targets = iter_sitemap_targets()
    content = render_sitemap(base_url, targets)
    SITEMAP_PATH.write_bytes(content)
    print(f'Wrote {SITEMAP_PATH} with {len(targets)} URLs')


if __name__ == '__main__':
    main()
