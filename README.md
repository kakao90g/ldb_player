# LDB Player (Live Desktop Background Player)

LDB Player is a Windows-specific media player that transforms your desktop into a live video player. It supports playlists, global hotkeys, drag-and-drop, multi-monitor displays, and seamless desktop integration.

![LDB Player Main UI](screenshots/main-ui.png)
![LDB Player Multi Instance](screenshots/multi-instance.png)

## Now available in Microsoft Store
- Download link: https://apps.microsoft.com/store/detail/9PP860QK40K2?cid=DevShareMCLPCS
- Currently supported regions as of 07/07/2026.
    - English (United States)
- Please check the **FAQ** section below.

## Features
- Play videos as live desktop backgrounds.
- Multi-display support — choose which monitor to use in Settings.
- Playlist management: Add, remove, shuffle, save, and load playlists.
- Global hotkeys for playback control, volume adjustment, seeking, and navigation.
- Repeat modes (single video or entire playlist).
- Auto play feature on system restart adjustable in Settings.
- Dark-themed, modern user interface.
- Built-in update checker with updater download support.

## Requirements
- Windows 11.
- VLC media player (optional but recommended, download from https://www.videolan.org/vlc/).
- Python 3.10+ (required only for running from source).

## Downloads (For End Users)
- For a ready-to-use version without needing Python or dependencies, download the latest standalone executable (.exe) from the [Releases](https://github.com/kakao90g/ldb_player/releases) page. Simply run the .exe to start the player — no installation required.

## Installation from Source (For Developers)
1. Clone or download this repository.
2. Install dependencies: pip install pyqt6 pywin32 python-vlc requests
3. Run the app: python ldb_player.py

## Building a Standalone Executable (For Developers)
To create a single .exe file for distribution (no Python required for users):
1. Install PyInstaller and Pillow if not already installed: pip install pyinstaller pillow.
2. From the project root, run: pyinstaller --onefile --windowed --icon=icons/tray_icon.png --name "LDB Player" --add-data "icons;icons" ldb_player.py
- This bundles the app into dist/LDB Player.exe.
- If VLC integration fails, locate your VLC installation (e.g., C:\Program Files\VideoLAN\VLC) and add flags: --add-binary "C:/Program Files/VideoLAN/VLC/libvlc.dll;." --add-data "C:/Program Files/VideoLAN/VLC/plugins;plugins"
- For PyQt6 issues, add: --add-data "path/to/site-packages/PyQt6/Qt6/plugins;PyQt6/Qt6/plugins"
(Replace with your actual Python site-packages path.)
3. Test the .exe on a clean Windows machine.

## Building the Updater Executable (For Developers)
The updater is a separate script (updater.py) that handles downloading and replacing the main executable during updates. To build it as a standalone .exe:
1. Ensure PyInstaller is installed (as above).
2. From the project root, run: pyinstaller --onefile --windowed --name "updater" updater.py
- This bundles the updater into dist/updater.exe.
- Place updater.exe in the same directory as LDB Player.exe for the update checker to use it automatically.

## Usage
- Add videos via drag-and-drop or the playlist dialog.
- Control playback with hotkeys: Space (play/pause), Arrow keys (seek/volume), etc. (View the full list in Settings > Hotkeys).
- Configuration is saved in %APPDATA%\LDBPlayer.
- Check for updates via Settings > Check for Updates. If an update is available, the app can download the updater and patch the new version automatically.

## Credits and Acknowledgments
- Powered by VLC media player (libvlc) from VideoLAN: https://www.videolan.org/vlc/
- Built with PyQt6 from Riverbank Computing: https://www.riverbankcomputing.com/software/pyqt/
- Utilizes Windows APIs via pywin32 for system integration.
- Other dependencies: Python standard libraries (sys, os, json, etc.), vlc.py bindings.

## FAQ

**1. How do I add files to play?**
- Open the playlist by pressing **Q** on the keyboard, or click the playlist icon on the main player, then select **Add files**.
- Drag and drop a video file directly onto the player — it will be automatically added to the playlist.

**2. What file types are currently supported?**
- `.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.mpeg`, `.mpg`, `.m4v`

**3. Why can't I see my desktop icons?**
- The video window is placed above your desktop icons (and below other open applications). This is normal behavior.

**4. When playing vertical "Shorts" videos, I see my desktop wallpaper on the left and right sides. Is this normal?**
- Yes. The current version does not change your wallpaper settings. For a cleaner look, you can temporarily set your desktop background to a solid color.

**5. The Windows taskbar blocks the bottom of the video. How do I fix this?**
- Right-click the taskbar → **Taskbar settings** → Enable **Automatically hide the taskbar**.

**6. How do I create or run a new instance?**
- Go to **Settings** → **Create a new LDB Player instance...** → **Confirm the creation**.

**7. What does a new instance do?**
- It allows you to run LDB Player on multiple displays.
- Each new instance has its own save configuration file for independent customization.

**8. How do I check which instances are currently open or running?**
- Go to **Settings** → **Instance Manager**.  
  A list of all created instances will be shown. Deleting an instance here will also clean up its save configuration files.

**9. How do I support the project or developer?**
- Share LDB Player with your friends.
- ⭐ Star the repository on GitHub: https://github.com/kakao90g/ldb_player
- Send a tip through the in-app sponsor links or via the links below.

**Currently Known Issues**
- Please report any issues you experience with the current version on GitHub Issues or in the Discord server.

**Support the project:**
- GitHub Sponsors: https://github.com/sponsors/kakao90g
- PayPal: https://paypal.me/kakao90g

**Join the community:**
- Discord: https://discord.gg/TAfUNGHYR3

## Version Changes
- v1.1.6
    - Added a small tweak for multi-instances
    - Latest stable release
- v1.1.5
    - Updated instance handler and instance manager
    - Various improvements and bug fixes
- v1.1.4
    - Added new instance handler and instance manager
    - Added support for multi-instances (up to 32 instances)
    - Updated display change playback behavior
- v1.1.3
    - Optimized code and memory efficiency
    - Stable release
- v1.1.2
    - Fixed critical playback issues
    - Minimal UI adjustments
- v1.1.0
    - A new updated UI
    - Various improvements and bug fixes
- v1.0.9
    - Added safety checks to prevent random crashes
- v1.0.8
    - Optimized code for improved performance and stability
    - Updated playback indexing
    - Fixed autoplay startup issue
- v1.0.6
    - Updated system tray menu
    - Fixed critical playback issue
- v1.0.5
    - Added new welcome screen for new users
    - Minor bug fixes
- v1.0.2
    - Multi-display support
    - Improved auto start stability
    - Removed desktop wallpaper manipulation
    - Various improvements and bug fixes
- v1.0.0
    - Minimal bug fixes
    - Updater function
- v0.9.8
    - Initial release

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Developed by @kakao90g.