# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`qoqolodownloader` is a Python + Selenium script that logs into the PCF Sparkle Tots Qoqolo school management system and downloads check-in/check-out photos and activity photos for a child.

## Commands

**Install dependencies:**
```bash
poetry install
```

**Run the downloader** (must be run from the `qoqolodownloader/` subdirectory, since `config.properties` is opened with a relative path):
```bash
cd qoqolodownloader && python downloader.py
```

**Build Windows executable:**
```bash
poetry run build
```
This invokes `pyinstaller.py:install()` via the `[tool.poetry.scripts]` entry in `pyproject.toml`, producing a single-file `downloader.exe` via PyInstaller.

## Architecture

The project is a single-script automation tool with no tests and no modular structure:

- **`qoqolodownloader/downloader.py`** — The entire runtime logic. Runs as a top-level script (not a callable module). At import time it reads config, creates output directories, launches a Chrome WebDriver, logs in, and then processes check-in/out and activity photos sequentially.
- **`qoqolodownloader/config.properties`** — All configuration: login credentials, child name, months/year to download, URL patterns, and XPath selectors. Loaded by `jproperties`. The script reads `config.properties` using a relative path so it **must be executed from the `qoqolodownloader/` directory**.
- **`qoqolodownloader/pyinstaller.py`** — Build helper; calls PyInstaller programmatically to produce a standalone `.exe`.

### Data flow

1. Config loaded from `config.properties`
2. Chrome launched via `selenium.webdriver.Chrome()` (requires `chromedriver.exe` on PATH or in the same directory, matching the installed Chrome version)
3. Login to `page_login` URL; child selected if multiple children exist
4. **Check-in/out section**: Iterates configured months, navigates to `page_checkin + month + "-" + year`, parses the attendance table rows, clicks each row to open a popup, extracts sign-in and sign-out photo URLs, and downloads them
5. **Activities section**: Navigates to `page_activities`, scrolls down `activities_scroll_times` times to trigger infinite scroll, finds all activity posts with images, clicks each album, and downloads each photo through the carousel
6. All downloaded images have EXIF metadata injected (date/time and a user comment) via `piexif`
7. Files saved to `{childname_lowercased_underscored}/{year}/checkinout/` and `{childname_lowercased_underscored}/{year}/activities/`

### Key limitations (documented in config.properties)

- No videos downloaded (images only, assumed JPG)
- If a child has a check-in but no check-out for a day, that row processing raises an exception (caught and logged)
- XPath selectors are brittle and may break if the website changes
- `default_sleep_time` controls all waits; increase if the site loads slowly
- `activities_scroll_times` controls how far back activities are loaded; increase for older posts