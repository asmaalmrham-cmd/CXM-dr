"""
دوال بايثون بسيطة تنفّذ الأدوات على البيانات الوهمية.
هذي مو الباك: هذي بيئة اختبار لكم. فريق الباك ينفذ نفس المواصفات (tools_spec.py) على قاعدة البيانات الحقيقية.
"""
import json
import re
from functools import lru_cache

import pandas as pd

from config import DATA_DIR, PERIOD_DAYS, REF_DATE
from utils import norm_ar


def _n(s):
    s = norm_ar(s)
    return re.sub(r"^(فرع|مدينه)\s+", "", s)


def _same(a, b):
    a, b = _n(a), _n(b)
    return bool(a) and bool(b) and (a == b or a in b or b in a)


@lru_cache(maxsize=1)
def _data():
    b = pd.read_csv(DATA_DIR / "branches.csv")
    s = pd.read_csv(DATA_DIR / "services.csv")
    bb = b.rename(columns={"id": "branch_id", "name": "branch", "city": "branch_city", "status": "branch_status"})
    ss = s.rename(columns={"id": "service_id", "name": "service"})
    r = pd.read_csv(DATA_DIR / "responses.csv", parse_dates=["date"]).merge(bb, on="branch_id").merge(ss, on="service_id")
    r["age_group"] = pd.cut(r["age"], [0, 24, 34, 44, 54, 200], labels=["18-24", "25-34", "35-44", "45-54", "55+"]).astype(str)
    c = pd.read_csv(DATA_DIR / "comments.csv", parse_dates=["date"]).merge(bb, on="branch_id")
    return b, s, r, c


def catalog():
    b, s, _, _ = _data()
    return {"services": s["name"].tolist(), "branches": b["name"].tolist(), "cities": sorted(b["city"].unique())}


def _period(df, period):
    end = pd.Timestamp(REF_DATE)
    start = end - pd.Timedelta(days=PERIOD_DAYS[period])
    return df[(df["date"] > start) & (df["date"] <= end)]


def _filter(df, col, value):
    if not value:
        return df
    return df[df[col].map(lambda x: _same(x, value))]


def _records(df):
    return json.loads(df.to_json(orient="records", force_ascii=False))


NO_DATA = {"error": "لا توجد بيانات مطابقة"}


def _rank(df, by, sort, limit):
    g = df.groupby(by).agg(avg=("rating", "mean"), responses=("rating", "size")).reset_index()
    g["avg"] = g["avg"].round(2)
    g = g.sort_values(["avg", "responses"], ascending=[sort == "bottom", False])
    if limit:
        g = g.head(int(limit))
    return _records(g)


# ------------------------------ الأدوات ------------------------------
def branches_count(city=None, status=None):
    b = _data()[0]
    if city:
        b = b[b["city"].map(lambda x: _same(x, city))]
    if status:
        b = b[b["status"] == status]
    return {"count": int(len(b))}


def branches_list(city=None, status=None):
    b = _data()[0]
    if city:
        b = b[b["city"].map(lambda x: _same(x, city))]
    if status:
        b = b[b["status"] == status]
    return {"count": int(len(b)), "branches": _records(b[["name", "city", "status"]])}


def services_list():
    s = _data()[1]
    return {"count": int(len(s)), "services": s["name"].tolist()}


def ratings_service_get(period, service=None, sort=None, limit=None):
    df = _filter(_period(_data()[2], period), "service", service)
    return _rank(df, "service", sort, limit) if len(df) else NO_DATA


def ratings_branch_get(period, city=None, sort=None, limit=None):
    df = _filter(_period(_data()[2], period), "branch_city", city)
    return _rank(df, "branch", sort, limit) if len(df) else NO_DATA


def ratings_overall(period, branch=None, service=None):
    df = _filter(_filter(_period(_data()[2], period), "branch", branch), "service", service)
    if not len(df):
        return NO_DATA
    return {"avg": round(float(df["rating"].mean()), 2), "responses": int(len(df))}


def responses_count(period, branch=None, service=None):
    df = _filter(_filter(_period(_data()[2], period), "branch", branch), "service", service)
    return {"count": int(len(df))}


def demographics_get(dimension, period=None):
    df = _data()[2]
    if period:
        df = _period(df, period)
    col = {"age_group": "age_group", "gender": "gender", "city": "respondent_city"}[dimension]
    if not len(df):
        return NO_DATA
    vc = df[col].value_counts()
    total = int(vc.sum())
    return {"dimension": dimension, "total": total,
            "distribution": [{"group": k, "count": int(v), "pct": round(100 * v / total, 1)} for k, v in vc.items()]}


def ratings_trend(service=None, branch=None):
    df = _filter(_filter(_data()[2], "service", service), "branch", branch)
    end = pd.Timestamp(REF_DATE)
    labels = ["آخر 30 يومًا", "من 30 إلى 60 يومًا مضت", "من 60 إلى 90 يومًا مضت"]
    out = []
    for i, label in enumerate(labels):
        w = df[(df["date"] > end - pd.Timedelta(days=30 * (i + 1))) & (df["date"] <= end - pd.Timedelta(days=30 * i))]
        if len(w):
            out.append({"window": label, "avg": round(float(w["rating"].mean()), 2), "responses": int(len(w))})
    return out or NO_DATA


def comments_get(period, branch=None, limit=None):
    df = _filter(_period(_data()[3], period), "branch", branch).sort_values("date", ascending=False)
    df = df.head(int(limit) if limit else 100)
    if not len(df):
        return NO_DATA
    df = df.assign(date=df["date"].dt.strftime("%Y-%m-%d"))
    return _records(df[["text", "date", "branch"]])


TOOL_FUNCS = {f.__name__: f for f in (
    branches_count, branches_list, services_list, ratings_service_get, ratings_branch_get,
    ratings_overall, responses_count, demographics_get, ratings_trend, comments_get)}


def execute_tool(name, args):
    fn = TOOL_FUNCS.get(name)
    if fn is None:
        return {"error": f"أداة غير معروفة: {name}"}
    clean = {k: v for k, v in (args or {}).items() if v not in (None, "")}
    try:
        return fn(**clean)
    except Exception as e:  # الباك الحقيقي لازم يرجع أخطاء بنفس الشكل
        return {"error": str(e)}
