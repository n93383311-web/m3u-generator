# main.py
import re
import time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

CDN_VARIANTS = [
    "https://cdn3.glebul.com/hls/",
    "https://cdn4.glebul.com/hls/"
]

URLS_FILE = "urls.txt"
OUTPUT_FILE = "index.m3u"

def find_m3u_in_requests(page, timeout=20):
    found = {"url": None}

    def on_request(request):
        u = request.url
        if "index.m3u8?" in u:
            found["url"] = u

    page.on("request", on_request)

    def on_response(response):
        u = response.url
        if "index.m3u8?" in u:
            found["url"] = u

    page.on("response", on_response)

    t0 = time.time()
    while time.time() - t0 < timeout:
        if found["url"]:
            return found["url"]
        time.sleep(0.5)
    return None

def normalize_channel(raw_path):
    raw = raw_path.strip("/")
    prefix = "hd-" if raw.endswith("-hd") else ""
    channel_for_url = raw
    return prefix, channel_for_url, raw

def process_urls(urls):
    lines = ["#EXTM3U"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context()
        page = context.new_page()
        for url in urls:
            print("Processing:", url)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                print("Error loading page:", e)
            m3u_url = find_m3u_in_requests(page, timeout=25)
            if not m3u_url:
                try:
                    html = page.content()
                    m = re.search(r'(index\.m3u8\?[^"\s<>]+)', html)
                    if m:
                        m3u_url = m.group(1)
                except Exception:
                    pass
            if not m3u_url:
                print("No index.m3u8 found for", url)
                continue
            if m3u_url.startswith("http"):
                extracted = m3u_url
            else:
                extracted = m3u_url
            parsed = urlparse(url)
            raw_name = parsed.path.strip('/').split('/')[-1]
            prefix, channel_part, extinf_name = normalize_channel(raw_name)
            for cdn_base in CDN_VARIANTS:
                if extracted.startswith("http"):
                    tail_match = re.search(r'(index\.m3u8\?.+)$', extracted)
                    tail = tail_match.group(1) if tail_match else extracted
                    final = f"{cdn_base}{prefix}{channel_part}/{tail}"
                else:
                    final = f"{cdn_base}{prefix}{channel_part}/{extracted}"
                lines.append(f"#EXTINF:-1, {extinf_name}")
                lines.append(final)
                print("Added:", final)
        browser.close()
    return "\n".join(lines) + "\n"

def main():
    with open(URLS_FILE, "r", encoding="utf-8") as f:
        urls = [l.strip() for l in f if l.strip()]
    result = process_urls(urls)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(result)
    print("Wrote", OUTPUT_FILE)

if __name__ == "__main__":
    main()
