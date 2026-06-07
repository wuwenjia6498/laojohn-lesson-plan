import os, pathlib
pw_path = str(pathlib.Path.home() / "AppData" / "Local" / "ms-playwright")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = pw_path

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 794, "height": 1200})
    page.goto("file:///E:/laojohn-lesson-plan/课程详案输出/俗世奇人-阅读指南.html", wait_until="networkidle")
    page.wait_for_selector("body[data-rendered='1']", timeout=15000)
    h = page.evaluate("() => document.getElementById('page').scrollHeight")
    browser.close()
    print("content height:", h, "px  →  PDF pages if A4:", round(h/1123, 2))
