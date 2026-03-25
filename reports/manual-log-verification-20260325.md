# ログ機能の試験実行結果（2026-03-25）

## 実行条件
- 対象カテゴリ: `--category 1`（電気製品販売店・自治体施設等）
- 対象都道府県: `東京都`、`愛媛県`
- ログ出力: `--log-file data/manual_category1_tokyo_ehime.log`
- CSV出力: `--output data/manual_category1_tokyo_ehime.csv`
- 実行コマンド:

```bash
uv run jbrc-scraper --category 1 --prefecture 東京都 --prefecture 愛媛県 --output data/manual_category1_tokyo_ehime.csv --log-file data/manual_category1_tokyo_ehime.log --prefecture-sleep 0 --pagination-sleep 0 --jitter 0
```

## 実行結果
- コマンド終了コード: `0`
- 標準エラー出力（要点）: `Saved 413 rows to data/manual_category1_tokyo_ehime.csv`
- 生成ログ:
  - `count=314 category=1 prefecture=東京都`
  - `count=99 category=1 prefecture=愛媛県`

## 判定
- 指定条件（カテゴリ1、東京都/愛媛県）で実行され、ログファイルへ都道府県別件数が追記されることを確認。
- CSV実データ件数（413件）とログ件数合計（314 + 99 = 413）が一致し、ログ集計は整合。
