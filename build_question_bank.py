"""يبني question_bank.csv (50 سؤال) — عدّلوا/زيدوا عليه ثم شغّلوه مرة ثانية، أو اشتغلوا على الـ CSV مباشرة."""
import json

import pandas as pd

N, S, C, O = "رقم", "تلخيص", "يحتاج توضيح", "برا النطاق"
BR, SV, RT, SU, DM, CM, OUT = "الفروع", "الخدمات", "التقييمات", "الاستبيانات", "التوزيع الديموغرافي", "التعليقات", "برا النطاق"

# (السؤال، النوع، الصفحة، الإجابة المتوقعة، الأداة الصحيحة، المدخلات الصحيحة)
Q = [
    ("كم فرع نشط؟", N, BR, "عدد الفروع النشطة", "branches_count", {"status": "active"}),
    ("كم عدد الفروع عندنا؟", N, BR, "إجمالي عدد الفروع", "branches_count", {}),
    ("كم فرع عندنا في جدة؟", N, BR, "عدد فروع جدة", "branches_count", {"city": "جدة"}),
    ("كم فرع غير نشط؟", N, BR, "عدد الفروع غير النشطة", "branches_count", {"status": "inactive"}),
    ("كم فرع عندنا في الرياض؟", N, BR, "عدد فروع الرياض", "branches_count", {"city": "الرياض"}),
    ("ما عدد الفروع النشطة في مدينة الدمام؟", N, BR, "عدد الفروع النشطة في الدمام", "branches_count", {"city": "الدمام", "status": "active"}),
    ("أعطني قائمة الفروع النشطة", N, BR, "أسماء الفروع النشطة", "branches_list", {"status": "active"}),
    ("وش الفروع اللي في الدمام؟", N, BR, "أسماء فروع الدمام", "branches_list", {"city": "الدمام"}),
    ("ما هي الخدمات المتوفرة في النظام؟", N, SV, "أسماء الخدمات", "services_list", {}),
    ("كم خدمة عندنا؟", N, SV, "عدد الخدمات", "services_list", {}),
    ("وش أعلى خدمة تقييمًا هالشهر؟", N, SV, "اسم الخدمة ومتوسط تقييمها", "ratings_service_get", {"period": "month", "sort": "top", "limit": 1}),
    ("ما هي أقل خدمة تقييمًا هذا الأسبوع؟", N, SV, "اسم الخدمة ومتوسط تقييمها", "ratings_service_get", {"period": "week", "sort": "bottom", "limit": 1}),
    ("وش تقييم الخدمات هالشهر؟", N, SV, "متوسط تقييم كل خدمة", "ratings_service_get", {"period": "month"}),
    ("كم تقييم خدمة البطاقات آخر 3 شهور؟", N, SV, "متوسط تقييم البطاقات", "ratings_service_get", {"period": "quarter", "service": "البطاقات"}),
    ("أفضل ثلاث خدمات من ناحية التقييم هذا الشهر", N, SV, "أعلى 3 خدمات", "ratings_service_get", {"period": "month", "sort": "top", "limit": 3}),
    ("وش متوسط تقييم التمويل الشخصي هالأسبوع؟", N, SV, "متوسط تقييم التمويل الشخصي", "ratings_service_get", {"period": "week", "service": "التمويل الشخصي"}),
    ("أي فرع أعلى تقييمًا هالشهر؟", N, RT, "اسم الفرع ومتوسط تقييمه", "ratings_branch_get", {"period": "month", "sort": "top", "limit": 1}),
    ("رتب لي الفروع حسب التقييم آخر أسبوع", N, RT, "الفروع مرتبة", "ratings_branch_get", {"period": "week", "sort": "top"}),
    ("وش أضعف فرع تقييمًا في الرياض هذا الشهر؟", N, RT, "اسم الفرع ومتوسطه", "ratings_branch_get", {"period": "month", "city": "الرياض", "sort": "bottom", "limit": 1}),
    ("ما هو أعلى فرع تقييمًا خلال الأسبوع الأخير؟", N, RT, "اسم الفرع ومتوسطه", "ratings_branch_get", {"period": "week", "sort": "top", "limit": 1}),
    ("كم متوسط التقييم العام آخر شهر؟", N, RT, "المتوسط العام", "ratings_overall", {"period": "month"}),
    ("وش تقييم فرع الحمراء هالشهر؟", N, RT, "متوسط تقييم الحمراء", "ratings_overall", {"period": "month", "branch": "الحمراء"}),
    ("كم المتوسط العام لخدمة الحوالات آخر 3 شهور؟", N, RT, "متوسط تقييم الحوالات", "ratings_overall", {"period": "quarter", "service": "الحوالات"}),
    ("كم استبيان جاءنا هذا الأسبوع؟", N, SU, "عدد الردود", "responses_count", {"period": "week"}),
    ("كم عدد الردود على الاستبيانات هالشهر؟", N, SU, "عدد الردود", "responses_count", {"period": "month"}),
    ("كم رد جانا على فرع العليا آخر شهر؟", N, SU, "عدد ردود العليا", "responses_count", {"period": "month", "branch": "العليا"}),
    ("كم عدد الردود على خدمة التطبيق الجوال آخر ثلاثة شهور؟", N, SU, "عدد الردود", "responses_count", {"period": "quarter", "service": "التطبيق الجوال"}),
    ("وش توزيع المستجيبين حسب الجنس؟", N, DM, "العدد والنسبة لكل جنس", "demographics_get", {"dimension": "gender"}),
    ("وزّع لي المستجيبين حسب الفئة العمرية هالشهر", N, DM, "توزيع الفئات العمرية", "demographics_get", {"dimension": "age_group", "period": "month"}),
    ("من أي مدن أغلب المستجيبين؟", N, DM, "توزيع المدن", "demographics_get", {"dimension": "city"}),
    ("كم نسبة الإناث بين المستجيبين آخر أسبوع؟", N, DM, "نسبة الإناث", "demographics_get", {"dimension": "gender", "period": "week"}),
    ("كيف تغير تقييم الخدمات خلال الشهور الماضية؟", N, RT, "المتوسط في الفترات الثلاث", "ratings_trend", {}),
    ("وش اتجاه تقييم فرع الروضة؟", N, RT, "اتجاه تقييم الروضة", "ratings_trend", {"branch": "الروضة"}),
    ("هل تحسن تقييم خدمة فتح حساب؟", N, RT, "اتجاه تقييم فتح حساب", "ratings_trend", {"service": "فتح حساب"}),
    ("لخّص لي تعليقات آخر أسبوع", S, CM, "ملخص + نسب المشاعر", "comments_get", {"period": "week"}),
    ("لخص التعليقات آخر شهر", S, CM, "ملخص + نسب المشاعر", "comments_get", {"period": "month"}),
    ("وش يقول العملاء عن فرع الحمراء هالشهر؟", S, CM, "ملخص تعليقات الحمراء", "comments_get", {"period": "month", "branch": "الحمراء"}),
    ("ما أبرز الشكاوى في التعليقات خلال الأسبوع الماضي؟", S, CM, "أبرز الشكاوى", "comments_get", {"period": "week"}),
    ("هل التعليقات إيجابية بشكل عام آخر 3 شهور؟", S, CM, "نسب المشاعر", "comments_get", {"period": "quarter"}),
    ("لخص لي آراء العملاء عن فرع الكورنيش آخر شهر", S, CM, "ملخص تعليقات الكورنيش", "comments_get", {"period": "month", "branch": "الكورنيش"}),
    ("وش أبرز مواضيع التعليقات هذا الشهر؟", S, CM, "أبرز المواضيع", "comments_get", {"period": "month"}),
    ("حلل مشاعر التعليقات الأسبوع الماضي", S, CM, "نسب المشاعر", "comments_get", {"period": "week"}),
    ("لخص لي آخر التعليقات", C, CM, "يسأل: آخر أسبوع ولا آخر شهر؟", "", {}),
    ("وش تقييم الخدمات؟", C, SV, "يسأل عن الفترة", "", {}),
    ("كم رد جانا؟", C, SU, "يسأل عن الفترة", "", {}),
    ("وش أعلى فرع تقييمًا؟", C, RT, "يسأل عن الفترة", "", {}),
    ("وش تقييم فرع العليا؟", C, RT, "يسأل عن الفترة", "", {}),
    ("وش أحوال الطقس اليوم؟", O, OUT, "يعتذر بلطف ويوضح وش يقدر يجاوب", "", {}),
    ("اكتب لي قصيدة عن الصيف", O, OUT, "يعتذر بلطف ويوضح وش يقدر يجاوب", "", {}),
    ("كم سعر الدولار اليوم؟", O, OUT, "يعتذر بلطف ويوضح وش يقدر يجاوب", "", {}),
]
assert len(Q) == 50, len(Q)
df = pd.DataFrame([(i + 1, q, t, p, a, tool, json.dumps(args, ensure_ascii=False)) for i, (q, t, p, a, tool, args) in enumerate(Q)],
                  columns=["id", "question", "type", "page", "expected_answer", "correct_tool", "correct_args"])
df.to_csv("question_bank.csv", index=False, encoding="utf-8-sig")  # utf-8-sig عشان Excel يقرا العربي
print(df["type"].value_counts().to_string())
