import json
import os
from collections import defaultdict


JSON_PATH = r"C:\Users\19642\Desktop\kg\total.json"  # 你的完整 JSON 文件
OUT_DIR = r"C:\Users\19642\Desktop\kg\ent_aug"  # 输出目录


def main():
    print("🚀 Start building entity txt files")

    if not os.path.exists(JSON_PATH):
        print("❌ JSON file not found:", JSON_PATH)
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    type2ents = defaultdict(set)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("DEBUG JSON top-level type:", type(data))
    print("DEBUG number of works:", len(data))

    # 🔑 关键：两层遍历
    for work_name, triples in data.items():
        if not isinstance(triples, list):
            continue

        for item in triples:
            if not isinstance(item, dict):
                continue

            # -------- head --------
            head = item.get("head")
            head_type = item.get("head_type")
            if head and head_type:
                head = clean_entity(head)
                if head:
                    type2ents[head_type].add(head)

            # -------- tail --------
            tail = item.get("tail")
            tail_type = item.get("tail_type")
            if tail and tail_type:
                tail = clean_entity(tail)
                if tail:
                    type2ents[tail_type].add(tail)

    print("DEBUG collected types:", list(type2ents.keys()))

    # 写入文件
    for t, ents in type2ents.items():
        out_path = os.path.join(OUT_DIR, f"{t}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            for e in sorted(ents):
                f.write(e + "\n")

        print(f"✔ 写入 {out_path}，共 {len(ents)} 个实体")

    print("✅ Done")


def clean_entity(text: str) -> str:
    """
    实体名清洗：
    - 去 <ref>...</ref>
    - 去残缺标签
    - 去空白
    """
    if not text:
        return ""

    # 去 <ref>...</ref>
    while "<ref>" in text and "</ref>" in text:
        s = text.find("<ref>")
        e = text.find("</ref>") + len("</ref>")
        text = text[:s] + text[e:]

    # 去掉其他残留标签
    if "<" in text:
        text = text.split("<")[0]

    return text.strip()


if __name__ == "__main__":
    main()
