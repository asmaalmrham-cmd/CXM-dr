"""
تقدير أثر الحراس بدون نموذج: نعيد تمرير مخرجات النماذج المحفوظة (got_tool / got_args) على الحراس الجديدة.
هذا تقدير فقط، الأرقام الرسمية تجي من إعادة evaluate.py على النموذج.
python replay_guards.py results_4b.csv
"""
import json
import sys

import pandas as pd

from evaluate import _norm_args, load_bank
from pipeline import validate_call
from tool_impl import catalog

bank = load_bank("question_bank.csv")
CAT = catalog()


def replay(path):
    df = pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False)
    tool_ok = args_ok = beh_ok = n_tool = n_beh = 0
    changed = []
    for _, r in df.iterrows():
        q = r["question"]
        got_type, got_tool = r["got_type"], r["got_tool"]
        got_args = json.loads(r["got_args"]) if r["got_args"] else {}
        exp = json.loads(r["expected_args"]) if r["expected_args"] else {}
        if got_type == "tool":
            new = validate_call(got_tool, got_args, question=q, catalog=CAT)
        else:
            new = {"type": "reply", "options": ["x"] if r["type"] == "يحتاج توضيح" else []}
        if r["type"] in ("رقم", "تلخيص"):
            n_tool += 1
            t = new["type"] == "tool" and new["tool"] == r["expected_tool"]
            a = t and _norm_args(new["args"]) == _norm_args(exp)
            tool_ok += t
            args_ok += a
            if bool(r["args_ok"] in (True, "True")) != a:
                changed.append((r["id"], q, "args", bool(r["args_ok"] in (True, "True")), a))
        else:
            n_beh += 1
            ok = new["type"] == "reply" and (bool(new.get("options")) if r["type"] == "يحتاج توضيح" else not new.get("options"))
            beh_ok += ok
            if bool(r["behavior_ok"] in (True, "True")) != ok:
                changed.append((r["id"], q, "behavior", bool(r["behavior_ok"] in (True, "True")), ok))
    return dict(tool=round(100 * tool_ok / n_tool, 1), args=round(100 * args_ok / n_tool, 1),
                behavior=round(100 * beh_ok / n_beh, 1)), changed


if __name__ == "__main__":
    m, ch = replay(sys.argv[1])
    print(m)
    for c in ch:
        print(c)
