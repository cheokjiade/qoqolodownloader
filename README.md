# qoqolodownloader

A Python + Selenium script to download check-in/check-out photos and activity photos from the PCF Sparkle Tots Qoqolo school management system.

## User Guide

### Requirements

- **Google Chrome** (or Chromium) must be installed. The application automates Chrome to navigate the Qoqolo website — it will not work without it.

### Download

Download the latest release from the [Releases page](https://github.com/cheokjiade/qoqolodownloader/releases/latest).

Each release includes:
- `downloader-windows.exe` — CLI version (Windows)
- `qoqolodownloader-gui-windows.exe` — GUI version (Windows)
- `config.properties` — configuration file (needed for CLI version)
- Linux and macOS builds (untested — see [Platform Support](#platform-support))

### Running the GUI version

1. Download `qoqolodownloader-gui-windows.exe`
2. Double-click to run
3. Fill in your login email, password, and child name
4. Select which months/year to download and what content (check-in/out, activities, or both)
5. Click **Start Download**
6. Photos are saved to the output folder shown in the app

### Running the CLI version

1. Download both `downloader-windows.exe` and `config.properties` into the same folder
2. Open `config.properties` in a text editor and fill in:
   - `username` — your Qoqolo login email
   - `password` — your Qoqolo password
   - `childname` — your child's name in CAPS, as shown in the child selector
   - `signin_months_to_download` — comma-separated months (e.g. `1,2,3` for Jan–Mar)
   - `signin_year_to_download` — the year to download
   - `download_checkin` / `download_activities` — `yes` or `no`
3. Run `downloader-windows.exe`
4. Photos are saved to `{childname}/{year}/checkinout/` and `{childname}/{year}/activities/`

### Configuration tips

| Setting | Default | Description |
|---|---|---|
| `default_sleep_time` | `3` | Seconds to wait between page actions. Increase if downloads fail due to slow loading. |
| `activities_scroll_times` | `7` | How many times to scroll down the activities page. Increase to load older posts. |

### Platform Support

| Platform | Status |
|---|---|
| Windows | Supported |
| Linux | Built but untested |
| macOS | Built but untested |

**macOS users:** The binary is unsigned. macOS Gatekeeper will block it on first run. To allow it:
- Right-click the file > **Open** > **Open**, or
- Run in terminal: `xattr -d com.apple.quarantine ./downloader-macos`

### Known Limitations

- Only downloads images, not videos
- All images are assumed to be JPG
- If a child has a check-in but no check-out for a day, that day may be skipped (logged as an error)
- XPath selectors used to navigate the website may break if Qoqolo changes their page structure

## Building from Source

### Prerequisites

- Python 3.10–3.13
- [Poetry](https://python-poetry.org/docs/#installation)
- Google Chrome (for running, not building)

### Setup

```bash
git clone https://github.com/cheokjiade/qoqolodownloader.git
cd qoqolodownloader
poetry install
```

### Run directly (without building)

```bash
cd qoqolodownloader
poetry run python downloader.py
```

Or for the GUI:

```bash
cd qoqolodownloader
poetry run python gui.py
```

### Build executables

Build the CLI version:

```bash
poetry run build
```

Build the GUI version:

```bash
poetry run build-gui
```

Both commands produce a standalone executable in the `dist/` folder.

### Project structure

| File | Description |
|---|---|
| `qoqolodownloader/downloader.py` | Main download logic |
| `qoqolodownloader/gui.py` | GUI wrapper using CustomTkinter |
| `qoqolodownloader/config.properties` | Configuration file |
| `qoqolodownloader/pyinstaller.py` | Build helper for PyInstaller |
| `pyproject.toml` | Project metadata and dependencies |
