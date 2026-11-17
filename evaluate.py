"""
التقييم على بنك الأسئلة كامل.
python evaluate.py --model Qwen/Qwen2.5-7B-Instruct --out results
يطلع: results.csv (كل سؤال) ، metrics.json (المقاييس) ، errors.csv (الحالات الغلط ونوع الخطأ)
"""
import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd

from tool_impl import execute_tool
from utils import invented_numbers, norm_ar, numbers_in

TOOL_TYPES = ("رقم", "تلخيص")
NUM_WORDS = {0: ["صفر", "لا يوجد", "لا توجد", "ما فيه", "ما في"], 1: ["واحد"], 2: ["اثن", "فرعين", "خدمتين", "ردين"],
             3: ["ثلاث"], 4: ["أربع", "اربع"], 5: ["خمس"], 6: ["ست"], 7: ["سبع"], 8: ["ثمان"], 9: ["تسع"], 10: ["عشر"]}

# الحقائق الأساسية اللي لازم تظهر في الجواب (فحص آلي تقريبي — راجعوا الأخطاء يدويًا)
KEY_FACTS = {
    "branches_count": lambda r: [r["count"]],
    "branches_list": lambda r: [b["name"] for b in r["branches"]],
    "services_list": lambda r: [r["count"]],
    "ratings_service_get": lambda r: [r[0]["service"], r[0]["avg"]],
    "ratings_branch_get": lambda r: [r[0]["branch"], r[0]["avg"]],
    "ratings_overall": lambda r: [r["avg"]],
    "responses_count": lambda r: [r["count"]],
    "demographics_get": lambda r: [r["distribution"][0]["pct"]],
    "ratings_trend": lambda r: [r[0]["avg"]],
    "comments_get": lambda r: [],
}


def _plain(s):
    return re.sub(r"\bفرع\s+", "", norm_ar(s))


def _present(fact, answer):
    if isinstance(fact, float):
        return any(abs(n - fact) < 1e-9 for n in numbers_in(answer))
    if isinstance(fact, int):
        return float(fact) in numbers_in(answer) or any(w in _plain(answer) for w in NUM_WORDS.get(fact, []))
    return _plain(fact) in _plain(answer)


def _norm_args(a):
    out = {}
    for k, v in (a or {}).items():
        if v in (None, ""):
            continue
        out[k] = v if isinstance(v, int) else norm_ar(v)
    return out


def run_eval(assistant, bank, compose=True):
    rows = []
    for _, r in bank.iterrows():
        t0 = time.time()
        resp = assistant.select_tool(r["question"], [])
        exp_args = json.loads(r["correct_args"]) if r["correct_args"] else {}
        row = dict(id=r["id"], question=r["question"], type=r["type"], expected_tool=r["correct_tool"],
                   expected_args=json.dumps(exp_args, ensure_ascii=False), got_type=resp["type"],
                   got_tool=resp.get("tool", ""), got_args=json.dumps(resp.get("args", {}), ensure_ascii=False),
                   tool_ok=None, args_ok=None, behavior_ok=None, final_ok=None, invented=0, answer="", error_type="")
        if r["type"] in TOOL_TYPES:
            tool_ok = resp["type"] == "tool" and resp["tool"] == r["correct_tool"]
            args_ok = tool_ok and _norm_args(resp["args"]) == _norm_args(exp_args)
            row.update(tool_ok=tool_ok, args_ok=args_ok)
            if not tool_ok:
                row["error_type"] = "رد/وضّح بدل ما يختار أداة" if resp["type"] == "reply" else "أداة غلط"
            elif not args_ok:
                row["error_type"] = "مدخلات غلط"
            if compose and tool_ok:
                result = execute_tool(resp["tool"], resp["args"])
                row["answer"] = assistant.compose_answer(r["question"], resp["tool"], result)["text"]
                if r["type"] == "رقم":
                    inv = invented_numbers(row["answer"], result, r["question"])
                    row["invented"] = len(inv)
                    try:
                        facts = KEY_FACTS[r["correct_tool"]](result)
                    except (KeyError, IndexError, TypeError):
                        facts = []
                    ok = args_ok and not inv and all(_present(f, row["answer"]) for f in facts)
                    if args_ok and not ok:
                        row["error_type"] = "رقم مخترع" if inv else "جواب ناقص/غلط"
                else:
                    ok = args_ok and "%" in row["answer"]
                    if args_ok and not ok:
                        row["error_type"] = "تلخيص ناقص"
                row["final_ok"] = bool(ok)
            elif compose:
                row["final_ok"] = False
        else:
            if r["type"] == "يحتاج توضيح":
                ok = resp["type"] == "reply" and bool(resp.get("options"))
                err = "ما سأل توضيح"
            else:
                ok = resp["type"] == "reply" and not resp.get("options")
                err = "ما رفض السؤال"
            row.update(behavior_ok=ok, final_ok=ok if compose else None, error_type="" if ok else err)
        row["latency_s"] = round(time.time() - t0, 2)
        rows.append(row)
        print(f'[{r["id"]:>2}] {"OK " if not row["error_type"] else "ERR"} {r["question"]}')
    return pd.DataFrame(rows)


def compute_metrics(df, compose=True):
    tq = df[df["type"].isin(TOOL_TYPES)]
    oq = df[~df["type"].isin(TOOL_TYPES)]
    pct = lambda s: round(100 * float(s.astype(float).mean()), 1) if len(s) else None
    m = {"عدد الأسئلة": len(df),
         "نسبة اختيار الأداة الصحيحة %": pct(tq["tool_ok"]),
         "نسبة المدخلات الصحيحة %": pct(tq["args_ok"]),
         "نسبة التوضيح والرفض الصحيح %": pct(oq["behavior_ok"]),
         "متوسط زمن الاستجابة (ثانية)": round(float(df["latency_s"].mean()), 2)}
    if compose:
        m["نسبة الجواب النهائي الصحيح %"] = pct(df["final_ok"])
        m["عدد الأرقام المخترعة"] = int(df["invented"].sum())
    return m


def load_bank(path):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    ap.add_argument("--bank", default="question_bank.csv")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()

    from model import LLM
    from pipeline import Assistant

    out = Path(a.out)
    out.mkdir(exist_ok=True)
    df = run_eval(Assistant(LLM(a.model)), load_bank(a.bank))
    df.to_csv(out / "results.csv", index=False, encoding="utf-8-sig")
    df[df["error_type"] != ""].to_csv(out / "errors.csv", index=False, encoding="utf-8-sig")
    metrics = compute_metrics(df)
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
