import json
import re

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")


def norm_ar(s) -> str:
    """توحيد الحروف العربية للمقارنة (أ/إ/آ، ة/ه، ى/ي) + إزالة التشكيل."""
    s = str(s).strip().lower()
    s = re.sub(r"[\u064B-\u0652\u0640]", "", s)
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ة", "ه"), ("ى", "ي")):
        s = s.replace(a, b)
    return s


def numbers_in(text) -> set:
    text = str(text).translate(AR_DIGITS)
    return {float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)}


def invented_numbers(answer, result, question="") -> list:
    """أرقام موجودة في الجواب وليست في نتيجة الأداة (ولا في السؤال). القاعدة رقم 1 في المشروع."""
    allowed = numbers_in(json.dumps(result, ensure_ascii=False)) | numbers_in(question)
    return sorted(n for n in numbers_in(answer) if n not in allowed)


def parse_tool_call(text):
    """يستخرج (name, args) من مخرجات النموذج. يدعم صيغة Qwen (<tool_call>) وصيغة JSON المجرد (Llama)."""
    cands = re.findall(r"<tool_call>\s*(.*?)\s*(?:</tool_call>|$)", text, re.S)
    if not cands:
        m = re.search(r"\{.*\}", text, re.S)
        cands = [m.group(0)] if m else []
    for c in cands:
        try:
            obj = json.loads(c)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or not obj.get("name"):
            continue
        args = obj.get("arguments", obj.get("parameters", {}))
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        return obj["name"], (args if isinstance(args, dict) else {})
    return None
