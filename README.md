---
title: CXM Assistant API
emoji: 🤖
sdk: gradio
app_file: app.py
---

# مساعد CXM الذكي (Tool Calling)

## 1. نظرة عامة
شات ذكي بالعربي يجاوب عن بيانات CXM (الفروع، الخدمات، التقييمات، الاستبيانات، التوزيع الديموغرافي، التعليقات).
النموذج **ما يحسب ولا يشوف البيانات**: يفهم السؤال ويختار أداة، الباك ينفذها، والنموذج يصيغ الجواب من النتيجة فقط.

```
المستخدم → POST /select_tool → {tool,args} → الباك ينفذ الأداة → POST /compose_answer → الجواب
```

## 2. النموذج المستخدم
`Qwen/Qwen3-4B-Instruct-2507` (يتغير بمتغير البيئة `MODEL_ID`).

سبب الاختيار (التفاصيل في [وثيقة القرار](docs/model_decision.md)):
- أفضل دقة في تصنيف المشاعر: 94% مقابل 80% لـ Qwen3-8B.
- نفس اختيار الأداة (97.6%) ونفس الجواب النهائي (66%) كـ Qwen3-8B، بذاكرة أقل (5.0 GB مقابل 8.4 GB).
- Qwen2.5-7B استُبعد: الأداة 92.9% والمدخلات 57.1% والجواب النهائي 46%.

رابط الـ Space: (يُضاف بعد الرفع)
## 3. هيكل الملفات
| الملف | وظيفته |
|---|---|
| `app.py` | الـ API (FastAPI): `/select_tool` و `/compose_answer` و `/health` + صفحة تجربة `/demo` |
| `pipeline.py` | منطق اختيار الأداة والتحقق من المدخلات والتوضيح والرفض وصياغة الجواب وفحص الأرقام المخترعة |
| `prompts.py` | كل البرومبتات |
| `summarize.py` | تلخيص التعليقات: النموذج يصنف ويلخص، **والكود يحسب النسب** |
| `tools_spec.py` / `tools_spec.json` | مواصفات الأدوات (العقد مع الباك) |
| `tool_impl.py` | تنفيذ الأدوات على البيانات الوهمية (للاختبار فقط) |
| `generate_data.py` / `data/` | البيانات الوهمية (5 فروع، 6 خدمات، 900 رد، 100 تعليق) |
| `build_question_bank.py` / `question_bank.csv` | بنك الأسئلة (50 سؤال) |
| `model.py` | تحميل النموذج |
| `evaluate.py` | التقييم على بنك الأسئلة |
| `compare_models.py` | مقارنة 3 نماذج (مرحلة 3) |
| `test_pipeline.py` | اختبار المنطق بدون GPU |
| `demo.py` | تجربة من الطرفية |

## 4. طريقة التشغيل
```bash
pip install -r requirements.txt
python generate_data.py            # البيانات الوهمية
python build_question_bank.py      # بنك الأسئلة
python tools_spec.py               # تصدير tools_spec.json
python test_pipeline.py            # اختبار المنطق (بدون نموذج)
python demo.py "كم فرع عندنا في جدة؟"
python evaluate.py --model Qwen/Qwen2.5-7B-Instruct --out results
python compare_models.py --models <نموذج1> <نموذج2> <نموذج3>
python app.py                      # يشغل الـ API على المنفذ 7860
```
GPU صغير؟ جربوا `MODEL_ID=Qwen/Qwen2.5-3B-Instruct` أو `LOAD_4BIT=1`.

## 5. قائمة الأدوات (للباك)
المخرجات بالتفصيل في `tool_impl.py`. الحقل `period` قيمه: `week` (7 أيام) / `month` (30) / `quarter` (90).

| الأداة | المدخلات (* إجباري) | المخرج |
|---|---|---|
| `branches_count` | city, status(active/inactive) | `{"count": 2}` |
| `branches_list` | city, status | `{"count":4,"branches":[{"name","city","status"}]}` |
| `services_list` | — | `{"count":6,"services":["..."]}` |
| `ratings_service_get` | period*, service, sort(top/bottom), limit | `[{"service","avg","responses"}]` |
| `ratings_branch_get` | period*, city, sort, limit | `[{"branch","avg","responses"}]` |
| `ratings_overall` | period*, branch, service | `{"avg":4.41,"responses":63}` |
| `responses_count` | period*, branch, service | `{"count":63}` |
| `demographics_get` | dimension*(age_group/gender/city), period | `{"dimension","total","distribution":[{"group","count","pct"}]}` |
| `ratings_trend` | service, branch | `[{"window","avg","responses"}]` |
| `comments_get` | period*, branch, limit | `[{"text","date","branch"}]` |

عند عدم وجود بيانات يرجع الباك `{"error": "..."}`. **الأرقام والنسب كلها يحسبها الباك** (مثل `pct`)، لأن النموذج ممنوع يحسب.

## 6. طريقة استدعاء الـ API
**الطلب 1 — اختيار الأداة** `POST /select_tool`
```json
{"question": "كم فرع عندنا في جدة؟", "history": []}
```
الرد: `{"type":"tool","tool":"branches_count","args":{"city":"جدة"}}`
أو (توضيح/رفض): `{"type":"reply","text":"تبغى النتيجة لأي فترة؟","options":["آخر أسبوع","آخر شهر","آخر 3 شهور"]}`
لما المستخدم يضغط خيار، الواجهة ترسله كسؤال جديد مع `history` (آخر رسائل المحادثة).

**الطلب 2 — صياغة الجواب** `POST /compose_answer`
```json
{"question": "كم فرع عندنا في جدة؟", "tool": "branches_count", "result": {"count": 2}}
```
الرد: `{"text": "عندك فرعين في جدة."}`
(لأداة `comments_get` الرد يتضمن الملخص + نسب المشاعر + المواضيع.)

```python
import requests
BASE = "https://<space-url>"
sel = requests.post(f"{BASE}/select_tool", json={"question": "كم فرع عندنا في جدة؟", "history": []}).json()
if sel["type"] == "tool":
    result = my_backend_execute(sel["tool"], sel["args"])   # الباك ينفذ الأداة
    ans = requests.post(f"{BASE}/compose_answer",
                        json={"question": "كم فرع عندنا في جدة؟", "tool": sel["tool"], "result": result}).json()
    print(ans["text"])
else:
    print(sel["text"], sel.get("options"))
```

## 7. البرومبتات
النص الكامل في `prompts.py`. **اكتبوا هنا النص ولماذا اخترتوه.** أهم قرارات التصميم في الكود:
- التحقق من المدخلات في الكود (`validate_call`): مدخل إجباري ناقص ← يسأل توضيح بدل التخمين، وقيمة غلط ← تنصلح أو تنحذف.
- كلام النموذج الحر في خطوة اختيار الأداة **ما يوصل للمستخدم** أبدًا (ممكن يكون جواب مخترع).
- فحص الأرقام: لو الجواب فيه رقم مو في نتيجة الأداة ← إعادة توليد مرة، وبعدها نعرض النتيجة الخام.
- نسب المشاعر يحسبها الكود من التصنيفات.

## 8. نتائج التقييم والقيود المعروفة
الصقوا هنا جدول `results/metrics.json` وأمثلة من `results/errors.csv` مع نوع الخطأ وطريقة الإصلاح.
القيود: فحص الجواب النهائي في `evaluate.py` تقريبي (يتأكد من الحقائق الأساسية وغياب الأرقام المخترعة) فراجعوا الأخطاء يدويًا؛
البيانات وهمية؛ والواجهة الحالية تدعم سؤال/جواب مع history قصير.
