# Checks the lighter image copies: every copy listed in issue.json exists, is narrower than or equal to the original,
# the built page offers it through srcset, and the plain src is never the heavy original when a lighter copy exists.
import json, os, re, glob
root = os.path.join(os.path.dirname(__file__), '..')
ok = fail = 0
def check(name, cond):
    global ok, fail
    print(('PASS ' if cond else 'FAIL ') + name); ok += cond; fail += (not cond)
bad = []; made = 0; total = 0
for f in sorted(glob.glob(os.path.join(root, 'issues', '*', 'issue.json'))):
    d = os.path.dirname(f); slug = os.path.basename(d); meta = json.load(open(f))
    y, w = slug.split('-w'); html = open(os.path.join(root, 'dist', y, f'week-{int(w)}', 'index.html')).read()
    for i, im in enumerate(meta['images']):
        total += 1
        v = [im[k] for k in ('m', 'l') if k in im]
        if not v: continue
        made += 1
        for x in v:
            if not os.path.exists(os.path.join(d, x['file'])) or x['w'] > im['w'] or os.path.getsize(os.path.join(d, x['file'])) >= os.path.getsize(os.path.join(d, im['file'])): bad.append((slug, i + 1, 'copy'))
            if f'/{x["file"]} {x["w"]}w' not in html: bad.append((slug, i + 1, 'srcset'))
        if f'src="/{y}/week-{int(w)}/{im["file"]}"' in html: bad.append((slug, i + 1, 'heavy src'))
check(f'lighter copies are valid and used ({made} of {total} images have them)', not bad and made > 300)
if bad: print(bad[:10])
print(f'{ok}/{ok + fail} passed'); raise SystemExit(1 if fail else 0)
