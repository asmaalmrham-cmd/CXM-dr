"""يولّد البيانات الوهمية في مجلد data/  —  python generate_data.py"""
import random
from datetime import timedelta

import numpy as np
import pandas as pd

from config import DATA_DIR, REF_DATE

random.seed(42)
np.random.seed(42)
DATA_DIR.mkdir(exist_ok=True)

# (id, الاسم, المدينة, نشط؟, انحياز التقييم)
BRANCHES = [
    (1, "فرع الحمراء", "جدة", True, 0.2),
    (2, "فرع الروضة", "جدة", True, -0.1),
    (3, "فرع العليا", "الرياض", True, 0.3),
    (4, "فرع النخيل", "الرياض", False, -0.4),
    (5, "فرع الكورنيش", "الدمام", True, 0.0),
]
SERVICES = [
    (1, "فتح حساب", 0.2), (2, "التمويل الشخصي", -0.2), (3, "البطاقات", 0.0),
    (4, "الحوالات", 0.3), (5, "خدمة العملاء الهاتفية", -0.4), (6, "التطبيق الجوال", 0.1),
]

pd.DataFrame([(i, n, c, "active" if a else "inactive") for i, n, c, a, _ in BRANCHES],
             columns=["id", "name", "city", "status"]).to_csv(DATA_DIR / "branches.csv", index=False, encoding="utf-8-sig")
pd.DataFrame([(i, n) for i, n, _ in SERVICES], columns=["id", "name"]).to_csv(
    DATA_DIR / "services.csv", index=False, encoding="utf-8-sig")

# ---- ردود الاستبيانات (تقييم + بيانات المستجيب) لـ 90 يوم ----
rows = []
for i in range(1, 901):
    days_ago = random.randint(0, 89)
    eligible = [b for b in BRANCHES if b[3] or days_ago > 45]  # الفرع غير النشط له بيانات قديمة فقط
    b = random.choice(eligible)
    s = random.choice(SERVICES)
    trend = 0.25 * (1 - days_ago / 90)  # تحسن بسيط مع الوقت
    rating = int(np.clip(round(np.random.normal(3.9 + b[4] + s[2] + trend, 0.9)), 1, 5))
    rows.append(dict(
        id=i, date=(REF_DATE - timedelta(days=days_ago)).isoformat(), branch_id=b[0], service_id=s[0],
        rating=rating, age=int(np.clip(np.random.normal(35, 12), 18, 70)),
        gender=random.choices(["ذكر", "أنثى"], [55, 45])[0],
        respondent_city=random.choices(["جدة", "الرياض", "الدمام", "مكة", "المدينة"], [30, 30, 20, 10, 10])[0]))
pd.DataFrame(rows).to_csv(DATA_DIR / "responses.csv", index=False, encoding="utf-8-sig")

# ---- 100 تعليق: فصحى ولهجة، إيجابي / سلبي / محايد ----
T = {
    "إيجابي": {
        "فصحى": ["الخدمة ممتازة والموظفون متعاونون جدًا", "سرعة الإنجاز رائعة والتعامل راقٍ",
                 "تجربة مميزة وأنصح بها الجميع", "الفرع نظيف ومنظم والخدمة سريعة",
                 "شكرًا لكم على الاحترافية العالية في التعامل", "التطبيق سهل الاستخدام وسريع الاستجابة"],
        "لهجة": ["الخدمة ممتازة والموظفين متعاونين مرة", "شغلكم تمام وسريعين في الإنجاز",
                 "والله تعامل راقي وما توقعته كذا", "الفرع نظيف وكل شي واضح، يعطيكم العافية",
                 "التطبيق سهل وسريع ما شاء الله", "الموظف ساعدني وشرح لي كل شي بالتفصيل"]},
    "سلبي": {
        "فصحى": ["مدة الانتظار طويلة جدًا ولم يهتم بي أحد", "الخدمة بطيئة والموظفون غير متعاونين",
                 "واجهت مشكلة في التطبيق ولم تُحل حتى الآن", "الرسوم غير واضحة ولم تُشرح لي",
                 "تجربة سيئة ولن أكررها", "الاتصال بخدمة العملاء لا يُجاب عليه"],
        "لهجة": ["الانتظار طويل مرة وما فيه أحد يرد", "الخدمة بطيئة وما حد اهتم فيني",
                 "التطبيق يعلق كل شوي ومشكلتي ما انحلت", "الرسوم مو واضحة وما شرحوا لي شي",
                 "تجربة سيئة وما أنصح فيها", "اتصلت على خدمة العملاء وما حد رد علي"]},
    "محايد": {
        "فصحى": ["قمت بزيارة الفرع لإنهاء معاملة عادية", "الخدمة مقبولة ولا يوجد ما يستحق الذكر",
                 "استغرقت المعاملة وقتًا متوسطًا", "تم إنجاز الطلب كما هو متوقع"],
        "لهجة": ["الخدمة عادية مو سيئة ولا ممتازة", "جيت أنهي معاملة وخلصت عادي",
                 "وقت الانتظار متوسط", "كل شي ماشي عادي"]},
}
comments = []
for i in range(1, 101):
    sent = random.choices(list(T), [40, 35, 25])[0]
    style = random.choice(["فصحى", "لهجة"])
    comments.append(dict(id=i, date=(REF_DATE - timedelta(days=random.randint(0, 89))).isoformat(),
                         branch_id=random.choice([b[0] for b in BRANCHES]),
                         text=random.choice(T[sent][style]), sentiment_true=sent))
pd.DataFrame(comments).to_csv(DATA_DIR / "comments.csv", index=False, encoding="utf-8-sig")
print("done: branches, services, responses (900), comments (100) ->", DATA_DIR)
