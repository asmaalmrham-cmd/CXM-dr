import os
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"

# "اليوم" في البيانات الوهمية (ثابت عشان النتائج تتكرر). في الإنتاج الباك هو اللي يحسب التواريخ.
REF_DATE = date.today() if os.getenv("CXM_USE_TODAY") == "1" else date(2026, 11, 1)

PERIOD_DAYS = {"week": 7, "month": 30, "quarter": 90}
PERIOD_LABELS = {"week": "آخر أسبوع", "month": "آخر شهر", "quarter": "آخر 3 شهور"}
LABEL_TO_PERIOD = {v: k for k, v in PERIOD_LABELS.items()}

DEFAULT_MODEL = os.getenv("MODEL_ID", "Qwen/Qwen2.5-7B-Instruct")
