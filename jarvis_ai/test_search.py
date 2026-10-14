import urllib.request
import urllib.parse
import re

def search_ddg(query):
    url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        with open("ddg.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Saved to ddg.html")
    except Exception as e:
        print("Error:", e)

search_ddg("latest AI news")
