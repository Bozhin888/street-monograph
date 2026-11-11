"""Parse the monograph draft (plain text from pandoc) into structured JSON."""
import json, re, sys, unicodedata

SRC = sys.argv[1]
OUT = sys.argv[2]
raw = open(SRC, encoding="utf-8").read()

# ---------- targeted fixes for drafting artifacts (exact strings) ----------
FIXES = [
    ("Gallery+2International Center of Photography+2", ""),
    (", echoing your analytic lens of the monograph.", "."),
    ("shaped so many of the voices in your earlier chapters", "shaped so many of the voices in earlier chapters"),
    ("Books such as Grim Street (1973) and True Color LES America? — sorry, remaining only black and white — positioned him",
     "Books such as Grim Street positioned him"),
    ("and the digital-era Instagram axis you later chapters will inhabit.", "and the digital-era Instagram generation of later chapters."),
    ("he mapped NYC, Tokyo, Tokyo?—only once—Tokyo, London, and Haiti", "he mapped NYC, Tokyo, London, and Haiti"),
    ("joyful accidents across MKD? only once – across Paris, Milan, and Manhattan during assignments.",
     "joyful accidents across Paris, Milan, and Manhattan during assignments."),
    ("across England and Europe during MKD? only once – during Paris and Manchester visits.",
     "across England and Europe, including Paris and Manchester visits."),
    ("His clandestine faces of Roma/Gypsies? — sorry, remaining respectful terminology — and the monumental streets",
     "His faces of Roma communities and the monumental streets"),
    ("shaping Franklin and Depression lineage? sorry discipline.", "shaping later documentary discipline."),
    ("influence on newer documentary observers inside threedots? not.", "influence on newer documentary observers."),
    ("Haiti Trip Fragments — 1986? — sorry — 2000s", "Haiti Trip Fragments — 2000s"),
    ("Black photographed also in Mexico, the U.S.-Albania migration dialogue?—sorry, establishing consistency—U.S.–Mexico border towns",
     "Black photographed also in Mexico and U.S.–Mexico border towns"),
    ("Pages from We Are Like Air — sorry title uncertain — sequencing 2010s", "Pages from We Are Like Air — 2010s"),
    ("Pages from Old World New Essays? — sorry title uncertain — 2020 sequencing", "Pages from Old World New Essays — 2020"),
    ("born in 1988 in the United Kim States?—sorry typo—in the United States", "born in 1988 in the United States"),
    ("influencing Bacani, Saguy, Saguy?—sorry.", "influencing Bacani and Saguy."),
    ("Books without captions? Kim usually photographs", "Kim usually photographs"),
    ("Bruce Bruce Gilden", "Bruce Gilden"),
    ("Steven Steven John Irby", "Steven John Irby"),
    ("Rui Rui Palha", "Rui Palha"),
    ("Mark Ellen Mark", "Mary Ellen Mark"),
    ("Xyza Cruz Bac John Irby", "Xyza Cruz Bacani and Steven John Irby"),
    ("Richard Weber Irby", "Matt Weber, Steven John Irby"),
    ("unobtr unobtrusive", "unobtrusive"),
    ("closer closer", "closer"),
    ("rather rather", "rather"),
    ("Garin Gardin", "Berengo Gardin"),
    ("Drake Heath", "Dave Heath"),
    ("connected At Bravo and Leiter polyphony", "connected Atget, Bravo and Leiter"),
    ("He connected Bravo Parr Atget Atget across oceans", "He connected Bravo, Parr and Atget across oceans"),
    ("later echoed by Depardon and Depardon workflows", "later echoed by Depardon"),
    ("such as Saguy, Saguy and Balkan observers", "such as Saguy and Balkan observers"),
    ("By photographing Okinawa and Okinawa squares", "By photographing Hiroshima and Okinawa squares"),
    ("Caracas, Port-au-Prince, Istanbul, and Caracas again became", "Caracas, Port-au-Prince, and Istanbul became"),
    ("influence on newer observers such Strauss lineage", "influence on newer observers such as Strauss"),
    ("influence on newer observers such Parr and Strauss", "influence on newer observers such as Parr and Strauss"),
    ("Moving essay lovers later influenced by Cooper and Cooper Parks.", "Moving essay later echoed by Cooper and Parks."),
    ("Street as evidence Miller later echoed Depardon.", "Street as evidence later echoed by Depardon."),
    ("later echoed by Martin Parr and Product League historians", "later echoed by Martin Parr and Photo League historians"),
    ("how later PMs of photography fused film", "how later photographers fused film"),
    ("Instagram screens and enable/disable apps allowed his archive", "Instagram and other apps allowed his archive"),
    ("Enable/disable screens of apps allowed her archive", "Apps allowed her archive"),
    ("autonomy of the subject before metrics segmentation cohort Depardon pipeline later echoed.", "autonomy of the subject."),
    ("treating the photobook as infrastructure rather than as segmentation cohort.", "treating the photobook as infrastructure."),
    ("Impact biography points: portable camera craft, ethics of the ordinary, and photobook sequencing as chapters of behavior.\n", ""),
    ("Cultural influence..", "Cultural influence."),
    ("Magnum institutional influence..", "Magnum institutional influence."),
    ("in the digital era..", "in the digital era."),
    ("with restraint.**", "with restraint."),
    ("Czechoslovakia in Boskovice region and", "Czechoslovakia, and"),
]
for a, b in FIXES:
    if a not in raw:
        print("FIX NOT FOUND:", a[:70], file=sys.stderr)
    raw = raw.replace(a, b)

lines = raw.split("\n")

def norm_ws(s):
    return re.sub(r"\s+", " ", s).strip()

def dashes(s):
    """House style: hyphens instead of em dashes in prose."""
    s = re.sub(r"\s*—\s*", " - ", s)
    return s

CITE = re.compile(r"\s+(International Center of Photography|Gallery|Artsy|Art Institute of Chicago)\s*$")

# ---------- locate parts and chapters ----------
PART_RE = re.compile(r"^Part ([IVX]+) — (.+)$")
heads = []  # (line_index, heading_text)
prev_idx = None
for i, l in enumerate(lines):
    if l.strip() == "Short Bio":
        j = i - 1
        while not lines[j].strip():
            j -= 1
        heads.append(j)
parts = [(i, PART_RE.match(l)) for i, l in enumerate(lines) if PART_RE.match(l)]

def part_at(i):
    cur = None
    for pi, m in parts:
        if pi <= i:
            cur = m.group(1)
    return cur

intro_end = parts[0][0]
intro = [norm_ws(l) for l in lines[1:intro_end] if l.strip()]

chapters = []
bounds = heads + [len(lines)]
for k, h in enumerate(heads):
    end = bounds[k + 1]
    # stop at a Part heading that falls inside
    for pi, _ in parts:
        if h < pi < end:
            end = pi
    block = lines[h:end]
    chapters.append((h, block))

SEC_IMP = re.compile(r"^Importance & Impact")
SEC_KEY = re.compile(r"^Key Photographs")

YEAR_RE = re.compile(
    r"^(?:c\.\s*)?(?:(?:early|mid|late)[\s-]+)?\d{4}s?(?:\s*[–-]\s*(?:(?:early|mid|late)[\s-]+)?(?:\d{2,4}s?|present))?",
    re.I)

PLACES = set("""Paris|New York|New York City|NYC|London|Tokyo|Haiti|Rome|Berlin|Mexico City|Mexico|Harlem|Brooklyn|Bronx|Queens|Chicago|Los Angeles|LA|
Amsterdam|Athens|Lisbon|Mumbai|Budapest|Istanbul|Sarajevo|Sofia|Bucharest|Skopje|Albania|Venice|Milan|Italy|Spain|Ireland|Dublin|Glasgow|
Prague|Zürich|Zurich|Lucerne|Kraków|Oslo|Naples|Westminster|Memphis|Greenwood, Mississippi|New Orleans|Albuquerque|Philadelphia|Fresno|Tijuana|Juárez|
Kensington|South Philly|Delaware Waterfront|Venice Beach|Santa Monica|Hong Kong|Kowloon|Shinjuku|Osaka|Okinawa|Nagasaki|Hiroshima|Valparaíso|Santiago|Chile|
Havana|Cuba|Rio de Janeiro|El Salvador|Nicaragua|Sahel|Kurdistan|Kabul|Peshawar|Tibet|Jaipur|India|Seattle|Grenada|Turkey|Bosnia|Romania|Kosovo|
Boston|Greece|Epirus, Greece|Charleston|American South|USA South|USA|UK|Hastings|Main Street|Vancouver|Manhattan|Times Square|Provincetown|Wilkes-Barre|
Pennsylvania|Washington Square, NYC|Times Square|Toronto|Bushwick|Belgrade|Moscow|Kyiv|Vilnius|Tbilisi|Georgia|Caracas|Newcastle|Bondi Road|Oxford|
Manchester|Bradford|Cyprus|Delancey Street|Lower East Side|LES|Central|Bronx-like UK|Kalamata|Sydney|Shanghai|Seville|Chartres|Normandy|Ahmedabad""".replace("\n", "").split("|"))

def strip_visit(seg):
    m = re.match(r"^(.*?)\s+(?:Visit|visit|Trip|trip)$", seg)
    return m.group(1) if m else seg

def is_place(seg):
    return strip_visit(seg.strip()) in PLACES

def cap(s):
    return s[:1].upper() + s[1:] if s else s

def clean_title(t):
    t = t.replace("?*", "").replace("*", "").replace("?", "")
    t = re.sub(r"\s+", " ", t).strip(" ;.,")
    return t

def split_item(text):
    """Return (title, year_text, trailing_desc)."""
    text = text.strip().rstrip(";").strip()
    text = CITE.sub("", text)
    # split on em dash (with or without spaces) and spaced en dash
    segs = re.split(r"\s*—\s*|\s+–\s+", text)
    segs = [s.strip() for s in segs if s.strip()]
    yi = None
    for idx in range(1, len(segs)):
        s = segs[idx]
        if YEAR_RE.match(s) or s.lower().startswith("conceptual"):
            yi = idx
            break
    if yi is None:
        return clean_title(" - ".join(segs)), "", ""
    title_segs = segs[:yi]
    ytxt = segs[yi]
    desc = " - ".join(segs[yi + 1:])
    m = YEAR_RE.match(ytxt)
    year = m.group(0).strip() if m else ""
    rest = ytxt[m.end():].strip() if m else ytxt
    # keep a small marker for non-photo notes
    note = ""
    low = ytxt.lower()
    if "recognition" in low:
        note = "recognition"
    elif "conceptual" in low:
        note = "conceptual"
    elif "sequencing" in low:
        note = "sequencing"
    if not year:
        m2 = re.search(r"\d{4}s?", ytxt)
        year = m2.group(0) if m2 else ""
    year = year.replace("-", "–") if re.match(r"^\d{4}-\d", year) else year
    # assemble title
    title_segs = [clean_title(s) for s in title_segs]
    if len(title_segs) == 1:
        title = title_segs[0]
    elif is_place(title_segs[0]) and not is_place(title_segs[-1]):
        place = strip_visit(title_segs[0])
        title = ", ".join(title_segs[1:] + [place])
    elif is_place(title_segs[-1]):
        title = ", ".join(title_segs)
    else:
        title = ": ".join([title_segs[0], ", ".join(title_segs[1:])])
    title = cap(title)
    return title, year, desc.strip(" .") + ("." if desc.strip(" .") else ""), note

def split_item4(text):
    r = split_item(text)
    if len(r) == 3:
        return r[0], r[1], r[2], ""
    return r

ITEM_PREFIX = re.compile(r"^(?:\d+\.\s+|-\s+|•\s*)")

out = []
for h, block in chapters:
    heading = norm_ws(block[0])
    num = None
    m = re.match(r"^(\d+)\.\s+(.*)$", heading)
    if m:
        num = int(m.group(1)); heading = m.group(2)
    part = part_at(h)
    # sections
    texts = block[1:]
    i_imp = next(i for i, l in enumerate(texts) if SEC_IMP.match(l.strip()))
    i_key = next(i for i, l in enumerate(texts) if SEC_KEY.match(l.strip()))
    bio_lines = [l for l in texts[1:i_imp] if l.strip()]
    imp_lines = texts[i_imp + 1:i_key]
    key_lines = texts[i_key + 1:]

    bio = [dashes(norm_ws(CITE.sub("", l))) for l in bio_lines]

    # impact
    impact_intro, impact = [], []
    cur = None
    for l in imp_lines:
        if not l.strip():
            continue
        s = l.rstrip()
        if re.match(r"^\d+\.\s+", s.strip()) or s.strip().startswith("•"):
            body = ITEM_PREFIX.sub("", s.strip()).strip()
            body = CITE.sub("", body).rstrip(";").strip()
            cur = [body, ""]
            impact.append(cur)
        elif s.startswith("    ") and cur is not None:
            cur[1] = (cur[1] + " " + s.strip()).strip()
        else:
            t = norm_ws(s)
            if t.lower() in ("impact points:",):
                continue
            impact_intro.append(t)
    imp_out = []
    for title, text in impact:
        title = CITE.sub("", title)
        if not text:
            # "Title. Rest" on one line, or a lowercase bullet phrase
            if title[:1].islower():
                imp_out.append(["", dashes(cap(title.rstrip(".;")) + ".")])
                continue
            mm = re.match(r"^(.+?[.])\s+(.+)$", title)
            if mm and len(mm.group(1)) < 80:
                imp_out.append([dashes(mm.group(1).rstrip(".")), dashes(mm.group(2))])
            else:
                imp_out.append(["", dashes(title)])
        else:
            imp_out.append([dashes(title.rstrip(".")), dashes(CITE.sub("", text))])
    impact_intro = [dashes(x) for x in impact_intro if not re.search(r"impact points:?$", x)]
    impact_intro = [re.sub(r"\s*(His )?impact points:\s*$", "", x).strip() for x in impact_intro]
    impact_intro = [x for x in impact_intro if x]

    # works
    nonempty = [l for l in key_lines if l.strip()]
    has_prefix = any(ITEM_PREFIX.match(l.strip()) for l in nonempty)
    works, preface = [], []
    curw = None
    for l in nonempty:
        s = l.strip()
        if has_prefix:
            if ITEM_PREFIX.match(s):
                body = ITEM_PREFIX.sub("", s)
                t, y, d, note = split_item4(body)
                curw = {"t": t, "y": y, "d": d, "n": note}
                works.append(curw)
            elif curw is None:
                preface.append(norm_ws(s))
            else:
                curw["d"] = (curw["d"] + " " + norm_ws(s)).strip()
        else:
            t, y, d, note = split_item4(s)
            works.append({"t": t, "y": y, "d": d, "n": note})
    for w in works:
        w["d"] = dashes(w["d"])
        w["t"] = w["t"].replace("“", "“").strip()

    out.append({
        "order": len(out), "num": num, "part": part, "heading": heading,
        "bio": bio, "impactIntro": impact_intro, "impact": imp_out,
        "worksPreface": preface, "works": works,
    })

json.dump({"intro": [dashes(x) for x in intro], "parts": {m.group(1): m.group(2) for _, m in parts}, "chapters": out},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out), "chapters")
