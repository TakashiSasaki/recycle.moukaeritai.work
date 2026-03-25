# jbrc-scraper

JBRC 回収協力店検索システムを巡回し、回収拠点一覧を CSV に保存する Python パッケージです。

## セットアップ (uv)

```bash
uv sync
```

## 実行方法

```bash
# コンソールスクリプト
uv run jbrc-scraper --output data/jbrc_locations.csv

# モジュール実行
uv run python -m jbrc_scraper --output data/jbrc_locations.csv

# 接続確認のみ
uv run jbrc-scraper --dry-run

# 1カテゴリ・1都道府県のみ実行（例: カテゴリ1 / 東京都）
uv run jbrc-scraper --category 1 --prefecture 13 --output data/1-13.csv

# 出力ディレクトリへカテゴリ×都道府県単位で保存（CSV + JSON）
uv run jbrc-scraper \
  --category 1 \
  --prefecture 13 \
  --output-dir docs/data \
  --output-format csv \
  --output-format json
```

## GitHub Actions 定期実行

`.github/workflows/scheduled-scrape.yml` で、**1ジョブ=1カテゴリ+1都道府県**として実行する構成です。
カテゴリ2種 × 都道府県47件 = 合計94組を、1日14ジョブ × 7日で1週間に1巡できるようにしています。
各ジョブは `docs/data/<category>-<prefcode>.csv` と
`docs/data/<category>-<prefcode>.json` を出力します。

`workflow_dispatch` では `category` と `prefecture` を指定して単発実行も可能です。
