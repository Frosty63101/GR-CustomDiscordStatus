# DiscCustomGRRP

This repository contains the source code and resources for the DiscCustomGRRP project.

## Getting Started

1. Clone the repository:
    ```
    git clone https://github.com/Frosty63101/DiscCustomGRRP.git
    cd DiscCustomGRRP
    ```
2. Install any required dependencies listed in `requirements.txt`.
    ```
    pip install -r requirements.txt
    ```

## Usage

Install dependencies and run the main script to start the application:
    ```
    python GR-CustomDiscordStatus.py
    ```

If you want to create a standalone executable, you can use PyInstaller. Make sure you have it installed:
    ```
    pip install pyinstaller
    ```

exe compiled with PyInstaller:
    ```
    pyinstaller --noconsole --onefile GR-CustomDiscordStatus.py
    ```

Do not change "discordAppId" from 1356666997760462859 unless you know how to setup a discord app for RP. 
Your goodreads user ID is the numbers before the username of the url for your profile page on Goodreads.

Note:
- This will only display the top line of currently reading at the following URL:
    ```
    https://www.goodreads.com/review/list/{userId}?shelf=currently-reading
    ```

## Features

- Discord Rich Presence integration
- Goodreads HTML parsing
- Customizable configuration
