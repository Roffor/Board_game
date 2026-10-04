import json, sys
R = [r for r in json.load(open(sys.argv[1])) if 'error' not in r]
err = sum(1 for r in json.load(open(sys.argv[1])) if 'error' in r)
by = {}
for r in R: by.setdefault(r['v'], {}).setdefault(r['sit'], []).append(r)
m = lambda x: sum(x) / len(x)
print('ошибок', err, '| коридоры: I 3.5–4 / 8–15%, II 3–3.5 / 5–12%, EL 4–6 / 20–35%, BOSS 5–8 / 30–60%')
for v in sorted(by):
    print(v, '  '.join(f"{s}: {m([x['rounds'] for x in d]):.2f}р {m([x['taken'] for x in d])/40*100:.0f}% в{m([x['won'] for x in d]):.2f} пр{sum(x['stuck'] for x in d)}"
                        for s, d in sorted(by[v].items(), key=lambda kv: ['I','II','EL','BOSS'].index(kv[0]))))
