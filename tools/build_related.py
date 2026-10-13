"""Regenerate data/related.json (the "More Strange Stories" links).

Run from the repo root after adding or removing a post:   python tools/build_related.py

Relatedness = curated topic clusters (edit CL below) + TF-IDF text similarity as a tiebreaker.
A post with no entry falls back to the three newest stories of the same type (see
themes/weirdstl/layouts/partials/related.html). Event posts that will expire go in EX so
nothing recommends a page that is about to be deleted.
"""
import re, glob, json, math, collections

STOP = set("""a about above after again all also am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have having he her
here hers him his how i if in into is it its just me more most my no nor not of off on once only or other our out
over own same she should so some such than that the their theirs them then there these they this those through to
too under until up very was we were what when where which while who whom why will with would you your st louis
louis's missouri one two three first new old year years city town like even still never ever made make makes many
much may might get got goes go went said says say way thing things time times day days back around across along
whole another every less least though yet""".split())

# Topic clusters: "section/slug" of each post. Stories sharing a cluster rank first.
CL = {
    "lemp": ["historical/lemp-mansion", "posts/lemp-mansion-ghosts", "posts/elsa-lemp-case", "posts/cherokee-cave"],
    "exorcist": ["historical/exorcist-house", "posts/the-exorcist-house-st-louis", "posts/PhysicistWhoWalkedIntoTheExorcist"],
    "fair1904": ["posts/1904-worlds-fair-x-rays", "historical/world-fair-ice-cream-cone", "posts/1904-olympic-marathon-disaster", "posts/river-under-forest-park"],
    "courthouse": ["posts/old-courthouse-last-slave-auction", "posts/old-courthouse-reopens", "posts/mill-creek-valley"],
    "haunted": ["historical/zombie-road", "current/bubblehead-road", "posts/lemp-mansion-ghosts", "posts/alton-confederate-prison", "posts/carrie-seib-psychic", "posts/the-exorcist-house-st-louis", "posts/saxtown-murders"],
    "death": ["posts/bellefontaine-living-gothic", "posts/wind-phones-st-louis-cemeteries", "posts/mcdowell-mad-doctor-st-louis", "posts/mound-72-cahokia"],
    "crime": ["posts/saxtown-murders", "posts/tumblety", "posts/elsa-lemp-case", "posts/WhereStLouisGangstersPracticedShooting", "posts/bloody-island-benton-lucas"],
    "vanished": ["posts/chouteaus-pond", "posts/mill-creek-valley", "posts/cherokee-cave", "posts/river-under-forest-park", "posts/benton-park-lake-sinkholes", "posts/mullanphy-emigrant-home"],
    "across_river": ["posts/alton-confederate-prison", "posts/robert-wadlow-alton-giant", "posts/saxtown-murders", "posts/mound-72-cahokia", "posts/bloody-island-benton-lucas"],
    "civilwar_slavery": ["posts/old-courthouse-last-slave-auction", "posts/alton-confederate-prison", "posts/mcdowell-mad-doctor-st-louis", "posts/mill-creek-valley"],
    "grand_buildings": ["posts/hotel-jefferson-gold-room-history", "posts/spanish-pavilion-hotel", "posts/old-courthouse-reopens", "posts/the-machine-that-pressed-st-louis"],
    "disasters": ["posts/the-great-fire-of-1849", "posts/2025-tornado-north-st-louis", "posts/benton-park-lake-sinkholes"],
    "20th_century_oddities": ["posts/when-st-louis-got-first-car-phone", "posts/escape-from-new-york-st-louis", "posts/monkeys-north-st-louis", "posts/spanish-pavilion-hotel", "posts/the-machine-that-pressed-st-louis"],
    "busch_brewing_wealth": ["posts/grants-farm-history", "posts/the-machine-that-pressed-st-louis", "posts/lemp-mansion-ghosts", "historical/lemp-mansion"],
    "south_city_names": ["posts/how-dogtown-got-its-name", "posts/chouteaus-pond", "posts/mullanphy-emigrant-home"],
    "now_news": ["posts/six-flags-mid-america-rebrand", "posts/one-vote-election-2026", "posts/2025-tornado-north-st-louis", "posts/monkeys-north-st-louis", "posts/benton-park-lake-sinkholes"],
}
# Event pages are skipped entirely above (they live in content/events and expire on their own).
EX = set()

docs, titles = {}, {}
for f in sorted(glob.glob("content/*/*.md")):
    if f.endswith("_index.md"):
        continue
    t = open(f, encoding="utf-8").read().replace("\r\n", "\n")
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    if not m:
        continue
    fm, body = m.group(1), t[m.end():]
    p = f.replace("\\", "/").split("/")
    if p[1] == "events":  # events expire and live in their own section
        continue
    key = "%s/%s" % (p[1], p[2][:-3])
    mt = re.search(r"^title:\s*(.+)$", fm, re.M)
    if not mt:
        continue
    title = mt.group(1).strip().strip("'\"")
    titles[key] = title
    text = (title + " ") * 3 + re.sub(r"[*_#>\[\]()`]", " ", body)
    docs[key] = collections.Counter(w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOP and len(w) > 2 and not w.isdigit())

for c, ks in CL.items():
    for k in ks:
        if k not in docs:
            print("WARNING: cluster %r lists %s, which no longer exists" % (c, k))

N = len(docs)
df = collections.Counter()
for c in docs.values():
    for w in c:
        df[w] += 1

def vec(c):
    v = {w: (1 + math.log(n)) * math.log(N / df[w]) for w, n in c.items() if df[w] <= N * 0.4}
    nrm = math.sqrt(sum(x * x for x in v.values())) or 1
    return {w: x / nrm for w, x in v.items()}

V = {k: vec(c) for k, c in docs.items()}

def cos(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(w, 0) for w, x in a.items())

member = collections.defaultdict(set)
for c, ks in CL.items():
    for k in ks:
        member[k].add(c)

out = {}
for k in V:
    sc = []
    for j in V:
        if j == k or j in EX:
            continue
        shared = len(member[k] & member[j])
        s = cos(V[k], V[j])
        if shared or s >= 0.12:
            sc.append((1.0 * shared + s, j))
    sc.sort(reverse=True)
    out[k] = [j for _, j in sc[:3]]

json.dump(out, open("data/related.json", "w"), indent=1)
print("wrote data/related.json for %d posts" % len(out))
unclustered = [titles[k] for k in V if not member[k]]
if unclustered:
    print("posts in no cluster (text similarity only):")
    for t in unclustered:
        print("  -", t)
