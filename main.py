# ===================== FULL SCRIPT =====================
import cv2
import numpy as np
import pyautogui
import time
import subprocess
import random
import pyperclip
import re
from urllib.parse import urlparse
import os
import webbrowser
import threading

# ---------------------------
# CONFIGURATION
# ---------------------------
urls_file = "urls.txt"            # file containing one website URL per line
small_img_path = "small_image.png"  # template image to find and click
m3u_output = "index.m3u"
cdn_variants = ["https://cdn3.glebul.com/hls/", "https://cdn4.glebul.com/hls/"]

# Path to Brave browser executable
brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

# Start fresh output file
with open(m3u_output, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")

# Check template image exists
if not os.path.exists(small_img_path):
    print(f"Missing template image: {small_img_path}")
    exit()

# Load template image once
small_img = cv2.imread(small_img_path)
small_gray = cv2.cvtColor(small_img, cv2.COLOR_BGR2GRAY)

# ---------------------------
# READ URLs
# ---------------------------
if not os.path.exists(urls_file):
    print(f"URLs file not found: {urls_file}")
    exit()

with open(urls_file, "r", encoding="utf-8") as f:
    urls = [line.strip() for line in f if line.strip()]

print(f"Found {len(urls)} URLs to process.")

# ---------------------------
# REGISTER BRAVE BROWSER
# ---------------------------
webbrowser.register('brave', None, webbrowser.GenericBrowser(brave_path))
browser = webbrowser.get('brave')

# Function to open a URL in Brave in a separate thread
def open_url(url):
    browser.open_new_tab(url)

# ---------------------------
# PROCESS EACH URL
# ---------------------------
for i, website_url in enumerate(urls):
    print(f"\nProcessing: {website_url}")

    # Close previous tab before opening a new one (except for the first site)
    if i > 0:
        pyautogui.hotkey('ctrl', 'w')
        time.sleep(5)

    # Open Brave URL in a new tab (threaded to avoid blocking)
    thread = threading.Thread(target=open_url, args=(website_url,))
    thread.start()
    time.sleep(10)  # wait for page to load (adjust if needed)

    # ---------------------------
    # 1️. Take screenshot of current window
    # ---------------------------
    screenshot_path = "screen_capture.png"
    pyautogui.screenshot(screenshot_path)
    large_img = cv2.imread(screenshot_path)
    large_gray = cv2.cvtColor(large_img, cv2.COLOR_BGR2GRAY)

    # ---------------------------
    # 2️. Find template image on screen
    # ---------------------------
    result = cv2.matchTemplate(large_gray, small_gray, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(result)

    top_left = max_loc
    bottom_right = (top_left[0] + small_img.shape[1], top_left[1] + small_img.shape[0])
    x1, y1 = top_left
    x2, y2 = bottom_right
    coords = [(x, y) for y in range(y1, y2) for x in range(x1, x2)]
    x, y = random.choice(coords)

    print(f"Clicking at random point: ({x},{y})")
    pyautogui.moveTo(x, y, duration=0.5)
    pyautogui.click()

    # ---------------------------
    # 3️. Open DevTools
    # ---------------------------
    pyautogui.hotkey('ctrl', 'shift', 'i')
    time.sleep(10)  # give DevTools time to open

    # ---------------------------
    # 4️. Wait and extract index.m3u8 link
    # ---------------------------
    first_link = None
    timeout = 30
    start_time = time.time()

    while time.time() - start_time < timeout:
        pyautogui.hotkey('ctrl', 'a')  # select all
        time.sleep(3)
        pyautogui.hotkey('ctrl', 'c')  # copy
        time.sleep(3)

        copied_text = pyperclip.paste()
        match = re.search(r'index\.m3u8\?e=[^\s]+', copied_text)
        if match:
            first_link = match.group(0)
            break
        time.sleep(3)

    if not first_link:
        print("❌ Link not found — skipping this site.")
        continue

    print(f"✅ Extracted link: {first_link}")

    # ---------------------------
    # 5️. Extract channel name and determine prefix
    # ---------------------------
    parsed = urlparse(website_url)
    raw_name = parsed.path.strip('/').split('/')[-1]  # last part
    print(f"Channel name (raw): {raw_name}")

    # Determine prefix and clean name
    if raw_name.endswith("-hd"):
        prefix = "hd-"
        channel_name = raw_name
    else:
        prefix = ""
        channel_name = raw_name

    print(f"Channel name (used in M3U): {channel_name}")
    print(f"Prefix for M3U link: '{prefix}'")

    # ---------------------------
    # 6️. Build final URLs for both cdn3 and cdn4
    # ---------------------------
    with open(m3u_output, "a", encoding="utf-8") as f:
        for cdn_base in cdn_variants:
            final_link = f"{cdn_base}{prefix}{channel_name}/{first_link}"
            f.write(f"#EXTINF:-1, {channel_name}\n{final_link}\n")
            print(f"Added to index.m3u: {final_link}")

    # Optional: wait a bit before next URL
    time.sleep(3)

# ---------------------------
# 7️. Close last tab after all URLs processed
# ---------------------------
if len(urls) > 0:
    pyautogui.hotkey('ctrl', 'w')
    time.sleep(3)

# ---------------------------
# 8️. Summary
# ---------------------------
print("\n✅ All URLs processed successfully!")
print(f"📂 Final M3U file created: {os.path.abspath(m3u_output)}")

# Optional cleanup: remove temporary screenshot
if os.path.exists(screenshot_path):
    os.remove(screenshot_path)
    print("🗑 Temporary screenshot removed.")
