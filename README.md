# LDB Player (Live Desktop Background Player)

LDB Player is a Windows-specific media player that transforms your desktop background into a live video player. It supports playlists, global hotkeys, drag-and-drop functionality, and seamless desktop integration.

## Features
- Play videos as live desktop backgrounds.
- Playlist management: Add, remove, shuffle, save, and load playlists.
- Global hotkeys for playback control, volume adjustment, and navigation.
- Repeat modes (single video or entire playlist).
- Autostart settings and hotkey reference.
- Dark-themed user interface.

## Requirements
- Windows 11.
- VLC media player installed (download from https://www.videolan.org/vlc/).
- Python 3.10+ (required only for running from source).

## Downloads (For End Users)
- For a ready-to-use version without needing Python or dependencies, download the latest standalone executable (.exe) from the Releases page. Simply run the .exe to start the player—no installation required.

## Installation from Source (For Developers)
1. Clone or download this repository.
2. Install dependencies:pip install pyqt6 pywin32 python-vlc
3. Run the app:python ldb_player.py

## Building a Standalone Executable (For Developers)
To create a single .exe file for distribution (no Python required for users):
1. Install PyInstaller and Pillow if not already installed:pip install pyinstaller pillow.
2. From the project root, run:pyinstaller --onefile --windowed --icon=icons/tray_icon.png --name "LDB Player" --add-data "icons;icons" ldb_player.py
- This bundles the app into dist/LDB Player.exe.
- If VLC integration fails, locate your VLC installation (e.g., C:\Program Files\VideoLAN\VLC) and add flags:--add-binary "C:/Program Files/VideoLAN/VLC/libvlc.dll;." --add-data "C:/Program Files/VideoLAN/VLC/plugins;plugins"
- For PyQt6 issues, add:--add-data "path/to/site-packages/PyQt6/Qt6/plugins;PyQt6/Qt6/plugins"
(Replace with your actual Python site-packages path.)
3. Test the .exe on a clean Windows machine.

## Usage
- Add videos via drag-and-drop or the playlist dialog.
- Control playback with hotkeys: Space (play/pause), Arrow keys (seek/volume), etc. (View the full list in Settings > Hotkeys).
- Configuration is saved in %APPDATA%\LDBPlayer.

## Credits and Acknowledgments
- Powered by VLC media player (libvlc) from VideoLAN: https://www.videolan.org/vlc/
- Built with PyQt6 from Riverbank Computing: https://www.riverbankcomputing.com/software/pyqt/
- Utilizes Windows APIs via pywin32 for system integration.
- Other dependencies: Python standard libraries (sys, os, json, etc.), vlc.py bindings.

Support the project:
- PayPal: https://paypal.me/kakao90g

Join the community:
- Discord: https://discord.gg/EBqnchP9

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Developed by @kakao90g.