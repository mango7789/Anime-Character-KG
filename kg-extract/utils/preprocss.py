import re

def extract_wiki_links(text):
    return re.findall(r"\[\[([^\]|]+)", text)

def del_wiki_links(text):
    return re.sub(r"\[\[[^\]]+\]\]", "", text)

def remove_del(text: str) -> str:
    return re.sub(r"<del>.*?</del>", "", text, flags=re.S)
    
def unwrap_ruby(text):
    # {{ruby|唯一的挚友|My one and only friend}} → 唯一的挚友
    return re.sub(r"\{\{ruby\|([^|}]+)\|[^}]+\}\}", r"\1", text, flags=re.IGNORECASE)
def unwrap_color(text):
    # {{ruby|唯一的挚友|My one and only friend}} → 唯一的挚友
    return re.sub(r"\{\{彩幕\|([^|}]+)\|[^}]+\}\}", r"\1", text)

def strip_lj_template(text: str) -> str:
    return re.sub(r"\{\{lj\|([^}]+)\}\}", r"\1", text)

def remove_ref(text: str):
    return re.sub(r"<ref>.*?</ref>", "", text, flags=re.DOTALL)


def unwrap_black(text):
    BLACK_RE = re.compile(r"\{\{黑幕\|([^{}]+)\}\}")
    spoilers = []
    while True:
        m = BLACK_RE.search(text)
        if not m:
            break
        spoilers.append(m.group(1))
        text = text[:m.start()] + m.group(1) + text[m.end():]
    return text, spoilers

def split_br(text):
    text = re.split(r"<br\s*/?>", text)
    return [t.strip() for t in text if t.strip()]

def preprocess_text(text):
    
    text = remove_ref(text)
    text = remove_del(text)

    text = unwrap_ruby(text)
    text = strip_lj_template(text)
    text = unwrap_color(text)
    text = unwrap_black(text)[0]
    
    # text = re.sub(r"\{\{[^}]+\}\}", text)
    return text