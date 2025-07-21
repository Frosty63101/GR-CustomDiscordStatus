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
elif IS_MAC:
    import pyobjc


configFile = "config.json"
# === Global Variables ===
discordAppId = None
goodreadsUserId = None
refreshInterval = 60 
minimizeToTray = True
StartOnStartup = False

# === Events ===
loopShouldRunEvent = threading.Event()
stayRunningAfterGUIEvent = threading.Event()
trayQuitEvent = threading.Event()

# === Logging Function ===
def log(message):
    try:
        with open("log.txt", "a") as logFile:
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
            "refreshInterval": 60
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
if config.get("keepRunning", True):
    stayRunningAfterGUIEvent.set()

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
            return None, None, None, None
        soup = BeautifulSoup(response.text, 'html.parser')
        bookTable = soup.find("table", {"id": "books"})
        if not bookTable:
            log("No book table found.")
            return None, None, None, None
        firstRow = bookTable.find("tr", {"id": lambda x: x and x.startswith("review_")})
        if not firstRow:
            log("No book row found.")
            return None, None, None, None
        title = firstRow.find("td", class_="field title").find("a").get_text(strip=True)
        author = firstRow.find("td", class_="field author").find("a").get_text(strip=True)
        coverArt = firstRow.find("td", class_="field cover").find("img")["src"]
        coverArt = re.sub(r'\._[A-Z0-9]+_(?=\.(jpg|jpeg|png))', '', coverArt, flags=re.IGNORECASE)
        startDateSpan = firstRow.find("td", class_="field date_started").find("span", class_="date_started_value")
        startDate = startDateSpan.get_text(strip=True) if startDateSpan else None
        return title, author, coverArt, startDate
    except Exception as e:
        log(f"Error in Goodreads getter: {e}")
        return None, None, None, None

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
                title, author, cover, start = get_currently_reading(goodreadsUserId)
                if title and author:
                    try:
                        rpc.update(
                            details=title,
                            state=f"by {author if author else 'Unknown Author'}",
                            large_image=cover or "https://i.gr-assets.com/images/S/compressed.photo.goodreads.com/nophoto/book/111x148._SX50_.png",
                            large_text="Reading via Goodreads",
                            start=int(time.mktime(time.strptime(start, "%b %d, %Y"))) if start else None,
                            buttons=[{
                                "label": "View Goodreads",
                                "url": f"https://www.goodreads.com/review/list/{goodreadsUserId}?shelf=currently-reading"
                            }]
                        )
                        log(f"[Updated] {title} by {author}")
                    except Exception as e:
                        log(f"RPC update failed: {e}")
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

# === GUI ===
def launch_gui():
    global discordAppId, goodreadsUserId, refreshInterval, minimizeToTray, StartOnStartup

    def save_config():
        global discordAppId, goodreadsUserId, refreshInterval, minimizeToTray, StartOnStartup
        configData = {
            "discordAppId": discordAppIdVar.get(),
            "goodreadsUserId": goodreadsUserIdVar.get(),
            "keepRunning": keepRunningVar.get(),
            "minimizeToTray": minimizeToTrayVar.get(),
            "startOnStartup": startOnStartupVar.get(),
            "refreshInterval": refreshIntervalVar.get()
        }
        with open(configFile, "w") as f:
            json.dump(configData, f, indent=4)
        discordAppId = configData["discordAppId"]
        goodreadsUserId = configData["goodreadsUserId"]
        refreshInterval = configData["refreshInterval"]
        minimizeToTray = configData["minimizeToTray"]
        StartOnStartup = configData["startOnStartup"]
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

    keepRunningCheck = ttk.Checkbutton(root, text="Keep presence running after closing", variable=keepRunningVar)
    keepRunningCheck.grid(row=2, column=0, columnspan=2, pady=5)
    keepRunningVar.trace_add("write", lambda *_: save_config())
    minimizeToTrayCheck = ttk.Checkbutton(root, text="Minimize to tray on close", variable=minimizeToTrayVar)
    minimizeToTrayCheck.grid(row=3, column=0, columnspan=2, pady=5)
    minimizeToTrayVar.trace_add("write", lambda *_: save_config())
    startOnStartupCheck = ttk.Checkbutton(root, text="Start this app on system startup", variable=startOnStartupVar)
    startOnStartupCheck.grid(row=4, column=0, columnspan=2, pady=5)
    startOnStartupVar.trace_add("write", lambda *_: save_config())

    ttk.Label(root, text="Refresh Interval (seconds):").grid(row=5, column=0, padx=10, pady=5, sticky="w")
    refreshIntervalEntry = ttk.Entry(root, textvariable=refreshIntervalVar, width=10)
    refreshIntervalEntry.grid(row=5, column=1, padx=10, pady=5)
    refreshIntervalEntry.bind("<Return>", lambda e: save_config())
    refreshIntervalEntry.bind("<FocusOut>", lambda e: save_config())

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
    loopShouldRunEvent.set()

    loopThread = threading.Thread(target=presence_loop, daemon=True)
    loopThread.start()
    trayThread = threading.Thread(target=show_tray, daemon=True)
    trayThread.start()
    launch_gui()
    if stayRunningAfterGUIEvent.is_set():
        loopThread.join()
