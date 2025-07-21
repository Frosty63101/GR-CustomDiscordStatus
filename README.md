# DiscCustomGRRP

This repository contains the source code and resources for the GR-CustomDiscordStatus project, a cross-platform application that shows your currently reading book on Goodreads as your Discord Rich Presence.

## 🔧 Getting Started

1. Clone the repository:
    ```bash
    git clone https://github.com/Frosty63101/DiscCustomGRRP.git
    cd DiscCustomGRRP
    ```

2. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the main script to start the application:
```bash
python GR-CustomDiscordStatus.py
```

### Build Executables

#### Windows:
```bash
pip install pyinstaller
pyinstaller --noconsole --onefile GR-CustomDiscordStatus.py
```

#### macOS:
```bash
pip install py2app pyobjc
python setup.py py2app
```

## Features

- **Discord Rich Presence** that updates with your current Goodreads book.
- Parses Goodreads "Currently Reading" shelf HTML.
- GUI config for:
  - Discord App ID
  - Goodreads User ID
  - Refresh interval
  - Minimize to tray behavior
  - Auto-start on system login (Windows and macOS supported)
- macOS `launchd` and Windows `Startup` shortcut support
- Custom system tray icon

## Notes

- Your Goodreads User ID is the number found in your Goodreads profile URL.
  Example: For `https://www.goodreads.com/user/show/174592014-frosty`, the ID is `174592014`.
- Discord App ID defaults to `1356666997760462859`. Change it only if you're hosting your own Discord RP app.

## Goodreads Parsing Behavior

This app fetches and displays the first book listed in the “Currently Reading” shelf at:
```
https://www.goodreads.com/review/list/{your_user_id}?shelf=currently-reading
```

## Releases

- Prebuilt `.exe` and `.app.zip` are available under the [Releases](https://github.com/Frosty63101/DiscCustomGRRP/releases) tab.

Enjoy your reading presence!
