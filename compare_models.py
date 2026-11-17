"""
مرحلة 3: مقارنة 3 نماذج على نفس بنك الأسئلة ونفس الأدوات ونفس البرومبت.
python compare_models.py --models Qwen/Qwen2.5-7B-Instruct Qwen/Qwen3-8B meta-llama/Llama-3.1-8B-Instruct
(تأكدوا إن كل نموذج يدعم Tool Calling في الـ chat template ويفهم عربي. Llama يحتاج موافقة على الترخيص.)
"""
import argparse
import gc
import json
from pathlib import Path

import pandas as pd
import torch

from evaluate import compute_metrics, load_bank, run_eval
from model import LLM
from pipeline import Assistant

ap = argparse.ArgumentParser()
ap.add_argument("--models", nargs=3, required=True)
ap.add_argument("--bank", default="question_bank.csv")
ap.add_argument("--out", default="model_comparison")
a = ap.parse_args()
out = Path(a.out)
out.mkdir(exist_ok=True)
bank = load_bank(a.bank)

table = {}
for mid in a.models:
    llm = LLM(mid)
    df = run_eval(Assistant(llm), bank, compose=True)
    m = compute_metrics(df)
    gpu = round(torch.cuda.max_memory_allocated() / 1024 ** 3, 1) if torch.cuda.is_available() else None
    table[mid] = {"نسبة اختيار الأداة الصحيحة %": m["نسبة اختيار الأداة الصحيحة %"],
                  "نسبة المدخلات الصحيحة %": m["نسبة المدخلات الصحيحة %"],
                  "جودة العربي وفهم اللهجة (1–5)": "قيّموها يدويًا من ملف sample_answers",
                  "متوسط زمن الاستجابة (ثانية)": m["متوسط زمن الاستجابة (ثانية)"],
                  "ذاكرة GPU القصوى (GB)": gpu}
    tag = mid.replace("/", "_")
    df[df["answer"] != ""].head(15)[["question", "answer"]].to_csv(out / f"sample_answers_{tag}.csv", index=False, encoding="utf-8-sig")
    df.to_csv(out / f"results_{tag}.csv", index=False, encoding="utf-8-sig")
    del llm
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

res = pd.DataFrame(table)
res.to_csv(out / "comparison.csv", encoding="utf-8-sig")
print(res.to_string())
