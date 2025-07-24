import time
import requests
from bs4 import BeautifulSoup
from pypresence import Presence
import re
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import pystray
from PIL import Image, ImageDraw
import math
import os
import sys
import platform
import subprocess

# === Platform Checks ===
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

if IS_WINDOWS:
    from win32com.client import Dispatch

basePath = os.path.dirname(os.path.realpath(sys.argv[0]))

def get_config_path():
    if IS_WINDOWS:
        appdata = os.getenv("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
        return os.path.join(appdata, "GoodreadsRPC", "config.json")
    elif IS_MAC:
        return os.path.expanduser("~/Library/Application Support/GoodreadsRPC/config.json")
    elif IS_LINUX:
        return os.path.expanduser("~/.config/GoodreadsRPC/config.json")
    else:
        return os.path.join(basePath, "config.json")

configFile = get_config_path()

# Ensure directory exists
os.makedirs(os.path.dirname(configFile), exist_ok=True)


# === Global Variables ===
discordAppId = None
goodreadsUserId = None
refreshInterval = 60 
minimizeToTray = True
StartOnStartup = False

books = {}
# Variables for current book details
currentBook = {
    "isbn": None,
    "title": None,
    "author": None,
    "cover": None,
    "start": None
}
currentISBN = None

# === Events ===
loopShouldRunEvent = threading.Event()
stayRunningAfterGUIEvent = threading.Event()
trayQuitEvent = threading.Event()

# === Logging Function ===
def log(message):
    try:
        logFilePath = os.path.join(basePath, "log.txt")
        with open(logFilePath, "a") as logFile:
            logFile.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception as e:
        print(f"Failed to log message: {e}")

# === Load Configuration ===
def load_config():
    try:
        with open(configFile, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        defaultConfig = {
            "discordAppId": "1356666997760462859",
            "goodreadsUserId": "YOUR_GOODREADS_USER_ID",
            "keepRunning": True,
            "minimizeToTray": True,
            "startOnStartup": False,
            "refreshInterval": 60,
            "currentISBN": None
        }
        with open(configFile, "w") as f:
            json.dump(defaultConfig, f, indent=4)
        return defaultConfig

# === Load Config and Initialize Variables ===
config = load_config()
discordAppId = config.get("discordAppId")
goodreadsUserId = config.get("goodreadsUserId")
refreshInterval = config.get("refreshInterval", 60)
minimizeToTray = config.get("minimizeToTray", True)
StartOnStartup = config.get("startOnStartup", False)
currentISBN = config.get("currentISBN", None)

if config.get("keepRunning", True):
    stayRunningAfterGUIEvent.set()

# only do this if running on github actions
if os.getenv("GITHUB_ACTIONS") == "true" or "CI" in os.environ:
    try:
        with open("/tmp/grrpc_launched.txt", "w") as f:
            f.write("Launched successfully.")
    except Exception as e:
        with open("/tmp/grrpc_launch_error.txt", "w") as f:
            f.write(str(e))

# === Restart Program Function ===
def restart_program():
    try:
        log("Restarting program...")
    except:
        pass
    python = sys.executable
    os.execv(python, [python] + sys.argv)

# === Updater Function ===
def update_application():
    try:
        log("Checking for updates...")
        latest_release_url = "https://api.github.com/repos/Frosty63101/GR-CustomDiscordStatus/releases/latest"
        response = requests.get(latest_release_url, timeout=10)
        response.raise_for_status()
        release_data = response.json()

        # Determine correct download URL
        download_url = None
        for asset in release_data.get("assets", []):
            if IS_WINDOWS and asset["name"].endswith(".exe"):
                download_url = asset["browser_download_url"]
                break
            elif IS_MAC and asset["name"].endswith(".app.zip"):
                download_url = asset["browser_download_url"]
                break

        if not download_url:
            messagebox.showerror("Update Error", "No compatible release found.")
            return

        # Prepare download
        tmp_file = os.path.join(basePath, "GoodreadsRPC_Update.tmp")
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

        log(f"Downloading update from: {download_url}")
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(tmp_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        current_path = os.path.realpath(sys.argv[0])

        # ================================
        # Windows: use .bat to update self
        # ================================
        if IS_WINDOWS:
            backup_path = current_path + ".bak"
            if os.path.exists(backup_path):
                log("Deleting previous .bak backup.")
                os.remove(backup_path)

            launcher_script = os.path.join(basePath, "update_launcher.bat")
            log("Creating update launcher .bat...")
            with open(launcher_script, "w") as f:
                f.write(f"""@echo off
timeout /t 1 >nul
move /Y "{current_path}" "{backup_path}"
move /Y "{tmp_file}" "{current_path}"
start "" "{current_path}"
del "%~f0"
""")

            subprocess.Popen(["cmd", "/c", launcher_script])
            trayQuitEvent.set()
            os._exit(0)
            return

        # ================================
        # macOS: use .sh to update .app bundle
        # ================================
        elif IS_MAC:
            import shutil
            import zipfile

            app_bundle_path = os.path.abspath(os.path.join(current_path, "../../../"))
            backup_path = app_bundle_path + ".bak"
            extracted_path = os.path.join(basePath, "update_temp")

            if os.path.exists(backup_path):
                log("Removing previous .app.bak backup.")
                shutil.rmtree(backup_path, ignore_errors=True)
            if os.path.exists(extracted_path):
                shutil.rmtree(extracted_path, ignore_errors=True)

            os.makedirs(extracted_path, exist_ok=True)

            log("Extracting update zip...")
            with zipfile.ZipFile(tmp_file, 'r') as zip_ref:
                zip_ref.extractall(extracted_path)

            extracted_app_path = next(
                (os.path.join(extracted_path, d) for d in os.listdir(extracted_path) if d.endswith(".app")),
                None
            )

            if not extracted_app_path or not os.path.exists(extracted_app_path):
                raise Exception("Extracted .app bundle not found.")

            launcher_script = os.path.join(basePath, "mac_updater.sh")
            log("Creating macOS update shell script...")
            with open(launcher_script, "w") as f:
                f.write(f"""#!/bin/bash
sleep 1
mv "{app_bundle_path}" "{backup_path}"
mv "{extracted_app_path}" "{app_bundle_path}"
open "{app_bundle_path}"
rm -- "$0"
""")

            os.chmod(launcher_script, 0o755)
            subprocess.Popen(["/bin/bash", launcher_script])
            trayQuitEvent.set()
            os._exit(0)
            return

        else:
            log("Updater not implemented for this platform.")
            messagebox.showerror("Unsupported", "Your OS is not supported for self-updates.")
            return

    except Exception as e:
        log(f"Update failed: {e}")
        messagebox.showerror("Update Error", f"Update failed: {e}")


# === Startup Shortcut Creation ===
def set_startup_enabled():
    if IS_WINDOWS:
        startup_dir = os.path.join(os.getenv('APPDATA'), "Microsoft\\Windows\\Start Menu\\Programs\\Startup")
        script_path = os.path.realpath(sys.argv[0])
        shortcut_path = os.path.join(startup_dir, "GoodreadsRPC.lnk")

        if StartOnStartup:
            try:
                shell = Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(shortcut_path)
                shortcut.Targetpath = script_path
                shortcut.WorkingDirectory = os.path.dirname(script_path)
                shortcut.IconLocation = script_path
                shortcut.save()
                log("Startup shortcut created.")
            except Exception as e:
                log(f"Failed to create startup shortcut: {e}")
        else:
            try:
                if os.path.exists(shortcut_path):
                    os.remove(shortcut_path)
                    log("Startup shortcut removed.")
            except Exception as e:
                log(f"Failed to remove startup shortcut: {e}")
    elif IS_MAC:
        plist_name = "com.goodreads.rpc.plist"
        plist_path = os.path.expanduser(f"~/Library/LaunchAgents/{plist_name}")
        python_exec = sys.executable
        script_path = os.path.realpath(sys.argv[0])
        if getattr(sys, 'frozen', False):
            script_path = sys.executable

        if StartOnStartup:
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.goodreads.rpc</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_exec}</string>
        <string>{script_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""
            try:
                with open(plist_path, "w") as f:
                    f.write(plist_content)
                subprocess.run(["launchctl", "load", plist_path], check=True)
                log("macOS launchd plist created and loaded.")
            except Exception as e:
                log(f"Failed to write/load launchd plist: {e}")
        else:
            try:
                if os.path.exists(plist_path):
                    subprocess.run(["launchctl", "unload", plist_path], check=True)
                    os.remove(plist_path)
                    log("macOS launchd plist removed.")
            except Exception as e:
                log(f"Failed to unload/remove launchd plist: {e}")

    else:
        log("Startup not implemented for this platform.")

# === Create System Tray Icon ===
def create_image():
    size = (96, 64)
    image = Image.new("RGBA", size, color=(30, 30, 30, 0))
    d = ImageDraw.Draw(image)

    d.polygon([
        (10, 48),
        (86, 48),
        (80, 56), 
        (16, 56)
    ], fill="blue", outline="white")

    center = (48, 48)

    page_angles = [-70, -50, -30, -15, 0, 15, 30, 50, 70]
    for angle in page_angles:
        endX = center[0] + int(40 * math.sin(math.radians(angle)))
        endY = center[1] - int(30 * math.cos(math.radians(angle)))
        d.line([center, (endX, endY)], fill="white", width=3)

    return image

def on_tray_quit(icon, item):
    log("Tray icon exit triggered.")
    trayQuitEvent.set()
    icon.stop()

def show_tray():
    icon = pystray.Icon("GoodreadsRPC")
    icon.icon = create_image()
    icon.title = "Goodreads RPC"
    icon.menu = pystray.Menu(
        pystray.MenuItem("Quit", on_tray_quit),
        pystray.MenuItem("Restart", lambda icon, item: restart_program()),
        pystray.MenuItem("Open", lambda icon, item: showGUI()),
    )
    icon.run()

def showGUI():
    log("Showing GUI from tray icon.")
    root.deiconify()
    root.lift()
    root.focus_force()
    log("GUI should be visible now.")
    log("Setting loopShouldRunEvent to True.")
    loopShouldRunEvent.set()

# === Goodreads Getter ===
def get_currently_reading(userId):
    url = f"https://www.goodreads.com/review/list/{userId}?shelf=currently-reading"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            log(f"Failed to fetch Goodreads page: {response.status_code}")
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        bookTable = soup.find("table", {"id": "books"})
        log("Book table found." if bookTable else "No book table found.")
        if not bookTable:
            log("No book table found.")
            return None
        rows = bookTable.find_all("tr", {"id": lambda x: x and x.startswith("review_")})
        log(f"Found {len(rows)} book rows.")
        if not rows:
            log("No book rows found.")
            return None
        books = {}
        for row in rows:
            log("Processing a book row.")
            title = row.find("td", class_="field title").find("a").get_text(strip=True)
            author = row.find("td", class_="field author").find("a").get_text(strip=True)
            coverArt = row.find("td", class_="field cover").find("img")["src"]
            coverArt = re.sub(r'\._[A-Z0-9]+_(?=\.(jpg|jpeg|png))', '', coverArt, flags=re.IGNORECASE)
            startDateSpan = row.find("td", class_="field date_started").find("span", class_="date_started_value")
            startDate = startDateSpan.get_text(strip=True) if startDateSpan else None
            isbn = row.find("td", class_="field isbn").find("div", class_="value").get_text(strip=True) if row.find("td", class_="field isbn").find("div", class_="value").get_text(strip=True) else f"noisbn-{title}-{author}"
            books[isbn] = (isbn, title, author, coverArt, startDate)
        return books
    except Exception as e:
        log(f"Error in Goodreads getter: {e}")
        return None

# === Presence Loop ===
def presence_loop():
    global discordAppId, goodreadsUserId
    rpc = Presence(discordAppId)
    try:
        rpc.connect()
    except Exception as e:
        log(f"Failed to connect to Discord RPC: {e}")
        return

    while True:
        if not trayQuitEvent.is_set():
            if loopShouldRunEvent.is_set():
                global title, author, cover, start, currentISBN
                data = get_currently_reading(goodreadsUserId)
                if data:
                    if currentISBN in data:
                        currentBook["isbn"], currentBook["title"], currentBook["author"], currentBook["cover"], currentBook["start"] = data[currentISBN][0:5]
                        log(f"Current book: {currentBook['title']} by {currentBook['author']}")
                    else:
                        default_isbn = list(data.keys())[0]
                        save_new_isbn(default_isbn)
                        currentBook["isbn"], currentBook["title"], currentBook["author"], currentBook["cover"], currentBook["start"] = data[default_isbn][0:5]
                        log(f"Default book set: {currentBook['title']} by {currentBook['author']}")
                else:
                    log("[Error] Could not retrieve currently reading books.")
                    time.sleep(10)
                    continue
                if currentBook["title"] and currentBook["author"]:
                    try:
                        rpc.update(
                            details=currentBook["title"],
                            state=f"by {currentBook['author'] if currentBook['author'] else 'Unknown Author'}",
                            large_image=currentBook["cover"] or "https://i.gr-assets.com/images/S/compressed.photo.goodreads.com/nophoto/book/111x148._SX50_.png",
                            large_text="Reading via Goodreads",
                            start=int(time.mktime(time.strptime(currentBook["start"], "%b %d, %Y"))) if currentBook["start"] else None,
                            buttons=[{
                                "label": "View Goodreads",
                                "url": f"https://www.goodreads.com/review/list/{goodreadsUserId}?shelf=currently-reading"
                            }]
                        )
                        log(f"[Updated] {currentBook['title']} by {currentBook['author']}")
                    except Exception as e:
                        errorMessage = str(e).lower()
                        if "pipe" in errorMessage or "closed" in errorMessage or isinstance(e, (ConnectionResetError, BrokenPipeError, OSError)):
                            log(f"RPC connection lost or pipe closed: {e}, attempting reconnect.")
                            try:
                                rpc.close()
                            except Exception:
                                pass
                            try:
                                rpc = Presence(discordAppId)
                                rpc.connect()
                                log("Reconnected to Discord RPC.")
                                rpc.update(
                                    details=currentBook["title"],
                                    state=f"by {currentBook['author'] if currentBook['author'] else 'Unknown Author'}",
                                    large_image=currentBook["cover"] or "https://i.gr-assets.com/images/S/compressed.photo.goodreads.com/nophoto/book/111x148._SX50_.png",
                                    large_text="Reading via Goodreads",
                                    start=int(time.mktime(time.strptime(currentBook["start"], "%b %d, %Y"))) if currentBook["start"] else None,
                                    buttons=[{
                                        "label": "View Goodreads",
                                        "url": f"https://www.goodreads.com/review/list/{goodreadsUserId}?shelf=currently-reading"
                                    }]
                                )
                            except Exception as reconnectError:
                                log(f"Reconnection failed: {reconnectError}")
                                time.sleep(10)
                                continue
                        else:
                            log(f"Unexpected RPC update error: {e}")

                else:
                    log("[Error] Could not retrieve current book.")
                    time.sleep(10)
                    continue
            else:
                try:
                    rpc.clear()
                    log("Presence cleared due to loop not running.")
                except Exception as e:
                    pass
                log("Presence loop paused.")
                time.sleep(10)
                continue
            for _ in range(refreshInterval):
                time.sleep(1)
                if (not loopShouldRunEvent.is_set() and not stayRunningAfterGUIEvent.is_set()) or trayQuitEvent.is_set():
                    break
        else:
            # close gui and exit loop
            log("Loop should not run, exiting presence loop.")
            log("Exiting presence loop due to tray quit event.")
            rpc.close()
            break

# === Save New ISBN Function ===
def save_new_isbn(isbn):
    global currentISBN
    currentISBN = isbn
    with open(configFile, "r+") as f:
        configData = json.load(f)
        configData["currentISBN"] = currentISBN
        f.seek(0)
        json.dump(configData, f, indent=4)
        f.truncate()
    log(f"New ISBN saved: {currentISBN}")

# === GUI ===
def launch_gui():
    global discordAppId, goodreadsUserId, refreshInterval, minimizeToTray, StartOnStartup

    def save_config():
        global discordAppId, goodreadsUserId, refreshInterval, minimizeToTray, StartOnStartup, currentISBN, currentBook
        configData = {
            "discordAppId": discordAppIdVar.get(),
            "goodreadsUserId": goodreadsUserIdVar.get(),
            "keepRunning": keepRunningVar.get(),
            "minimizeToTray": minimizeToTrayVar.get(),
            "startOnStartup": startOnStartupVar.get(),
            "refreshInterval": refreshIntervalVar.get(),
            "currentISBN": currentBookVar.get().split(" -- ")[-1] if currentBookVar.get() != "None" else None
        }
        with open(configFile, "w") as f:
            json.dump(configData, f, indent=4)
        discordAppId = configData["discordAppId"]
        goodreadsUserId = configData["goodreadsUserId"]
        refreshInterval = configData["refreshInterval"]
        minimizeToTray = configData["minimizeToTray"]
        StartOnStartup = configData["startOnStartup"]
        currentISBN = configData["currentISBN"]
        currentBook = books.get(currentISBN, {"isbn": None, "title": None, "author": None, "cover": None, "start": None})
        set_startup_enabled()
        if keepRunningVar.get():
            stayRunningAfterGUIEvent.set()
        else:
            stayRunningAfterGUIEvent.clear()

    def on_close():
        log(f"GUI closed. stayRunningAfterGUIEvent: {stayRunningAfterGUIEvent.is_set()}")
        if not stayRunningAfterGUIEvent.is_set():
            loopShouldRunEvent.clear()
        if minimizeToTray:
            log("Minimizing to tray.")
            root.withdraw()
        else:
            log("Closing GUI and exiting.")
            root.destroy()

    global root
    root = tk.Tk()
    root.title("Discord RPC Config")

    discordAppIdVar = tk.StringVar(value=discordAppId)
    goodreadsUserIdVar = tk.StringVar(value=goodreadsUserId)
    keepRunningVar = tk.BooleanVar(value=stayRunningAfterGUIEvent.is_set())
    refreshIntervalVar = tk.IntVar(value=refreshInterval)
    minimizeToTrayVar = tk.BooleanVar(value=minimizeToTray)
    startOnStartupVar = tk.BooleanVar(value=config.get("startOnStartup", False))
    currentBookVar = tk.StringVar(value=str(books[currentISBN][1]) + " -- " + str(currentISBN) if currentISBN else "None")

    ttk.Label(root, text="Discord App ID (Enter to Save):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
    discordAppIdEntry = ttk.Entry(root, textvariable=discordAppIdVar, width=40)
    discordAppIdEntry.grid(row=0, column=1, padx=10, pady=5)
    discordAppIdEntry.bind("<Return>", lambda e: save_config())
    discordAppIdEntry.bind("<FocusOut>", lambda e: save_config())
    

    ttk.Label(root, text="Goodreads User ID (Enter to Save):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
    goodreadsUserIdEntry = ttk.Entry(root, textvariable=goodreadsUserIdVar, width=40)
    goodreadsUserIdEntry.grid(row=1, column=1, padx=10, pady=5)
    goodreadsUserIdEntry.bind("<Return>", lambda e: save_config())
    goodreadsUserIdEntry.bind("<FocusOut>", lambda e: save_config())
    
    ttk.Label(root, text="displayed book:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
    bookOptions = [str(title) + " -- " + str(isbn) for isbn, (isbnin, title, author, cover, start) in books.items()]
    currentBookDropdown = ttk.Combobox(root, textvariable=currentBookVar, values=bookOptions, state="readonly")
    currentBookDropdown.grid(row=2, column=1, columnspan=2, padx=10, pady=5, sticky="w")
    currentBookDropdown.bind("<<ComboboxSelected>>", lambda e: save_config())

    keepRunningCheck = ttk.Checkbutton(root, text="Keep presence running after closing", variable=keepRunningVar)
    keepRunningCheck.grid(row=3, column=0, columnspan=2, pady=5)
    keepRunningVar.trace_add("write", lambda *_: save_config())
    minimizeToTrayCheck = ttk.Checkbutton(root, text="Minimize to tray on close", variable=minimizeToTrayVar)
    minimizeToTrayCheck.grid(row=4, column=0, columnspan=2, pady=5)
    minimizeToTrayVar.trace_add("write", lambda *_: save_config())
    startOnStartupCheck = ttk.Checkbutton(root, text="Start this app on system startup", variable=startOnStartupVar)
    startOnStartupCheck.grid(row=5, column=0, columnspan=2, pady=5)
    startOnStartupVar.trace_add("write", lambda *_: save_config())

    ttk.Label(root, text="Refresh Interval (seconds):").grid(row=6, column=0, padx=10, pady=5, sticky="w")
    refreshIntervalEntry = ttk.Entry(root, textvariable=refreshIntervalVar, width=10)
    refreshIntervalEntry.grid(row=6, column=1, padx=10, pady=5)
    refreshIntervalEntry.bind("<Return>", lambda e: save_config())
    refreshIntervalEntry.bind("<FocusOut>", lambda e: save_config())
    
    updateButton = ttk.Button(root, text="Check for Updates", command=update_application)
    updateButton.grid(row=7, column=0, columnspan=2, pady=10)

    root.protocol("WM_DELETE_WINDOW", on_close)
    
    def check_tray_quit():
        if trayQuitEvent.is_set():
            log("Tray quit event detected, closing GUI.")
            root.destroy()
        else:
            root.after(1000, check_tray_quit)
    
    check_tray_quit()
    root.mainloop()

# === Main ===
if __name__ == "__main__":
    log("Starting Goodreads Discord RPC application.")
    books = get_currently_reading(goodreadsUserId)
    if books:
        if currentISBN:
            if currentISBN in books:
                currentBook["isbn"], currentBook["title"], currentBook["author"], currentBook["cover"], currentBook["start"] = books[currentISBN]
                log(f"Current book: {currentBook['title']} by {currentBook['author']}")
            else:
                default_isbn = list(books.keys())[0]
                currentBook["isbn"], currentBook["title"], currentBook["author"], currentBook["cover"], currentBook["start"] = books[default_isbn]
                log(f"Current book: {currentBook['title']} by {currentBook['author']}")
        else:
            default_isbn = list(books.keys())[0]
            currentBook["isbn"], currentBook["title"], currentBook["author"], currentBook["cover"], currentBook["start"] = books[default_isbn]
            log(f"Current book: {currentBook['title']} by {currentBook['author']}")
    else:
        log("No currently reading book found.")
    
    loopShouldRunEvent.set()

    loopThread = threading.Thread(target=presence_loop, daemon=True)
    loopThread.start()
    trayThread = threading.Thread(target=show_tray, daemon=True)
    trayThread.start()
    launch_gui()
    if stayRunningAfterGUIEvent.is_set():
        loopThread.join()
