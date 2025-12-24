import time
import requests

API = "https://zh.moegirl.org.cn/api.php"

def fetch_page_wikitext(title: str, interval=2.0):
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "format": "json",
        "titles": title
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0"
    }
    time.sleep(interval)
    r = requests.get(API, 
                     params=params, 
                     headers=headers, 
                     timeout=15)
    r.raise_for_status()
    try:
        data = r.json()
    except:
        print(f"{title} error")
        print(r)
        return ""
    
    pages = data["query"]["pages"]
    for _, page in pages.items():
        if "revisions" in page:
            print(title, "OK")
            return page["revisions"][0]["*"]
    return ""

def is_redirected(wikitext: str):
    return wikitext.upper().startswith("#REDIRECT") or wikitext.startswith("#重定向")

def is_disambiguation(wikitext: str) -> bool:
    return wikitext.lower().endswith('{{disambig}}')
