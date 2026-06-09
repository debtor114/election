from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
o=Options(); o.add_argument("--headless=new"); o.add_argument("--window-size=900,700"); o.add_argument("--hide-scrollbars")
d=webdriver.Chrome(options=o)
d.get("https://debtor114.github.io/election/methodology.html"); time.sleep(4)
for e in d.find_elements("css selector","h2"):
    if "닫힌 공식" in e.text: d.execute_script("arguments[0].scrollIntoView({block:'start'});",e); break
time.sleep(1.5); d.save_screenshot("_preview.png")
# KaTeX 에러 요소 탐지
errs=d.find_elements("css selector",".katex-error")
print("katex-error 요소 수:", len(errs))
for e in errs[:3]: print("  ERR:", e.get_attribute("title")[:80])
d.quit(); print("ok")
