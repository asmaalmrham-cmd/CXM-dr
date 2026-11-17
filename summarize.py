"""تلخيص التعليقات: النموذج يصنّف ويلخّص، والكود يحسب النسب."""
import json
import re
from collections import Counter

from prompts import NO_COMMENTS_TEXT, SENTIMENT_SYSTEM, SUMMARY_SYSTEM

LABELS = ["إيجابي", "سلبي", "محايد"]


def _label(x) -> str:
    x = str(x)
    return next((l for l in LABELS if l in x), "محايد")


def _parse_array(raw):
    m = re.search(r"\[.*?\]", raw, re.S)
    if not m:
        return None
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return arr if isinstance(arr, list) else None


def classify_sentiments(llm, texts, batch=20):
    out = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        numbered = "\n".join(f"{j + 1}. {t}" for j, t in enumerate(chunk))
        msgs = [{"role": "system", "content": SENTIMENT_SYSTEM}, {"role": "user", "content": numbered}]
        arr = _parse_array(llm.chat(msgs, max_new_tokens=200))
        if arr is None or len(arr) != len(chunk):  # احتياط: تصنيف كل تعليق لحاله
            arr = [_label(llm.chat([{"role": "system", "content": SENTIMENT_SYSTEM},
                                    {"role": "user", "content": f"1. {t}"}], max_new_tokens=30)) for t in chunk]
        out += [_label(a) for a in arr]
    return out


def _summarize(llm, texts, strict=False):
    sample = "\n".join(f"- {t}" for t in texts[:60])
    system = SUMMARY_SYSTEM + ("\nتنبيه: ممنوع أي رقم في الملخص." if strict else "")
    raw = llm.chat([{"role": "system", "content": system}, {"role": "user", "content": sample}], max_new_tokens=350)
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        obj = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        obj = {}
    return str(obj.get("summary") or raw).strip(), [str(t) for t in obj.get("topics", [])][:5]


def summarize_comments(llm, question, comments) -> str:
    texts = [c["text"] for c in comments if isinstance(c, dict) and c.get("text")]
    if not texts:
        return NO_COMMENTS_TEXT
    labels = classify_sentiments(llm, texts)
    counts, n = Counter(labels), len(labels)
    pct = {l: f"{100 * counts.get(l, 0) / n:.1f}%" for l in LABELS}  # النسب يحسبها الكود

    summary, topics = _summarize(llm, texts)
    if re.search(r"[\d٠-٩]", summary):
        summary, topics = _summarize(llm, texts, strict=True)

    lines = [summary, "",
             f"المشاعر: إيجابي {pct['إيجابي']} · سلبي {pct['سلبي']} · محايد {pct['محايد']} (من {n} تعليق)"]
    if topics:
        lines.append("أبرز المواضيع: " + "، ".join(topics))
    return "\n".join(lines)
