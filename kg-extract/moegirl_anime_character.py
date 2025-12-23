import requests
# from curl_cffi import requests
# from curl_cffi.const import CurlHttpVersion

import json
import time
import os
from collections import defaultdict
import re

from utils import load_json, save_json
from utils.wiki_crawler import fetch_page_wikitext, is_redirected, is_disambiguation
from utils.preprocss import extract_wiki_links


if __name__ == "__main__":
    pre_results_path = None
    try:
        pre_results = load_json(pre_results_path)
    except:
        pre_results = dict()

    output_path = "anime_char_info.json"
    crawl_list = load_json("anime_char_list_zh.json")
    results = defaultdict(dict)
    cnt = 0
    for i, (anime, char_list) in enumerate(crawl_list.items()):
        for char in char_list:
            cnt += 1
            if pre_results.get(anime, {}) and pre_results[anime].get(char, ""):
                text = pre_results[anime][char]
            else:
                text = fetch_page_wikitext(char)

            if is_redirected(text):
                char = extract_wiki_links(text)[0]
                text = fetch_page_wikitext(char)
            elif is_disambiguation(text):
                text = fetch_page_wikitext(f"{char}({anime})")

            results[anime][char] = text
            if cnt % 10 == 0:
                save_json(results, output_path)
                print(f'{cnt+1}步,保存中间结果')
    
    save_json(results, output_path)
    # print((text))
