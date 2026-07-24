import urllib.request
import re

# 直接检查主站 /zh/cn/07-22/ 是否可访问
urls_to_check = [
    "https://history.ai-term-hub.com/zh/cn/07-22/",
    "https://history.ai-term-hub.com/zh/cn/",
    "https://history.ai-term-hub.com/zh/",
]

for url in urls_to_check:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "TodayInHistoryArchive/1.0"},
            method="HEAD",
        )
        resp = urllib.request.urlopen(req, timeout=30)
        print(url + " -> " + str(resp.status))
    except urllib.error.HTTPError as e:
        print(url + " -> HTTP " + str(e.code))
    except Exception as e:
        print(url + " -> Error: " + str(e))

# 检查 sitemap
try:
    req = urllib.request.Request(
        "https://history.ai-term-hub.com/zh/sitemap.xml",
        headers={"User-Agent": "TodayInHistoryArchive/1.0"},
    )
    resp = urllib.request.urlopen(req, timeout=60)
    content = resp.read().decode("utf-8")
    urls = re.findall(r"<loc>([^<]+)</loc>", content)
    print("\nSitemap URLs: " + str(len(urls)))

    dates = set()
    for u in urls:
        parts = u.split("/")
        for p in parts:
            if re.match(r"^\d\d-\d\d$", p):
                dates.add(p)
    print("Unique dates: " + str(len(dates)))
    print("Has 07-22: " + str("07-22" in dates))
except Exception as e:
    print("Sitemap error: " + str(e))
