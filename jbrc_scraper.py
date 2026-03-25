"""Backward-compatible entry point.

Use `python -m jbrc_scraper` or the `jbrc-scraper` console command.
"""

from jbrc_scraper.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
