import PyInstaller.__main__
from pathlib import Path

HERE = Path(__file__).parent.absolute()
path_to_main = str(HERE / "downloader.py")
print(path_to_main)
def install():
    PyInstaller.__main__.run([
        path_to_main,
        '--onefile',
        '--console',
        # other pyinstaller options...
    ])