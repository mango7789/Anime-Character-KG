import re
import mwparserfromhell
from collections import defaultdict

from utils import load_json, save_json
from extraction_fields import infer_role_relation, FIELD_TO_RELATION_ROLE
from utils.preprocss import preprocess_text, extract_wiki_links, del_wiki_links, split_br


def parse_relation_line(line):
    if "：" not in line:
        return None, []

    rel, rest = line.split("：", 1)
    names = extract_wiki_links(rest)
    return rel.strip(), names


def extract_person_info(wikitext: str) -> str:
    """
    提取 {{人物信息 ... }} 模板块
    """
    code = mwparserfromhell.parse(wikitext)
    data = dict()
    for tpl in code.filter_templates():
        if "人物信息" in tpl.name or "角色信息" in tpl.name or "info" in tpl.name.lower():
            data = parse_infobox_template(tpl, data)
    i = 1
    # 对于 {"1": , "2": ...} 
    while str(i) in data:
        line = data[str(i)]
        try:
            k,v = line.split("::", maxsplit=1)
        except:
            i += 1
            continue
        if k.strip() and v.strip():
            data[k.strip()] = v.strip()
        i += 1
    return data

def parse_infobox_template(tpl, data=dict()):
    if not tpl:  return {}
    for param in tpl.params:
        key = str(param.name).strip()
        value = str(param.value).strip()
        data[key] = value
    return data


def extract_voice_actors(role_name, infobox):
    triples = []
    if '声优' in infobox:
        triples.append({
            "head": role_name,
            "relation": "VoiceBy",
            "tail": infobox['声优'],
            "head_type": "Character",
            "tail_type": "Person",
            "source": "MoegirlWiki",
        })
    elif '多位声优' in infobox:
        text = infobox['多位声优']
        voice_list = split_br(text)
        NON_JP_MARKERS = [
            "中国", "大陆", "国配","香港", "港配", "台湾", "台配", "（台","（中", "粤语", "<ref>", "汉语"
        ]
        for voice in voice_list:
            if any([x in voice for x in NON_JP_MARKERS]):
                continue
            tail = extract_wiki_links(voice)
            if tail:
                triples.append({
                    "head": role_name,
                    "relation": "VoiceBy",
                    "tail": tail[0],
                    "head_type": "Character",
                    "tail_type": "Person",
                    "source": "MoegirlWiki",
                    "raw": voice
                })
    return triples

def extract_role_relation(role_name, infobox):
    related = infobox.get('相关人士', "")
    triples = []

    if related:  #存在"相关人士"的情况
        related = preprocess_text(related)
        for rel_text1 in split_br(related):
            for rel_text2 in re.split(r"[；;]", rel_text1):
                for rel_text3 in re.split(r"\s+", rel_text2):
                    rel, val = parse_relation_line(rel_text3)
                    if not rel or not val: continue

                    for r in re.split(r'[/&兼]', rel):
                        r = infer_role_relation(r)
                        if not r: continue
                        for v in val:
                            triples.append({
                                "head": role_name,
                                "relation": r,
                                "tail": v,
                                "head_type": "Character",
                                "tail_type": "Character",
                                "source": "MoegirlWiki",
                                "raw": rel_text1
                            })
    else:
        keys = list(filter(lambda x: '相关人士' in x, infobox.keys()))
        for key in keys:
            raw_value = infobox[key]
            
            rel_hint = ""
            if "-" in key:
                rel_hint = key.split("-", 1)[1]
                rel_hint = preprocess_text(rel_hint)
            # 若"相关人士-[[Roselia]]"
            if extract_wiki_links(rel_hint):
                triples.append({
                    "head": role_name,
                    "relation": "MemberOf",
                    "tail": extract_wiki_links(rel_hint)[0],
                    "head_type": "Character",
                    "tail_type": "Group",
                    "source": "MoegirlWiki",
                    "raw": key + "::" + raw_value
                })
                rel_hint = ""
            
            text = preprocess_text(raw_value)
            people = re.split(r"[、，,]", text)
            
            for p in people:
                names = extract_wiki_links(p)
                if not names:
                    continue

                # 3. 括号里的补充关系
                extra_rel = ""
                m = re.search(r"（([^）]+)）", p)
                if m:
                    extra_rel = m.group(1)
                    extra_rel = infer_role_relation(extra_rel)

                relation = infer_role_relation(rel_hint)

                for name in names:
                    for rel in [extra_rel, relation]:
                        if rel:
                            triples.append({
                                "head": role_name,
                                "relation": rel,
                                "tail": name,
                                "head_type": "Character",
                                "tail_type": "Character",
                                "source": "MoegirlWiki",
                                "raw": key + "::" + raw_value
                            })
    return triples


SPLIT_RE = re.compile(r"(?:、|<br\s*/?>)+", flags=re.I)

def extract_other_infobox(role_name, infobox):
    triples = []

    for field, cfg in FIELD_TO_RELATION_ROLE.items():
        if field not in infobox:
            continue
        
        raw = infobox[field]
        text = preprocess_text(raw)

        # 统一分隔
        values = re.split(SPLIT_RE, text)
        values = [v.strip() for v in values if v.strip()]

        for value in values:
            if field == "萌点":
                m = re.search(r"\{\{萌点\|([^}]+)\}\}", value)
                if m: 
                    tags = m.group(1).split('|')
                    triples.extend([{"head": role_name,
                        "relation": cfg["relation"],
                        "tail": tag,
                        "head_type": "Character",
                        "tail_type": cfg["type"],
                        "source": "MoegirlWiki",
                        "raw": infobox[field]} for tag in tags])
                    value = re.sub(r"\{\{萌点\|([^}]+)\}\}", "", value).strip()
            # wiki link 优先
            links = extract_wiki_links(value)
            for link in links:
                triples.append({
                    "head": role_name,
                    "relation": cfg["relation"],
                    "tail": link,
                    "head_type": "Character",
                    "tail_type": cfg["type"],
                    "source": "MoegirlWiki",
                    "raw": infobox[field],
                })
            value = del_wiki_links(value).strip()
            if value:
                # 字面值属性（性别 / 身高 / 生日 / 萌点）
                triples.append({
                    "head": role_name,
                    "relation": cfg["relation"],
                    "tail": value,
                    "head_type": "Character",
                    "tail_type": cfg["type"],
                    "source": "MoegirlWiki",
                    "raw": infobox[field],
                })
    return triples


def extract_from_infobox(role_name, infobox):
    triples = []
    func_list = [extract_voice_actors, extract_role_relation, extract_other_infobox]
    for func in func_list:
        triples.extend(func(role_name, infobox))
    return triples


if __name__ == "__main__":
    
    input_path = "anime_char_info.json"
    char_info = load_json(input_path)

    results = defaultdict(list)

    for anime, char_dict in char_info.items():
        for char, info in char_dict.items():
            if not info:  continue

            # info = preprocess_text(info)
            infobox = extract_person_info(info)
            
            results[anime].append({
                "head": char,
                "relation": "AppearsIn",
                "tail": anime,
                "head_type": "Character",
                "tail_type": "Work",
                "source": "MoegirlWiki"
            })
            results[anime].extend(extract_from_infobox(char, infobox))

    save_json(results, "triples_role.json")
