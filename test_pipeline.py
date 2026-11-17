"""
اختبار سريع للمنطق (بدون نموذج ولا GPU) باستخدام نموذج وهمي يتصرف كأنه "مثالي".
python test_pipeline.py
"""
import json

from evaluate import compute_metrics, load_bank, run_eval
from pipeline import Assistant, validate_call

bank = load_bank("question_bank.csv")
BY_Q = {r["question"]: r for _, r in bank.iterrows()}


class FakeLLM:
    def chat(self, messages, tools=None, max_new_tokens=300):
        system, user = messages[0]["content"], messages[-1]["content"]
        if tools:
            r = BY_Q[user]
            if r["type"] in ("رقم", "تلخيص"):
                call = {"name": r["correct_tool"], "arguments": json.loads(r["correct_args"])}
            elif r["type"] == "يحتاج توضيح":
                call = {"name": "ask_clarification", "arguments": {"question": "تبغى لأي فترة؟", "options": ["آخر أسبوع", "آخر شهر"]}}
            else:
                call = {"name": "out_of_scope", "arguments": {}}
            return "<tool_call>\n" + json.dumps(call, ensure_ascii=False) + "\n</tool_call>"
        if "صنّف مشاعر" in system:
            return json.dumps(["إيجابي"] * user.count("\n") + ["سلبي"], ensure_ascii=False)
        if "محلل تجربة" in system:
            return '{"summary": "العملاء يمدحون سرعة الخدمة ويشتكون من الانتظار.", "topics": ["الانتظار", "التطبيق"]}'
        return "النتيجة: " + user.split("(JSON):\n", 1)[1]  # يعيد نتيجة الأداة حرفيًا


# 1) الدورة كاملة مع نموذج مثالي → لازم كل شي يطلع صح
df = run_eval(Assistant(FakeLLM()), bank)
m = compute_metrics(df)
print(json.dumps(m, ensure_ascii=False, indent=2))
assert m["نسبة اختيار الأداة الصحيحة %"] == 100 and m["نسبة المدخلات الصحيحة %"] == 100
assert m["نسبة التوضيح والرفض الصحيح %"] == 100 and m["عدد الأرقام المخترعة"] == 0

# 2) الكود يحرس القواعد: مدخل إجباري ناقص → توضيح، قيمة enum غلط تتصلح، أداة مو موجودة → رفض
assert validate_call("ratings_service_get", {"sort": "top"})["type"] == "reply"
assert validate_call("ratings_service_get", {"period": "آخر شهر"})["args"] == {"period": "month"}
assert validate_call("hack_database", {})["type"] == "reply"
print("كل الاختبارات نجحت ✅")
