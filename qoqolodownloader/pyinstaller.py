import PyInstaller.__main__
from pathlib import Path

HERE = Path(__file__).parent.absolute()
path_to_main = str(HERE / "downloader.py")
print(path_to_main)


def install():
    """Build CLI version (console, existing behavior)."""
    PyInstaller.__main__.run([
        path_to_main,
        '--onefile',
        '--console',
        '--collect-submodules', 'selenium',
    ])


def install_gui():
    """Build GUI version (windowed, no console window)."""
    path_to_gui = str(HERE / "gui.py")
    print(f"Building GUI: {path_to_gui}")
    PyInstaller.__main__.run([
        path_to_gui,
        '--onefile',
        '--windowed',
        '--name', 'qoqolodownloader-gui',
        '--hidden-import', 'customtkinter',
        '--hidden-import', 'qoqolodownloader.downloader',
        '--collect-data', 'customtkinter',
        '--collect-all', 'qoqolodownloader',
        '--collect-submodules', 'selenium',
    ])