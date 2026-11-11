"""Fact-checked build: draft text + corrections + rebuilt works -> site/data.js"""
import json, re, sys, os
from collections import defaultdict
sys.path.insert(0, ".")
from meta import M, STATUS, ALIAS
from corrections import C, META_FIX, STATUS_EXTRA
from works import W

d = json.load(open("draft.json", encoding="utf-8"))
CH = d["chapters"]
assert len(CH) == len(M) == 103
UNSURE = {("feinstein","Coke Sign"),("feinstein","Blanket Toss"),("feinstein","125th Street"),("sandler","Grand Central"),("sandler","Two Faces"),
          ("herzog","Jackpot"),("herzog","Curtains"),("bulmer","Mill Girls"),("bulmer","Hartlepool"),("boogie","Sao Paulo"),("boogie","A Wah Do Dem"),
          ("fanho","Journey to Uncertainty"),("fanho","A Day Is Done"),("fanho","Hong Kong Venice"),("fanho","Private"),("eisenstaedt","Premiere at La Scala"),
          ("eisenstaedt","Nurses"),("levinstein","Fifth Avenue"),("levinstein","Handball"),("kalvar","Woman Looking"),("kalvar","Piazza della Rotonda"),
          ("schaller","Metropolis"),("weber","Street Trip"),("genthe","Steps That Lead"),("heath","Elevated in Brooklyn"),("parke","Moving Bus"),
          ("economopoulos","Lignite"),("economopoulos","On the Road"),("eskenazi","The Black Garden"),("eskenazi","Departure Lounge"),("lepkoff","Vermont"),
          ("cohen","Upside Down Girl"),("cohen","Karate Stance"),("strauss","Monique"),("kim","Only in America")}

people, log = [], []
for c, m in zip(CH, M):
    pid, name, short, born, died, place, streets, pal, appr, lede = m
    p = {"id": pid, "name": name, "short": short, "born": born, "died": died, "place": place, "streets": streets,
         "palette": pal, "approach": appr, "lede": lede, "part": c["part"], "num": c["num"], "order": c["order"],
         "bio": [b for b in c["bio"] if b.strip() != "Short Bio"], "impactIntro": c["impactIntro"], "impact": c["impact"],
         "status": STATUS.get(pid, "") or STATUS_EXTRA.get(pid, ""), "bq": False}
    p.update(META_FIX.get(pid, {}))
    people.append(p)
byid = {p["id"]: p for p in people}

# apply corrections
def apply(p, old, new):
    n = 0
    def rep(s):
        nonlocal n
        if old in s:
            n += s.count(old); s = s.replace(old, new)
            s = re.sub(r"\s{2,}", " ", s).strip()
        return s
    p["bio"] = [x for x in (rep(b) for b in p["bio"]) if x]
    p["impactIntro"] = [x for x in (rep(b) for b in p["impactIntro"]) if x]
    p["impact"] = [[rep(t), rep(x)] for t, x in p["impact"]]
    return n
seen = defaultdict(int)
for pid, old, new, why in C:
    n = apply(byid[pid], old, new)
    assert n == 1, (pid, old[:50], n)
    if why.startswith("See above") or why in ("Publication year corrected.", "Release year corrected.", "Book year corrected."):
        if seen[pid]:
            continue
    seen[pid] += 1
    log.append({"id": pid, "old": old, "new": new, "why": why})

# final sweep for leftovers
for p in people:
    txt = " ".join(p["bio"] + p["impactIntro"] + [a + " " + b for a, b in p["impact"]])
    for bad in ["sorry", "? -", "—"]:
        if bad in txt:
            print("LEFTOVER", p["id"], bad, "|", txt[max(0, txt.find(bad) - 60): txt.find(bad) + 40])

# works
def num_year(y):
    m = re.search(r"(early|mid|late)?[\s-]*(\d{4})(s)?", y or "")
    if not m: return None
    base = int(m.group(2))
    if m.group(3): base += {"early": 2, "mid": 5, "late": 8}.get(m.group(1), 5)
    return base
tot = {"p": 0, "s": 0, "pd": 0}
for p in people:
    ws = []
    for t, y, k, note, cq in W[p["id"]]:
        yn = num_year(y)
        if yn is not None:
            assert yn >= p["born"] + 8, (p["id"], t, y)
            if p["died"] and k == "p": assert yn <= p["died"], (p["id"], t, y)
        w = {"t": t, "y": y, "yn": yn, "k": k, "d": note}
        if cq: w["c"] = cq; tot["pd"] += 1
        if any(p["id"] == a and t.startswith(b) for a, b in UNSURE): w["u"] = 1
        ws.append(w); tot[k] += 1
    p["works"] = ws

# lineage from cross mentions in the corrected text
pats = {}
for p in people:
    pat = ALIAS.get(p["id"]) or (r"\b" + re.escape(p["short"]) + r"\b")
    pats[p["id"]] = re.compile(f"(?:{pat})|(?:{re.escape(p['name'])})")
def ctext(p):
    parts = list(p["bio"]) + list(p["impactIntro"])
    for t, x in p["impact"]: parts += [t, x]
    for w in p["works"]: parts += [w["d"]]
    return "\n".join(parts)
mentions = defaultdict(int)
for a in people:
    txt = ctext(a)
    for b in people:
        if a is b: continue
        n = len(pats[b["id"]].findall(txt))
        if n: mentions[(a["id"], b["id"])] += n
older = lambda x, y: (x["born"], x["order"]) < (y["born"], y["order"])
frm = defaultdict(lambda: defaultdict(int)); to = defaultdict(lambda: defaultdict(int)); cited = defaultdict(set)
for (a, b), n in mentions.items():
    cited[b].add(a)
    if older(byid[b], byid[a]): frm[a][b] += n; to[b][a] += n
    else: to[a][b] += n; frm[b][a] += n
for p in people:
    srt = lambda dct: [k for k, _ in sorted(dct.items(), key=lambda kv: (-kv[1], byid[kv[0]]["born"]))]
    p["from"] = srt(frm[p["id"]]); p["to"] = srt(to[p["id"]]); p["citedBy"] = len(cited[p["id"]])

out = {"intro": d["intro"], "parts": {k: v.replace("“", "").replace("”", "") for k, v in d["parts"].items()},
       "people": people, "log": log,
       "stats": {"photos": tot["p"], "series": tot["s"], "pd": tot["pd"], "fixes": len(log), "fixedChapters": len({l["id"] for l in log}), "removed": 1000}}
os.makedirs("site", exist_ok=True)
js = json.dumps(out, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
open("site/data.js", "w", encoding="utf-8").write("window.SM=" + js + ";\n")
print(out["stats"], len(js))
