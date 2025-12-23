import requests

import json
import time
import os

from utils import load_json, save_json
from utils.wiki_crawler import fetch_page_wikitext, is_redirected, is_disambiguation
from utils.preprocss import extract_wiki_links

if __name__ == "__main__":

    output_path = "anime_info_full.json"
    crawl_list = load_json("anime_char_list_zh.json")
    results = dict()

    for i, anime in enumerate(crawl_list):
        # anime = anime.strip('《').strip('》')
        text = fetch_page_wikitext(anime)
        if is_redirected(text):
            anime = extract_wiki_links(text)[0]
            text = fetch_page_wikitext(anime)

        results[anime] = text
        if (i+1) % 10 == 0:
            save_json(results, output_path)
            print(f'{i}步,保存中间结果')
    
    save_json(results, output_path)
    # print((text))
