"""JBRC collection point scraper.

This script automates retrieval of battery collection points from the public
JBRC search system.

What it does:
- opens the JBRC search page with Selenium
- enumerates both categories (general electrical-product stores / municipal
  facilities, and bicycle stores)
- enumerates prefectures from the live select element instead of hard-coding
  47 codes
- follows pagination carefully
- writes normalized rows to CSV

Dependencies:
- selenium>=4.0
- beautifulsoup4>=4.0
- webdriver-manager>=4.0  (optional; only needed when chromedriver is not
  already available in PATH)

Example:
    python jbrc_scraper.py --output jbrc_locations.csv
    python jbrc_scraper.py --dry-run  # 接続確認・事前検証用（実クロールなし）

Notes:
- Run only during the service availability window published by JBRC.
- Be conservative with sleep values.  Defaults are intentionally slow.
- The result-table parser is position-based when possible.  If JBRC changes the
  result-page DOM, selectors may need adjustment.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

try:
    from webdriver_manager.chrome import ChromeDriverManager  # type: ignore

    _USE_MANAGER = True
except ImportError:
    _USE_MANAGER = False

BASE_URL = "https://www.jbrc-sys.com/brsp/a2A/itiran.G01"
DEFAULT_WAIT_SECONDS = 15


@dataclass(frozen=True)
class CollectionPoint:
    category: str
    prefecture: str
    store_name: str
    address: str
    phone: str


@dataclass(frozen=True)
class PrefectureOption:
    code: str
    name: str


@dataclass(frozen=True)
class CrawlSettings:
    pagination_sleep_seconds: float = 2.0
    prefecture_sleep_seconds: float = 5.0
    random_jitter_seconds: float = 1.5
    wait_seconds: int = DEFAULT_WAIT_SECONDS


def polite_sleep(base_seconds: float, jitter_seconds: float) -> None:
    """Sleep for a base interval plus random jitter."""
    time.sleep(base_seconds + random.uniform(0.0, jitter_seconds))


def get_driver(*, headless: bool = True) -> webdriver.Chrome:
    """Create a Selenium 4 compatible Chrome driver."""
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1400,1600")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    if _USE_MANAGER:
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    return webdriver.Chrome(options=options)


def get_prefecture_options(
    driver: webdriver.Chrome, wait: WebDriverWait
) -> List[PrefectureOption]:
    """Read prefecture codes from the live select element."""
    driver.get(BASE_URL)
    select_el = wait.until(EC.presence_of_element_located((By.ID, "CD_TODOFUKEN")))
    select = Select(select_el)
    options: List[PrefectureOption] = []
    for option in select.options:
        code = (option.get_attribute("value") or "").strip()
        name = option.text.strip()
        if code and name:
            options.append(PrefectureOption(code=code, name=name))
    if not options:
        raise RuntimeError("都道府県一覧を取得できませんでした。")
    return options


def open_search_form(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    driver.get(BASE_URL)
    wait.until(EC.presence_of_element_located((By.NAME, "TORIATUKAI_SEIHIN")))
    wait.until(EC.presence_of_element_located((By.ID, "CD_TODOFUKEN")))
    wait.until(EC.presence_of_element_located((By.ID, "BTN_NEXT")))


def submit_search(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    *,
    category_value: str,
    prefecture_code: str,
) -> None:
    """Fill the search form and submit it."""
    open_search_form(driver, wait)

    radio_buttons = driver.find_elements(By.NAME, "TORIATUKAI_SEIHIN")
    matched = False
    for rb in radio_buttons:
        if rb.get_attribute("value") == category_value:
            driver.execute_script("arguments[0].click();", rb)
            matched = True
            break
    if not matched:
        raise NoSuchElementException(
            f"カテゴリ value={category_value!r} のラジオボタンが見つかりません。"
        )

    Select(driver.find_element(By.ID, "CD_TODOFUKEN")).select_by_value(prefecture_code)

    next_button = driver.find_element(By.ID, "BTN_NEXT")
    driver.execute_script("arguments[0].click();", next_button)

    # Wait until either a result table appears or a page with explicit no-result
    # text appears.  Without the live DOM we keep this intentionally broad.
    wait.until(
        lambda d: bool(d.find_elements(By.CSS_SELECTOR, "table tr"))
        or "0件" in d.page_source
        or "該当" in d.page_source
    )


def get_result_rows(driver: webdriver.Chrome) -> List[WebElement]:
    """Return candidate result rows.

    The form page itself also contains table rows, so callers should use this only
    after a search has been submitted.
    """
    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
    return [row for row in rows if row.is_displayed()]


def find_pagination_next_link(driver: webdriver.Chrome) -> WebElement | None:
    """Locate the pagination '次へ' link on a result page.

    We intentionally exclude the search-form submit button id `BTN_NEXT`.  On the
    result page we prefer displayed anchors whose text is exactly `次へ`.
    """
    candidates = driver.find_elements(By.XPATH, "//a[normalize-space()='次へ']")
    for link in candidates:
        if not link.is_displayed():
            continue
        if (link.get_attribute("id") or "").strip() == "BTN_NEXT":
            continue
        return link
    return None


def advance_to_next_page(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    settings: CrawlSettings,
) -> bool:
    """Advance pagination safely.

    Returns True if a next page was loaded, otherwise False.
    """
    next_link = find_pagination_next_link(driver)
    if next_link is None:
        return False

    current_rows = get_result_rows(driver)
    sentinel = current_rows[0] if current_rows else next_link
    old_url = driver.current_url
    old_page = driver.page_source

    driver.execute_script("arguments[0].click();", next_link)

    transitioned = False
    try:
        wait.until(EC.staleness_of(sentinel))
        transitioned = True
    except TimeoutException:
        # Fallback: some systems re-render in place.  In that case wait for URL or
        # page source change.
        wait.until(lambda d: d.current_url != old_url or d.page_source != old_page)
        transitioned = True

    if transitioned:
        polite_sleep(settings.pagination_sleep_seconds, settings.random_jitter_seconds)
    return transitioned


def parse_result_rows(
    page_source: str,
    *,
    category: str,
    prefecture: str,
) -> List[CollectionPoint]:
    """Parse a result page into collection-point rows.

    This parser is intentionally deterministic.  It uses column positions instead
    of the previous store-name/address/phone heuristic.

    Supported patterns:
    - 4 columns: [index, store_name, address, phone]
    - 3 columns: [store_name, address, phone]
    - 5+ columns: if the first column is an index, second is store_name, last is
      phone, middle columns are joined as address.

    Rows that look like headers, notices, or empty separators are skipped.
    """
    soup = BeautifulSoup(page_source, "html.parser")
    points: List[CollectionPoint] = []

    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cols = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if not cols:
                continue
            normalized = [c.strip() for c in cols if c and c.strip()]
            if len(normalized) < 3:
                continue
            if any(token in normalized[0] for token in ("協力店", "店舗名", "住所", "電話")):
                continue

            if normalized[0].isdigit() and len(normalized) >= 4:
                store_name = normalized[1]
                address = " ".join(normalized[2:-1]).strip()
                phone = normalized[-1]
            elif len(normalized) == 3:
                store_name, address, phone = normalized
            else:
                # Still positional, but without a leading numeric index.
                store_name = normalized[0]
                address = " ".join(normalized[1:-1]).strip()
                phone = normalized[-1]

            if not store_name or store_name.isdigit():
                continue
            points.append(
                CollectionPoint(
                    category=category,
                    prefecture=prefecture,
                    store_name=store_name,
                    address=address,
                    phone=phone,
                )
            )
    return points


def deduplicate(points: Iterable[CollectionPoint]) -> List[CollectionPoint]:
    seen: set[CollectionPoint] = set()
    unique: List[CollectionPoint] = []
    for point in points:
        if point in seen:
            continue
        seen.add(point)
        unique.append(point)
    return unique


def scrape_category(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    *,
    category_value: str,
    category_label: str,
    prefectures: Sequence[PrefectureOption],
    settings: CrawlSettings,
) -> Tuple[List[CollectionPoint], List[str]]:
    points: List[CollectionPoint] = []
    errors: List[str] = []

    for prefecture in prefectures:
        try:
            submit_search(
                driver,
                wait,
                category_value=category_value,
                prefecture_code=prefecture.code,
            )
        except TimeoutException:
            errors.append(f"{category_label} / {prefecture.name}: 検索フォーム送信後の待機がタイムアウト")
            continue
        except NoSuchElementException as exc:
            errors.append(f"{category_label} / {prefecture.name}: 必須要素が見つからない: {exc}")
            continue
        except WebDriverException as exc:
            errors.append(f"{category_label} / {prefecture.name}: WebDriver例外: {exc}")
            continue

        visited_pages: set[str] = set()
        while True:
            page_marker = driver.page_source
            if page_marker in visited_pages:
                errors.append(
                    f"{category_label} / {prefecture.name}: 同一ページを再訪したためページングを中断"
                )
                break
            visited_pages.add(page_marker)

            parsed = parse_result_rows(
                driver.page_source,
                category=category_label,
                prefecture=prefecture.name,
            )
            points.extend(parsed)

            try:
                moved = advance_to_next_page(driver, wait, settings)
            except TimeoutException:
                errors.append(f"{category_label} / {prefecture.name}: 次ページ遷移待機がタイムアウト")
                break
            except (NoSuchElementException, StaleElementReferenceException, WebDriverException) as exc:
                errors.append(f"{category_label} / {prefecture.name}: ページング失敗: {exc}")
                break

            if not moved:
                break

        polite_sleep(settings.prefecture_sleep_seconds, settings.random_jitter_seconds)

    return deduplicate(points), errors


def write_csv(output_path: Path, points: Sequence[CollectionPoint]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "prefecture", "store_name", "address", "phone"])
        for point in points:
            writer.writerow(
                [
                    point.category,
                    point.prefecture,
                    point.store_name,
                    point.address,
                    point.phone,
                ]
            )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape JBRC collection points to CSV.")
    parser.add_argument(
        "--output",
        default="jbrc_locations.csv",
        help="output CSV path (default: %(default)s)",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="run with a visible browser instead of headless mode",
    )
    parser.add_argument(
        "--pagination-sleep",
        type=float,
        default=2.0,
        help="base sleep in seconds between result pages",
    )
    parser.add_argument(
        "--prefecture-sleep",
        type=float,
        default=5.0,
        help="base sleep in seconds between prefectures",
    )
    parser.add_argument(
        "--jitter",
        type=float,
        default=1.5,
        help="random additional sleep in seconds",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="最初の検索ページ取得と都道府県一覧確認のみ。実クロールしない",
    )
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=DEFAULT_WAIT_SECONDS,
        help="explicit wait timeout in seconds",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    settings = CrawlSettings(
        pagination_sleep_seconds=args.pagination_sleep,
        prefecture_sleep_seconds=args.prefecture_sleep,
        random_jitter_seconds=args.jitter,
        wait_seconds=args.wait_seconds,
    )

    categories = [
        ("1", "電気製品販売店・自治体施設等"),
        ("2", "自転車販売店"),
    ]

    driver = get_driver(headless=not args.headful)
    wait = WebDriverWait(driver, settings.wait_seconds)

    all_points: List[CollectionPoint] = []
    all_errors: List[str] = []

    try:
        prefectures = get_prefecture_options(driver, wait)
        if args.dry_run:
            sample_size = min(5, len(prefectures))
            print(
                f"[DRY-RUN] 都道府県一覧を取得しました: {len(prefectures)} 件",
                file=sys.stderr,
            )
            for index, pref in enumerate(prefectures[:sample_size], start=1):
                print(
                    f"[DRY-RUN] sample[{index}] code={pref.code} name={pref.name}",
                    file=sys.stderr,
                )
            if len(prefectures) > sample_size:
                print(
                    f"[DRY-RUN] ... and {len(prefectures) - sample_size} more",
                    file=sys.stderr,
                )
            return 0
        for category_value, category_label in categories:
            print(f"[INFO] category={category_label}", file=sys.stderr)
            points, errors = scrape_category(
                driver,
                wait,
                category_value=category_value,
                category_label=category_label,
                prefectures=prefectures,
                settings=settings,
            )
            all_points.extend(points)
            all_errors.extend(errors)
    finally:
        driver.quit()

    unique_points = deduplicate(all_points)
    write_csv(Path(args.output), unique_points)

    print(f"Saved {len(unique_points)} rows to {args.output}", file=sys.stderr)
    if all_errors:
        print("[WARN] failures:", file=sys.stderr)
        for error in all_errors:
            print(f"  - {error}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
