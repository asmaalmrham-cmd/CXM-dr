"""
مواصفات الأدوات — هذا الملف هو "العقد" بينكم وبين فريق الباك.
أي تغيير بعد الاعتماد لازم ينبلغ فيه الفريق (قاعدة 4).
للتصدير:  python tools_spec.py   ← يطلع tools_spec.json
"""
import json
from pathlib import Path


def _tool(name, description, properties=None, required=None):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties or {}, "required": required or []}}}


PERIOD = {"type": "string", "enum": ["week", "month", "quarter"],
          "description": "الفترة: week = آخر 7 أيام، month = آخر 30 يوم، quarter = آخر 3 شهور"}
SORT = {"type": "string", "enum": ["top", "bottom"],
        "description": "top = الأعلى تقييمًا أولًا، bottom = الأقل تقييمًا أولًا"}
LIMIT = {"type": "integer", "description": "عدد النتائج المطلوب (1 لأعلى/أقل واحد، 3 لأفضل ثلاثة...)"}
CITY = {"type": "string", "description": "اسم المدينة بالعربي مثل: جدة، الرياض، الدمام"}
BRANCH = {"type": "string", "description": "اسم الفرع بالعربي بدون كلمة (فرع) مثل: الحمراء"}
SERVICE = {"type": "string", "description": "اسم الخدمة بالعربي كما هو في النظام"}
STATUS = {"type": "string", "enum": ["active", "inactive"], "description": "active = نشط، inactive = غير نشط"}

TOOLS = [
    _tool("branches_count",
          "تحسب عدد الفروع. يمكن تحديد المدينة أو الحالة (نشط/غير نشط). للأسئلة من نوع: كم فرع؟",
          {"city": CITY, "status": STATUS}),
    _tool("branches_list",
          "ترجع قائمة الفروع بأسمائها ومدنها وحالتها. للأسئلة من نوع: وش الفروع؟ أعطني قائمة الفروع.",
          {"city": CITY, "status": STATUS}),
    _tool("services_list",
          "ترجع قائمة الخدمات المتوفرة في النظام وعددها. للأسئلة من نوع: وش الخدمات؟ كم خدمة عندنا؟"),
    _tool("ratings_service_get",
          "ترجع متوسط تقييم كل خدمة خلال فترة، ويمكن ترتيبها (الأعلى/الأقل) أو تحديد خدمة وحدة. "
          "للأسئلة عن تقييم الخدمات أو تقييم خدمة معينة (مثل: كم تقييم خدمة البطاقات؟) وأعلى/أقل خدمة تقييمًا.",
          {"period": PERIOD, "service": SERVICE, "sort": SORT, "limit": LIMIT}, ["period"]),
    _tool("ratings_branch_get",
          "ترجع متوسط تقييم كل فرع خلال فترة، ويمكن ترتيبها أو تحديد مدينة. "
          "للأسئلة عن أعلى/أقل فرع تقييمًا وترتيب الفروع.",
          {"period": PERIOD, "city": CITY, "sort": SORT, "limit": LIMIT}, ["period"]),
    _tool("ratings_overall",
          "ترجع متوسط التقييم العام (رقم واحد) خلال فترة، ويمكن حصره بفرع معين أو خدمة معينة. "
          "تُستخدم فقط لما السؤال يطلب (المتوسط العام) أو تقييم فرع معين: كم متوسط التقييم العام؟ وش تقييم فرع كذا؟ "
          "لا تُستخدم لسؤال عن تقييم خدمة (للخدمات استخدم ratings_service_get).",
          {"period": PERIOD, "branch": BRANCH, "service": SERVICE}, ["period"]),
    _tool("responses_count",
          "تحسب عدد ردود الاستبيانات خلال فترة، ويمكن حصرها بفرع أو خدمة. للأسئلة عن عدد الاستبيانات/الردود.",
          {"period": PERIOD, "branch": BRANCH, "service": SERVICE}, ["period"]),
    _tool("demographics_get",
          "ترجع التوزيع الديموغرافي للمستجيبين (العدد والنسبة) حسب العمر أو الجنس أو المدينة، ويمكن تحديد فترة.",
          {"dimension": {"type": "string", "enum": ["age_group", "gender", "city"],
                         "description": "age_group = الفئة العمرية، gender = الجنس، city = المدينة"},
           "period": PERIOD}, ["dimension"]),
    _tool("ratings_trend",
          "ترجع تغير متوسط التقييم عبر آخر 3 شهور (3 فترات)، ويمكن حصرها بخدمة أو فرع. "
          "للأسئلة عن التحسن أو التراجع أو الاتجاه.",
          {"service": SERVICE, "branch": BRANCH}),
    _tool("comments_get",
          "ترجع نصوص تعليقات العملاء خلال فترة، ويمكن حصرها بفرع. تُستخدم لتلخيص التعليقات وتحليل المشاعر "
          "وأبرز الشكاوى والمواضيع.",
          {"period": PERIOD, "branch": BRANCH,
           "limit": {"type": "integer", "description": "أقصى عدد تعليقات (افتراضي 100)"}}, ["period"]),
]

# أدوات "وهمية" يستخدمها النموذج للتوضيح والرفض، والكود هو اللي يعالجها (مو الباك).
META_TOOLS = [
    _tool("ask_clarification",
          "تُستدعى لما السؤال ناقص مدخل أساسي (مثل الفترة الزمنية) بدل التخمين. "
          "اكتب سؤال توضيح قصير بالعربي مع خيارات.",
          {"question": {"type": "string", "description": "سؤال التوضيح للمستخدم"},
           "options": {"type": "array", "items": {"type": "string"}, "description": "خيارات الإجابة"}},
          ["question"]),
    _tool("out_of_scope",
          "تُستدعى لما السؤال ما له علاقة ببيانات نظام CXM (طقس، أخبار، شعر، أسعار...).",
          {"reason": {"type": "string", "description": "سبب مختصر"}}),
]

TOOL_BY_NAME = {t["function"]["name"]: t for t in TOOLS}

if __name__ == "__main__":
    out = Path(__file__).parent / "tools_spec.json"
    out.write_text(json.dumps(TOOLS, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(TOOLS)} tools)")
