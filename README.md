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
```

## GitHub Actions 定期実行

`.github/workflows/scheduled-scrape.yml` に、毎週の定期実行ワークフローを用意しています。
`workflow_dispatch` も有効なので手動実行も可能です。

生成した `data/jbrc_locations.csv` は Actions Artifact として保存されます。
