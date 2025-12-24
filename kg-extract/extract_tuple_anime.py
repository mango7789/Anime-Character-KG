import re
import mwparserfromhell
from collections import defaultdict

from utils import load_json, save_json
from extraction_fields import FIELD_TO_RELATION_ANIME
from utils.preprocss import (
    preprocess_text,
    extract_wiki_links,
    del_wiki_links,
    split_br,
)


def extract_anime_info(wikitext):
    code = mwparserfromhell.parse(wikitext)
    data = dict()
    for tpl in code.filter_templates():
        if "infobox" in tpl.name.lower() or "信息" in tpl.name:
            data = parse_infobox_template(tpl, data)
    return data


def parse_infobox_template(tpl, data=dict()):
    if not tpl:
        return data
    for param in tpl.params:
        key = str(param.name).strip()
        value = str(param.value).strip()
        data[key] = value
    return data


def extract_categories(anime_name, wikitext: str) -> list[str]:
    CATEGORY_PATTERN = re.compile(r"\[\[(?:分类|Category):([^\]]+)\]\]")
    cat_list = CATEGORY_PATTERN.findall(wikitext)
    triples = []
    for cat in cat_list:
        cat = cat.replace("題材", "题材")
        if cat.strip().endswith("题材"):
            triples.append(
                {
                    "head": anime_name,
                    "relation": "WorkCategory",
                    "tail": cat.strip(),
                    "head_type": "Work",
                    "tail_type": "Tag",
                    "source": "MoegirlWiki",
                }
            )
    return triples


def extract_anime_relations(anime_name, infobox):
    triples = []

    for field, cfg in FIELD_TO_RELATION_ANIME.items():
        if field not in infobox:
            continue

        raw = infobox[field]
        text = preprocess_text(raw)
        # 处理 wiki 链接
        entities = extract_wiki_links(text)

        for ent in entities:
            triples.append(
                {
                    "head": anime_name,
                    "relation": cfg["relation"],
                    "tail": ent,
                    "head_type": "Work",
                    "tail_type": cfg["type"],
                    "source": "MoegirlWiki",
                    "raw": raw,
                }
            )
        text = del_wiki_links(text)
        value_list = split_br(text)
        for val in value_list:
            # 纯文本字段
            triples.append(
                {
                    "head": anime_name,
                    "relation": cfg["relation"],
                    "tail": val,
                    "head_type": "Work",
                    "tail_type": cfg["type"],
                    "source": "MoegirlWiki",
                    "raw": raw,
                }
            )
    return triples


if __name__ == "__main__":

    input_path = "anime_info_full.json"
    anime_info_dict: dict = load_json(input_path)
    results = defaultdict(list)
    for anime_name, anime_text in anime_info_dict.items():
        infobox = extract_anime_info(anime_text)
        results[anime_name].extend(extract_anime_relations(anime_name, infobox))
        results[anime_name].extend(extract_categories(anime_name, anime_text))

    # save_json(infobox, "temp_infobox.json")
    save_json(results, "triples_anime.json")
