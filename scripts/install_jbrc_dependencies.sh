#!/usr/bin/env bash
set -euo pipefail

# Installs runtime dependencies needed for jbrc_scraper.py dry-run/scraping:
# - Usable Chrome/Chromium browser binary (required by Selenium)
# - Python packages (selenium, beautifulsoup4, webdriver-manager)

log() {
  printf '[setup] %s\n' "$*"
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif have_cmd sudo; then
    sudo "$@"
  else
    log "sudo が見つからないため root 権限で実行してください: $*"
    return 1
  fi
}

resolve_browser_path() {
  command -v google-chrome-stable || command -v google-chrome || command -v chromium || command -v chromium-browser || true
}

browser_usable() {
  local browser_path="$1"
  if [ -z "$browser_path" ]; then
    return 1
  fi

  local version_out
  version_out="$($browser_path --version 2>&1 || true)"
  if [ -z "$version_out" ]; then
    return 1
  fi
  if printf '%s' "$version_out" | grep -q 'requires the chromium snap to be installed'; then
    return 1
  fi
  return 0
}

install_google_chrome_apt() {
  log "APT で Google Chrome stable を導入します。"
  as_root apt-get update
  as_root apt-get install -y ca-certificates curl gnupg
  as_root install -d -m 0755 /etc/apt/keyrings
  curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | as_root gpg --dearmor -o /etc/apt/keyrings/google-linux-signing.gpg
  printf 'deb [arch=amd64 signed-by=/etc/apt/keyrings/google-linux-signing.gpg] http://dl.google.com/linux/chrome/deb/ stable main\n' \
    | as_root tee /etc/apt/sources.list.d/google-chrome.list >/dev/null
  as_root apt-get update
  as_root apt-get install -y google-chrome-stable
}

install_browser_apt() {
  log "APT 環境を検出。まず Chromium を試行します。"
  as_root apt-get update
  as_root apt-get install -y chromium || as_root apt-get install -y chromium-browser || true

  local browser_path
  browser_path="$(resolve_browser_path)"
  if browser_usable "$browser_path"; then
    log "利用可能なブラウザを確認しました: $browser_path"
    return 0
  fi

  log "Chromium が利用不可（snap ラッパー等）のため Google Chrome にフォールバックします。"
  install_google_chrome_apt

  browser_path="$(resolve_browser_path)"
  if browser_usable "$browser_path"; then
    log "利用可能なブラウザを確認しました: $browser_path"
    return 0
  fi

  log "ブラウザ導入後も実行可能な Chrome/Chromium が確認できませんでした。"
  return 1
}

install_browser() {
  local browser_path
  browser_path="$(resolve_browser_path)"
  if browser_usable "$browser_path"; then
    log "ブラウザは既に導入済みです: $browser_path"
    return 0
  fi

  if have_cmd apt-get; then
    install_browser_apt
    return 0
  fi

  if have_cmd dnf; then
    log "DNF 環境を検出。Chromium を導入します。"
    as_root dnf install -y chromium
  elif have_cmd yum; then
    log "YUM 環境を検出。Chromium を導入します。"
    as_root yum install -y chromium
  elif have_cmd apk; then
    log "APK 環境を検出。Chromium を導入します。"
    as_root apk add --no-cache chromium
  else
    log "対応していないパッケージマネージャーです。Chrome/Chromium を手動で導入してください。"
    return 1
  fi

  browser_path="$(resolve_browser_path)"
  if browser_usable "$browser_path"; then
    log "利用可能なブラウザを確認しました: $browser_path"
    return 0
  fi

  log "ブラウザ導入後も実行可能な Chrome/Chromium が確認できませんでした。"
  return 1
}

install_python_deps() {
  local py_bin="${PYTHON_BIN:-python3}"
  if ! have_cmd "$py_bin"; then
    log "$py_bin が見つかりません。PYTHON_BIN を指定するか Python 3 を導入してください。"
    return 1
  fi

  log "Python 依存を導入します。"
  "$py_bin" -m pip install --upgrade pip
  "$py_bin" -m pip install selenium beautifulsoup4 webdriver-manager
}

print_versions() {
  local browser_path
  browser_path="$(resolve_browser_path)"
  if [ -n "$browser_path" ]; then
    log "browser: $browser_path"
    "$browser_path" --version || true
  fi

  local py_bin="${PYTHON_BIN:-python3}"
  if have_cmd "$py_bin"; then
    "$py_bin" - <<'PY'
import importlib
mods = ["selenium", "bs4", "webdriver_manager"]
for m in mods:
    mod = importlib.import_module(m)
    print(f"{m}: {getattr(mod, '__version__', 'unknown')}")
PY
  fi
}

main() {
  install_browser
  install_python_deps
  print_versions
  log "完了: 次は 'python3 jbrc_scraper.py --dry-run' で事前確認できます。"
}

main "$@"
