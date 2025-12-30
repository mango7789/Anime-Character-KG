import json
from openai import OpenAI
from utils import load_json, save_json
from prompts import EXTRACTION_PROMPT
from extract_tuple_character import parse_infobox_template
import mwparserfromhell

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


# =========================
# 全局 schema（共用）
# =========================
schema = load_json("schema.json")


def extract_person_info(wikitext: str):
    """
    提取 {{人物信息 ... }} / {{角色信息 ...}} 模板块
    """
    code = mwparserfromhell.parse(wikitext)
    data = {}
    for tpl in code.filter_templates():
        name = str(tpl.name)
        if "人物信息" in name or "角色信息" in name or "info" in name.lower():
            data = parse_infobox_template(tpl, data)
    return data


def call_llm(client, messages, timeout=300):
    completion = client.chat.completions.create(
        model="/data/models/Qwen/Qwen3-235B-A22B-Instruct-2507",
        messages=messages,
        temperature=0,
        timeout=timeout,
    )
    return completion.choices[0].message.content


def get_messages(char, info):
    system_prompt = EXTRACTION_PROMPT.replace(
        "{schema}", json.dumps(schema, ensure_ascii=False), 1
    )

    if not isinstance(info, str):
        info = json.dumps(info, ensure_ascii=False)

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"主实体：\n{char}\n\n输入文本：\n{info}",
        },
    ]
    return messages


def process_one_character(client, anime, character, text):
    """
    单个角色的完整处理流程（供并发调用）
    """
    if not text or not text.strip():
        return []

    triples = [{
        "head": character,
        "relation": "AppearsIn",
        "tail": anime,
        "head_type": "Character",
        "tail_type": "Work",
        "source": "MoegirlWiki"
    }]
    try:
        info = extract_person_info(text)
        messages = get_messages(character, info)
        response = call_llm(client, messages)

        triples.extend(json.loads(response))

        # # 可选：在这里统一补充 source / work 信息
        # for t in triples:
        #     t.setdefault("source", "MoegirlWiki")

        return triples

    except json.JSONDecodeError:
        print(f"[WARN] JSON解析失败: {anime} / {character}")
        return triples
    except Exception as e:
        print(f"[ERROR] {anime} / {character} 处理失败：{e}")
        return triples


if __name__ == "__main__":
    client = OpenAI(
        api_key="Empty",
        base_url="http://0.0.0.0:8001/v1",
    )

    # characters_by_anime = load_json("ex_character.json")
    characters_by_anime = load_json("anime_char_info.json")

    all_triples = defaultdict(list)

    SAVE_INTERVAL = 10
    OUTPUT_PATH = "triples_llm.json"
    max_workers = 8   # ⭐ 235B 建议 2~4

    completed = 0

    # =========================
    # 构建任务列表
    # =========================
    tasks = []
    for anime, chars in characters_by_anime.items():
        for character, text in chars.items():
            tasks.append((anime, character, text))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                process_one_character, client, anime, character, text
            ): (anime, character)
            for anime, character, text in tasks
        }

        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Extracting triples",
        ):
            anime, character = futures[future]
            triples = future.result()

            if triples:
                all_triples[anime].extend(triples)

            completed += 1

            if completed % SAVE_INTERVAL == 0:
                save_json(all_triples, OUTPUT_PATH)
                print(
                    f"\n💾 已完成 {completed}/{len(tasks)}，"
                    f"当前三元组数：{len(all_triples)}，已保存"
                )

    save_json(all_triples, OUTPUT_PATH)
    print(f"\n✅ 全部完成，共 {len(all_triples)} 条三元组，已最终保存")
