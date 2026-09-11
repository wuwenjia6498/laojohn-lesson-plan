#!/usr/bin/env python3
import os, sys, pathlib

pw_path = str(pathlib.Path.home() / "AppData" / "Local" / "ms-playwright")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = pw_path

from playwright.sync_api import sync_playwright

html_path = sys.argv[1]
out_png   = sys.argv[2]
file_url  = "file:///" + html_path.replace("\\", "/")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 794, "height": 1123})
    page.goto(file_url, wait_until="networkidle")
    page.wait_for_selector("body[data-rendered='1']", timeout=15000)
    page.screenshot(path=out_png, full_page=True)
    browser.close()

print("Screenshot:", out_png)
