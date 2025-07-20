import time
from turtle import st
import requests
from bs4 import BeautifulSoup
from pypresence import Presence
import re
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox

configFile = "config.json"
# === Global Variables ===
discordAppId = None
goodreadsUserId = None

# === Events ===
loopShouldRunEvent = threading.Event()
stayRunningAfterGUIEvent = threading.Event()

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
            "keepRunning": True
        }
        with open(configFile, "w") as f:
            json.dump(defaultConfig, f, indent=4)
        return defaultConfig

# === Load Config and Initialize Variables ===
config = load_config()
discordAppId = config.get("discordAppId")
goodreadsUserId = config.get("goodreadsUserId")
if config.get("keepRunning", True):
    stayRunningAfterGUIEvent.set()

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
            log("Presence loop paused.")
        for _ in range(60):
            time.sleep(1)
            if not loopShouldRunEvent.is_set() and not stayRunningAfterGUIEvent.is_set():
                break

# === GUI ===
def launch_gui():
    global discordAppId, goodreadsUserId

    def save_config():
        global discordAppId, goodreadsUserId
        configData = {
            "discordAppId": discordAppIdVar.get(),
            "goodreadsUserId": goodreadsUserIdVar.get(),
            "keepRunning": keepRunningVar.get()
        }
        with open(configFile, "w") as f:
            json.dump(configData, f, indent=4)
        discordAppId = configData["discordAppId"]
        goodreadsUserId = configData["goodreadsUserId"]
        if keepRunningVar.get():
            stayRunningAfterGUIEvent.set()
        else:
            stayRunningAfterGUIEvent.clear()
        messagebox.showinfo("Saved", "Configuration saved successfully.")

    def on_close():
        log(f"GUI closed. stayRunningAfterGUIEvent: {stayRunningAfterGUIEvent.is_set()}")
        if not stayRunningAfterGUIEvent.is_set():
            loopShouldRunEvent.clear()
        root.destroy()

    root = tk.Tk()
    root.title("Discord RPC Config")

    discordAppIdVar = tk.StringVar(value=discordAppId)
    goodreadsUserIdVar = tk.StringVar(value=goodreadsUserId)
    keepRunningVar = tk.BooleanVar(value=stayRunningAfterGUIEvent.is_set())

    ttk.Label(root, text="Discord App ID:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
    ttk.Entry(root, textvariable=discordAppIdVar, width=40).grid(row=0, column=1, padx=10, pady=5)

    ttk.Label(root, text="Goodreads User ID:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
    ttk.Entry(root, textvariable=goodreadsUserIdVar, width=40).grid(row=1, column=1, padx=10, pady=5)

    ttk.Checkbutton(root, text="Keep presence running after closing", variable=keepRunningVar).grid(row=2, column=0, columnspan=2, pady=5)

    ttk.Button(root, text="Save", command=save_config).grid(row=3, column=0, columnspan=2, pady=10)

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

# === Main ===
if __name__ == "__main__":
    loopShouldRunEvent.set()

    loopThread = threading.Thread(target=presence_loop, daemon=True)
    loopThread.start()
    launch_gui()

    if stayRunningAfterGUIEvent.is_set():
        loopThread.join()
