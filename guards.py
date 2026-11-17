"""
حراس الكود: القواعد اللي ما نتركها للنموذج.
- فهم الفترة من نص السؤال (عشان ما يخمّن النموذج الفترة)
- تنظيف المدخلات الاختيارية اللي ما ذكرها المستخدم (sort / limit / period)
- مطابقة تقريبية لأسماء الفروع والخدمات والمدن مع قائمة النظام
"""
import difflib
import re

from utils import norm_ar

# كلمات الفترة الزمنية (بعد norm_ar). "آخر" وحدها لا تكفي: "لخص لي آخر التعليقات" بدون فترة.
_PERIOD_RE = re.compile(r"اسبوع|اسابيع|شهر|شهور|اشهر|ربع")

# كلمات الترتيب (أعلى/أفضل/أقل/أضعف/رتب...)
_RANK_RE = re.compile(r"اعل[يىا]|افضل|احسن|اقل|اضعف|اسو|ادني|رتب|ترتيب")
_BOTTOM_RE = re.compile(r"اقل|اضعف|اسو|ادني")
_LIST_RE = re.compile(r"رتب|ترتيب")

# عدد مطلوب ("أفضل ثلاث خدمات")، ونستثني "ثلاث شهور" لأنها فترة مو عدد
_COUNT_RE = re.compile(r"(\d+|ثلاث[ه]?|اثن[يا]ن|اربع[ه]?|خمس[ه]?|عشر[ه]?)(?!\s*(?:شهور|اشهر|اسابيع|ايام|%))")
_COUNT_WORDS = {"ثلاث": 3, "ثلاثه": 3, "اثنين": 2, "اثنان": 2, "اربع": 4, "اربعه": 4,
                "خمس": 5, "خمسه": 5, "عشر": 10, "عشره": 10}


def has_period_words(text) -> bool:
    return bool(_PERIOD_RE.search(norm_ar(text)))


def _count_in(text):
    for m in _COUNT_RE.finditer(norm_ar(text)):
        tok = m.group(1)
        n = int(tok) if tok.isdigit() else _COUNT_WORDS.get(tok)
        if n:
            return n
    return None


def sanitize_args(name, args, question):
    """يحذف المدخلات الاختيارية اللي النموذج أضافها من عنده، ويكمل limit لـ'أعلى/أضعف' المفردة."""
    out = dict(args)
    q = norm_ar(question)
    if "sort" in out or name in ("ratings_service_get", "ratings_branch_get"):
        if not _RANK_RE.search(q):
            out.pop("sort", None)
            out.pop("limit", None)
        else:
            out.setdefault("sort", "bottom" if _BOTTOM_RE.search(q) else "top")
            n = _count_in(question)
            if n:
                out["limit"] = n
            elif _LIST_RE.search(q):
                out.pop("limit", None)
            else:
                out["limit"] = 1
    if name == "demographics_get" and "period" in out and not has_period_words(question):
        out.pop("period")
    if name == "comments_get":
        out.pop("limit", None)
    return out


def match_name(value, names, cutoff=0.75):
    """يرجع الاسم الصحيح من القائمة (بدون كلمة فرع). لو ما فيه تشابه كافٍ يرجع القيمة كما هي."""
    canon = {norm_ar(re.sub(r"^فرع\s+", "", n)): re.sub(r"^فرع\s+", "", n) for n in names}
    key = norm_ar(re.sub(r"^فرع\s+", "", str(value).strip()))
    if key in canon:
        return canon[key]
    close = difflib.get_close_matches(key, list(canon), n=1, cutoff=cutoff)
    return canon[close[0]] if close else str(value).strip()


def fix_names(args, catalog):
    if not catalog:
        return args
    pools = {"branch": catalog.get("branches", []), "service": catalog.get("services", []),
             "city": catalog.get("cities", [])}
    return {k: (match_name(v, pools[k]) if k in pools and pools[k] else v) for k, v in args.items()}
