import json

from config import LABEL_TO_PERIOD, PERIOD_LABELS
from prompts import (COMPOSE_STRICT_SUFFIX, COMPOSE_SYSTEM, NO_DATA_TEXT, OUT_OF_SCOPE_TEXT,
                     build_select_prompt)
from guards import fix_names, has_period_words, sanitize_args
from summarize import summarize_comments
from tool_impl import catalog as default_catalog, execute_tool
from tools_spec import META_TOOLS, TOOL_BY_NAME, TOOLS
from utils import invented_numbers, parse_tool_call


def _guess_period(v):
    v = str(v).strip()
    if v in LABEL_TO_PERIOD:
        return LABEL_TO_PERIOD[v]
    if any(k in v for k in ("3", "٣", "ثلاث", "ربع")):
        return "quarter"
    if "اسبوع" in v or "أسبوع" in v:
        return "week"
    if "شهر" in v:
        return "month"
    return None


def _coerce_enum(key, value, allowed):
    if value in allowed:
        return value
    if key == "period":
        return _guess_period(value)
    v = str(value).strip().lower()
    return v if v in allowed else None


def _clarification_for(param):
    if param == "period":
        return {"type": "reply", "text": "تبغى النتيجة لأي فترة؟", "options": list(PERIOD_LABELS.values())}
    if param == "dimension":
        return {"type": "reply", "text": "تبغى التوزيع حسب إيش؟", "options": ["العمر", "الجنس", "المدينة"]}
    return {"type": "reply", "text": "ممكن توضح أكثر قصدك إيش بالضبط؟", "options": []}


def validate_call(name, args, question=None, catalog=None):
    """يتحقق من اختيار النموذج: أداة موجودة؟ مدخلات صحيحة؟ ناقص مدخل إجباري؟ (الكود مو النموذج يحرس القواعد).
    question (اختياري): نص السؤال + رسائل المستخدم السابقة، يفعّل حراس الفترة والمدخلات الاختيارية وتصحيح الأسماء."""
    spec = TOOL_BY_NAME.get(name)
    if spec is None:
        return {"type": "reply", "text": OUT_OF_SCOPE_TEXT, "options": []}
    params = spec["function"]["parameters"]
    clean = {}
    for k, v in (args or {}).items():
        p = params["properties"].get(k)
        if p is None or v in (None, "", []):
            continue
        if "enum" in p:
            v = _coerce_enum(k, v, p["enum"])
            if v is None:
                continue
        elif p["type"] == "integer":
            try:
                v = int(v)
            except (TypeError, ValueError):
                continue
        else:
            v = str(v).strip()
        clean[k] = v
    if question is not None:
        clean = sanitize_args(name, fix_names(clean, catalog), question)
        # الفترة إجبارية والمستخدم ما ذكرها: نسأل بدل ما نقبل تخمين النموذج
        if "period" in params["required"] and not has_period_words(question):
            return _clarification_for("period")
    for req in params["required"]:
        if req not in clean:
            return _clarification_for(req)
    return {"type": "tool", "tool": name, "args": clean}


class Assistant:
    def __init__(self, llm, catalog=None):
        self.llm = llm
        self.catalog = catalog or default_catalog()

    # ------------- الطلب 1: اختيار الأداة -------------
    def select_tool(self, question, history=None):
        msgs = [{"role": "system", "content": build_select_prompt(self.catalog)}]
        for m in (history or [])[-6:]:
            if m.get("role") in ("user", "assistant") and m.get("content"):
                msgs.append({"role": m["role"], "content": str(m["content"])})
        msgs.append({"role": "user", "content": question})

        raw = self.llm.chat(msgs, tools=TOOLS + META_TOOLS, max_new_tokens=300)
        call = parse_tool_call(raw)
        if call is None:  # ما نمرر كلام النموذج الحر أبدًا: ممكن يكون جواب مخترع
            return {"type": "reply", "text": OUT_OF_SCOPE_TEXT, "options": []}
        name, args = call
        if name == "out_of_scope":
            return {"type": "reply", "text": OUT_OF_SCOPE_TEXT, "options": []}
        if name == "ask_clarification":
            opts = args.get("options") if isinstance(args.get("options"), list) else []
            return {"type": "reply", "text": str(args.get("question") or "ممكن توضح أكثر؟"),
                    "options": [str(o) for o in opts]}
        context = " ".join([m.get("content", "") for m in (history or [])[-6:] if m.get("role") == "user"] + [question])
        return validate_call(name, args, question=context, catalog=self.catalog)

    # ------------- الطلب 2: صياغة الجواب -------------
    def _compose(self, question, tool, result, strict=False):
        user = (f"سؤال المستخدم: {question}\nالأداة: {tool}\n"
                f"نتيجة الأداة (JSON):\n{json.dumps(result, ensure_ascii=False)}")
        system = COMPOSE_SYSTEM + (COMPOSE_STRICT_SUFFIX if strict else "")
        return self.llm.chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                             max_new_tokens=250)

    def compose_answer(self, question, tool, result):
        if isinstance(result, dict) and "error" in result:
            return {"text": NO_DATA_TEXT}
        if tool == "comments_get":
            return {"text": summarize_comments(self.llm, question, result)}
        text = self._compose(question, tool, result)
        if invented_numbers(text, result, question):
            text = self._compose(question, tool, result, strict=True)
            if invented_numbers(text, result, question):  # آخر حل: ما نسمح برقم مخترع يوصل للمستخدم
                text = "النتيجة: " + json.dumps(result, ensure_ascii=False)
        return {"text": text}

    # ------------- الدورة كاملة (للاختبار فقط: الباك الحقيقي ينفذ الأداة) -------------
    def run(self, question, history=None):
        sel = self.select_tool(question, history)
        if sel["type"] == "reply":
            return sel
        result = execute_tool(sel["tool"], sel["args"])
        return {"type": "answer", "text": self.compose_answer(question, sel["tool"], result)["text"],
                "tool": sel["tool"], "args": sel["args"], "result": result}
