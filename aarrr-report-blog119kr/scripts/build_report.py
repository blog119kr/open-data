#!/usr/bin/env python3
"""AARRR 리포트 빌더.

GA4 조회 결과(results.json)와 설정(config.json)을 받아
assets/template.html에 데이터를 채운 HTML 리포트를 만든다.

사용법:
    python3 scripts/build_report.py config.json results.json out.html

- results.json의 행은 snake_case(예: active_users, 일부 MCP·빅쿼리 템플릿)나
  GA4 Data API 형식(camelCase, 예: activeUsers) 모두 받는다.
- 수치는 손으로 옮기지 말고 조회 결과를 그대로 저장해 이 스크립트로 집계한다.
"""
import datetime
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "template.html"

# GA4 Data API(camelCase) → 이 스크립트가 쓰는 이름
ALIASES = {
    "activeUsers": "active_users", "newUsers": "newusers", "new_users": "newusers",
    "engagedSessions": "engaged_sessions", "averageSessionDuration": "average_session_duration",
    "keyEvents": "conversions", "key_events": "conversions",
    "newVsReturning": "new_vs_returning", "sessionSourceMedium": "session_source_medium",
    "deviceCategory": "devicecategory", "device_category": "devicecategory",
    "pageTitle": "pagetitle", "page_title": "pagetitle", "screenPageViews": "screen_page_views",
    "sessionGoogleAdsCampaignName": "session_google_ads_campaign_name",
    "sessionManualCampaignName": "session_manual_campaign_name",
    "advertiserAdCost": "advertiser_ad_cost",
}
NUM = {"active_users", "newusers", "sessions", "engaged_sessions", "average_session_duration",
       "conversions", "screen_page_views", "advertiser_ad_cost"}


def norm_row(r):
    out = {}
    for k, v in r.items():
        k = ALIASES.get(k, k)
        if k in NUM:
            v = float(v or 0)
        elif k == "date" and isinstance(v, str) and re.fullmatch(r"\d{8}", v):
            v = f"{v[:4]}-{v[4:6]}-{v[6:]}"
        elif isinstance(v, str) and v.strip() == "":
            v = "(not set)"
        out[k] = v
    return out


def load_results(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    res = {}
    for k, v in raw.items():
        rows = v.get("data", v) if isinstance(v, dict) else v
        res[k] = [norm_row(r) for r in (rows or [])]
    return res


def days_between(a, b):
    d0, d1 = datetime.date.fromisoformat(a), datetime.date.fromisoformat(b)
    return [(d0 + datetime.timedelta(i)).isoformat() for i in range((d1 - d0).days + 1)]


def div(a, b):
    return a / b if b else 0


def kpi(t, v, p, f, sp=None, **kw):
    return dict(t=t, v=v, p=p, f=f, sp=sp, **kw)


def build(cfg, R):
    C, P = cfg["cur"], cfg["prev"]
    svc = cfg.get("service")  # {"name","key","title","prefix"} 또는 None
    prefix = (svc or {}).get("prefix", "") or ""
    tot, totP = R["tot"][0], R["totP"][0]
    days = days_between(*C)
    in_cur = lambda d: C[0] <= d <= C[1]

    def dayagg(filt=None):
        m = {d: dict(au=0, s=0, e=0, dw=0, c=0) for d in days}
        for r in R["daily"]:
            if r["date"] in m and (filt is None or r["new_vs_returning"] == filt):
                o = m[r["date"]]
                o["au"] += r["active_users"]; o["s"] += r["sessions"]; o["e"] += r["engaged_sessions"]
                o["dw"] += r["average_session_duration"] * r["sessions"]; o["c"] += r["conversions"]
        for o in m.values():
            o["er"], o["dur"], o["cr"] = div(o["e"], o["s"]), div(o["dw"], o["s"]), div(o["c"], o["s"])
        return [m[d] for d in days]

    dA, dN, dR = dayagg(), dayagg("new"), dayagg("returning")
    er = lambda t: div(t["engaged_sessions"], t["sessions"])

    # ACQUISITION
    by = defaultdict(lambda: {"new": 0, "returning": 0, "(not set)": 0})
    for r in R["src"]:
        nv = r["new_vs_returning"] if r["new_vs_returning"] in ("new", "returning") else "(not set)"
        by[r["session_source_medium"]][nv] += r["sessions"]
    rows = sorted(by.items(), key=lambda x: -sum(x[1].values()))
    bars = [dict(label=k, **v) for k, v in rows[:6]]
    if len(rows) > 6:
        rest = {"new": 0, "returning": 0, "(not set)": 0}
        for _, v in rows[6:]:
            for k in rest:
                rest[k] += v[k]
        bars.append(dict(label="기타", **rest))
    acq = dict(
        kpi=[kpi("세션수", tot["sessions"], totP["sessions"], "int", [x["s"] for x in dA]),
             kpi("활성 사용자", tot["active_users"], totP["active_users"], "int", [x["au"] for x in dA]),
             kpi("새 사용자", tot["newusers"], totP["newusers"], "int", [x["au"] for x in dN]),
             kpi("활성 사용자당 세션", div(tot["sessions"], tot["active_users"]),
                 div(totP["sessions"], totP["active_users"]), "dec",
                 [div(x["s"], x["au"]) for x in dA])],
        bars=bars,
        dev=[dict(k=r["devicecategory"], s=r["sessions"], c=r["conversions"]) for r in R["dev"]])

    # ACTIVATION (인기 페이지는 페이지 제목 기준으로 묶는다)
    pgs = defaultdict(lambda: dict(v=0, u=0))
    for r in R["pg"]:
        o = pgs[r.get("pagetitle", "(not set)")]
        o["v"] += r["screen_page_views"]; o["u"] += r["active_users"]
    pg_sorted = sorted(pgs.items(), key=lambda x: -x[1]["v"])
    act = dict(
        kpi=[kpi("참여율", er(tot), er(totP), "pct", [x["er"] for x in dA]),
             kpi("평균 세션 시간", tot["average_session_duration"], totP["average_session_duration"], "dur",
                 [x["dur"] for x in dA]),
             kpi("주요 이벤트(전환)", tot["conversions"], totP["conversions"], "int", [x["c"] for x in dA]),
             kpi("세션 전환율", div(tot["conversions"], tot["sessions"]),
                 div(totP["conversions"], totP["sessions"]), "pct", [x["cr"] for x in dA])],
        pages=[dict(k=k, v=o["v"], u=o["u"]) for k, o in pg_sorted[:10]],
        pages_total=sum(o["v"] for o in pgs.values()),
        daily=[dict(d=d[5:].replace("-", "/"), s=x["s"], er=x["er"]) for d, x in zip(days, dA)],
        funnel=dict(cur=[tot["sessions"], tot["engaged_sessions"], tot["conversions"]],
                    prev=[totP["sessions"], totP["engaged_sessions"], totP["conversions"]]))

    # RETENTION (returning만)
    empty = dict(active_users=0, sessions=0, engaged_sessions=0, average_session_duration=0, conversions=0)
    rc = next((r for r in R["nvr"] if r["new_vs_returning"] == "returning"), empty)
    rp = next((r for r in R["nvrP"] if r["new_vs_returning"] == "returning"), empty)
    pie = defaultdict(float)
    for r in R["nvr"]:
        pie[r["new_vs_returning"] if r["new_vs_returning"] in ("new", "returning") else "(not set)"] += r["sessions"]
    ret = dict(
        pie=[dict(k=k, s=pie[k]) for k in ("new", "returning", "(not set)")],
        kpi=[kpi("재방문 사용자", rc["active_users"], rp["active_users"], "int", [x["au"] for x in dR]),
             kpi("참여율", er(rc), er(rp), "pct", [x["er"] for x in dR]),
             kpi("평균 세션 시간", rc["average_session_duration"], rp["average_session_duration"], "dur",
                 [x["dur"] for x in dR]),
             kpi("주요 이벤트(전환)", rc["conversions"], rp["conversions"], "int", [x["c"] for x in dR]),
             kpi("세션 전환율", div(rc["conversions"], rc["sessions"]), div(rp["conversions"], rp["sessions"]),
                 "pct", [x["cr"] for x in dR])])

    # REVENUE → CPA (광고비 없으면 세션 주요 이벤트 비율)
    cost = [("google / cpc", r.get("session_google_ads_campaign_name", ""), r) for r in R.get("costG", [])]
    cost += [(r["session_source_medium"], r.get("session_manual_campaign_name", ""), r) for r in R.get("costN", [])]
    cost = [x for x in cost if x[2]["advertiser_ad_cost"] > 0]
    if cost:
        cur, prv = defaultdict(lambda: dict(cost=0, s=0, e=0, c=0)), defaultdict(lambda: dict(cost=0, s=0, e=0, c=0))
        dcost = {d: 0 for d in days}
        for sm, camp, r in cost:
            camp = camp[len(prefix):] if prefix and camp.startswith(prefix) else camp
            o = (cur if in_cur(r["date"]) else prv)[(sm, camp)]
            o["cost"] += r["advertiser_ad_cost"]; o["s"] += r["sessions"]
            o["e"] += r["engaged_sessions"]; o["c"] += r["conversions"]
            if r["date"] in dcost:
                dcost[r["date"]] += r["advertiser_ad_cost"]
        TC = sum(o["cost"] for o in cur.values()); TS = sum(o["s"] for o in cur.values())
        TCc = sum(o["c"] for o in cur.values())
        PC = sum(o["cost"] for o in prv.values()); PCc = sum(o["c"] for o in prv.values())
        avg = TC / TCc if TCc else None
        rr = []
        for (sm, camp), o in cur.items():
            if o["cost"] <= 0:
                continue
            cpa = o["cost"] / o["c"] if o["c"] else None
            po = prv.get((sm, camp))
            pcpa = po["cost"] / po["c"] if po and po["c"] else None
            if cpa is None or (avg and cpa >= avg * 1.5):
                tag = "bad"
            elif avg and cpa <= avg * 0.7:
                tag = "good"
            else:
                tag = "mid"
            rr.append(dict(sm=sm, camp=camp or "(not set)", cost=round(o["cost"]), s=o["s"], er=div(o["e"], o["s"]),
                           c=o["c"], cr=div(o["c"], o["s"]), cpa=cpa,
                           dcpa=(cpa / pcpa - 1) if cpa and pcpa else None, tag=tag))
        rr.sort(key=lambda r: (r["cpa"] is None, r["cpa"] if r["cpa"] is not None else -r["cost"]))
        dsm = defaultdict(float)
        for (sm, _), o in cur.items():
            dsm[sm] += o["cost"]
        rev = dict(
            kpi=[kpi("CPA", avg, (PC / PCc if PCc else None), "won", None, inv=True),
                 kpi("광고비", TC, PC, "won", [dcost[d] for d in days], neutral=True),
                 kpi("광고 전환", TCc, PCc, "int")],
            rows=rr[:10], nrows=len(rr), avg=avg, total=dict(cost=TC, s=TS, c=TCc, cpa=avg),
            donut=[dict(k=k, v=round(v)) for k, v in sorted(dsm.items(), key=lambda x: -x[1]) if v > 0])
        rev_note = "CPA = 광고비 ÷ 광고 전환"
    else:
        def bysm(rows):
            m = defaultdict(lambda: dict(s=0, e=0, c=0))
            for r in rows:
                o = m[r["session_source_medium"]]
                o["s"] += r["sessions"]; o["e"] += r["engaged_sessions"]; o["c"] += r["conversions"]
            return m
        cm, pm = bysm(R["src"]), bysm(R["srcP"])
        rr = []
        for sm, o in cm.items():
            p = pm.get(sm)
            rr.append(dict(sm=sm, s=o["s"], er=div(o["e"], o["s"]), c=o["c"], cr=div(o["c"], o["s"]),
                           dcr=(div(o["c"], o["s"]) - div(p["c"], p["s"])) if p and p["s"] else None))
        rr.sort(key=lambda r: (-r["c"], -r["s"]))
        conv = sorted([(sm, o["c"]) for sm, o in cm.items() if o["c"] > 0], key=lambda x: -x[1])
        donut = [dict(k=k, v=v) for k, v in conv[:5]]
        if len(conv) > 5:
            donut.append(dict(k="기타", v=sum(v for _, v in conv[5:])))
        rev = dict(
            mode="rate",
            kpi=[kpi("세션 주요 이벤트 비율", div(tot["conversions"], tot["sessions"]),
                     div(totP["conversions"], totP["sessions"]), "pct", [x["cr"] for x in dA]),
                 kpi("주요 이벤트(전환)", tot["conversions"], totP["conversions"], "int", [x["c"] for x in dA]),
                 kpi("세션수", tot["sessions"], totP["sessions"], "int", [x["s"] for x in dA])],
            rows=rr[:10], nrows=len(rr),
            total=dict(s=tot["sessions"], er=er(tot), c=tot["conversions"],
                       cr=div(tot["conversions"], tot["sessions"])),
            donut=donut or [dict(k="전환 없음", v=0)])
        rev_note = "광고비 데이터가 없어 세션 주요 이벤트 비율을 표시"

    # REFERRAL (매체 referral 또는 organic)
    isref = lambda sm: bool(re.search(r" / (referral|organic)$", sm or ""))

    def refagg(rows):
        m = defaultdict(lambda: dict(s=0, e=0, dw=0, c=0))
        for r in rows:
            if isref(r["session_source_medium"]):
                o = m[r["session_source_medium"]]
                o["s"] += r["sessions"]; o["e"] += r["engaged_sessions"]
                o["dw"] += r["average_session_duration"] * r["sessions"]; o["c"] += r["conversions"]
        T = dict(s=0, e=0, dw=0, c=0)
        for o in m.values():
            for k in T:
                T[k] += o[k]
        return m, T

    f = lambda T: dict(s=T["s"], er=div(T["e"], T["s"]), dur=div(T["dw"], T["s"]), c=T["c"], cr=div(T["c"], T["s"]))
    rb, rT = refagg(R["src"]); _, rPT = refagg(R["srcP"])
    fc, fp = f(rT), f(rPT)
    ref = dict(
        kpi=[kpi("세션수", fc["s"], fp["s"], "int"), kpi("참여율", fc["er"], fp["er"], "pct"),
             kpi("평균 세션 시간", fc["dur"], fp["dur"], "dur"), kpi("주요 이벤트(전환)", fc["c"], fp["c"], "int"),
             kpi("세션 전환율", fc["cr"], fp["cr"], "pct")],
        rows=[dict(sm=k, **f(o)) for k, o in sorted(rb.items(), key=lambda x: -x[1]["s"])[:10]],
        nrows=len(rb), total=fc)

    # 메타
    name = cfg.get("property_name") or cfg.get("property_id", "GA4")
    block_date = cfg.get("block_date")
    blocked = bool(block_date and P[0] < block_date)
    if svc:
        label = f"{name} · {svc['name']} ({svc.get('key', '')})"
        page_note = f"페이지 제목에 '{svc['title']}' 포함, 조회수 3 이상" if svc.get("title") else "조회수 3 이상"
        svc_line = f"서비스 필터: 방문 페이지·캠페인에 '{svc.get('key', '')}' 포함"
    else:
        label, page_note, svc_line = f"{name} · total", "조회수 3 이상", "서비스 구분 없음(total)"
    footer = [
        f"속성: {name}" + (f" (GA4 {cfg['property_id']})" if cfg.get("property_id") else "") + f" · {svc_line}",
        f"조회 기간: {C[0]} ~ {C[1]} (KST) · 비교 기간: {P[0]} ~ {P[1]}",
        f"전환 = 주요 이벤트(purchase) · {rev_note} · REFERRAL = 세션 매체 referral 또는 organic",
        "재방문(returning) 항목은 빨간색으로 표시합니다.",
    ]
    return dict(
        label=label, cur=list(C), prev=list(P), asof=cfg.get("asof", datetime.date.today().isoformat()),
        blocked=blocked,
        blockNote=f"{cfg.get('block_reason', '비교 불가 기준일')}({block_date})" if blocked else "",
        prefix=prefix, pageNote=page_note, footer=footer,
        acq=acq, act=act, ret=ret, rev=rev, ref=ref)


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    cfg = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    D = build(cfg, load_results(sys.argv[2]))
    title = f"{cfg.get('property_name', '')} · {(cfg.get('service') or {}).get('name', 'total')} AARRR 리포트".strip(" ·")
    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("__TITLE__", title).replace(
        "__DATA__", json.dumps(D, ensure_ascii=False).replace("</", "<\\/"))
    Path(sys.argv[3]).write_text(html, encoding="utf-8")
    print(f"wrote {sys.argv[3]} (rev mode: {D['rev'].get('mode', 'cpa')}, blocked: {D['blocked']})")


if __name__ == "__main__":
    main()
