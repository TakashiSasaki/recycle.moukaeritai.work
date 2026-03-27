# AGENTS.md

## Front-end update policy (docs/)

- `docs/index.html` はトップのハブページとして扱う。
- ダウンロード機能は `docs/download.html` に実装する。
- HTML と CSS / JavaScript は必ず分離する。
- 分離した CSS / JavaScript のファイル名ステムは対象 HTML と一致させる。
  - 例: `download.html` は `download.css` と `download.js` を参照する。
  - 例: `index.html` は `index.css` と `index.js` を参照する。
- 新規ページを追加する場合も同じルール（同名ステム）を適用する。
