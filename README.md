# qoqolodownloader
A python + selenium script to download photos from pcfsparkletots qoqolo school management system

### Quickstart

1. The binary release is for Windows only
2. Download the zip archive from https://github.com/cheokjiade/qoqolodownloader/releases/latest
2. Extract the files
3. Update config.properties to add in login email/password/child name in caps
4. Ensure you have the latest chrome browser installed
5. Run downloader.exe
6. The files will be output to "activities" and "checkinout" folder

#### The main files needed are

qoqolodownloader/downloader.py - The code

qoqolodownloader/config.properties - Enter details like username or password

qoqolodownloader/chromedriver.exe - Download this from https://googlechromelabs.github.io/chrome-for-testing/

You will also need Chrome

The python project is managed with poetry and the dependencies are listed in pyproject.toml

Or just download the latest release, extract it, update the config file and run. You will still need Chrome browser.

